import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import database as db
import config as c
import strings as s
import admin_handlers as admin
import task_handlers as tasks
from datetime import datetime

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- MAIN MENU KEYBOARD ---
def main_menu_keyboard():
    keyboard = [
        ["🚀 تنفيذ مهام", "💰 رصيدي"],
        ["🎁 هدية يومية", "👥 دعوة الأصدقاء"],
        ["👤 حسابي", "📊 الإحصائيات"],
        ["📜 الشروط"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# --- START HANDLER ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    
    # Check registration
    is_new = db.register_user(user.id, user.username, initial_points=c.WELCOME_POINTS)
    
    # Referral Logic
    if is_new and args:
        referrer_id = int(args[0])
        if referrer_id != user.id: # Cannot refer self
            db.add_points(referrer_id, c.REFERRAL_POINTS)
            db.update_daily_claim(user.id) # Initial setup for daily column
            # Notify referrer
            try:
                await context.bot.send_message(referrer_id, s.REFERRAL_NOTIFICATION, parse_mode="Markdown")
            except:
                pass

    await update.message.reply_text(
        s.START_MSG,
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown"
    )

# --- PROFILE HANDLER ---
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if not user_data:
        return

    await update.message.reply_text(
        s.PROFILE_MSG.format(
            user_id=user_data[0],
            points=user_data[2],
            joined_at=user_data[6]
        ),
        parse_mode="Markdown"
    )

# --- DAILY REWARD ---
async def daily_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if db.can_claim_daily(user_id):
        db.add_points(user_id, c.DAILY_POINTS)
        db.update_daily_claim(user_id)
        await update.message.reply_text(s.DAILY_SUCCESS.format(amount=c.DAILY_POINTS), parse_mode="Markdown")
    else:
        await update.message.reply_text(s.DAILY_WAIT, parse_mode="Markdown")

# --- INVITE CODE ---
async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bot_username = (await context.bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    
    await update.message.reply_text(
        s.INVITE_MSG.format(referral_link=referral_link),
        parse_mode="Markdown"
    )

# --- STATS (Public or Admin) ---
async def public_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_users, total_points = db.get_stats()
    await update.message.reply_text(
        s.STATS_MSG.format(total_users=total_users, total_points=total_points),
        parse_mode="Markdown"
    )

# --- TEXT HANDLER FOR KEYBOARD BUTTONS ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "🚀 تنفيذ مهام":
        await tasks.show_tasks(update, context)
    elif text == "👤 حسابي":
        await profile(update, context)
    elif text == "💰 رصيدي":
        await profile(update, context)
    elif text == "🎁 هدية يومية":
        await daily_gift(update, context)
    elif text == "👥 دعوة الأصدقاء":
        await invite(update, context)
    elif text == "📊 الإحصائيات":
        await public_stats(update, context)
    elif text == "📜 الشروط":
        await update.message.reply_text("⚖️ **قوانين البوت:**\n\n1. يمنع الغش باستخدام حسابات وهمية.\n2. أي محاولة تلاعب ستؤدي لحظر الحساب.")

# --- MAIN ---
def main():
    # Initialize Database
    db.init_db()
    
    # Create Application
    application = Application.builder().token(c.TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("daily", daily_gift))
    application.add_handler(CommandHandler("points", profile))
    application.add_handler(CommandHandler("invite", invite))
    application.add_handler(CommandHandler("stats", public_stats))
    
    # Task Handlers
    application.add_handler(CallbackQueryHandler(tasks.task_callback, pattern="^task_"))
    application.add_handler(CallbackQueryHandler(tasks.start_submission, pattern="^submit_"))
    application.add_handler(MessageHandler(filters.PHOTO, tasks.handle_proof))
    
    # Admin Handlers
    application.add_handler(CommandHandler("admin", lambda update, context: update.message.reply_text(s.ADMIN_CMD_LIST, parse_mode="Markdown")))
    application.add_handler(CommandHandler("broadcast", admin.broadcast))
    application.add_handler(CommandHandler("add", admin.add_points_cmd))
    application.add_handler(CommandHandler("sub", admin.sub_points_cmd))
    application.add_handler(CommandHandler("add_task", admin.add_task_cmd))
    application.add_handler(CommandHandler("stats_admin", admin.stats))
    
    # Admin Callbacks
    application.add_handler(CallbackQueryHandler(admin.approve_callback, pattern="^appr_"))
    application.add_handler(CallbackQueryHandler(admin.reject_menu_callback, pattern="^rejmenu_"))
    application.add_handler(CallbackQueryHandler(admin.final_reject_callback, pattern="^rej_"))
    
    # Text Messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the Bot
    print("🚀 Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
