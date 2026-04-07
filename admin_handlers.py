import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db
import config as c
import strings as s

logger = logging.getLogger(__name__)

def get_str(user_id, key, **kwargs):
    lang = db.get_user_lang(user_id)
    text = s.STRINGS.get(lang, s.STRINGS['ar']).get(key, s.STRINGS['ar'].get(key, key))
    if kwargs:
        return text.format(**kwargs)
    return text

async def pending_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
        
    task_count, withd_count = db.get_pending_counts()
    
    keyboard = [
        [InlineKeyboardButton(f"📸 مراجعة المهام ({task_count})", callback_data="rev_tasks")],
        [InlineKeyboardButton(f"💰 مراجعة السحوبات ({withd_count})", callback_data="rev_withd")]
    ]
    
    msg = get_str(update.effective_user.id, 'ADMIN_PENDING_MSG').format(task_count=task_count, withd_count=withd_count)
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

async def review_tasks_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
    query = update.callback_query
    await query.answer()
    
    task = db.get_next_pending_task()
    if not task:
        await query.edit_message_text("✅ **لا توجد مهام معلقة حالياً!**")
        return
        
    sub_id, user_id, task_id, photo_id, status, date = task
    task_info = db.get_task_by_id(task_id)
    
    keyboard = [
        [InlineKeyboardButton("✅ موافقة", callback_data=f"appr_{sub_id}")],
        [InlineKeyboardButton("❌ رفض", callback_data=f"rejmenu_{sub_id}")],
        [InlineKeyboardButton("➡️ التالي", callback_data="rev_tasks")],
        [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="admin_main")]
    ]
    
    await query.message.delete()
    await context.bot.send_photo(
        c.ADMIN_ID,
        photo=photo_id,
        caption=get_str(c.ADMIN_ID, 'NEW_SUBMISSION_MSG').format(user_id=user_id, url=task_info[1], reward=task_info[3]),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def review_withd_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
    query = update.callback_query
    await query.answer()
    
    withd = db.get_next_pending_withdrawal()
    if not withd:
        await query.edit_message_text("✅ **لا توجد طلبات سحب معلقة حالياً!**")
        return
        
    w_id, user_id, amount, method, details, status, date = withd
    
    keyboard = [
        [InlineKeyboardButton("✅ صرف المبلغ", callback_data=f"wthappr_{w_id}")],
        [InlineKeyboardButton("❌ رفض الطلب", callback_data=f"wthrej_{w_id}")],
        [InlineKeyboardButton("➡️ التالي", callback_data="rev_withd")],
        [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="admin_main")]
    ]
    
    await query.edit_message_text(
        get_str(c.ADMIN_ID, 'ADMIN_NEW_WITHDRAW_MSG').format(user_id=user_id, amount=amount, method=method, details=details),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def withdraw_approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
    query = update.callback_query
    await query.answer()
    
    w_id = int(query.data.split("_")[1])
    res = db.approve_withdrawal(w_id)
    
    if res:
        user_id, amount = res
        await query.edit_message_text(f"✅ **تمت الموافقة على سحب {amount} نقطة!**")
        try:
            await context.bot.send_message(user_id, get_str(user_id, 'WITHDRAW_APPROVE_USER').format(amount=amount), parse_mode="Markdown")
        except:
            pass
    else:
        await query.edit_message_text("❌ **خطأ في المعالجة.**")

async def withdraw_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
    query = update.callback_query
    await query.answer()
    
    w_id = int(query.data.split("_")[1])
    res = db.reject_withdrawal(w_id)
    
    if res:
        user_id, amount = res
        await query.edit_message_text(f"❌ **تم رفض طلب السحب وإعادة {amount} نقطة للمستخدم.**")
        try:
            await context.bot.send_message(user_id, get_str(user_id, 'WITHDRAW_REJECT_USER').format(amount=amount), parse_mode="Markdown")
        except:
            pass
    else:
        await query.edit_message_text("❌ **خطأ في المعالجة.**")

async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
    query = update.callback_query
    await query.answer()
    
    total_users, total_points = db.get_stats()
    task_count = db.get_active_task_count()
    await query.edit_message_text(
        get_str(update.effective_user.id, 'STATS_MSG', total_users=total_users, total_points=total_points, task_count=task_count),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data="admin_main")]])
    )

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

# --- ADVANCED SETTINGS MENU ---

async def admin_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        exec_func = query.edit_message_text
    else:
        exec_func = update.message.reply_text
        
    keyboard = [
        [InlineKeyboardButton("💳 محفظة USDT (TRC20)", callback_data="set_usdt_start")],
        [InlineKeyboardButton("🏦 الحساب البنكي (بنكك)", callback_data="set_bank_start")],
        [InlineKeyboardButton("💎 سعر الـ VIP", callback_data="set_vprice_start")],
        [InlineKeyboardButton("📈 مضاعف الـ VIP", callback_data="set_vmult_start")],
        [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="admin_main")]
    ]
    
    usdt = db.get_setting('usdt_wallet', 'غير محدد')
    v_mult = db.get_setting('vip_multiplier', '2.0')
    v_price = db.get_setting('vip_price', '1000')
    
    msg = f"⚙️ **إعدادات المنصة العالمية**\n\n💰 **USDT:** `{usdt}`\n📈 **VIP Multiplier:** `{v_mult}x`\n💎 **VIP Price:** `{v_price}` pts\n\nاختر الإعداد الذي تود تعديله:"
    
    await exec_func(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def admin_setting_edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
    query = update.callback_query
    await query.answer()
    
    setting_type = query.data
    context.user_data['awaiting_admin_setting'] = setting_type
    
    labels = {
        "set_usdt_start": "محفظة USDT (TRC20)",
        "set_bank_start": "بيانات الحساب البنكي",
        "set_vprice_start": "سعر اشتراك الـ VIP (بالنقاط)",
        "set_vmult_start": "مضاعف أرباح الـ VIP (مثلاً 2.0)"
    }
    
    label = labels.get(setting_type, "الإعداد")
    await query.edit_message_text(f"📝 **تعديل {label}**\n\nمن فضلك أرسل القيمة الجديدة الآن:")

async def handle_admin_setting_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
        
    setting_type = context.user_data.get('awaiting_admin_setting')
    if not setting_type:
        return
        
    new_val = update.message.text
    
    map_keys = {
        "set_usdt_start": "usdt_wallet",
        "set_bank_start": "bankak_details",
        "set_vprice_start": "vip_price",
        "set_vmult_start": "vip_multiplier"
    }
    
    db_key = map_keys.get(setting_type)
    db.set_setting(db_key, new_val)
    
    del context.user_data['awaiting_admin_setting']
    
    await update.message.reply_text(f"✅ **تم تحديث الإعداد بنجاح!**\nالقيمة الجديدة: `{new_val}`", parse_mode="Markdown")
    await admin_settings_menu(update, context)

# --- ADMIN DASHBOARD ---

async def admin_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"👮 Admin Attempt: User {user_id} | Required: {c.ADMIN_ID}")

    try:
        if user_id != c.ADMIN_ID:
            logger.warning(f"🚫 Denied: {user_id} != {c.ADMIN_ID}")
            msg = f"❌ **عذراً! أنت لست مديراً.**\n\n👤 الأيدي الخاص بك: `{user_id}`\n🔑 الأيدي المسجل: `{c.ADMIN_ID}`\n\nيرجى مطابقة الأرقام في Railway."
            if update.callback_query:
                await update.callback_query.answer(msg, show_alert=True)
            else:
                await update.message.reply_text(msg, parse_mode="Markdown")
            return

        total_users, total_points = db.get_stats()
        text = get_str(user_id, 'ADMIN_DASHBOARD_OVERVIEW', total_users=total_users, total_points=total_points)

        m_mode = db.get_setting('maintenance_mode', 'off')
        m_icon = "🟢" if m_mode == 'off' else "🔴"
        text += f"\n\n⚙️ حالة الصيانة: {m_icon} **{m_mode.upper()}**"

        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(text, reply_markup=await admin_buttons_keyboard(), parse_mode="Markdown")
        else:
            await update.message.reply_text(text, reply_markup=await admin_buttons_keyboard(), parse_mode="Markdown")

        logger.info(f"✅ Admin menu sent to {user_id}")

    except Exception as e:
        logger.error(f"💥 Admin Menu Error: {str(e)}", exc_info=True)
        error_msg = f"⚠️ **خطأ تقني في لوحة الإدارة:**\n`{str(e)}`"
        if update.callback_query:
            try:
                await update.callback_query.answer(error_msg, show_alert=True)
            except:
                pass
        else:
            await update.message.reply_text(error_msg, parse_mode="Markdown")

async def admin_buttons_keyboard():
    m_mode = db.get_setting('maintenance_mode', 'off')
    m_text = "🛠️ تفعيل الصيانة" if m_mode == 'off' else "✅ إنهاء الصيانة"
    
    keyboard = [
        [InlineKeyboardButton("📋 مراجعة الطلبات", callback_data="admin_pending")],
        [InlineKeyboardButton("⚙️ إعدادات النظام", callback_data="admin_settings"), 
         InlineKeyboardButton("📈 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 إرسال جماعي", callback_data="admin_broadcast"),
         InlineKeyboardButton("📦 إضافة باقة", callback_data="admin_add_pkg_start")],
        [InlineKeyboardButton("💾 نسخة احتياطية", callback_data="admin_backup"),
         InlineKeyboardButton(m_text, callback_data="toggle_maintenance")],
        [InlineKeyboardButton("🔄 تحديث البوت", callback_data="admin_refresh")],
        [InlineKeyboardButton("📜 سجل الأمان", callback_data="admin_logs_view")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def admin_add_package_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📦 **إضافة باقة شحن جديدة**\n\nمن فضلك استخدم الأمر التالي:\n`/add_package [النقاط] [السعر] [العملة]`\n\nمثال: `/add_package 1000 5000 SDG`",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data="admin_main")]]),
        parse_mode="Markdown"
    )



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
    if update.effective_user.id != c.ADMIN_ID:
        return
    query = update.callback_query
    await query.answer()
    
    # query.data format: "appr_{sub_id}"
    sub_id = int(query.data.split("_")[1])
    res = db.approve_submission(sub_id)
    
    if res:
        user_id, base_reward = res
        
        # VIP Multiplier Logic
        final_reward = base_reward
        if db.is_vip(user_id):
            multiplier = float(db.get_setting('vip_multiplier', '2.0'))
            final_reward = int(base_reward * multiplier)
            # Update balance with the EXTRA points (base is already added by db.approve_submission)
            extra = final_reward - base_reward
            if extra > 0:
                db.add_points(user_id, extra)
        
        db.log_admin_action(c.ADMIN_ID, "APPROVE_TASK", user_id)
        # IMP-02 FIX: APPROVE_SUCCESS now exists in strings.py, use it directly
        await query.edit_message_caption(
            get_str(c.ADMIN_ID, 'APPROVE_SUCCESS').format(reward=final_reward),
            parse_mode="Markdown"
        )
        
        # Notify user with localized message
        try:
            lang = db.get_user_lang(user_id)
            msg = s.STRINGS[lang]['AI_AUTO_APPROVED'].format(reward=final_reward)
            if final_reward > base_reward:
                vip_extra = final_reward - base_reward
                msg += f"\n💎 (+{vip_extra} VIP Bonus!)"
            await context.bot.send_message(user_id, msg, parse_mode="Markdown")
        except Exception:
            pass
    else:
        await query.edit_message_caption("❌ **خطأ في معالجة الموافقة.**")

async def reject_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
    query = update.callback_query
    await query.answer()
    
    # query.data format: "rejmenu_{sub_id}"
    sub_id = int(query.data.split("_")[1])
    
    # Ready-made reasons keyboard
    keyboard = []
    reasons = get_str(c.ADMIN_ID, 'REJECT_REASONS')
    for key, reason in reasons.items():
        # Display short version of reason in button
        keyboard.append([InlineKeyboardButton(reason.split("\n")[0], callback_data=f"rej_{sub_id}_{key}")])
    
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))

async def final_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
    query = update.callback_query
    await query.answer()
    
    # query.data format: "rej_{sub_id}_{reason_key}"
    parts = query.data.split("_")
    sub_id = int(parts[1])
    reason_key = parts[2]
    
    user_id = db.reject_submission(sub_id)
    
    if user_id:
        reasons = get_str(c.ADMIN_ID, 'REJECT_REASONS')
        reason_text = reasons.get(reason_key, "غير محدد")
        await query.edit_message_caption(get_str(c.ADMIN_ID, 'REJECT_SUCCESS'), parse_mode="Markdown")
        # Notify user with ready reason
        try:
            await context.bot.send_message(user_id, get_str(user_id, 'REJECT_REPLY_USER').format(reason=reason_text), parse_mode="Markdown")
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
    if update.effective_user.id != c.ADMIN_ID:
        return
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
    if update.effective_user.id != c.ADMIN_ID:
        return
    query = update.callback_query
    await query.answer()
    
    d_id = int(query.data.split("_")[1])
    res = db.approve_deposit(d_id)
    
    if res:
        u_id, pts = res
        # HIGH-03 FIX: DB operations must happen OUTSIDE the try block so they
        # always execute even if the Telegram notification to user fails.
        db.log_transaction(u_id, pts, "DEPOSIT", f"شراء باقة نقاط ({pts} نقطة)")
        db.log_admin_action(c.ADMIN_ID, "APPROVE_DEPOSIT", u_id)
        await query.edit_message_caption(f"✅ **تم شحن {pts} نقطة للمستخدم {u_id}!**", parse_mode="Markdown")
        try:
            await context.bot.send_message(u_id, f"✅ **تم تأكيد عملية الدفع!**\nلقد أضفنا **{pts}** نقطة إلى رصيدك. تسوق ممتع! 🛒", parse_mode="Markdown")
        except Exception:
            pass
    else:
        await query.edit_message_text("❌ **خطأ في المعالجة.**")

async def deposit_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
    query = update.callback_query
    await query.answer()
    
    d_id = int(query.data.split("_")[1])
    # For now, we just mark as rejected in DB (implementation in db depends on your schema, 
    # assuming we just update status to 'rejected')
    user_id = db.reject_deposit(d_id)
    
    if user_id:
        await query.edit_message_caption("❌ **تم رفض طلب الشحن.**")
        try:
            await context.bot.send_message(user_id, get_str(user_id, 'DEPOSIT_REJECT_USER'), parse_mode="Markdown")
            db.log_admin_action(c.ADMIN_ID, "REJECT_DEPOSIT", user_id)
        except:
            pass
    else:
        await query.edit_message_caption("❌ **خطأ في المعالجة.**")

# --- CAMPAIGN REVIEW ---

async def review_campaigns_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
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
    if update.effective_user.id != c.ADMIN_ID:
        return
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

async def campaign_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
    query = update.callback_query
    await query.answer()
    
    c_id = int(query.data.split("_")[1])
    user_id = db.reject_campaign(c_id)
    
    if user_id:
        await query.edit_message_text("❌ **تم رفض حملة الترويج.**")
        try:
            await context.bot.send_message(user_id, get_str(user_id, 'CAMPAIGN_REJECT_USER'), parse_mode="Markdown")
            db.log_admin_action(c.ADMIN_ID, "REJECT_CAMPAIGN", user_id)
        except:
            pass
    else:
        await query.edit_message_text("❌ **خطأ في المعالجة.**")

# --- MAINTENANCE & REFRESH ---

async def toggle_maintenance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
    query = update.callback_query
    await query.answer()
    
    current = db.get_setting('maintenance_mode', 'off')
    new_mode = 'on' if current == 'off' else 'off'
    db.set_setting('maintenance_mode', new_mode)
    
    db.log_admin_action(c.ADMIN_ID, f"TOGGLE_MAINTENANCE_{new_mode.upper()}", None)
    await admin_main_menu(update, context)

async def admin_refresh_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    
    await query.edit_message_text(s.STRINGS[lang]['REFRESH_MSG'], parse_mode="Markdown")
    db.log_admin_action(c.ADMIN_ID, "BOT_REFRESH", None)
    
    # Small delay then exit to trigger Railway restart
    import sys
    import os
    os._exit(0)

async def admin_backup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    
    await query.message.reply_chat_action("upload_document")
    try:
        with open("bot_database.db", "rb") as db_file:
            await context.bot.send_document(
                c.ADMIN_ID,
                document=db_file,
                filename=f"backup_{datetime.now().strftime('%Y%m%d_%H%M')}.db",
                caption=s.STRINGS[lang]['BACKUP_SUCCESS'],
                parse_mode="Markdown"
            )
        db.log_admin_action(c.ADMIN_ID, "DATABASE_BACKUP", None)
    except Exception as e:
        await query.message.reply_text(f"❌ **خطأ أثناء النسخ الاحتياطي:** {str(e)}")

async def admin_logs_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
    query = update.callback_query
    await query.answer()
    
    # Export admin_logs to a professional .txt file
    import io
    logs = db.get_admin_logs(limit=50)
    
    if not logs:
        await query.edit_message_text("📜 **سجل الأمان فارغ حالياً.**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 عودة", callback_data="admin_main")]]))
        return
        
    log_stream = io.StringIO()
    log_stream.write("ADMIN SECURITY LOGS - EXPORT\n")
    log_stream.write("="*30 + "\n\n")
    for log in logs:
        # log: (id, admin_id, action, target_id, timestamp)
        log_stream.write(f"[{log[4]}] Action: {log[2]} | Target: {log[3]}\n")
        
    log_stream.seek(0)
    # Convert to bytes for telegram
    log_bytes = io.BytesIO(log_stream.getvalue().encode('utf-8'))
    
    await context.bot.send_document(
        c.ADMIN_ID,
        document=log_bytes,
        filename=f"security_logs_{datetime.now().strftime('%Y%m%d')}.txt",
        caption="📜 **إليك سجل الأمان الاحترافي للمنصة (آخر 50 عملية).**",
        parse_mode="Markdown"
    )

async def admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
    query = update.callback_query
    await query.answer()
    
    context.user_data['admin_action'] = 'broadcasting'
    await query.edit_message_text(
        "📢 **قسم الإرسال الجماعي الاحترافي**\n\n- أرسل الآن أي (صورة، فيديو، نص، ملف) ليتم تحويله فوراً لجميع المستخدمين.\n- التقنية المستخدمة تضمن وصول الرسالة بشكلها الأصلي.\n\n❌ للإلغاء، اكتب `/cancel`",
        parse_mode="Markdown"
    )

# --- SUPPORT SYSTEM (REPLY) ---

async def support_reply_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
    query = update.callback_query
    await query.answer()
    
    # CRIT-04 FIX: Store target_user_id as int to ensure correct type for send_message
    target_user_id = int(query.data.split("_")[1])
    context.user_data['replyING_to'] = target_user_id
    
    await query.message.reply_text(f"📝 **جاري الرد على المستخدم `{target_user_id}`**\nأرسل رسالتك الآن:", parse_mode="Markdown")

async def handle_support_reply_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != c.ADMIN_ID:
        return
    target_uid = context.user_data.get('replyING_to')
    if not target_uid:
        return
        
    reply_text = update.message.text
    try:
        await context.bot.send_message(
            target_uid, 
            f"📨 **رد من الدعم الفني:**\n\n{reply_text}",
            parse_mode="Markdown"
        )
        await update.message.reply_text("✅ **تم إرسال الرد بنجاح!**")
        db.log_admin_action(c.ADMIN_ID, "SUPPORT_REPLY", target_uid)
    except:
        await update.message.reply_text("❌ **فشل إرسال الرد. قد يكون المستخدم حظر البوت.**")
        
    del context.user_data['replyING_to']

async def handle_broadcast_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    NEW: Professional Media Broadcast Handler.
    This function catches any message from the admin when 'admin_action' is 'broadcasting'.
    It uses copy_message to broadcast any message type (text, photo, video, etc.)
    while preserving captions and formatting without 'Forwarded' tag.
    """
    if update.effective_user.id != c.ADMIN_ID:
        return False
        
    if context.user_data.get('admin_action') != 'broadcasting':
        return False
        
    if update.message.text == '/cancel':
        del context.user_data['admin_action']
        await update.message.reply_text(get_str(c.ADMIN_ID, 'BROADCAST_CANCELLED'))
        return True
        
    # Start Broadcasting
    del context.user_data['admin_action']
    all_users = db.get_all_users()
    
    status_msg = await update.message.reply_text(get_str(c.ADMIN_ID, 'BROADCAST_STARTED'), parse_mode="Markdown")
    
    count = 0
    failed = 0
    for uid in all_users:
        try:
            # copy_message preserves captions, formatting, and buttons
            await context.bot.copy_message(
                chat_id=uid,
                from_chat_id=update.message.chat_id,
                message_id=update.message.message_id
            )
            count += 1
            # Add small delay to avoid hitting rate limits if user list is huge
            import asyncio
            if count % 25 == 0:
                await asyncio.sleep(0.5)
        except Exception:
            failed += 1
            
    await status_msg.edit_text(
        get_str(c.ADMIN_ID, 'BROADCAST_COMPLETED', count=count, failed=failed),
        parse_mode="Markdown"
    )
    db.log_admin_action(c.ADMIN_ID, "BROADCAST_ALL", count)
    return True
