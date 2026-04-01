from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db
import config as c

def get_str(user_id, key):
    lang = db.get_user_lang(user_id)
    return s.STRINGS.get(lang, s.STRINGS['ar']).get(key, s.STRINGS['ar'].get(key, key))

async def start_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    
    commission = db.get_setting('commission_pct', 20)
    
    await update.message.reply_text(
        get_str(user_id, 'PROMO_MENU_MSG').format(commission=commission),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎯 البدء الآن", callback_data="promo_start")]]),
        parse_mode="Markdown"
    )

async def promo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "promo_start":
        context.user_data['promo_step'] = 'url'
        await query.edit_message_text(get_str(update.effective_user.id, 'PROMO_ENTER_URL'), parse_mode="Markdown")

async def process_promo_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get('promo_step')
    if not step:
        return False
        
    text = update.message.text.strip()
    
    if step == 'url':
        context.user_data['promo_url'] = text
        context.user_data['promo_step'] = 'budget'
        await update.message.reply_text(get_str(update.effective_user.id, 'PROMO_ENTER_BUDGET'), parse_mode="Markdown")
        return True
        
    elif step == 'budget':
        try:
            budget = int(text)
            user_id = update.effective_user.id
            user_data = db.get_user(user_id)
            
            if user_data[2] < budget:
                await update.message.reply_text("❌ **رصيدك غير كافي لهذه الميزانية.**")
                return True
                
            context.user_data['promo_budget'] = budget
            context.user_data['promo_step'] = 'reward'
            
            commission = int(db.get_setting('commission_pct', 20))
            await update.message.reply_text("🎁 **كم ستدفع للمتابع الواحد؟** (مثلاً: 10)")
            return True
        except ValueError:
            await update.message.reply_text("❌ **أدخل رقماً صحيحاً.**")
            return True
            
    elif step == 'reward':
        try:
            reward = int(text)
            budget = context.user_data.get('promo_budget')
            
            if reward > budget:
                await update.message.reply_text("❌ **الجائزة لا يمكن أن تكون أكبر من الميزانية.**")
                return True
                
            context.user_data['promo_reward'] = reward
            
            # Finalize
            user_id = update.effective_user.id
            url = context.user_data.get('promo_url')
            
            # Add to DB
            success = db.add_campaign(user_id, url, budget, reward, "Follow")
            if success:
                db.log_transaction(user_id, -budget, "PROMOTION", f"طلب ترويج لحساب: {url}")
                await update.message.reply_text(get_str(user_id, 'PROMO_SUCCESS'), parse_mode="Markdown")
                # Notify Admin
                await context.bot.send_message(c.ADMIN_ID, f"🚀 **طلب ترويج جديد للمراجعة!**\nالمستخدم: `{user_id}`\nالرابط: {url}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 مراجعة الترويجات", callback_data="rev_campaigns")]]))
            else:
                await update.message.reply_text("❌ **فشل في إنشاء الحملة.**")
                
            del context.user_data['promo_step']
            return True
        except ValueError:
            await update.message.reply_text("❌ **أدخل رقماً صحيحاً.**")
            return True
            
    return False
