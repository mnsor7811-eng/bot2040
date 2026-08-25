async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # فحص الأزرار القديمة وإعادة التوجيه للقائمة الرئيسية تلقائياً
    valid_callbacks = ["buy_num", "select_provider", "my_orders", "support", "main_menu"]
    if query.data not in valid_callbacks and not query.data.startswith(("svc_", "cnt_", "set_prov_")):
        await start(update, context)
        return

    # معالجة القائمة الرئيسية
    if query.data == "main_menu":
        await start(update, context)
        
    # عرض قائمة الخدمات والتطبيقات
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
        
    # عرض قائمة الدول للخدمة المحددة
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

    # عرض قائمة المزودات الـ 22
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

    # قسم الدعم الفني والمعلومات
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
