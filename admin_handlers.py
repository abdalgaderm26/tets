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
