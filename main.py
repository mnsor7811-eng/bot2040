import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import config

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# معرف الآدمن (يستدعى من config أو ضع معرفك هنا)
ADMIN_ID = getattr(config, 'ADMIN_ID', 0)

# ==================== القائمة الرئيسية ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # أزرار المستخدم العادي
    keyboard = [
        [InlineKeyboardButton("🛒 قائمة الخدمات والمزودين", callback_data="providers"), InlineKeyboardButton("💰 حسابي والرصيد", callback_data="my_account")],
        [InlineKeyboardButton("💳 شحن الحساب", callback_data="recharge"), InlineKeyboardButton("📥 طلباتي", callback_data="my_orders")],
        [InlineKeyboardButton("🛠️ الدعم الفني والتعليمات", callback_data="support")]
    ]
    
    # إضافة زر لوحة التحكم إذا كان المستخدم هو الآدمن
    if user_id == ADMIN_ID or str(user_id) in str(ADMIN_ID):
        keyboard.append([InlineKeyboardButton("⚙️ لوحة تحكم الإدارة (الآدمن)", callback_data="admin_panel")])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_text = (
        f"أهلاً بك **{update.effective_user.first_name}** في بوت الخدمات الشاملة! 🚀\n\n"
        "يرجى اختيار القسم المطلوب من القائمة أدناه:"
    )
    
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

# ==================== معالجة الأزرار ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    # --- قائمة المزودين ---
    if query.data == "providers":
        buttons = []
        p_keys = list(config.PROVIDERS_CONFIG.keys()) if hasattr(config, 'PROVIDERS_CONFIG') else ["المزود الرئيسي"]
        for i in range(0, len(p_keys), 2):
            row = [InlineKeyboardButton(p_keys[i], callback_data=f"prov_{p_keys[i]}")]
            if i + 1 < len(p_keys):
                row.append(InlineKeyboardButton(p_keys[i+1], callback_data=f"prov_{p_keys[i+1]}"))
            buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")])
        
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.edit_message_text("📊 **قائمة المزودين المتاحين:**\nاختر المزود لرؤية الخدمات والأسعار:", reply_markup=reply_markup, parse_mode="Markdown")

    # --- حسابي والرصيد ---
    elif query.data == "my_account":
        msg = f"👤 **معلومات الحساب:**\n\n🆔 المعرف: `{user_id}`\n💵 الرصيد الحالي: **0.00 $**\n📦 إجمالي الطلبات: **0**"
        buttons = [[InlineKeyboardButton("💳 شحن الرصيد", callback_data="recharge")], [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

    # --- شحن الحساب ---
    elif query.data == "recharge":
        payment_info = getattr(config, 'PAYMENT_INFO', 'تواصل مع الإدارة لشحن الحساب')
        msg = f"💳 **طرق شحن الحساب المتاحة:**\n\n{payment_info}\n\nبعد التحويل يرجى إرسال الإشعار للدعم الفني لتأكيد الشحن."
        buttons = [[InlineKeyboardButton("📩 تواصل مع الدعم", callback_data="support")], [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

    # --- طلباتي ---
    elif query.data == "my_orders":
        msg = "📥 **سجل الطلبات:**\n\nلا توجد لديك طلبات حالياً."
        buttons = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(buttons))

    # --- الدعم الفني ---
    elif query.data == "support":
        bot_user = getattr(config, 'BOT_USERNAME', '@NUM1_SMBOT')
        admin_user = getattr(config, 'ADMIN_USERNAME', 'غير محدد')
        msg = f"🛠️ **مركز الدعم الفني والإدارة**\n\n🤖 البوت الرسمـي: {bot_user}\n👤 المطور والإدارة: {admin_user}\n\nلأي استفسار أو مشكلة في الشحن يرجى التواصل مباشر مع الإدارة."
        buttons = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(buttons))

    # --- ⚙️ لوحة تحكم الإدارة (الآدمن) ---
    elif query.data == "admin_panel":
        if user_id != ADMIN_ID and str(user_id) not in str(ADMIN_ID):
            await query.edit_message_text("⚠️ عذراً، هذه اللوحة مخصصة للإدارة فقط.")
            return

        admin_buttons = [
            [InlineKeyboardButton("➕ إضافة رصيد لمستخدم", callback_data="admin_add_balance"), InlineKeyboardButton("📊 إحصائيات البوت", callback_data="admin_stats")],
            [InlineKeyboardButton("📢 إذاعة (إرسال جماعي)", callback_data="admin_broadcast"), InlineKeyboardButton("⚙️ إعدادات المزودين", callback_data="admin_providers")],
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]
        ]
        msg = "⚙️ **لوحة تحكم الإدارة والتحكم الكامل:**\nمرحباً بك عزيزي الأدمن، اختر الإجراء المطلوب:"
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(admin_buttons), parse_mode="Markdown")

    # --- إحصائيات الآدمن ---
    elif query.data == "admin_stats":
        msg = "📊 **إحصائيات النظام:**\n\n👥 إجمالي المستخدمين: **1**\n📦 إجمالي الطلبات: **0**\n💵 الأرباح والإيداعات: **0.00 $**"
        buttons = [[InlineKeyboardButton("🔙 لوحة الإدارة", callback_data="admin_panel")]]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

    # --- العودة للقائمة الرئيسية ---
    elif query.data == "main_menu":
        await start(update, context)

# ==================== التشغيل الرئيسي ====================
if __name__ == "__main__":
    app = ApplicationBuilder().token(config.BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("...تم تشغيل البوت بالواجهة الكاملة بنجاح")
    app.run_polling()
