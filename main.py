import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
import config

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("عرض المزودين والخدمات 📊", callback_data="providers")],
        [InlineKeyboardButton("الدعم الفني 🛠️", callback_data="support")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_text = (
        f"أهلاً بك عزيزي في بوت الخدمات الشاملة! 🚀\n\n"
        f"يرجى اختيار أحد الخيارات من القائمة أدناه:"
    )
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "providers":
        buttons = []
        p_keys = list(config.PROVIDERS_CONFIG.keys()) if hasattr(config, 'PROVIDERS_CONFIG') else []
        for i in range(0, len(p_keys), 2):
            row = [InlineKeyboardButton(p_keys[i], callback_data=f"provider_{p_keys[i]}")]
            if i + 1 < len(p_keys):
                row.append(InlineKeyboardButton(p_keys[i+1], callback_data=f"provider_{p_keys[i+1]}"))
            buttons.append(row)
        buttons.append([InlineKeyboardButton("رجوع 🔙", callback_data="main_menu")])
        
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.edit_message_text("اختر المزود المطلوب لرؤية التفاصيل والخدمات المتاحة:", reply_markup=reply_markup)
        
    elif query.data == "support":
        support_msg = (
            f"📊 **مركز الدعم الفني والخدمات**\n\n"
            f"📢 **البوت الرسمي:** {getattr(config, 'BOT_USERNAME', '@NUM1_SMBOT')}\n"
            f"👤 **المطور والإدارة:** {getattr(config, 'ADMIN_USERNAME', 'غير محدد')}\n"
            f"💳 **معرف الشحن المباشر:** {getattr(config, 'PAYMENT_INFO', 'تواصل مع الدعم')}\n"
        )
        buttons = [[InlineKeyboardButton("رجوع 🔙", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.edit_message_text(support_msg, parse_mode="Markdown", reply_markup=reply_markup)
        
    elif query.data == "main_menu":
        await start(update, context)

# ==================== تشغيل التطبيق ====================
if __name__ == "__main__":
    app = ApplicationBuilder().token(config.BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("...تم تشغيل البوت بنجاح")
    app.run_polling()
