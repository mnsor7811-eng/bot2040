import math
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_ID, SERVERS, fetch_server_prices, get_clean_country_info

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

def servers_keyboard(user_id=None):
    markup = InlineKeyboardMarkup()
    is_admin = (str(user_id) == str(ADMIN_ID)) if user_id else False
    for idx, (srv_id, srv_info) in enumerate(SERVERS.items(), start=1):
        srv_name = srv_info['name'] if is_admin else f"⚙️ سيرفر الأرقام {idx}"
        markup.add(InlineKeyboardButton(srv_name, callback_data=f"select_server_{srv_id}"))
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
        try:
            p_val = float(price)
        except (ValueError, TypeError):
            p_val = 0.0
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


def smm_servers_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🚀 سيرفر سمم تون (SMMStone)", callback_data="select_smm_srv_1"))
    markup.add(InlineKeyboardButton("🚀 سيرفر سمم اكسترا (SMMExtra)", callback_data="select_smm_srv_2"))
    markup.add(InlineKeyboardButton("🚀 سيرفر سمم فلورس (SMMFollows)", callback_data="select_smm_srv_3"))
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="smm_main"))
    return markup


def boost_keyboard(smm_server_id="2"):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("📱 - رشق تيليجرام . telegram", callback_data=f"smmc_{smm_server_id}_telegram"),
        InlineKeyboardButton("📸 - رشق انستا . instagram", callback_data=f"smmc_{smm_server_id}_instagram"),
        InlineKeyboardButton("▶️ - رشق يوتيوب . youtube", callback_data=f"smmc_{smm_server_id}_youtube"),
        InlineKeyboardButton("🐦 - رشق تويتر . twitter", callback_data=f"smmc_{smm_server_id}_twitter"),
        InlineKeyboardButton("📘 - رشق فيسبوك . facebook", callback_data=f"smmc_{smm_server_id}_facebook"),
        InlineKeyboardButton("🎵 - رشق تيك توك . tiktok", callback_data=f"smmc_{smm_server_id}_tiktok"),
        InlineKeyboardButton("👤 - رشق ثريدز . threads", callback_data=f"smmc_{smm_server_id}_threads"),
        InlineKeyboardButton("🟢 - واتس اب . whatsapp", callback_data=f"smmc_{smm_server_id}_whatsapp"),
        InlineKeyboardButton("➕ - خدمات اخرى . other services", callback_data=f"smmc_{smm_server_id}_others"),
        InlineKeyboardButton("🔙 رجوع لاختيار السيرفر", callback_data="smm_servers_menu")
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
    per_page = 20
    total_pages = (len(services_list) + per_page - 1) // per_page if services_list else 1
    page = max(0, min(page, total_pages - 1))
    current_items = services_list[page * per_page : (page + 1) * per_page]
    
    for srv in current_items:
        srv_id = srv.get('service')
        raw_name = str(srv.get('name', 'بدون اسم'))
        translated_name = translate_text(raw_name)
        try:
            rate = float(srv.get('rate', 0))
        except (ValueError, TypeError):
            rate = 0.0
        price_with_profit = round(rate * 1.10, 3)
        short_name = translated_name[:45] + ("..." if len(translated_name) > 45 else "")
        display_text = f"💰 {price_with_profit}$ | {short_name}"
        markup.add(InlineKeyboardButton(display_text, callback_data=f"smmbuy_{smm_server_id}_{srv_id}"))
        
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"smmp_{smm_server_id}_{category_code}_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="ignore"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"smmp_{smm_server_id}_{category_code}_{page+1}"))
        
    if nav_buttons:
        markup.row(*nav_buttons)
    markup.add(InlineKeyboardButton("🔙 رجوع للأقسام", callback_data=f"select_smm_srv_{smm_server_id}"))
    return markup

def smm_service_detail_keyboard(srv_id, smm_server_id="2"):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("❇️ : طلب الخدمة", callback_data=f"smm_order_{smm_server_id}_{srv_id}"))
    markup.add(InlineKeyboardButton("⭐ : إضافة للمفضلة", callback_data=f"fav_add_{srv_id}"))
    markup.add(InlineKeyboardButton(f"📋 ID {srv_id}", callback_data="ignore"))
    markup.add(InlineKeyboardButton("🔄 رجوع", callback_data=f"select_smm_srv_{smm_server_id}"))
    return markup

def smm_detail_grid_keyboard(service_id, price, speed, quality, guarantee, min_q, max_q, smm_server_id="2"):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("- ⬇️ بيانات الخدمة ⬇️ -", callback_data="ignore"))
    markup.row(InlineKeyboardButton(f"{price}$", callback_data="ignore"), InlineKeyboardButton("💰 : سعر 1K", callback_data="ignore"))
    markup.row(InlineKeyboardButton(f"{speed}", callback_data="ignore"), InlineKeyboardButton("🚀 : السرعة", callback_data="ignore"))
    markup.row(InlineKeyboardButton(f"{quality}", callback_data="ignore"), InlineKeyboardButton("🏆 : الجودة", callback_data="ignore"))
    markup.row(InlineKeyboardButton(f"{guarantee}", callback_data="ignore"), InlineKeyboardButton("♻️ : الضمان", callback_data="ignore"))
    markup.row(InlineKeyboardButton(f"{min_q}", callback_data="ignore"), InlineKeyboardButton("📊 : الحد الأدنى", callback_data="ignore"))
    markup.row(InlineKeyboardButton(f"{max_q}", callback_data="ignore"), InlineKeyboardButton("📉 : الحد الأقصى", callback_data="ignore"))
    markup.add(InlineKeyboardButton("❇️ : طلب الخدمة", callback_data=f"smm_order_{smm_server_id}_{service_id}"))
    markup.add(InlineKeyboardButton("⭐ : إضافة للمفضلة", callback_data=f"fav_add_{service_id}"))
    markup.add(InlineKeyboardButton(f"📋 ID {service_id}", callback_data="ignore"))
    markup.add(InlineKeyboardButton("🔄 رجوع", callback_data=f"select_smm_srv_{smm_server_id}"))
    return markup

def smm_confirm_keyboard(srv_id, quantity, total_price, smm_server_id="2"):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ تأكيد الطلب", callback_data=f"smm_confirm_{smm_server_id}_{srv_id}_{quantity}_{total_price}"),
        InlineKeyboardButton("❌ إلغاء", callback_data=f"select_smm_srv_{smm_server_id}")
    )
    return markup
