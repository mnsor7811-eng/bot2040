import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

import config
from services_countries import SERVICES, COUNTRIES
from providers import PROVIDERS_CONFIG, ProviderAPI

logging.basicConfig(level=logging.INFO)

# ==================== الدالة الرئيسية /start ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    keyboard = [
        [InlineKeyboardButton("📱 طلب رقم جديد", callback_data="buy_num")],
        [InlineKeyboardButton("🌐 اختيار المزود (22 مزود)", callback_data="select_provider")],
        [
            InlineKeyboardButton(
                "💳 شحن الرصيد (Binance Pay)", 
                web_app=WebAppInfo(url=f"{config.BINANCE_WEBAPP_URL}&user_id={user_id}")
            )
        ],
        [
            InlineKeyboardButton("📋 طلباتي النشطة", callback_data="my_orders"),
            InlineKeyboardButton("📊 الدعم الفني", callback_data="support")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        f"مرحباً بك في بوت الأرقام والخدمات {config.BOT_USERNAME} 🤖\n\n"
        f"👤 المعرف الخاص بك: `{user_id}`\n"
        f"💳 معرف Binance Pay للشحن: `{config.BINANCE_PAY_ID}`\n"
        f"💰 رصيدك الحالي: *0.00 $*"
    )
    
    if update.message:
        await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)

# ==================== دالة معالجة جميع الأزرار ====================
async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # التعامل مع الأزرار القديمة أو المجهولة
    valid_callbacks = ["buy_num", "select_provider", "my_orders", "support", "main_menu"]
    if query.data not in valid_callbacks and not query.data.startswith(("svc_", "cnt_", "set_prov_")):
        await start(update, context)
        return

    # القائمة الرئيسية
    if query.data == "main_menu":
        await start(update, context)
        
    # قائمة الخدمات والتطبيقات
    elif query.data == "buy_num":
        buttons = []
        keys = list(SERVICES.keys())
        for i in range(0, len(keys), 2):
            row = [InlineKeyboardButton(SERVICES[keys[i]], callback_data=f"svc_{keys[i]}")]
            if i + 1 < len(keys):
                row.append(InlineKeyboardButton(SERVICES[keys[i+1]], callback_data=f"svc_{keys[i+1]}"))
            buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")])
        await query.edit_message_text("اختر التطبيق أو الخدمة المراد تفعيلها:", reply_markup=InlineKeyboardMarkup(buttons))
        
    # اختيار الدولة
    elif query.data.startswith("svc_"):
        svc_code = query.data.split("_")[1]
        buttons = []
        c_keys = list(COUNTRIES.keys())
        for i in range(0, len(c_keys), 2):
            row = [InlineKeyboardButton(COUNTRIES[c_keys[i]]["name"], callback_data=f"cnt_{c_keys[i]}_{svc_code}")]
            if i + 1 < len(c_keys):
                row.append(InlineKeyboardButton(COUNTRIES[c_keys[i+1]]["name"], callback_data=f"cnt_{c_keys[i+1]}_{svc_code}"))
            buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 رجوع للتطبيقات", callback_data="buy_num")])
        await query.edit_message_text("اختر الدولة المطلوبة للحصول على الرقم:", reply_markup=InlineKeyboardMarkup(buttons))

    # اختيار المزود من الـ 22 مزود
    elif query.data == "select_provider":
        buttons = []
        p_keys = list(PROVIDERS_CONFIG.keys())
        for i in range(0, len(p_keys), 2):
            row = [InlineKeyboardButton(f"⚙️ {p_keys[i]}", callback_data=f"set_prov_{p_keys[i]}")]
            if i + 1 < len(p_keys):
                row.append(InlineKeyboardButton(f"⚙️ {p_keys[i+1]}", callback_data=f"set_prov_{p_keys[i+1]}"))
            buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 العودة", callback_data="main_menu")])
        await query.edit_message_text("اختر مزود الأرقام المفضل لديك من المزودات الـ 22 المتاحة:", reply_markup=InlineKeyboardMarkup(buttons))

    # الدعم الفني
    elif query.data == "support":
        support_msg = (
            f"📊 **مركز الدعم الفني والخدمات**\n\n"
            f"📢 البوت الرسمي: {config.BOT_USERNAME}\n"
            f"👤 المطور والإدارة: `{config.ADMIN_ID}`\n"
            f"💳 معرف الشحن المباشر: `{config.BINANCE_PAY_ID}`"
        )
        await query.edit_message_text(
            support_msg,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data="main_menu")]])
        )

# ==================== تشغيل التطبيق ====================
if __name__ == "__main__":
    app = ApplicationBuilder().token(config.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    
    print("تم تشغيل البوت بنجاح...")
    app.run_polling()
