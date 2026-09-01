import math
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import (
    ADMIN_ID, SERVERS, CHANNEL_OFFICIAL_URL, CHANNEL_ORDERS_URL,
    fetch_server_prices, get_clean_country_info, fetch_ready_accounts_api
)

# ==================== دالة الترجمة التلقائية للخدمات والأقسام ====================
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

# ==================== القوائم الرئيسية للأزرار ====================
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

# ==================== لوحة الإدارة الكبرى ====================
def admin_panel_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("⚡ شحن رصيد ذاتي لي (يدوي)", callback_data="admin_self_charge_manual")
    )
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
    markup.row(
        InlineKeyboardButton("🛠️ وضع الصيانة", callback_data="admin_toggle_maintenance")
    )
    markup.row(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
    return markup

# ==================== قائمة الإعدادات والمزيد (مطابقة للصورة 8) ====================
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
    markup.row(
        InlineKeyboardButton("🔄 طلب تعويض لجميع طلباتي", callback_data="request_refill_all")
    )
    markup.row(
        InlineKeyboardButton("🔍 كشف طلب", callback_data="check_single_order"),
        InlineKeyboardButton("📜 الشروط والتعليمات", callback_data="terms_and_rules")
    )
    markup.row(
        InlineKeyboardButton("❌ إلغاء طلب", callback_data="cancel_single_order")
    )
    markup.row(
        InlineKeyboardButton("🔙 رجوع", callback_data="back_main")
    )
    return markup

# ==================== قائمة سيرفرات الحسابات الجاهزة (بدون ذكر المزودين) ====================
def ready_accounts_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🦁 السيرفر 1", callback_data="ready_server_1"))
    markup.add(InlineKeyboardButton("🕷️ السيرفر 2", callback_data="ready_server_2"))
    markup.add(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
    return markup

def ready_accounts_countries_keyboard(server_id='1', page=0):
    markup = InlineKeyboardMarkup(row_width=2)
    countries = fetch_ready_accounts_api(server_id)
    
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
    nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="ignore"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"readypg_{server_id}_{page+1}"))

    if nav_buttons:
        markup.row(*nav_buttons)
    markup.add(InlineKeyboardButton("🔙 العودة لاختيار السيرفر", callback_data="ready_accounts_menu"))
    return markup

# ==================== بطاقة تفاصيل شراء الحساب الجاهز (مطابقة للصورة 7) ====================
def ready_account_detail_keyboard(server_id, country_name, price):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("• شـbuyـراء •", callback_data=f"do_buy_ready_{server_id}_{country_name}_{price}"))
    markup.add(InlineKeyboardButton("• ↩️ عودة •", callback_data=f"ready_server_{server_id}"))
    return markup

# ==================== سيرفرات عروض تيليجرام المباشرة (بدون أسماء المزودين) ====================
def tg_servers_keyboard():
    markup = InlineKeyboardMarkup()
    for idx, (srv_id, srv_info) in enumerate(SERVERS.items(), start=1):
        markup.add(InlineKeyboardButton(f"🔵 سيرفر تليجرام {idx}", callback_data=f"srv_app_{srv_id}_tg"))
    markup.add(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
    return markup

def recharge_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🏦 بنك الكريمي", callback_data="pay_kuraimi"))
    markup.add(InlineKeyboardButton("📱 محفظة جيب", callback_data="pay_jeeb"))
    markup.add(InlineKeyboardButton("💳 محفظة ون كاش", callback_data="pay_onecash"))
    markup.add(InlineKeyboardButton("🟡 Binance (تلقائي)", callback_data="pay_binance"))
    markup.add(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
    return markup

def servers_keyboard(user_id=None):
    markup = InlineKeyboardMarkup()
    for idx, (srv_id, srv_info) in enumerate(SERVERS.items(), start=1):
        markup.add(InlineKeyboardButton(f"⚙️ سيرفر الأرقام {idx}", callback_data=f"select_server_{srv_id}"))
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
        display_name = f"{base_name} {flag}" if count == 1 else f"{base_name} {count} {flag}"
        try: p_val = float(price)
        except: p_val = 0.0
        button_text = f"{display_name} : ${p_val:.2f}"
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
    markup.add(InlineKeyboardButton("❤️ الرشق وزيادة المتابعين", callback_data="smm_servers_menu"))
    markup.add(InlineKeyboardButton("🔙 الصفحة الرئيسية", callback_data="back_main"))
    return markup

def boost_keyboard(smm_server_id="2"):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("📱 - رشق تيليجرام . telegram", callback_data="smmc_2_telegram"),
        InlineKeyboardButton("📸 - رشق انستا . instagram", callback_data="smmc_2_instagram"),
        InlineKeyboardButton("▶️ - رشق يوتيوب . youtube", callback_data="smmc_2_youtube"),
        InlineKeyboardButton("🐦 - رشق تويتر . twitter", callback_data="smmc_2_twitter"),
        InlineKeyboardButton("📘 - رشق فيسبوك . facebook", callback_data="smmc_2_facebook"),
        InlineKeyboardButton("🎵 - رشق تيك توك . tiktok", callback_data="smmc_2_tiktok"),
        InlineKeyboardButton("👤 - رشق ثريدز . threads", callback_data="smmc_2_threads"),
        InlineKeyboardButton("🟢 - واتس اب . whatsapp", callback_data="smmc_2_whatsapp"),
        InlineKeyboardButton("➕ - خدمات اخرى . other services", callback_data="smmc_2_others"),
        InlineKeyboardButton("🔙 رجوع", callback_data="smm_main")
    )
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

def dynamic_smm_keyboard(services_list, category_code, page=0, smm_server_id="2"):
    markup = InlineKeyboardMarkup(row_width=1)
    per_page = 15
    total_pages = (len(services_list) + per_page - 1) // per_page if services_list else 1
    page = max(0, min(page, total_pages - 1))
    current_items = services_list[page * per_page : (page + 1) * per_page]
    
    for srv in current_items:
        srv_id = srv.get('service')
        raw_name = str(srv.get('name', 'بدون اسم'))
        translated_name = translate_text(raw_name)
        try: rate = float(srv.get('rate', 0))
        except: rate = 0.0
        price_with_profit = round(rate * 1.10, 4)
        short_name = translated_name[:45] + ("..." if len(translated_name) > 45 else "")
        display_text = f"💰 {price_with_profit}$ | {short_name}"
        markup.add(InlineKeyboardButton(display_text, callback_data=f"smmbuy_2_{srv_id}_{category_code}"))
        
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"smmp_2_{category_code}_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="ignore"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"smmp_2_{category_code}_{page+1}"))
        
    if nav_buttons:
        markup.row(*nav_buttons)
    markup.add(InlineKeyboardButton("🔙 رجوع للأقسام", callback_data="smm_servers_menu"))
    return markup

def smm_detail_grid_keyboard(service_id, price, speed, quality, guarantee, min_q, max_q, category_code="others", smm_server_id="2"):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("⬇️ - بيانات الخدمة - ⬇️", callback_data="ignore"))
    markup.row(InlineKeyboardButton(f"{price:.4f}$", callback_data="ignore"), InlineKeyboardButton("💰 : سعر 1K", callback_data="ignore"))
    markup.row(InlineKeyboardButton(f"{speed}", callback_data="ignore"), InlineKeyboardButton("🚀 : السرعة", callback_data="ignore"))
    markup.row(InlineKeyboardButton(f"{quality}", callback_data="ignore"), InlineKeyboardButton("🏆 : الجودة", callback_data="ignore"))
    markup.row(InlineKeyboardButton(f"{guarantee}", callback_data="ignore"), InlineKeyboardButton("♻️ : الضمان", callback_data="ignore"))
    markup.row(InlineKeyboardButton(f"{min_q} ⚜️", callback_data="ignore"), InlineKeyboardButton("📊 : الحد الادنى", callback_data="ignore"))
    markup.row(InlineKeyboardButton(f"{max_q} ✔️", callback_data="ignore"), InlineKeyboardButton("📉 : الحد الاقصى", callback_data="ignore"))
    markup.add(InlineKeyboardButton("✳️ : طلب الخدمة", callback_data=f"smm_order_2_{service_id}_{category_code}"))
    markup.add(InlineKeyboardButton("⭐ : إضافة للمفضلة", callback_data=f"fav_add_{service_id}"))
    markup.add(InlineKeyboardButton(f"📋 ID {service_id}", callback_data="ignore"))
    markup.add(InlineKeyboardButton("🔄 رجوع", callback_data=f"smmc_2_{category_code}"))
    return markup

def smm_cancel_link_keyboard(service_id, category_code):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔄 رجوع", callback_data=f"smmbuy_2_{service_id}_{category_code}"))
    return markup

def smm_confirm_keyboard(srv_id, quantity, total_price, category_code="others", smm_server_id="2"):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("☑️ - تأكيد الطلب", callback_data=f"smm_confirm_2_{srv_id}_{quantity}_{total_price}_{category_code}"))
    markup.add(InlineKeyboardButton("⚠️ - إلغاء الطلب", callback_data=f"smmc_2_{category_code}"))
    return markup

def smm_order_status_keyboard(order_id, service_id, qty, total_cost, link, category_name, service_name):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("♻️ - تحديث الطلب", callback_data=f"smm_stat_{order_id}"))
    markup.add(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
    return markup
