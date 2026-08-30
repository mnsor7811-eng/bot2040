from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_ID, SERVERS, fetch_server_prices, get_clean_country_info

def main_keyboard(user_id):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🤖 اشتراكات برامج AI", callback_data="ai_landing"))
    markup.row(InlineKeyboardButton("📞 شراء رقم افتراضي", callback_data="buy_number"))
    markup.row(InlineKeyboardButton("🔵 جاهز Telegram", callback_data="fast_buy_tg"), InlineKeyboardButton("🟢 عروض WhatsApp", callback_data="fast_buy_wa"))
    markup.row(InlineKeyboardButton("🔥 السيرفرات الأكثر مبيعاً", callback_data="best_selling"))
    markup.row(InlineKeyboardButton("🎳 شحن الرصيد / الاشتراكات", callback_data="recharge_menu"), InlineKeyboardButton("🎲 الأكثر توفراً", callback_data="most_available"))
    markup.row(InlineKeyboardButton("🚀 الرشق وشحن الألعاب والبرامج", callback_data="smm_main"))
    markup.row(InlineKeyboardButton("💎 اربح رصيد مجانا", callback_data="free_ruble"))
    markup.row(InlineKeyboardButton("🎧 الدعم", callback_data="support"), InlineKeyboardButton("🔄 تحويل الرصيد", callback_data="transfer"))
    markup.row(InlineKeyboardButton("✔ إحصائيات الشراء الناجح", callback_data="purchase_stats"))
    markup.row(InlineKeyboardButton("👤 حسابي", callback_data="my_account"))
    markup.row(InlineKeyboardButton("🛸 خدمات وميزات أخرى", callback_data="other_services"))
    
    if str(user_id) == str(ADMIN_ID):
        markup.row(InlineKeyboardButton("⚙️ لوحة الإدارة الكبرى", callback_data="admin_panel"))
    return markup

def back_button():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
    return markup

def admin_back_button():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 رجوع لوحة الإدارة", callback_data="admin_panel"))
    return markup

def recharge_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🏦 بنك الكريمي", callback_data="pay_kuraimi"))
    markup.add(InlineKeyboardButton("📱 محفظة جيب", callback_data="pay_jeeb"))
    markup.add(InlineKeyboardButton("💳 محفظة ون كاش", callback_data="pay_onecash"))
    markup.add(InlineKeyboardButton("🟡 Binance (تلقائي)", callback_data="pay_binance"))
    markup.add(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
    return markup

def servers_keyboard():
    markup = InlineKeyboardMarkup()
    for srv_id, srv_info in SERVERS.items():
        markup.add(InlineKeyboardButton(srv_info['name'], callback_data=f"select_server_{srv_id}"))
    markup.add(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
    return markup

def services_keyboard(server_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🟢 واتساب (WhatsApp)", callback_data=f"srv_app_{server_id}_wa"))
    markup.add(InlineKeyboardButton("🔵 تليجرام (Telegram)", callback_data=f"srv_app_{server_id}_tg"))
    markup.add(InlineKeyboardButton("📸 إنستغرام (Instagram)", callback_data=f"srv_app_{server_id}_ig"))
    markup.add(InlineKeyboardButton("🎵 تيك توك (TikTok)", callback_data=f"srv_app_{server_id}_tk"))
    markup.add(InlineKeyboardButton("🔙 العودة لقائمة السيرفرات", callback_data="buy_number"))
    return markup

def countries_keyboard_fast(server_id, service_code, page=0):
    markup = InlineKeyboardMarkup(row_width=2)
    prices = fetch_server_prices(server_id, service_code)

    items = list(prices.items())
    country_counts = {}
    formatted_list = []

    for code, price in items:
        base_name, flag = get_clean_country_info(code)
        country_counts[base_name] = country_counts.get(base_name, 0) + 1
        count = country_counts[base_name]
        
        if count == 1:
            display_name = f"{base_name} {flag}"
        else:
            display_name = f"{base_name} {count} {flag}"
            
        button_text = f"{display_name} : ${price:.2f}"
        callback_data = f"b_{server_id}_{service_code}_{code}"
        formatted_list.append((button_text, callback_data))

    per_page = 16
    total_pages = (len(formatted_list) + per_page - 1) // per_page if formatted_list else 1
    page = max(0, min(page, total_pages - 1))
    current_items = formatted_list[page * per_page : (page + 1) * per_page]

    buttons = [InlineKeyboardButton(text, callback_data=cdata) for text, cdata in current_items]
    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"pg_{server_id}_{service_code}_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="ignore"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"pg_{server_id}_{service_code}_{page+1}"))

    markup.row(*nav_buttons)
    markup.add(InlineKeyboardButton("🔙 العودة لاختيار التطبيق", callback_data=f"select_server_{server_id}"))
    return markup

def active_number_keyboard(tz_id, server_id):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🔄 تغيير الرقم", callback_data=f"change_num_{server_id}_{tz_id}"))
    markup.row(InlineKeyboardButton("📩 طلب الكود", callback_data=f"check_sms_{server_id}_{tz_id}"))
    markup.row(InlineKeyboardButton("✖️ إلغاء الطلب واسترجاع المبلغ", callback_data=f"cancel_num_{server_id}_{tz_id}"))
    return markup

def smm_main_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🚁 شحن الالعاب والبرامج", callback_data="games_menu"))
    markup.add(InlineKeyboardButton("❤️ الرشق وزيادة المتابعين", callback_data="boost_menu"))
    markup.add(InlineKeyboardButton("🔙 الصفحة الرئيسية", callback_data="back_main"))
    return markup

def games_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🎮 PUBG MOBIL", callback_data="game_pubg"),
        InlineKeyboardButton("🎮 PUBG NEWSTATE", callback_data="game_newstate"),
        InlineKeyboardButton("🔥 FREEFIRE", callback_data="game_freefire"),
        InlineKeyboardButton("🔥 PIN FREEFIRE", callback_data="game_pin_ff"),
        InlineKeyboardButton("🏰 CLASH OF CLANS", callback_data="game_coc"),
        InlineKeyboardButton("⚔️ MOBILE LEGENDS", callback_data="game_mlbb"),
        InlineKeyboardButton("💀 BRAWL STARS", callback_data="game_brawl"),
        InlineKeyboardButton("🏆 LORDS MOBILE", callback_data="game_lords"),
        InlineKeyboardButton("🌌 GENSHIN IMPACT", callback_data="game_genshin"),
        InlineKeyboardButton("🎯 FORTNITE", callback_data="game_fortnite"),
        InlineKeyboardButton("🤖 ROBLOX", callback_data="game_roblox"),
        InlineKeyboardButton("🔙 رجوع", callback_data="smm_main")
    )
    return markup

def boost_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("📱 - رشق تيليجرام . telegram", callback_data="smmc_telegram"),
        InlineKeyboardButton("📸 - رشق انستا . instagram", callback_data="smmc_instagram"),
        InlineKeyboardButton("▶️ - رشق يوتيوب . youtube", callback_data="smmc_youtube"),
        InlineKeyboardButton("🐦 - رشق تويتر . twitter", callback_data="smmc_twitter"),
        InlineKeyboardButton("📘 - رشق فيسبوك . facebook", callback_data="smmc_facebook"),
        InlineKeyboardButton("🎵 - رشق تيك توك . tiktok", callback_data="smmc_tiktok"),
        InlineKeyboardButton("👤 - رشق ثريدز . threads", callback_data="smmc_threads"),
        InlineKeyboardButton("🟢 - واتس اب . whatsapp", callback_data="smmc_whatsapp"),
        InlineKeyboardButton("➕ - خدمات اخرى . other services", callback_data="smmc_others"),
        InlineKeyboardButton("🔙 رجوع", callback_data="smm_main")
    )
    return markup

def smm_service_detail_keyboard(srv_id):
    """كيبورد عرض تفاصيل الخدمة قبل طلب الرابط"""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🛒 طلب هذه الخدمة", callback_data=f"smm_order_{srv_id}"))
    markup.add(InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="boost_menu"))
    return markup

def dynamic_smm_keyboard(services_list, category_code, page=0):
    markup = InlineKeyboardMarkup(row_width=1)
    
    per_page = 8
    total_pages = (len(services_list) + per_page - 1) // per_page if services_list else 1
    page = max(0, min(page, total_pages - 1))
    current_items = services_list[page * per_page : (page + 1) * per_page]
    
    for srv in current_items:
        srv_id = srv.get('service')
        name = str(srv.get('name', 'بدون اسم'))
        rate = float(srv.get('rate', 0))
        
        # إضافة نسبة الربح 10% وتنسيق السعر
        price_with_profit = round(rate * 1.10, 3)
        
        # قص الاسم حتى 22 حرفًا لضمان ظهور السعر بوضوح وعدم اقتطاعه بواسطة تلجرام
        short_name = name[:22] + ".." if len(name) > 22 else name
        display_text = f"{short_name} ▻ ${price_with_profit}"
        
        markup.add(InlineKeyboardButton(display_text, callback_data=f"smmbuy_{srv_id}"))
        
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"smmp_{category_code}_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="ignore"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"smmp_{category_code}_{page+1}"))
        
    markup.row(*nav_buttons)
    markup.add(InlineKeyboardButton("🔙 رجوع للأقسام", callback_data="boost_menu"))
    return markup

def smm_confirm_keyboard(srv_id, quantity, total_price):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ تأكيد الطلب", callback_data=f"smm_confirm_{srv_id}_{quantity}_{total_price}"),
        InlineKeyboardButton("❌ إلغاء", callback_data="boost_menu")
    )
    return markup
