from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
import database as db
import config as c
import strings as s

def get_str(user_id, key):
    lang = db.get_user_lang(user_id)
    return s.STRINGS.get(lang, s.STRINGS['ar']).get(key, s.STRINGS['ar'].get(key, key))

# Conversation States
WAITING_FOR_PROOF = 1

async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tasks = db.get_available_tasks(user_id)
    
    # Diagnostic logging
    print(f"🔍 User {user_id} requested tasks. Found: {len(tasks)} available tasks.")
    
    if not tasks:
        await update.effective_message.reply_text(get_str(user_id, 'TASKS_MENU_MSG_EMPTY') if 'TASKS_MENU_MSG_EMPTY' in s.STRINGS['ar'] else "✨ **لا توجد مهام متاحة حالياً. تفقدنا لاحقاً!**", parse_mode="Markdown")
        return

    keyboard = []
    for task in tasks:
        # task structure: (id, url, task_type, reward, total_needed, completed_count, status, created_at)
        btn_text = f"🎥 {task[2]} - {task[3]} نقطة"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"task_{task[0]}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.effective_message.reply_text(get_str(user_id, 'TASKS_MENU_MSG'), reply_markup=reply_markup, parse_mode="Markdown")

async def task_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    task_id = int(query.data.split("_")[1])
    task = db.get_task_by_id(task_id)
    
    if not task:
        await query.edit_message_text(get_str(update.effective_user.id, 'TASK_NOT_FOUND'))
        return
        
    context.user_data['current_task_id'] = task_id
    
    lang = db.get_user_lang(update.effective_user.id)
    keyboard = [
        [InlineKeyboardButton(get_str(update.effective_user.id, 'GO_TO_TASK'), url=task[1])],
        [InlineKeyboardButton(get_str(update.effective_user.id, 'SUBMIT_PROOF_BTN'), callback_data=f"submit_{task_id}")]
    ]
    
    await query.edit_message_text(
        get_str(update.effective_user.id, 'TASK_DETAILS_MSG').format(url=task[1], type=task[2], reward=task[3]),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def start_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    task_id = int(query.data.split("_")[1])
    context.user_data['waiting_for_proof'] = task_id
    
    await query.edit_message_text(get_str(update.effective_user.id, 'WAIT_FOR_PROOF'), parse_mode="Markdown")

import os
import vision_ai
import logging

logger = logging.getLogger(__name__)

async def handle_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    task_id = context.user_data.get('waiting_for_proof')
    if not task_id:
        return
        
    user_id = update.effective_user.id
    photo = update.message.photo[-1] # Get highest resolution
    file_id = photo.file_id
    file_unique_id = photo.file_unique_id
    
    # 1. Register submission and check for duplicates
    sub_id = db.submit_proof(user_id, task_id, file_id, file_unique_id)
    
    if sub_id == "ALREADY_SUBMITTED":
        await update.message.reply_text("❌ **لقد أرسلت إثباتاً لهذه المهمة مسبقاً!** انتظر المراجعة.")
        return
    elif sub_id == "DUPLICATE_PHOTO":
        await update.message.reply_text(get_str(user_id, 'DUPLICATE_PHOTO_ERROR') if 'DUPLICATE_PHOTO_ERROR' in s.STRINGS['ar'] else "❌ **هذا الإثبات تم استخدامه من قبل!**", parse_mode="Markdown")
        return
        
    # Clear state
    del context.user_data['waiting_for_proof']
    
    # 2. AI Vision Analysis
    await_msg_text = get_str(user_id, 'AI_VERIFYING') if 'AI_VERIFYING' in s.STRINGS['ar'] else "🔍 **جاري فحص الإثبات بالذكاء الاصطناعي...**"
    status_msg = await update.message.reply_text(await_msg_text, parse_mode="Markdown")
    
    # Download the photo
    try:
        new_file = await photo.get_file()
        path = f"tmp_proof_{user_id}.jpg"
        await new_file.download_to_drive(path)
        
        task = db.get_task_by_id(task_id)
        ai_result = await vision_ai.analyze_screenshot(path, task[2])
        
        # Cleanup file
        if os.path.exists(path):
            os.remove(path)
            
        if ai_result == "PASS":
            # AUTO-APPROVE
            res = db.approve_submission(sub_id)
            if res:
                base_reward = task[3]
                final_reward = base_reward
                
                # VIP Multiplier Logic
                if db.is_vip(user_id):
                    multiplier = float(db.get_setting('vip_multiplier', '2.0'))
                    final_reward = int(base_reward * multiplier)
                    extra = final_reward - base_reward
                    if extra > 0:
                        db.add_points(user_id, extra)
                
                lang = db.get_user_lang(user_id)
                reward_msg = s.STRINGS[lang]['AI_AUTO_APPROVED'].format(reward=final_reward)
                if final_reward > base_reward:
                    reward_msg += f"\n💎 (+{final_reward - base_reward} VIP Bonus!)"
                    
                await status_msg.edit_text(reward_msg, parse_mode="Markdown")
                # Also notify admin of auto-approval
                await context.bot.send_photo(
                    c.ADMIN_ID,
                    photo=file_id,
                    caption=f"✨ **تمت الموافقة التلقائية!**\nعن طريق الذكاء الاصطناعي.\n\n👤 المستخدم: `{user_id}`\n💰 المكافأة: {final_reward}",
                    parse_mode="Markdown"
                )
                return
                
        # If AI is unsure or failed, or auto-approve failed
        await status_msg.edit_text(get_str(user_id, 'PROOF_SUBMITTED'), parse_mode="Markdown")
        
        # Notify Admin with AI suggestion
        ai_label = "❌ لم ينجح" if ai_result == "FAIL" else "❓ غير متأكد"
        admin_keyboard = [
            [InlineKeyboardButton("✅ موافقة", callback_data=f"appr_{sub_id}")],
            [InlineKeyboardButton("❌ رفض", callback_data=f"rejmenu_{sub_id}")]
        ]
        
        await context.bot.send_photo(
            c.ADMIN_ID,
            photo=file_id,
            caption="🚀 **إثبات جديد (AI)**\n\n👤 المستخدم: `{user_id}`\n🔗 الرابط: {url}\n💰 المكافأة: {reward}\n💡 فحص الذكاء الاصطناعي: {ai_suggestion}".format(
                user_id=user_id, 
                url=task[1], 
                reward=task[3],
                ai_suggestion=ai_label
            ),
            reply_markup=InlineKeyboardMarkup(admin_keyboard),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error handling proof: {str(e)}")
        await status_msg.edit_text(get_str(user_id, 'PROOF_SUBMITTED'), parse_mode="Markdown")
        # Notify Admin without AI info
        admin_keyboard = [[InlineKeyboardButton("✅ موافقة", callback_data=f"appr_{sub_id}")], [InlineKeyboardButton("❌ رفض", callback_data=f"rejmenu_{sub_id}")]]
        await context.bot.send_photo(c.ADMIN_ID, photo=file_id, caption="📸 **إثبات جديد للمراجعة اليدوية**\n\n👤 المستخدم: `{user_id}`\n🔗 الرابط: {url}\n💰 المكافأة: {reward}".format(user_id=user_id, url=task[1], reward=task[3]), reply_markup=InlineKeyboardMarkup(admin_keyboard), parse_mode="Markdown")
