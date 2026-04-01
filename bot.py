import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import database as db
import config as c
import strings as s
import admin_handlers as admin
import task_handlers as tasks
import promo_handlers as promo
from datetime import datetime
import time

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- MAIN MENU KEYBOARD ---
def main_menu_keyboard():
    keyboard = [
        ["🚀 تنفيذ مهام", "💰 رصيد"],
        ["🛒 شراء نقاط", "🚀 ترويج"],
        ["🎁 هدية يومية", "👥 دعوة"],
        ["📜 السجل", "💰 سحب الأرباح"],
        ["👤 حسابي", "📊 الإحصائيات"],
        ["📜 الشروط"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# --- SECURITY CHECK (BAN & RATE LIMIT) ---

async def check_security(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # 1. Ban Check
    if db.is_user_banned(user_id):
        await update.effective_message.reply_text(s.USER_BANNED_MSG, parse_mode="Markdown")
        return False
        
    # 2. Rate Limit (1 request per 1.5 seconds)
    now = time.time()
    last_req = context.user_data.get('last_req_time', 0)
    if now - last_req < 1.5:
        # Only notify once every few spams to avoid spamming the user back
        if not context.user_data.get('notified_rate_limit'):
            await update.effective_message.reply_text(s.RATE_LIMIT_MSG, parse_mode="Markdown")
            context.user_data['notified_rate_limit'] = True
        return False
    
    context.user_data['last_req_time'] = now
    context.user_data['notified_rate_limit'] = False
    return True

# --- SHOP (BUY POINTS) FLOW ---

async def start_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    currencies = db.get_currencies()
    if not currencies:
        await update.message.reply_text("❌ **المتجر مغلق حالياً.**")
        return
        
    keyboard = []
    for curr in currencies:
        keyboard.append([InlineKeyboardButton(curr, callback_data=f"buycurr_{curr}")])
        
    await update.message.reply_text(s.SHOP_CURRENCY_MSG, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def shop_currency_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    curr = query.data.split("_")[1]
    packages = db.get_packages_by_currency(curr)
    
    keyboard = []
    for p in packages:
        # p: (id, points, price, currency, instructions)
        btn_text = f"📦 {p[1]} نقطة - {p[2]} {p[3]}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"buypkg_{p[0]}")])
        
    await query.edit_message_text(s.SHOP_PACKAGES_MSG.format(currency=curr), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def shop_package_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    pkg_id = int(query.data.split("_")[1])
    package = db.get_package_by_id(pkg_id)
    
    context.user_data['waiting_for_deposit'] = pkg_id
    
    await query.edit_message_text(
        s.SHOP_INSTRUCTIONS_MSG.format(points=package[1], instructions=package[4]),
        parse_mode="Markdown"
    )

async def handle_deposit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pkg_id = context.user_data.get('waiting_for_deposit')
    if not pkg_id:
        return False
        
    user_id = update.effective_user.id
    photo_id = update.message.photo[-1].file_id
    
    db.add_deposit_request(user_id, pkg_id, photo_id)
    del context.user_data['waiting_for_deposit']
    
    await update.message.reply_text(s.SHOP_DEPOSIT_SUBMITTED, parse_mode="Markdown")
    
    # Notify Admin
    pkg = db.get_package_by_id(pkg_id)
    admin_kb = [
        [InlineKeyboardButton("✅ مراجعة طلبات الشحن", callback_data="rev_deposits")]
    ]
    await context.bot.send_message(c.ADMIN_ID, f"🛒 **طلب شحن جديد!**\nالمستخدم: `{user_id}`\nالباقة: {pkg[1]} نقطة", reply_markup=InlineKeyboardMarkup(admin_kb))
    return True

# --- TRANSACTION HISTORY ---

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    txs = db.get_transactions(user_id)
    
    if not txs:
        await update.message.reply_text("📭 **لا توجد عمليات مسجلة حالياً.**")
        return
        
    history_text = ""
    for t in txs:
        # t: (id, user_id, amount, type, description, created_at)
        history_text += s.HISTORY_ITEM.format(
            date=t[5].split(" ")[0],
            type=t[3],
            amount=f"+{t[2]}" if t[2] > 0 else t[2],
            desc=t[4]
        )
        
    await update.message.reply_text(s.HISTORY_MSG.format(history=history_text), parse_mode="Markdown")

# --- WITHDRAWAL FLOW ---
async def start_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    if user_data[2] < c.MIN_WITHDRAW:
        await update.message.reply_text(s.WITHDRAW_FAILED_MIN.format(min_points=c.MIN_WITHDRAW), parse_mode="Markdown")
        return

    keyboard = [
        [InlineKeyboardButton("📱 رصيد", callback_data="wth_credit")],
        [InlineKeyboardButton("🏦 تحويل", callback_data="wth_transfer")]
    ]
    
    await update.message.reply_text(
        s.WITHDRAW_MENU_MSG.format(min_points=c.MIN_WITHDRAW),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    method = "رصيد" if query.data == "wth_credit" else "تحويل"
    context.user_data['wth_method'] = method
    context.user_data['wth_step'] = 'amount'
    
    await query.edit_message_text(s.WITHDRAW_AMOUNT_MSG.format(min_points=c.MIN_WITHDRAW), parse_mode="Markdown")

async def process_withdraw_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get('wth_step')
    if not step:
        return False
        
    text = update.message.text.strip()
    
    if step == 'amount':
        try:
            amount = int(text)
            if amount < c.MIN_WITHDRAW:
                await update.message.reply_text(s.WITHDRAW_FAILED_MIN.format(min_points=c.MIN_WITHDRAW), parse_mode="Markdown")
                return True
            
            user_id = update.effective_user.id
            user_data = db.get_user(user_id)
            if user_data[2] < amount:
                await update.message.reply_text(s.WITHDRAW_FAILED_POINTS, parse_mode="Markdown")
                return True
                
            context.user_data['wth_amount'] = amount
            context.user_data['wth_step'] = 'details'
            await update.message.reply_text(s.WITHDRAW_DETAILS_MSG, parse_mode="Markdown")
            return True
        except ValueError:
            await update.message.reply_text("❌ **من فضلك أدخل رقماً صحيحاً.**")
            return True
            
    elif step == 'details':
        method = context.user_data.get('wth_method')
        amount = context.user_data.get('wth_amount')
        user_id = update.effective_user.id
        
        success = db.add_withdrawal_request(user_id, amount, method, text)
        if success:
            # Notify Admin
            admin_kb = [
                [InlineKeyboardButton("✅ موافقة", callback_data=f"wth_appr_last")],
                [InlineKeyboardButton("❌ رفض", callback_data=f"wth_rej_last")]
            ]
            # Since we don't have the ID yet, we'll fetch it from the next_pending later in dashboard
            # But for quick review, we can just fetch the last one for this user
            conn = db.sqlite3.connect(db.DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM withdrawals WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
            wth_id = cursor.fetchone()[0]
            conn.close()
            
            admin_kb = [
                [InlineKeyboardButton("✅ موافقة", callback_data=f"wthappr_{wth_id}")],
                [InlineKeyboardButton("❌ رفض", callback_data=f"wthrej_{wth_id}")]
            ]
            
            await context.bot.send_message(
                c.ADMIN_ID,
                s.ADMIN_NEW_WITHDRAW_MSG.format(user_id=user_id, amount=amount, method=method, details=text),
                reply_markup=InlineKeyboardMarkup(admin_kb),
                parse_mode="Markdown"
            )
            
            await update.message.reply_text(s.WITHDRAW_SUCCESS, parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ **فشل الطلب! تأكد من رصيدك.**")
            
        # Clean state
        del context.user_data['wth_step']
        return True
        
    return False

# --- START HANDLER ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_security(update, context):
        return
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

# --- TASKS DISPLAY LOGIC (MOVED HERE FOR RELIABILITY) ---
async def show_all_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tasks_list = db.get_available_tasks(user_id)
    
    print(f"🔍 User {user_id} clicked Tasks. Found: {len(tasks_list)} tasks in DB.")
    
    if not tasks_list:
        await update.effective_message.reply_text("✨ **لا توجد مهام متاحة حالياً. تفقدنا لاحقاً!**", parse_mode="Markdown")
        return

    keyboard = []
    for task in tasks_list:
        btn_text = f"🎥 {task[2]} - {task[3]} نقطة"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"task_{task[0]}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.effective_message.reply_text(s.TASKS_MENU_MSG, reply_markup=reply_markup, parse_mode="Markdown")

# --- TEXT HANDLER FOR KEYBOARD BUTTONS ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_security(update, context):
        return
    text = update.message.text.strip() if update.message.text else ""
    user_id = update.effective_user.id
    
    # Admin Actions (Broadcasting, etc)
    if user_id == c.ADMIN_ID and context.user_data.get('admin_action') == 'broadcasting':
        if text.lower() == '/cancel':
            del context.user_data['admin_action']
            await update.message.reply_text("❌ **تم إلغاء الإرسال الجماعي.**")
            return
        
        await update.message.reply_text(s.BROADCAST_START, parse_mode="Markdown")
        users = db.get_all_users()
        count = 0
        for u in users:
            try:
                await context.bot.send_message(u[0], text, parse_mode="Markdown")
                count += 1
            except:
                continue
        del context.user_data['admin_action']
        await update.message.reply_text(f"✅ {s.BROADCAST_DONE}\nتم الإرسال لـ {count} مستخدم.")
        return

    if await process_withdraw_text(update, context):
        return
        
    if await promo.process_promo_text(update, context):
        return

    if "مهام" in text:
        await show_all_tasks(update, context)
    elif "حسابي" in text or "رصيدي" in text:
        await profile(update, context)
    elif "هدية يومية" in text:
        await daily_gift(update, context)
    elif "سحب الأرباح" in text:
        await start_withdraw(update, context)
    elif "شراء نقاط" in text:
        await start_shop(update, context)
    elif "ترويج" in text:
        await promo.start_promo(update, context)
    elif "السجل" in text:
        await show_history(update, context)
    elif "دعوة" in text:
        await public_stats(update, context)
    elif "الشروط" in text:
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
    application.add_handler(CallbackQueryHandler(withdraw_callback, pattern="^wth_"))
    
    # Shop & Promo Callbacks
    application.add_handler(CallbackQueryHandler(shop_currency_callback, pattern="^buycurr_"))
    application.add_handler(CallbackQueryHandler(shop_package_callback, pattern="^buypkg_"))
    application.add_handler(CallbackQueryHandler(promo.promo_callback, pattern="^promo_"))
    
    # Message Handlers
    async def merged_photo_handler(update, context):
        if not await check_security(update, context):
            return
        # Try shop deposit first
        if await handle_deposit_proof(update, context):
            return
        # Otherwise standard task proof
        await tasks.handle_proof(update, context)

    application.add_handler(MessageHandler(filters.PHOTO, merged_photo_handler))
    
    # Admin Handlers
    application.add_handler(CommandHandler("admin", admin.admin_main_menu))
    
    # Core Admin Commands
    application.add_handler(CommandHandler("add_task", admin.add_task_cmd))
    application.add_handler(CommandHandler("set_api_key", admin.set_api_key_cmd))
    application.add_handler(CommandHandler("set_setting", admin.set_setting_cmd))
    application.add_handler(CommandHandler("add_package", admin.add_package_cmd))
    application.add_handler(CommandHandler("ban", admin.ban_user_cmd))
    application.add_handler(CommandHandler("unban", admin.unban_user_cmd))
    
    # Admin Callbacks
    application.add_handler(CallbackQueryHandler(admin.admin_main_menu, pattern="^admin_main$"))
    application.add_handler(CallbackQueryHandler(admin.stats_callback, pattern="^admin_stats$"))
    application.add_handler(CallbackQueryHandler(admin.admin_settings_menu, pattern="^admin_settings$"))
    application.add_handler(CallbackQueryHandler(admin.admin_broadcast_start, pattern="^admin_broadcast$"))
    application.add_handler(CallbackQueryHandler(admin.admin_add_package_start, pattern="^admin_add_pkg_start$"))
    application.add_handler(CallbackQueryHandler(admin.admin_logs_view_callback, pattern="^admin_logs_view$"))
    
    application.add_handler(CallbackQueryHandler(admin.review_tasks_callback, pattern="^rev_tasks$"))
    application.add_handler(CallbackQueryHandler(admin.review_withd_callback, pattern="^rev_withd$"))
    application.add_handler(CallbackQueryHandler(admin.review_deposits_callback, pattern="^rev_deposits$"))
    application.add_handler(CallbackQueryHandler(admin.review_campaigns_callback, pattern="^rev_campaigns$"))
    
    application.add_handler(CallbackQueryHandler(admin.approve_callback, pattern="^appr_"))
    application.add_handler(CallbackQueryHandler(admin.reject_menu_callback, pattern="^rejmenu_"))
    application.add_handler(CallbackQueryHandler(admin.final_reject_callback, pattern="^rej_"))
    application.add_handler(CallbackQueryHandler(admin.withdraw_approve_callback, pattern="^wthappr_"))
    application.add_handler(CallbackQueryHandler(admin.withdraw_reject_callback, pattern="^wthrej_"))
    application.add_handler(CallbackQueryHandler(admin.deposit_approve_callback, pattern="^depappr_"))
    application.add_handler(CallbackQueryHandler(admin.campaign_approve_callback, pattern="^cmpappr_"))
    
    # Text Messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the Bot
    print("🚀 Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
