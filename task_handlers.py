import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db
import config as c
import strings as s
import vision_ai

# Logger must be defined at the top before any function uses it
logger = logging.getLogger(__name__)

def get_str(user_id, key, **kwargs):
    lang = db.get_user_lang(user_id)
    text = s.STRINGS.get(lang, s.STRINGS['ar']).get(key, s.STRINGS['ar'].get(key, key))
    if kwargs:
        return text.format(**kwargs)
    return text

# Conversation States
WAITING_FOR_PROOF = 1

async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tasks = db.get_available_tasks(user_id)
    
    logger.info(f"🔍 User {user_id} requested tasks. Found: {len(tasks)} available tasks.")
    
    if not tasks:
        # BUG-04 FIX: Use the correct key 'TASKS_EMPTY' (was using non-existent 'TASKS_MENU_MSG_EMPTY')
        await update.effective_message.reply_text(get_str(user_id, 'TASKS_EMPTY'), parse_mode="Markdown")
        return

    keyboard = []
    pts_label = get_str(user_id, 'TASK_POINTS_LABEL')
    for task in tasks:
        # task structure: (id, url, task_type, reward, total_needed, completed_count, status, created_at)
        btn_text = f"🎥 {task[2]} - {task[3]} {pts_label}"
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

async def handle_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    task_id = context.user_data.get('waiting_for_proof')
    if not task_id:
        return
        
    user_id = update.effective_user.id
    photo = update.message.photo[-1]  # Get highest resolution
    file_id = photo.file_id
    file_unique_id = photo.file_unique_id
    
    # 1. Register submission and check for duplicates
    sub_id = db.submit_proof(user_id, task_id, file_id, file_unique_id)
    
    if sub_id == "ALREADY_SUBMITTED":
        await update.message.reply_text(get_str(user_id, 'ALREADY_SUBMITTED_ERROR'), parse_mode="Markdown")
        return
    elif sub_id == "DUPLICATE_PHOTO":
        await update.message.reply_text(get_str(user_id, 'DUPLICATE_PHOTO_ERROR'), parse_mode="Markdown")
        return
        
    # Clear state
    del context.user_data['waiting_for_proof']
    
    # 2. AI Vision Analysis
    status_msg = await update.message.reply_text(get_str(user_id, 'AI_VERIFYING'), parse_mode="Markdown")
    
    # Download the photo
    try:
        new_file = await photo.get_file()
        path = f"tmp_proof_{user_id}.jpg"
        await new_file.download_to_drive(path)
        
        task = db.get_task_by_id(task_id)
        ai_result = await vision_ai.analyze_screenshot(path, task[2])
        
        # Cleanup temp file
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
                    vip_bonus_text = f"\n💎 (+{final_reward - base_reward} VIP Bonus!)"
                    reward_msg += vip_bonus_text
                    
                await status_msg.edit_text(reward_msg, parse_mode="Markdown")
                # Also notify admin of auto-approval
                try:
                    await context.bot.send_photo(
                        c.ADMIN_ID,
                        photo=file_id,
                        caption=f"✨ **Auto-Approved by AI**\n\n👤 User: `{user_id}`\n💰 Reward: {final_reward} pts",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
                return
                
        # AI UNSURE or FAIL → send to admin for manual review
        await status_msg.edit_text(get_str(user_id, 'PROOF_SUBMITTED'), parse_mode="Markdown")
        
        ai_label = "❌ FAIL" if ai_result == "FAIL" else "❓ UNSURE"
        admin_keyboard = [
            [InlineKeyboardButton("✅ Approve", callback_data=f"appr_{sub_id}")],
            [InlineKeyboardButton("❌ Reject", callback_data=f"rejmenu_{sub_id}")]
        ]
        
        task = db.get_task_by_id(task_id)
        await context.bot.send_photo(
            c.ADMIN_ID,
            photo=file_id,
            caption=get_str(c.ADMIN_ID, 'NEW_SUBMISSION_MSG').format(
                user_id=user_id,
                url=task[1],
                reward=task[3]
            ) + f"\n\n🤖 AI: {ai_label}",
            reply_markup=InlineKeyboardMarkup(admin_keyboard),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"❌ Error handling proof for user {user_id}: {str(e)}")
        await status_msg.edit_text(get_str(user_id, 'PROOF_SUBMITTED'), parse_mode="Markdown")
        # Notify Admin without AI info for manual fallback
        try:
            task = db.get_task_by_id(task_id)
            admin_keyboard = [
                [InlineKeyboardButton("✅ Approve", callback_data=f"appr_{sub_id}")],
                [InlineKeyboardButton("❌ Reject", callback_data=f"rejmenu_{sub_id}")]
            ]
            await context.bot.send_photo(
                c.ADMIN_ID,
                photo=file_id,
                caption=get_str(c.ADMIN_ID, 'NEW_SUBMISSION_MSG').format(
                    user_id=user_id,
                    url=task[1] if task else 'N/A',
                    reward=task[3] if task else 'N/A'
                ) + "\n\n⚠️ AI Error — Manual Review Required",
                reply_markup=InlineKeyboardMarkup(admin_keyboard),
                parse_mode="Markdown"
            )
        except Exception:
            pass
