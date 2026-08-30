import math
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from config import SERVERS, ADMIN_ID, get_clean_country_info, fetch_server_prices, DEFAULT_PRICE

def main_keyboard(user_id=None):
    markup = InlineKeyboardMarkup(row_width=2)
    
    btn_ai = InlineKeyboardButton("🤖 اشتراكات برامج AI", callback_data="ai_landing")
    btn_buy = InlineKeyboardButton("📞 شراء رقم افتراضي", callback_data="buy_number")
    markup.row(btn_ai, btn_buy)

    btn_whats = InlineKeyboardButton("🟢 عروض WhatsApp", callback_data="fast_buy_wa")
    btn_tele = InlineKeyboardButton("🔵 جاهز Telegram", callback_data="fast_buy_tg")
    markup.row(btn_whats, btn_tele)

    btn_best = InlineKeyboardButton("🔥 السيرفرات الأكثر مبيعاً", callback_data="best_selling")
    btn_more = InlineKeyboardButton("🎲 الأكثر توفراً", callback_data="most_available")
    markup.row(btn_best, btn_more)

    btn_recharge = InlineKeyboardButton("🎳 شحن الرصيد / الاشتراكات", callback_data="recharge_menu")
    markup.row(btn_recharge)

    btn_smm = InlineKeyboardButton("🚀 الرشق وشحـن الألعاب والبرامج", callback_data="smm_main")
    markup.row(btn_smm)

    btn_free = InlineKeyboardButton("💎 اربح رصيد مجاناً", callback_data="free_ruble")
    btn_transfer = InlineKeyboardButton("🔄 تحويل الرصيد", callback_data="transfer")
    markup.row(btn_free, btn_transfer)

    btn_support = InlineKeyboardButton("🎧 الدعم", callback_data="support")
    btn_mart = InlineKeyboardButton("✔ إحصائيات الشراء الناجح", callback_data="purchase_stats")
    markup.row(btn_support, btn_mart)

    btn_account = InlineKeyboardButton("👤 حسابي", callback_data="my_account")
    btn_other = InlineKeyboardButton("🛸 خدمات وميزات أخرى", callback_data="other_services")
    markup.row(btn_account, btn_other)

    if user_id and str(user_id) == str(ADMIN_ID):
        btn_admin = InlineKeyboardButton("⚙️ لوحة الإدارة الكبرى", callback_data="admin_panel")
        markup.row(btn_admin)

    return markup

def back_button():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
    return markup

def admin_back_button():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 العودة للوحة الإدارة", callback_data="admin_panel"))
    return markup

def recharge_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🟡 Binance Pay (تلقائي)", callback_data="deposit_binance"),
        InlineKeyboardButton("🇾🇪 تحويل كريمي (اليمن)", callback_data="pay_kuraimi"),
        InlineKeyboardButton("🟢 تحويل جوال (اليمن)", callback_data="pay_jawwal"),
        InlineKeyboardButton("🔴 تحويل ون كاش", callback_data="pay_onecash"),
        InlineKeyboardButton("🇸🇦 تحويل الراجحي (السعودية)", callback_data="pay_rajhi"),
        InlineKeyboardButton("💵 USDT (TRC20)", callback_data="pay_usdt"),
        InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main")
    )
    return markup

def servers_keyboard():
    markup = InlineKeyboardMarkup()
    for srv_id, srv in SERVERS.items():
        markup.add(InlineKeyboardButton(f"⚙️ {srv['name']}", callback_data=f"select_server_{srv_id}"))
    markup.add(InlineKeyboardButton("🔙 إلغاء والعودة", callback_data="back_main"))
    return markup

def services_keyboard(server_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🟢 واتساب (WhatsApp)", callback_data=f"srv_app_{server_id}_wa"),
        InlineKeyboardButton("🔵 تيليجرام (Telegram)", callback_data=f"srv_app_{server_id}_tg"),
        InlineKeyboardButton("🟣 انستغرام (Instagram)", callback_data=f"srv_app_{server_id}_ig"),
        InlineKeyboardButton("🎵 تيك توك (TikTok)", callback_data=f"srv_app_{server_id}_lf"),
        InlineKeyboardButton("🔴 يوتيوب (YouTube)", callback_data=f"srv_app_{server_id}_yo"),
        InlineKeyboardButton("📘 فيسبوك (Facebook)", callback_data=f"srv_app_{server_id}_fb"),
        InlineKeyboardButton("❌ تويتر (X / Twitter)", callback_data=f"srv_app_{server_id}_tw"),
        InlineKeyboardButton("🟡 إيمو (Imo)", callback_data=f"srv_app_{server_id}_imo"),
        InlineKeyboardButton("🔙 العودة لسيرفرات الأرقام", callback_data="buy_number")
    )
    return markup

def countries_keyboard_fast(server_id, srv_code, page=0):
    markup = InlineKeyboardMarkup(row_width=2)
    prices = fetch_server_prices(server_id, srv_code)
    
    countries_list = []
    for c_code, p_val in prices.items():
        c_name, c_flag = get_clean_country_info(c_code)
        countries_list.append((c_code, c_name, c_flag, p_val))

    countries_list.sort(key=lambda x: x[3])

    items_per_page = 10
    total_pages = math.ceil(len(countries_list) / items_per_page) if countries_list else 1
    start = page * items_per_page
    end = start + items_per_page
    page_items = countries_list[start:end]

    for c_code, c_name, c_flag, price in page_items:
        btn_text = f"{c_name} {c_flag} | ${price:.2f}"
        callback_data = f"b_{server_id}_{srv_code}_{c_code}"
        markup.add(InlineKeyboardButton(btn_text, callback_data=callback_data))

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"pg_{server_id}_{srv_code}_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="ignore"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"pg_{server_id}_{srv_code}_{page+1}"))

    if nav_buttons:
        markup.row(*nav_buttons)

    markup.add(InlineKeyboardButton("🔙 العودة للتطبيقات", callback_data=f"select_server_{server_id}"))
    return markup

def active_number_keyboard(tz_id, server_id):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🔄 تحديث / جلب الكود", callback_data=f"check_sms_{server_id}_{tz_id}"),
        InlineKeyboardButton("🔄 تغيير الرقم (طلب جديد)", callback_data=f"change_num_{server_id}_{tz_id}"),
        InlineKeyboardButton("❌ إلغاء الطلب واسترجاع الرصيد", callback_data=f"cancel_num_{server_id}_{tz_id}")
    )
    return markup

def smm_main_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🚀 خدمات الرشق والدعم", callback_data="smm_servers_menu"),
        InlineKeyboardButton("🎮 شحن الألعاب وبرامج بلاس", callback_data="games_menu"),
        InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main")
    )
    return markup

# كيبورد اختيار سيرفر الرشق والمتابعين
def smm_servers_select_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🇾🇪 السيرفر الأول (عربي - SMMXStar)", callback_data="select_smm_prov_1"),
        InlineKeyboardButton("🌐 السيرفر الثاني (SMMStone)", callback_data="select_smm_prov_2"),
        InlineKeyboardButton("🚀 السيرفر الثالث (SMMFollows)", callback_data="select_smm_prov_3"),
        InlineKeyboardButton("🔙 رجوع", callback_data="smm_main")
    )
    return markup

def boost_keyboard(provider_id="1"):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🔵 خدمات تليجرام", callback_data=f"smmc_{provider_id}_telegram"),
        InlineKeyboardButton("🟣 خدمات انستغرام", callback_data=f"smmc_{provider_id}_instagram"),
        InlineKeyboardButton("🎵 خدمات تيك توك", callback_data=f"smmc_{provider_id}_tiktok"),
        InlineKeyboardButton("🔴 خدمات يوتيوب", callback_data=f"smmc_{provider_id}_youtube"),
        InlineKeyboardButton("📘 خدمات فيسبوك", callback_data=f"smmc_{provider_id}_facebook"),
        InlineKeyboardButton("❌ خدمات تويتر X", callback_data=f"smmc_{provider_id}_twitter"),
        InlineKeyboardButton("🧵 خدمات ثريدز", callback_data=f"smmc_{provider_id}_threads"),
        InlineKeyboardButton("🟢 خدمات واتساب", callback_data=f"smmc_{provider_id}_whatsapp"),
        InlineKeyboardButton("🔙 العودة لسيرفرات الرشق", callback_data="smm_servers_menu")
    )
    return markup

def games_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🔥 ببجي موبايل (PUBG)", callback_data="game_pubg"),
        InlineKeyboardButton("💎 فري فاير (Free Fire)", callback_data="game_ff"),
        InlineKeyboardButton("⚽ ببجي نيواستيت", callback_data="game_ns"),
        InlineKeyboardButton("🎮 لودو ستار (Ludo)", callback_data="game_ludo"),
        InlineKeyboardButton("🔙 العودة لقسم الرشق", callback_data="smm_main")
    )
    return markup

def dynamic_smm_keyboard(services, category_code, provider_id="1", page=0):
    markup = InlineKeyboardMarkup(row_width=1)
    items_per_page = 8
    total_pages = math.ceil(len(services) / items_per_page) if services else 1
    
    start = page * items_per_page
    end = start + items_per_page
    page_items = services[start:end]

    for srv in page_items:
        srv_id = srv.get('service')
        name = srv.get('name', 'خدمة غير محددة')
        rate = float(srv.get('rate', 0))
        price_with_profit = round(rate * 1.10, 3) 
        
        btn_text = f"{name} ▻ ${price_with_profit}"
        markup.add(InlineKeyboardButton(btn_text, callback_data=f"smmbuy_{provider_id}_{srv_id}"))

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"smmp_{provider_id}_{category_code}_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="ignore"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"smmp_{provider_id}_{category_code}_{page+1}"))

    if nav_buttons:
        markup.row(*nav_buttons)

    markup.add(InlineKeyboardButton("🔙 العودة للأقسام", callback_data=f"select_smm_prov_{provider_id}"))
    return markup

def smm_detail_grid_keyboard(provider_id, service_id, price, speed, quality, guarantee, min_q, max_q):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(f"💵 السعر/1000: ${price}", callback_data="ignore"),
        InlineKeyboardButton(f"⚡ السرعة: {speed}", callback_data="ignore"),
        InlineKeyboardButton(f"⭐️ الجودة: {quality}", callback_data="ignore"),
        InlineKeyboardButton(f"♻️ الضمان: {guarantee}", callback_data="ignore"),
        InlineKeyboardButton(f"📉 الحد الأدنى: {min_q}", callback_data="ignore"),
        InlineKeyboardButton(f"📈 الحد الأقصى: {max_q}", callback_data="ignore")
    )
    markup.add(InlineKeyboardButton("⭐ إضافة إلى المفضلة", callback_data=f"fav_add_{service_id}"))
    markup.add(InlineKeyboardButton("🛍️ طلب هذه الخدمة الآن", callback_data=f"smm_order_{provider_id}_{service_id}"))
    markup.add(InlineKeyboardButton("🔙 العودة للخدمات", callback_data=f"select_smm_prov_{provider_id}"))
    return markup

def smm_confirm_keyboard(provider_id, service_id, qty, total_cost):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ تأكيد الشراء", callback_data=f"smm_confirm_{provider_id}_{service_id}_{qty}_{total_cost}"),
        InlineKeyboardButton("❌ إلغاء", callback_data="smm_main")
    )
    return markup
