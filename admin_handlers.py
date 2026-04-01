from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db
import strings as s
import config as c

async def pending_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
        
    task_count, withd_count = db.get_pending_counts()
    
    keyboard = [
        [InlineKeyboardButton(f"📸 مراجعة المهام ({task_count})", callback_data="rev_tasks")],
        [InlineKeyboardButton(f"💰 مراجعة السحوبات ({withd_count})", callback_data="rev_withd")]
    ]
    
    await update.message.reply_text(
        s.ADMIN_PENDING_MSG.format(task_count=task_count, withd_count=withd_count),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def review_tasks_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    task = db.get_next_pending_task()
    if not task:
        await query.edit_message_text("✅ **لا توجد مهام معلقة حالياً!**")
        return
        
    # task: (id, user_id, task_id, screenshot_id, status, submitted_at)
    sub_id, user_id, task_id, photo_id, status, date = task
    task_info = db.get_task_by_id(task_id)
    
    keyboard = [
        [InlineKeyboardButton("✅ موافقة", callback_data=f"appr_{sub_id}")],
        [InlineKeyboardButton("❌ رفض", callback_data=f"rejmenu_{sub_id}")],
        [InlineKeyboardButton("➡️ التالي", callback_data="rev_tasks")],
        [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="admin_main")]
    ]
    
    await query.message.delete() # Delete dashboard message
    await context.bot.send_photo(
        c.ADMIN_ID,
        photo=photo_id,
        caption=s.NEW_SUBMISSION_MSG.format(user_id=user_id, url=task_info[1], reward=task_info[3]),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def review_withd_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    withd = db.get_next_pending_withdrawal()
    if not withd:
        await query.edit_message_text("✅ **لا توجد طلبات سحب معلقة حالياً!**")
        return
        
    # withd: (id, user_id, amount, method, details, status, created_at)
    w_id, user_id, amount, method, details, status, date = withd
    
    keyboard = [
        [InlineKeyboardButton("✅ صرف المبلغ", callback_data=f"wthappr_{w_id}")],
        [InlineKeyboardButton("❌ رفض الطلب", callback_data=f"wthrej_{w_id}")],
        [InlineKeyboardButton("➡️ التالي", callback_data="rev_withd")],
        [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="admin_main")]
    ]
    
    await query.edit_message_text(
        s.ADMIN_NEW_WITHDRAW_MSG.format(user_id=user_id, amount=amount, method=method, details=details),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def withdraw_approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    w_id = int(query.data.split("_")[1])
    res = db.approve_withdrawal(w_id)
    
    if res:
        user_id, amount = res
        await query.edit_message_text(f"✅ **تمت الموافقة على سحب {amount} نقطة!**")
        try:
            await context.bot.send_message(user_id, s.WITHDRAW_APPROVE_USER.format(amount=amount), parse_mode="Markdown")
        except:
            pass
    else:
        await query.edit_message_text("❌ **خطأ في المعالجة.**")

async def withdraw_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    w_id = int(query.data.split("_")[1])
    res = db.reject_withdrawal(w_id)
    
    if res:
        user_id, amount = res
        await query.edit_message_text(f"❌ **تم رفض طلب السحب وإعادة {amount} نقطة للمستخدم.**")
        try:
            await context.bot.send_message(user_id, s.WITHDRAW_REJECT_USER.format(amount=amount), parse_mode="Markdown")
        except:
            pass
    else:
        await query.edit_message_text("❌ **خطأ في المعالجة.**")

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

# --- ADMIN MAIN MENU (BUTTONS) ---

def admin_buttons_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 إحصائيات النظام", callback_data="admin_stats")],
        [InlineKeyboardButton("📋 مراجعة المهام", callback_data="rev_tasks"), 
         InlineKeyboardButton("💰 مراجعة السحوبات", callback_data="rev_withd")],
        [InlineKeyboardButton("🛒 مراجعة الشحن", callback_data="rev_deposits"), 
         InlineKeyboardButton("🚀 مراجعة الترويج", callback_data="rev_campaigns")],
        [InlineKeyboardButton("📢 إرسال جماعي", callback_data="admin_broadcast")],
        [InlineKeyboardButton("⚙️ إعدادات البوت", callback_data="admin_settings"),
         InlineKeyboardButton("📦 إضافة باقة شحن", callback_data="admin_add_pkg_start")],
        [InlineKeyboardButton("📜 سجل التدقيق", callback_data="admin_logs_view")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def admin_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
        
    msg = "👮 **لوحة تحكم المدير الاحترافية**\n\nمرحباً بك! اختر القسم الذي تود إدارته من الأزرار أدناه:"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=admin_buttons_keyboard(), parse_mode="Markdown")
    else:
        await update.message.reply_text(msg, reply_markup=admin_buttons_keyboard(), parse_mode="Markdown")

async def admin_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    msg = """
⚙️ **إعدادات النظام**

للتعديل، استخدم الأوامر التالية (مؤقتاً):
• `/set_api_key [KEY]` - مفتاح الذكاء الاصطناعي
• `/set_setting [KEY] [VAL]` - أي إعداد آخر
• `/add_package [PTS] [PRICE] [CURR]` - إضافة باقة

**الإعدادات الحالية:**
"""
    # Quick list of current settings for convenience
    settings = ["google_api_key", "min_withdraw", "commission_pct", "bankak_details"]
    for s_key in settings:
        val = db.get_setting(s_key, "غير محدد")
        msg += f"• `{s_key}`: `{val[:15]}...`\n"

    keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="admin_main")]]
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def admin_add_package_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📦 **إضافة باقة شحن جديدة**\n\nمن فضلك استخدم الأمر التالي:\n`/add_package [النقاط] [السعر] [العملة]`\n\nمثال: `/add_package 1000 5000 SDG`",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data="admin_main")]]),
        parse_mode="Markdown"
    )

async def admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📢 **من فضلك أرسل الرسالة التي تود توجيهها للكل الآن:**\n(أو اكتب /cancel للإلغاء)")
    context.user_data['admin_action'] = 'broadcasting'

async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    total_users, total_points = db.get_stats()
    keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="admin_main")]]
    await query.edit_message_text(
        s.STATS_MSG.format(total_users=total_users, total_points=total_points),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def admin_logs_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    logs = db.get_admin_logs(15)
    if not logs:
        msg = "📜 **سجل التدقيق فارغ حالياً.**"
    else:
        msg = "📜 **آخر عمليات التدقيق (الأمن):**\n\n"
        for l in logs:
            # l: (id, admin_id, action, target_id, time)
            target = f" للمستخدم `{l[3]}`" if l[3] else ""
            msg += f"🔹 {l[4].split(' ')[1]} | {l[2]}{target}\n"
            
    keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="admin_main")]]
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# --- SECURITY COMMANDS ---

async def ban_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("👮 **استخدام:** `/ban [USER_ID]`")
        return
    
    target_id = int(context.args[0])
    db.ban_user(target_id)
    db.log_admin_action(c.ADMIN_ID, "BAN_USER", target_id)
    await update.message.reply_text(f"🛑 **تم حظر المستخدم `{target_id}` نهائياً.**")

async def unban_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("👮 **استخدام:** `/unban [USER_ID]`")
        return
    
    target_id = int(context.args[0])
    db.unban_user(target_id)
    db.log_admin_action(c.ADMIN_ID, "UNBAN_USER", target_id)
    await update.message.reply_text(f"✅ **تم إلغاء حظر المستخدم `{target_id}`.**")

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
        db.log_admin_action(c.ADMIN_ID, "APPROVE_TASK", user_id)
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
        keyboard.append([InlineKeyboardButton(reason.split("\n")[1][:30], callback_data=f"rej_{sub_id}_{key}")])
    
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

# --- PROFESSIONAL SETTINGS ---

async def set_api_key_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("👮 **استخدام:** `/set_api_key [KEY]`")
        return
    db.set_setting('google_api_key', context.args[0])
    await update.message.reply_text("✅ **تم تحديث مفتاح الذكاء الاصطناعي بنجاح!**")

async def set_setting_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
    if len(context.args) < 2:
        await update.message.reply_text("👮 **استخدام:** `/set_setting [KEY] [VALUE]`")
        return
    db.set_setting(context.args[0], " ".join(context.args[1:]))
    await update.message.reply_text(f"✅ **تم تحديث الإعداد `{context.args[0]}` بنجاح!**")

async def add_package_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
    if len(context.args) < 3:
        await update.message.reply_text("👮 **استخدام:** `/add_package [POINTS] [PRICE] [CURRENCY]`\nمثال: `/add_package 1000 5000 SDG`")
        return
    
    try:
        pts = int(context.args[0])
        price = float(context.args[1])
        curr = context.args[2].upper()
        # Custom instructions based on currency
        instr = db.get_setting('bankak_details') if curr == "SDG" else "Please contact admin for payment details."
        
        db.add_package(pts, price, curr, instr)
        await update.message.reply_text(f"✅ **تم إضافة باقة ({pts} نقطة) بسعر {price} {curr} بنجاح!**")
    except:
        await update.message.reply_text("❌ **خطأ في البيانات المرسلة.**")

# --- DEPOSIT REVIEW ---

async def review_deposits_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    dep = db.get_next_pending_deposit()
    if not dep:
        await query.edit_message_text("✅ **لا توجد طلبات شحن معلقة حالياً!**")
        return
        
    # dep: (id, user_id, package_id, screenshot_id, status, created_at)
    d_id, u_id, p_id, photo_id, status, date = dep
    package = db.get_package_by_id(p_id)
    
    keyboard = [
        [InlineKeyboardButton("✅ تأكيد الشحن", callback_data=f"depappr_{d_id}")],
        [InlineKeyboardButton("❌ رفض", callback_data=f"deprej_{d_id}")],
        [InlineKeyboardButton("➡️ التالي", callback_data="rev_deposits")],
        [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="admin_main")]
    ]
    
    await query.message.delete()
    await context.bot.send_photo(
        c.ADMIN_ID,
        photo=photo_id,
        caption=f"🛒 **طلب شحن رصيد جديد!**\n\n👤 المستخدم: `{u_id}`\n📦 الباقة: {package[1]} نقطة\n💰 السعر: {package[2]} {package[3]}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def deposit_approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    d_id = int(query.data.split("_")[1])
    res = db.approve_deposit(d_id)
    
    if res:
        u_id, pts = res
        await query.edit_message_text(f"✅ **تم شحن {pts} نقطة للمستخدم {u_id}!**")
        try:
            await context.bot.send_message(u_id, f"✅ **تم تأكيد عملية الدفع!**\nلقد أضفنا **{pts}** نقطة إلى رصيدك. تسوق ممتع! 🛒")
            db.log_transaction(u_id, pts, "DEPOSIT", f"شراء باقة نقاط ({pts} نقطة)")
            db.log_admin_action(c.ADMIN_ID, "APPROVE_DEPOSIT", u_id)
        except:
            pass
    else:
        await query.edit_message_text("❌ **خطأ في المعالجة.**")

# --- CAMPAIGN REVIEW ---

async def review_campaigns_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    camp = db.get_next_pending_campaign()
    if not camp:
        await query.edit_message_text("✅ **لا توجد طلبات ترويج معلقة حالياً!**")
        return
        
    # camp: (id, user_id, url, task_type, budget, reward, status, created_at)
    c_id, u_id, url, ttype, budget, reward, status, date = camp
    
    keyboard = [
        [InlineKeyboardButton("✅ موافقة وتفعيل", callback_data=f"cmpappr_{c_id}")],
        [InlineKeyboardButton("❌ رفض", callback_data=f"cmprej_{c_id}")],
        [InlineKeyboardButton("➡️ التالي", callback_data="rev_campaigns")],
        [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="admin_main")]
    ]
    
    await query.edit_message_text(
        f"🚀 **طلب ترويج جديد!**\n\n👤 المستخدم: `{u_id}`\n🔗 الرابط: {url}\n📝 النوع: {ttype}\n💰 الميزانية: {budget}\n🎁 الجائزة للمتابع: {reward}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def campaign_approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    c_id = int(query.data.split("_")[1])
    res = db.approve_campaign(c_id)
    
    if res:
        u_id, url = res
        await query.edit_message_text(f"✅ **تم تفعيل حملة الترويج بنجاح!**")
        try:
            await context.bot.send_message(u_id, "✅ **تهانينا!** تمت الموافقة على حملة الترويج الخاصة بك وهي الآن نشطة للمستخدمين. 🚀")
        except:
            pass
    else:
        await query.edit_message_text("❌ **خطأ في المعالجة.**")
