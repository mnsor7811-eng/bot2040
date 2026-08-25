import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "8927305428:AAHlCPINlpyeymiPL7WnxxZtjufvZxd6--Y"
ADMIN_ID = 5000000000  # استبدل هذا الرقم بـ ID الحساب الخاص بك

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    keyboard = [
        [InlineKeyboardButton("🛒 قائمة الخدمات والمزودين", callback_data="providers"), InlineKeyboardButton("💰 حسابي والرصيد", callback_data="my_account")],
        [InlineKeyboardButton("💳 شحن الحساب", callback_data="recharge"), InlineKeyboardButton("📥 طلباتي", callback_data="my_orders")],
        [InlineKeyboardButton("🛠️ الدعم الفني", callback_data="support")]
    ]
    
    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("⚙️ لوحة تحكم الإدارة", callback_data="admin_panel")])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"أهلاً بك **{update.effective_user.first_name}** في بوت الخدمات الشاملة! 🚀"
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "providers":
        btn = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
        await query.edit_message_text("📊 **قائمة المزودين:**\nلا توجد خدمات مضافة حالياً.", reply_markup=InlineKeyboardMarkup(btn), parse_mode="Markdown")
    elif query.data == "my_account":
        btn = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
        await query.edit_message_text(f"👤 **حسابك:**\n🆔 المعرف: `{query.from_user.id}`\n💵 الرصيد: **0.00 $**", reply_markup=InlineKeyboardMarkup(btn), parse_mode="Markdown")
    elif query.data == "recharge":
        btn = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
        await query.edit_message_text("💳 **طريقة الشحن:**\nتواصل مع الدعم الفني لإضافة رصيد.", reply_markup=InlineKeyboardMarkup(btn), parse_mode="Markdown")
    elif query.data == "my_orders":
        btn = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
        await query.edit_message_text("📥 لا توجد طلبات حافلة.", reply_markup=InlineKeyboardMarkup(btn))
    elif query.data == "support":
        btn = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
        await query.edit_message_text("🛠️ **الدعم الفني:**\nتواصل مع الإدارة عبر المعرف الخاص بك.", reply_markup=InlineKeyboardMarkup(btn))
    elif query.data == "admin_panel":
        btn = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
        await query.edit_message_text("⚙️ **لوحة التحكم الخاصّة بالإدارة.**", reply_markup=InlineKeyboardMarkup(btn))
    elif query.data == "main_menu":
        await start(update, context)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("...البوت يعمل حالياً")
    app.run_polling()
