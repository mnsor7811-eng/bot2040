import math
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import (
    ADMIN_ID, SERVERS, CHANNEL_OFFICIAL_URL, CHANNEL_ORDERS_URL,
    fetch_server_prices, get_clean_country_info, fetch_ready_accounts_api
)

def translate_text(text: str) -> str:
    translations = {
        "instagram": "إنستغرام", "telegram": "تيليجرام", "tiktok": "تيك توك",
        "youtube": "يوتيوب", "facebook": "فيسبوك", "twitter": "تويتر (X)",
        "x": "تويتر (X)", "pubg": "ببجي", "free fire": "فري فاير",
        "services": "خدمات", "category": "قسم", "followers": "متابعين",
        "follower": "متابع", "likes": "إعجابات", "like": "إعجاب",
        "views": "مشاهدات", "view": "مشاهدة", "comments": "تعليقات",
        "comment": "تعليق", "subscribers": "مشتركين", "subscriber": "مشترك",
        "members": "أعضاء", "member": "عضو", "shares": "مشاركات",
        "repost": "إعادة نشر", "story": "ستوري", "reel": "ريلز",
        "live": "بث مباشر", "bot": "بوتات", "real": "حقيقي",
        "active": "نشط", "cheap": "رخيص", "fast": "سريع",
        "instant": "فوري", "non drop": "بدون نقص", "no drop": "بدون نقص",
        "refill": "مع ضمان تعويض", "guarantee": "ضمان", "target": "مستهدف",
        "arab": "عربي", "organic": "عضوي", "high quality": "جودة عالية",
        "hq": "جودة عالية", "best": "الأفضل", "speed": "سرعة فائقة"
    }
    translated = str(text)
    for en, ar in translations.items():
        translated = translated.replace(en, ar).replace(en.capitalize(), ar).replace(en.upper(), ar)
    return translated

def main_keyboard(user_id):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🤖 اشتراكات برامج AI", callback_data="ai_landing"))
    markup.row(InlineKeyboardButton("📞 شراء أرقام وهمية", callback_data="buy_number"), InlineKeyboardButton("🔵 عروض Telegram", callback_data="fast_buy_tg_servers"))
    markup.row(InlineKeyboardButton("💯 حسابات تيليجرام جاهزة", callback_data="ready_accounts_menu"))
    markup.row(InlineKeyboardButton("🔥 السيرفرات الأكثر مبيعاً", callback_data="best_selling"), InlineKeyboardButton("🟢 عروض WhatsApp", callback_data="fast_buy_wa"))
    markup.row(InlineKeyboardButton("🎳 شحن الرصيد / الاشتراكات", callback_data="recharge_menu"), InlineKeyboardButton("🎲 الأكثر توفراً", callback_data="most_available"))
    markup.row(InlineKeyboardButton("🚀 الرشق وشحن الألعاب والبرامج", callback_data="smm_main"))
    markup.row(InlineKeyboardButton("💎 اربح رصيد مجانا", callback_data="free_ruble"))
    markup.row(InlineKeyboardButton("🎧 الدعم", callback_data="support"), InlineKeyboardButton("🔄 تحويل الرصيد", callback_data="transfer"))
    markup.row(InlineKeyboardButton("✔ إحصائيات الشراء الناجح", callback_data="purchase_stats"))
    markup.row(InlineKeyboardButton("👤 حسابي", callback_data="my_account"))
    markup.row(InlineKeyboardButton("⚙️ الإعدادات والمزيد", callback_data="more_settings_menu"))
    
    if str(user_id) == str(ADMIN_ID):
        markup.row(InlineKeyboardButton("👑 لوحة الإدارة الكبرى ⚙️", callback_data="admin_panel"))
    return markup

def back_button():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
    return markup

def admin_back_button():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 رجوع لوحة الإدارة", callback_data="admin_panel"))
    return markup

def admin_panel_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("⚡ شحن رصيد ذاتي لي (يدوي)", callback_data="admin_self_charge_manual"))
    markup.row(
        InlineKeyboardButton("💰 إضافة رصيد لمستخدم", callback_data="admin_add_balance"),
        InlineKeyboardButton("➖ خصم رصيد من مستخدم", callback_data="admin_deduct_balance")
    )
    markup.row(
        InlineKeyboardButton("🔍 البحث عن مستخدم", callback_data="admin_search_user"),
        InlineKeyboardButton("👥 عرض جميع المستخدمين", callback_data="admin_all_users")
    )
    markup.row(
        InlineKeyboardButton("🤖 شحن أسئلة AI", callback_data="admin_add_ai"),
        InlineKeyboardButton("🚫 حظر / فك حظر", callback_data="admin_ban_menu")
    )
    markup.row(
        InlineKeyboardButton("📊 الإحصائيات الشاملة", callback_data="admin_stats"),
        InlineKeyboardButton("📢 إذاعة عامة (Broadcast)", callback_data="admin_broadcast")
    )
    markup.row(
        InlineKeyboardButton("📦 أحدث طلبات الرشق", callback_data="admin_recent_smm"),
        InlineKeyboardButton("📞 أحدث طلبات الأرقام", callback_data="admin_recent_numbers")
    )
    markup.row(InlineKeyboardButton("🛠️ وضع الصيانة", callback_data="admin_toggle_maintenance"))
    markup.row(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
    return markup

def more_settings_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("📢 قناة البوت الرسمية", url=CHANNEL_OFFICIAL_URL),
        InlineKeyboardButton("🛍️ قناة التفعيلات والطلبات", url=CHANNEL_ORDERS_URL)
    )
    markup.row(
        InlineKeyboardButton("📊 الإحصائيات", callback_data="purchase_stats"),
        InlineKeyboardButton("📦 طلباتي", callback_data="my_orders_menu")
    )
    markup.row(InlineKeyboardButton("🔄 طلب تعويض لجميع طلباتي", callback_data="request_refill_all"))
    markup.row(
        InlineKeyboardButton("🔍 كشف طلب", callback_data="check_single_order"),
        InlineKeyboardButton("📜 الشروط والتعليمات", callback_data="terms_and_rules")
    )
    markup.row(InlineKeyboardButton("❌ إلغاء طلب", callback_data="cancel_single_order"))
    markup.row(InlineKeyboardButton("🔙 رجوع", callback_data="back_main"))
    return markup

def ready_accounts_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("السيرفر 1", callback_data="ready_server_1"))
    markup.add(InlineKeyboardButton("السيرفر 2", callback_data="ready_server_2"))
    markup.add(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
    return markup

def ready_accounts_countries_keyboard(server_id='1', page=0):
    markup = InlineKeyboardMarkup(row_width=2)
    countries = fetch_ready_accounts_api(server_id)
    
    if not countries:
        markup.add(InlineKeyboardButton("🔄 تحديث وجلب الحسابات من المزود", callback_data=f"ready_server_{server_id}"))
        markup.add(InlineKeyboardButton("🔙 العودة لاختيار السيرفر", callback_data="ready_accounts_menu"))
        return markup

    per_page = 10
    total_pages = (len(countries) + per_page - 1) // per_page if countries else 1
    page = max(0, min(page, total_pages - 1))
    current_items = countries[page * per_page : (page + 1) * per_page]

    buttons = []
    for item in current_items:
        c_name = item['name']
        price = item['price']
        btn_text = f"{c_name} : ${price:.2f}"
        callback_data = f"view_ready_{server_id}_{c_name}_{price}_{item['count']}"
        buttons.append(InlineKeyboardButton(btn_text, callback_data=callback_data))

    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"readypg_{server_id}_{page-1}"))
    if total_pages > 1:
        nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="ignore"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"readypg_{server_id}_{page+1}"))

    if nav_buttons:
        markup.row(*nav_buttons)
    markup.add(InlineKeyboardButton("🔙 العودة لاختيار السيرفر", callback_data="ready_accounts_menu"))
    return markup

def ready_account_detail_keyboard(server_id, country_name, price):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("• شـbuyـراء •", callback_data=f"do_buy_ready_{server_id}_{country_name}_{price}"))
    markup.add(InlineKeyboardButton("• ↩️ عودة •", callback_data=f"ready_server_{server_id}"))
    return markup

def tg_servers_keyboard():
    markup = InlineKeyboardMarkup()
    for idx, (srv_id, srv_info) in enumerate(SERVERS.items(), start=1):
        markup.add(InlineKeyboardButton(f"🔵 سيرفر تليجرام {idx}", callback_data=f"srv_app_{srv_id}_tg"))
    markup.add(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
    return markup

def servers_keyboard():
    markup = InlineKeyboardMarkup()
    for srv_id, srv_info in SERVERS.items():
        markup.add(InlineKeyboardButton(srv_info['name'], callback_data=f"srv_{srv_id}"))
    markup.add(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
    return markup

def services_keyboard(server_id):
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("🔵 Telegram", callback_data=f"srv_app_{server_id}_tg"),
        InlineKeyboardButton("🟢 WhatsApp", callback_data=f"srv_app_{server_id}_wa"),
        InlineKeyboardButton("🟣 Viber", callback_data=f"srv_app_{server_id}_vi"),
        InlineKeyboardButton("📸 Instagram", callback_data=f"srv_app_{server_id}_ig"),
        InlineKeyboardButton("📘 Facebook", callback_data=f"srv_app_{server_id}_fb"),
        InlineKeyboardButton("🎵 TikTok", callback_data=f"srv_app_{server_id}_lf"),
        InlineKeyboardButton("🐦 Twitter", callback_data=f"srv_app_{server_id}_tw"),
        InlineKeyboardButton("💬 Discord", callback_data=f"srv_app_{server_id}_ds"),
        InlineKeyboardButton("🔍 خدمات أخرى", callback_data=f"srv_app_{server_id}_ot")
    ]
    markup.add(*buttons)
    markup.add(InlineKeyboardButton("🔙 رجوع لاختيار السيرفر", callback_data="buy_number"))
    return markup

def countries_keyboard_fast(server_id, service_code, page=0):
    markup = InlineKeyboardMarkup(row_width=2)
    prices = fetch_server_prices(server_id, service_code)
    
    country_list = []
    if prices:
        for c_code, price in prices.items():
            name, flag = get_clean_country_info(c_code)
            country_list.append((c_code, name, flag, price))
    
    per_page = 10
    total_pages = (len(country_list) + per_page - 1) // per_page if country_list else 1
    page = max(0, min(page, total_pages - 1))
    current_items = country_list[page * per_page : (page + 1) * per_page]

    buttons = []
    for c_code, name, flag, price in current_items:
        btn_text = f"{flag} {name} (${price:.2f})"
        callback_data = f"buy_{server_id}_{service_code}_{c_code}_{price}"
        buttons.append(InlineKeyboardButton(btn_text, callback_data=callback_data))

    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"page_{server_id}_{service_code}_{page-1}"))
    if total_pages > 1:
        nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="ignore"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"page_{server_id}_{service_code}_{page+1}"))

    if nav_buttons:
        markup.row(*nav_buttons)
    markup.add(InlineKeyboardButton("🔙 رجوع لاختيار الخدمة", callback_data=f"srv_{server_id}"))
    return markup

def recharge_keyboard():
    markup = InlineKeyboardMarkup()
    for method_key, info in PAYMENT_DETAILS.items():
        markup.add(InlineKeyboardButton(f"{info['name']} - تحويل", callback_data=f"pay_{method_key}"))
    markup.add(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
    return markup

def binance_amount_keyboard():
    markup = InlineKeyboardMarkup(row_width=3)
    amounts = [1, 2, 5, 10, 20, 50]
    buttons = [InlineKeyboardButton(f"${amt}", callback_data=f"bin_amt_{amt}") for amt in amounts]
    markup.add(*buttons)
    markup.add(InlineKeyboardButton("✏️ مبلغ مخصص", callback_data="bin_amt_custom"))
    markup.add(InlineKeyboardButton("🔙 رجوع لوسائل الدفع", callback_data="recharge_menu"))
    return markup

def binance_details_keyboard(amount):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ لقد قمت بالتحويل (إدخال TxID)", callback_data=f"bin_paid_{amount}"))
    markup.add(InlineKeyboardButton("🔙 رجوع لاختيار المبلغ", callback_data="pay_binance"))
    return markup

def binance_txid_input_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 إلغاء والرجوع لوسائل الدفع", callback_data="recharge_menu"))
    return markup

def binance_txid_fail_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔄 إعادة المحاولة", callback_data="pay_binance"))
    markup.add(InlineKeyboardButton("🎧 مراسلة الدعم الفني", callback_data="support"))
    markup.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_main"))
    return markup

def active_number_keyboard(tz_id, server_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔄 تحديث الكود", callback_data=f"chk_{server_id}_{tz_id}"))
    markup.add(InlineKeyboardButton("❌ إلغاء واسترجاع الرصيد", callback_data=f"cnc_{server_id}_{tz_id}"))
    markup.add(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
    return markup

def smm_main_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🎮 قسم شحن الألعاب", callback_data="smm_games"))
    markup.row(InlineKeyboardButton("⭐ قسم دعم التليجرام (Boost / Stars)", callback_data="smm_boost"))
    markup.row(InlineKeyboardButton("🚀 سيرفر الرشق الأقوى 1", callback_data="smm_srv_2"))
    markup.row(InlineKeyboardButton("📦 متابعة حالة طلباتي", callback_data="my_orders_menu"))
    markup.row(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
    return markup

def games_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔫 شحن شدات ببجي (PUBG Mobile)", callback_data="game_pubg"))
    markup.add(InlineKeyboardButton("🔥 شحن جواهر فري فاير (Free Fire)", callback_data="game_ff"))
    markup.add(InlineKeyboardButton("🔙 رجوع لقسم الرشق", callback_data="smm_main"))
    return markup

def boost_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🚀 باقة دعم البوست (Boost Level 1-5)", callback_data="boost_level"))
    markup.add(InlineKeyboardButton("⭐ شحن نجوم التليجرام (Telegram Stars)", callback_data="boost_stars"))
    markup.add(InlineKeyboardButton("🔙 رجوع لقسم الرشق", callback_data="smm_main"))
    return markup

def smm_detail_grid_keyboard(services, server_id, category_name, page=0):
    markup = InlineKeyboardMarkup()
    per_page = 5
    total_pages = (len(services) + per_page - 1) // per_page if services else 1
    page = max(0, min(page, total_pages - 1))
    current_items = services[page * per_page : (page + 1) * per_page]

    for s in current_items:
        s_id = s.get('service')
        raw_rate = float(s.get('rate', 1.0))
        calc_rate = round(raw_rate * 1.10, 2)
        translated_name = translate_text(s.get('name', 'خدمة'))
        
        btn_text = f"🔹 {translated_name[:28]} | ${calc_rate}/1k"
        callback_data = f"smm_choose_{server_id}_{s_id}"
        markup.add(InlineKeyboardButton(btn_text, callback_data=callback_data))

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"smmcatpage_{server_id}_{page-1}"))
    if total_pages > 1:
        nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="ignore"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"smmcatpage_{server_id}_{page+1}"))

    if nav_buttons:
        markup.row(*nav_buttons)
    markup.add(InlineKeyboardButton("🔙 رجوع لاختيار القسم", callback_data=f"smm_srv_{server_id}"))
    return markup

def dynamic_smm_keyboard(categories, server_id, page=0):
    markup = InlineKeyboardMarkup()
    per_page = 8
    total_pages = (len(categories) + per_page - 1) // per_page if categories else 1
    page = max(0, min(page, total_pages - 1))
    current_items = categories[page * per_page : (page + 1) * per_page]

    for cat in current_items:
        trans_cat = translate_text(cat)
        markup.add(InlineKeyboardButton(f"📁 {trans_cat[:35]}", callback_data=f"smm_cat_{server_id}_{cat[:20]}"))

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"smmpage_{server_id}_{page-1}"))
    if total_pages > 1:
        nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="ignore"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"smmpage_{server_id}_{page+1}"))

    if nav_buttons:
        markup.row(*nav_buttons)
    markup.add(InlineKeyboardButton("🔙 رجوع لقسم الرشق", callback_data="smm_main"))
    return markup

def smm_confirm_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ تأكيد وتنفيذ الطلب", callback_data="smm_confirm_yes"),
        InlineKeyboardButton("❌ إلغاء", callback_data="smm_main")
    )
    return markup

def smm_cancel_link_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("❌ إلغاء والعودة للقائمة", callback_data="smm_main"))
    return markup

def smm_order_status_keyboard(order_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔄 فحص وتحديث الحالة", callback_data=f"smm_chk_{order_id}"))
    markup.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_main"))
    return markup
