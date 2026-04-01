from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
import database as db
import strings as s
import config as c

# Conversation States
WAITING_FOR_PROOF = 1

async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = db.get_available_tasks()
    user_id = update.effective_user.id
    
    # Diagnostic logging
    print(f"🔍 User {user_id} requested tasks. Found: {len(tasks)} available tasks.")
    
    if not tasks:
        await update.effective_message.reply_text("✨ **لا توجد مهام متاحة حالياً. تفقدنا لاحقاً!**", parse_mode="Markdown")
        return

    keyboard = []
    for task in tasks:
        # task structure: (id, url, task_type, reward, total_needed, completed_count, status, created_at)
        btn_text = f"🎥 {task[2]} - {task[3]} نقطة"
        keyboard.append([InlineKeyboardButton(btn_text, callback_query_data=f"task_{task[0]}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.effective_message.reply_text(s.TASKS_MENU_MSG, reply_markup=reply_markup, parse_mode="Markdown")

async def task_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    task_id = int(query.data.split("_")[1])
    task = db.get_task_by_id(task_id)
    
    if not task:
        await query.edit_message_text("❌ **المهمة غير موجودة.**")
        return
        
    context.user_data['current_task_id'] = task_id
    
    keyboard = [
        [InlineKeyboardButton("🔗 اذهب للمهمة", url=task[1])],
        [InlineKeyboardButton("📸 إرسال الإثبات", callback_query_data=f"submit_{task_id}")]
    ]
    
    await query.edit_message_text(
        s.TASK_DETAILS_MSG.format(url=task[1], type=task[2], reward=task[3]),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def start_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    task_id = int(query.data.split("_")[1])
    context.user_data['waiting_for_proof'] = task_id
    
    await query.edit_message_text(s.WAIT_FOR_PROOF, parse_mode="Markdown")

async def handle_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    task_id = context.user_data.get('waiting_for_proof')
    if not task_id:
        return
        
    user_id = update.effective_user.id
    photo = update.message.photo[-1] # Get highest resolution
    file_id = photo.file_id
    
    success = db.submit_proof(user_id, task_id, file_id)
    
    if success:
        # Clear state
        del context.user_data['waiting_for_proof']
        await update.message.reply_text(s.PROOF_SUBMITTED, parse_mode="Markdown")
        
        # Notify Admin
        task = db.get_task_by_id(task_id)
        # Get the submission ID (last insert)
        # We need a way to get it, or just use user_id + task_id
        # Let's rebuild the message with relevant buttons
        # We'll need the submission entry to get its ID for buttons
        all_users = db.get_all_users() # Just to find admin, or use config
        
        # Send to Admin
        admin_keyboard = [
            [InlineKeyboardButton("✅ موافقة", callback_query_data=f"approve_{user_id}_{task_id}")],
            [InlineKeyboardButton("❌ رفض", callback_query_data=f"reject_menu_{user_id}_{task_id}")]
        ]
        
        # Actually we need submission table ID for safer buttons, but this works if user_id is unique per task.
        # Let's find the submission ID
        conn = db.sqlite3.connect(db.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM user_tasks WHERE user_id = ? AND task_id = ? ORDER BY id DESC LIMIT 1", (user_id, task_id))
        sub_id = cursor.fetchone()[0]
        conn.close()
        
        admin_keyboard = [
            [InlineKeyboardButton("✅ موافقة", callback_query_data=f"appr_{sub_id}")],
            [InlineKeyboardButton("❌ رفض", callback_query_data=f"rejmenu_{sub_id}")]
        ]
        
        await context.bot.send_photo(
            c.ADMIN_ID,
            photo=file_id,
            caption=s.NEW_SUBMISSION_MSG.format(user_id=user_id, url=task[1], reward=task[3]),
            reply_markup=InlineKeyboardMarkup(admin_keyboard),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ **لقد أرسلت إثباتاً لهذه المهمة مسبقاً!** انتظر المراجعة.")
