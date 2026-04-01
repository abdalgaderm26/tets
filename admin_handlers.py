from telegram import Update
from telegram.ext import ContextTypes
import database as db
import strings as s
import config as c

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
    
    total_users, total_points = db.get_stats()
    await update.message.reply_text(
        s.STATS_MSG.format(total_users=total_users, total_points=total_points),
        parse_mode="Markdown"
    )

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
    
    if not context.args:
        await update.message.reply_text("👮 **استخدام:** `/broadcast [الرسالة]`", parse_mode="Markdown")
        return
    
    message = " ".join(context.args)
    all_users = db.get_all_users()
    
    await update.message.reply_text(s.BROADCAST_START, parse_mode="Markdown")
    
    count = 0
    for user_id in all_users:
        try:
            await context.bot.send_message(user_id, message)
            count += 1
        except:
            pass
            
    await update.message.reply_text(f"✅ **تم إرسال الرسالة إلى {count} مستخدم!**", parse_mode="Markdown")

async def add_points_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
        
    if len(context.args) < 2:
        await update.message.reply_text("👮 **استخدام:** `/add [ID] [النقاط]`", parse_mode="Markdown")
        return
        
    try:
        user_id = int(context.args[0])
        points = int(context.args[1])
        db.add_points(user_id, points)
        await update.message.reply_text(f"✅ **تم إضافة {points} نقطة للمستخدم {user_id}!**", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ **خطأ:** {str(e)}")

async def sub_points_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
        
    if len(context.args) < 2:
        await update.message.reply_text("👮 **استخدام:** `/sub [ID] [النقاط]`", parse_mode="Markdown")
        return
        
    try:
        user_id = int(context.args[0])
        points = int(context.args[1])
        db.deduct_points(user_id, points)
        await update.message.reply_text(f"✅ **تم خصم {points} نقطة من المستخدم {user_id}!**", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ **خطأ:** {str(e)}")

# --- TASK MANAGEMENT ---

async def add_task_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
        
    if len(context.args) < 4:
        await update.message.reply_text("👮 **استخدام:** `/add_task [URL] [Type] [Reward] [Count]`\n\nمثال: `/add_task https://tiktok.com/... Follow 10 100`", parse_mode="Markdown")
        return
        
    try:
        url = context.args[0]
        task_type = context.args[1]
        reward = int(context.args[2])
        count = int(context.args[3])
        
        db.add_task(url, task_type, reward, count)
        await update.message.reply_text(f"✅ **تم إضافة المهمة بنجاح!**\n\n🔗 الرابط: {url}\n📝 النوع: {task_type}\n💰 الجائزة: {reward}\n👥 العدد المطلوب: {count}", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ **خطأ:** {str(e)}")

# --- PROOF REVIEW ---

async def approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # query.data format: "appr_{sub_id}"
    sub_id = int(query.data.split("_")[1])
    res = db.approve_submission(sub_id)
    
    if res:
        user_id, reward = res
        await query.edit_message_caption(s.APPROVE_SUCCESS.format(reward=reward), parse_mode="Markdown")
        # Notify user
        try:
            await context.bot.send_message(user_id, f"✅ **تهانينا!** تمت الموافقة على الإثبات وتم إضافة **{reward}** نقطة لرصيدك.")
        except:
            pass
    else:
        await query.edit_message_caption("❌ **خطأ في معالجة الموافقة.**")

async def reject_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # query.data format: "rejmenu_{sub_id}"
    sub_id = int(query.data.split("_")[1])
    
    # Ready-made reasons keyboard
    keyboard = []
    for key, reason in s.REJECT_REASONS.items():
        # Display short version of reason in button
        keyboard.append([InlineKeyboardButton(reason.split("\n")[1][:30], callback_query_data=f"rej_{sub_id}_{key}")])
    
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))

async def final_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # query.data format: "rej_{sub_id}_{reason_key}"
    parts = query.data.split("_")
    sub_id = int(parts[1])
    reason_key = parts[2]
    
    user_id = db.reject_submission(sub_id)
    
    if user_id:
        reason_text = s.REJECT_REASONS.get(reason_key, "غير محدد")
        await query.edit_message_caption(s.REJECT_SUCCESS, parse_mode="Markdown")
        # Notify user with ready reason
        try:
            await context.bot.send_message(user_id, s.REJECT_REPLY_USER.format(reason=reason_text), parse_mode="Markdown")
        except:
            pass
    else:
        await query.edit_message_caption("❌ **خطأ في معالجة الرفض.**")

# --- DEBUG COMMAND ---

async def debug_tasks_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
        
    conn = db.sqlite3.connect(db.DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks")
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        await update.message.reply_text("📭 **لا توجد أي مهام في قاعدة البيانات حالياً.**")
        return
        
    msg = "📝 **قائمة جميع المهام في القاعدة:**\n\n"
    for r in rows:
        msg += f"🆔 {r[0]} | 🔗 {r[1][:20]}... | 💰 {r[3]} | 👥 {r[5]}/{r[4]} | 🟢 {r[6]}\n"
    
    await update.message.reply_text(msg, parse_mode="Markdown")
