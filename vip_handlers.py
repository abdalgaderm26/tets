from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db
import strings as s

async def start_vip_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    price = int(db.get_setting('vip_price', 1000))
    multiplier = db.get_setting('vip_multiplier', '2.0')
    
    # Get localized string
    lang = db.get_user_lang(user_id)
    msg = s.STRINGS[lang]['VIP_INFO_MSG'].format(multiplier=multiplier, price=price)
    
    btn_text = "💎 شراء الآن" if lang == 'ar' else "💎 Buy Now"
    keyboard = [[InlineKeyboardButton(btn_text, callback_data="vip_buy")]]
    
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def buy_vip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = db.get_user_lang(user_id)
    
    price = int(db.get_setting('vip_price', 1000))
    user_data = db.get_user(user_id)
    
    if user_data[2] < price:
        await query.edit_message_text(s.STRINGS[lang]['VIP_INSUFFICIENT'])
        return
        
    # Process purchase
    # BUG-07 FIX: Use deduct_points() instead of add_points(-price) for correctness
    db.deduct_points(user_id, price)
    db.set_vip(user_id, 30)  # 30 days
    db.log_transaction(user_id, -price, "PURCHASE", "شراء عضوية VIP لمدة 30 يوم" if lang == 'ar' else "Purchased VIP for 30 days")
    
    await query.edit_message_text(s.STRINGS[lang]['VIP_SUCCESS'])
