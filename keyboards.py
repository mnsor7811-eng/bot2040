import math
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import (
    ADMIN_ID, SERVERS, CHANNEL_OFFICIAL_URL, CHANNEL_ORDERS_URL,
    fetch_server_prices, get_clean_country_info, fetch_ready_accounts_api,
    is_section_enabled, get_setting, get_payment_methods_db, get_providers_db, get_agents_db,
    POPULAR_SERVICES
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

# زر المتجر الرئيسي (الأقسام الثلاثة)
def get_store_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🎁 بطاقات الهدايا", callback_data="cat_giftcards"),
        InlineKeyboardButton("🎮 شحن الألعاب", callback_data="cat_gaming"),
        InlineKeyboardButton("🌐 خدمات الإنترنت والبرمجيات", callback_data="cat_services"),
        InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_main")
    )
    return markup

# كيبورد العودة للمتجر
def get_back_to_store_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🔙 عودة للمتجر", callback_data="store_menu")
    )
    return markup

def main_keyboard(user_id):
    markup = InlineKeyboardMarkup()
    
    # 1. الأزرار الصغيرة المتقابلة: عروض واتساب يقابله عروض تيليجرام
    row_offers = []
    if is_section_enabled('offers_whatsapp'):
        row_offers.append(InlineKeyboardButton("🟢 عروض WhatsApp", callback_data="fast_buy_wa"))
    if is_section_enabled('offers_telegram'):
        row_offers.append(InlineKeyboardButton("🔵 عروض Telegram", callback_data="fast_buy_tg_servers"))
    if row_offers:
        markup.row(*row_offers)

    # 2. شراء أرقام وهمية يقابله اشتراكات البرامج والذكاء الاصطناعي
    row_numbers_ai = []
    if is_section_enabled('numbers'):
        row_numbers_ai.append(InlineKeyboardButton("📞 شراء أرقام وهمية", callback_data="buy_number"))
    if is_section_enabled('ai'):
        row_numbers_ai.append(InlineKeyboardButton("🤖 اشتراكات AI والبرامج", callback_data="ai_landing"))
    if row_numbers_ai:
        markup.row(*row_numbers_ai)

    # 3. الأزرار الكبيرة المستقلة (كل زر بسطر كامل واضح وبارز)
    # زر الحسابات الجاهزة كبير لحاله
    if is_section_enabled('ready'):
        markup.row(InlineKeyboardButton("💯 قسم حسابات تيليجرام الجاهزة 🚀", callback_data="ready_accounts_menu"))

    # زر شحن الرصيد والاشتراكات كبير لحاله
    if is_section_enabled('recharge'):
        markup.row(InlineKeyboardButton("🎳 شحن الرصيد / وسائل الدفع 💳", callback_data="recharge_menu"))

    # 4. باقي الأقسام في عمودين متناسقين
    row_store_smm = []
    if is_section_enabled('store'):
        row_store_smm.append(InlineKeyboardButton("🛍️ المتجر والخدمات الرقمية", callback_data="store_menu"))
    if is_section_enabled('smm'):
        row_store_smm.append(InlineKeyboardButton("🚀 خدمات الرشق والألعاب", callback_data="smm_main"))
    if row_store_smm:
        markup.row(*row_store_smm)

    row_free_transfer = []
    if is_section_enabled('free'):
        row_free_transfer.append(InlineKeyboardButton("💎 اربح رصيد مجانا", callback_data="free_ruble"))
    if is_section_enabled('transfer'):
        row_free_transfer.append(InlineKeyboardButton("🔄 تحويل الرصيد", callback_data="transfer"))
    if row_free_transfer:
        markup.row(*row_free_transfer)

    # الحساب والدعم الفني
    markup.row(
        InlineKeyboardButton("👤 حسابي ورصيدي", callback_data="my_account"),
        InlineKeyboardButton("🎧 الدعم الفني", callback_data="support")
    )

    # إحصائيات التفعيلات والإعدادات
    markup.row(
        InlineKeyboardButton("✔️ إحصائيات التفعيلات", callback_data="purchase_stats"),
        InlineKeyboardButton("⚙️ الإعدادات والمزيد", callback_data="more_settings_menu")
    )
    
    # زر لوحة الإدارة الكبرى للمشرف فقط (زر كامل وبارز)
    if str(user_id) == str(ADMIN_ID):
        markup.row(InlineKeyboardButton("👑 لوحة الإدارة والتحكم الكبرى ⚙️", callback_data="admin_panel"))
    return markup

def back_button():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
    return markup

def admin_back_button():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 رجوع لوحة الإدارة", callback_data="admin_panel"))
    return markup

# ==================== لوحة الإدارة الكبرى الشاملة ====================
def admin_panel_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🎛️ تشغيل/إغلاق الأقسام", callback_data="adm_sections"),
        InlineKeyboardButton("📈 نسب الأرباح (% الربح)", callback_data="adm_profits")
    )
    markup.row(
        InlineKeyboardButton("💳 إدارة طرق الدفع والحسابات", callback_data="adm_payments"),
        InlineKeyboardButton("🌐 إدارة المزودين ومفاتيح API", callback_data="adm_providers")
    )
    markup.row(
        InlineKeyboardButton("📢 إدارة القنوات والاشتراك", callback_data="adm_channels"),
        InlineKeyboardButton("🤝 إدارة الوكلاء والموزعين", callback_data="adm_agents")
    )
    markup.row(
        InlineKeyboardButton("🎧 إدارة حسابات الدعم", callback_data="adm_support"),
        InlineKeyboardButton("🔄 إعدادات تحويل الرصيد", callback_data="adm_transfer")
    )
    markup.row(
        InlineKeyboardButton("💎 إعدادات (شارك واربح)", callback_data="adm_referrals"),
        InlineKeyboardButton("📦 مخزون الحسابات القديمة (3)", callback_data="adm_aged_stock")
    )
    markup.row(
        InlineKeyboardButton("💰 إضافة رصيد لمستخدم", callback_data="admin_add_balance"),
        InlineKeyboardButton("➖ خصم رصيد من مستخدم", callback_data="admin_deduct_balance")
    )
    markup.row(
        InlineKeyboardButton("⚡ شحن رصيد ذاتي لي", callback_data="admin_self_charge_manual"),
        InlineKeyboardButton("🔍 البحث وكشف مستخدم", callback_data="admin_search_user")
    )
    markup.row(
        InlineKeyboardButton("🚫 تقييد / فك تقييد عضو", callback_data="admin_ban_menu"),
        InlineKeyboardButton("📢 إذاعة عامة (Broadcast)", callback_data="admin_broadcast")
    )
    markup.row(
        InlineKeyboardButton("👥 عرض جميع المستخدمين", callback_data="admin_all_users"),
        InlineKeyboardButton("📊 الإحصائيات الشاملة", callback_data="admin_stats")
    )
    markup.row(
        InlineKeyboardButton("🛠️ وضع الصيانة العام", callback_data="admin_toggle_maintenance"),
        InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_main")
    )
    markup.row(
        InlineKeyboardButton("💾 تحميل نسخة احتياطية من البيانات", callback_data="adm_backup_db"),
        InlineKeyboardButton("🔍 استعادة تلقائية من السيرفر 🔄", callback_data="adm_recover_db")
    )
    markup.row(
        InlineKeyboardButton("📥 رفع واستعادة نسخة احتياطية", callback_data="adm_upload_db"),
        InlineKeyboardButton("📢 فحص وتجربة قناة التفعيلات", callback_data="adm_test_channel")
    )
    return markup

def admin_users_pagination_keyboard(page=0, total_pages=1):
    markup = InlineKeyboardMarkup()
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"adm_users_pg_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="ignore"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"adm_users_pg_{page+1}"))
    if len(nav_buttons) > 1:
        markup.row(*nav_buttons)
    markup.row(InlineKeyboardButton("🔙 رجوع لوحة الإدارة", callback_data="admin_panel"))
    return markup

# 1. كيبورد تشغيل وإغلاق الأقسام
def admin_sections_keyboard():
    markup = InlineKeyboardMarkup()
    sections = [
        ('offers_whatsapp', '🟢 عروض WhatsApp'),
        ('offers_telegram', '🔵 عروض Telegram'),
        ('numbers', '📞 أرقام وهمية'),
        ('ready', '💯 حسابات جاهزة'),
        ('smm', '🚀 خدمات الرشق والألعاب'),
        ('recharge', '🎳 شحن الرصيد'),
        ('transfer', '🔄 تحويل الرصيد'),
        ('free', '💎 شارك واربح'),
        ('store', '🛍️ المتجر الرقمي'),
        ('ai', '🤖 اشتراكات AI')
    ]
    for sec_key, sec_name in sections:
        st = "✅ مفعل" if is_section_enabled(sec_key) else "❌ معطل"
        markup.row(
            InlineKeyboardButton(f"{sec_name}: {st}", callback_data=f"adm_tgl_sec_{sec_key}")
        )
    markup.row(InlineKeyboardButton("🔙 رجوع لوحة الإدارة", callback_data="admin_panel"))
    return markup

# 2. كيبورد نسب الأرباح
def admin_profits_keyboard():
    markup = InlineKeyboardMarkup()
    p_num = float(get_setting('profit_margin_numbers', '0.10')) * 100
    p_ready = float(get_setting('profit_margin_ready', '0.10')) * 100
    p_smm = float(get_setting('profit_margin_smm', '0.10')) * 100
    
    markup.row(InlineKeyboardButton(f"📞 ربح الأرقام: {p_num:.1f}% ✏️", callback_data="adm_set_profit_numbers"))
    markup.row(InlineKeyboardButton(f"💯 ربح الحسابات الجاهزة: {p_ready:.1f}% ✏️", callback_data="adm_set_profit_ready"))
    markup.row(InlineKeyboardButton(f"🚀 ربح الرشق SMM: {p_smm:.1f}% ✏️", callback_data="adm_set_profit_smm"))
    markup.row(InlineKeyboardButton("🔙 رجوع لوحة الإدارة", callback_data="admin_panel"))
    return markup

# 3. كيبورد إدارة طرق الدفع
def admin_payments_keyboard():
    markup = InlineKeyboardMarkup()
    methods = get_payment_methods_db()
    for m_id, m in methods.items():
        st = "✅" if m['is_active'] else "❌"
        markup.row(
            InlineKeyboardButton(f"{m['name']} {st}", callback_data=f"adm_pay_detail_{m_id}")
        )
    markup.row(InlineKeyboardButton("➕ إضافة وسيلة دفع جديدة", callback_data="adm_add_payment_method"))
    markup.row(InlineKeyboardButton("🔙 رجوع لوحة الإدارة", callback_data="admin_panel"))
    return markup

def admin_payment_detail_keyboard(m_id):
    markup = InlineKeyboardMarkup()
    methods = get_payment_methods_db()
    m = methods.get(m_id, {})
    st_btn = "تعطيل ❌" if m.get('is_active') else "تفعيل ✅"
    markup.row(InlineKeyboardButton(f"حالة الوسيلة: {st_btn}", callback_data=f"adm_pay_tgl_{m_id}"))
    markup.row(InlineKeyboardButton("✏️ تعديل رقم الحساب / المحفظة", callback_data=f"adm_pay_edit_acc_{m_id}"))
    markup.row(InlineKeyboardButton("✏️ تعديل سعر الصرف", callback_data=f"adm_pay_edit_rate_{m_id}"))
    markup.row(InlineKeyboardButton("✏️ تعديل الحد الأدنى", callback_data=f"adm_pay_edit_min_{m_id}"))
    markup.row(InlineKeyboardButton("🔙 رجوع لقائمة طرق الدفع", callback_data="adm_payments"))
    return markup

# 4. كيبورد إدارة المزودين ومفاتيح API
def admin_providers_keyboard():
    markup = InlineKeyboardMarkup()
    prvs = get_providers_db()
    for p_id, p in prvs.items():
        st = "🟢" if p['is_active'] else "🔴"
        markup.row(InlineKeyboardButton(f"{st} {p['name']}", callback_data=f"adm_prv_detail_{p_id}"))
    markup.row(InlineKeyboardButton("➕ إضافة موقع / مزود جديد", callback_data="adm_add_provider"))
    markup.row(InlineKeyboardButton("🔙 رجوع لوحة الإدارة", callback_data="admin_panel"))
    return markup

def admin_provider_detail_keyboard(p_id):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🔑 تعديل مفتاح API Key", callback_data=f"adm_prv_edit_key_{p_id}"))
    markup.row(InlineKeyboardButton("🗑️ حذف هذا المزود", callback_data=f"adm_prv_delete_{p_id}"))
    markup.row(InlineKeyboardButton("🔙 رجوع لقائمة المزودين", callback_data="adm_providers"))
    return markup

# 5. كيبورد إدارة القنوات
def admin_channels_keyboard():
    markup = InlineKeyboardMarkup()
    sub_st = "✅ مفعل" if get_setting('force_sub_active', '1') == '1' else "❌ معطل"
    markup.row(InlineKeyboardButton(f"الاشتراك الإجباري: {sub_st}", callback_data="adm_tgl_force_sub"))
    markup.row(InlineKeyboardButton("📢 تعديل القناة الرسمية", callback_data="adm_edit_ch_official"))
    markup.row(InlineKeyboardButton("🛍️ تعديل قناة التفعيلات والطلبات", callback_data="adm_edit_ch_orders"))
    markup.row(InlineKeyboardButton("🧪 فحص وإرسال تجربة لقناة التفعيلات", callback_data="adm_test_channel"))
    markup.row(InlineKeyboardButton("🔙 رجوع لوحة الإدارة", callback_data="admin_panel"))
    return markup

# 6. كيبورد إدارة الوكلاء
def admin_agents_keyboard():
    markup = InlineKeyboardMarkup()
    agents = get_agents_db()
    for ag in agents:
        markup.row(InlineKeyboardButton(f"👤 {ag[1]} (خصم {ag[2]}%) ❌ حذف", callback_data=f"adm_del_agent_{ag[0]}"))
    markup.row(InlineKeyboardButton("➕ إضافة وكيل جديد بالآيدي", callback_data="adm_add_agent_input"))
    markup.row(InlineKeyboardButton("🔙 رجوع لوحة الإدارة", callback_data="admin_panel"))
    return markup

# 7. كيبورد الدعم الفني
def admin_support_keyboard():
    markup = InlineKeyboardMarkup()
    sup1 = get_setting('support_admin_1', '@Num_s7')
    sup2 = get_setting('support_admin_2', '@Support_SMS7')
    markup.row(InlineKeyboardButton(f"👤 الدعم 1: {sup1} ✏️", callback_data="adm_edit_sup_1"))
    markup.row(InlineKeyboardButton(f"👤 الدعم 2: {sup2} ✏️", callback_data="adm_edit_sup_2"))
    markup.row(InlineKeyboardButton("🔙 رجوع لوحة الإدارة", callback_data="admin_panel"))
    return markup

# 8. كيبورد إعدادات تحويل الرصيد
def admin_transfer_keyboard():
    markup = InlineKeyboardMarkup()
    min_t = get_setting('min_transfer_amount', '1.0')
    fee_t = get_setting('transfer_fee_percent', '0.0')
    markup.row(InlineKeyboardButton(f"💵 الحد الأدنى للتحويل: ${min_t} ✏️", callback_data="adm_edit_transfer_min"))
    markup.row(InlineKeyboardButton(f"📊 عمولة التحويل: {fee_t}% ✏️", callback_data="adm_edit_transfer_fee"))
    markup.row(InlineKeyboardButton("🔙 رجوع لوحة الإدارة", callback_data="admin_panel"))
    return markup

# 9. كيبورد إعدادات شارك واربح
def admin_referrals_keyboard():
    markup = InlineKeyboardMarkup()
    rew = get_setting('reward_per_invite', '0.05')
    min_w = get_setting('min_invite_withdraw', '1.0')
    markup.row(InlineKeyboardButton(f"🎁 مكافأة الإحالة الواحدة: ${rew} ✏️", callback_data="adm_edit_ref_reward"))
    markup.row(InlineKeyboardButton(f"🏧 الحد الأدنى لسحب الأرباح: ${min_w} ✏️", callback_data="adm_edit_ref_min"))
    markup.row(InlineKeyboardButton("🔙 رجوع لوحة الإدارة", callback_data="admin_panel"))
    return markup

# 10. كيبورد مخزون السيرفر 3
def admin_aged_stock_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("➕ إضافة حساب قديم للمخزون الفوري", callback_data="adm_add_aged_account"))
    markup.row(InlineKeyboardButton("📋 عرض الطلبات المعلقة للتسليم اليدوي", callback_data="adm_view_aged_orders"))
    markup.row(InlineKeyboardButton("🔙 رجوع لوحة الإدارة", callback_data="admin_panel"))
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
    markup.add(InlineKeyboardButton("السيرفر 3 (حسابات قديمة)", callback_data="ready_server_3"))
    markup.add(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
    return markup

def ready_aged_years_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("5-60 day", callback_data="aged_age_5-60day"),
        InlineKeyboardButton("60-180 day", callback_data="aged_age_60-180day")
    )
    markup.row(
        InlineKeyboardButton("2025", callback_data="aged_age_2025"),
        InlineKeyboardButton("2024", callback_data="aged_age_2024"),
        InlineKeyboardButton("2023", callback_data="aged_age_2023"),
        InlineKeyboardButton("2022", callback_data="aged_age_2022")
    )
    markup.row(
        InlineKeyboardButton("2021", callback_data="aged_age_2021"),
        InlineKeyboardButton("2020", callback_data="aged_age_2020"),
        InlineKeyboardButton("2019", callback_data="aged_age_2019"),
        InlineKeyboardButton("2018", callback_data="aged_age_2018")
    )
    markup.row(
        InlineKeyboardButton("2017", callback_data="aged_age_2017"),
        InlineKeyboardButton("2016", callback_data="aged_age_2016"),
        InlineKeyboardButton("2015", callback_data="aged_age_2015"),
        InlineKeyboardButton("2014", callback_data="aged_age_2014")
    )
    markup.add(InlineKeyboardButton("• رجوع •", callback_data="ready_accounts_menu"))
    return markup

def ready_accounts_countries_keyboard(server_id='1', age=None, page=0):
    markup = InlineKeyboardMarkup(row_width=2)
    countries = fetch_ready_accounts_api(server_id, age=age)
    
    back_cb = "ready_server_3" if str(server_id) == "3" and age else "ready_accounts_menu"
    refresh_cb = f"readyref_{server_id}_{age or 'none'}"

    if not countries:
        markup.add(InlineKeyboardButton("🔄 إعادة المحاولة وتحديث البيانات", callback_data=refresh_cb))
        markup.add(InlineKeyboardButton("🔙 العودة لاختيار السيرفر", callback_data=back_cb))
        return markup

    per_page = 20
    total_pages = (len(countries) + per_page - 1) // per_page if countries else 1
    page = max(0, min(page, total_pages - 1))
    current_items = countries[page * per_page : (page + 1) * per_page]

    buttons = []
    for item in current_items:
        c_name = item['name']
        price = item['price']
        code = item['code']
        btn_text = f"{c_name} : ${price:.2f}"
        callback_data = f"view_ready_{server_id}_{code}_{age or 'none'}"
        buttons.append(InlineKeyboardButton(btn_text, callback_data=callback_data))

    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"readypg_{server_id}_{age or 'none'}_{page-1}"))
    if total_pages > 1:
        nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="ignore"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"readypg_{server_id}_{age or 'none'}_{page+1}"))

    if nav_buttons:
        markup.row(*nav_buttons)
    markup.row(
        InlineKeyboardButton("🔄 تحديث المخزون", callback_data=refresh_cb),
        InlineKeyboardButton("🔙 العودة للخلف", callback_data=back_cb)
    )
    return markup

def ready_account_detail_keyboard(server_id, country_code, age=None):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("• شراء الحساب الآن 🛍️ •", callback_data=f"do_buy_ready_{server_id}_{country_code}_{age or 'none'}"))
    back_cb = f"readypg_{server_id}_{age or 'none'}_0"
    markup.add(InlineKeyboardButton("• ↩️ عودة لقائمة الدول •", callback_data=back_cb))
    return markup

def ready_account_code_keyboard(server_id, number_or_hash):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📩 جلب كود التفعيل / كلمة السر", callback_data=f"get_ready_code_{server_id}_{number_or_hash}"))
    markup.add(InlineKeyboardButton("🔙 العودة لقائمة الحسابات", callback_data="ready_accounts_menu"))
    return markup

def tg_servers_keyboard():
    markup = InlineKeyboardMarkup()
    for idx, (srv_id, srv_info) in enumerate(SERVERS.items(), start=1):
        markup.add(InlineKeyboardButton(f"🔵 سيرفر تليجرام {idx}", callback_data=f"tg_srv_{srv_id}"))
    markup.add(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
    return markup

def wa_servers_keyboard():
    markup = InlineKeyboardMarkup()
    for idx, (srv_id, srv_info) in enumerate(SERVERS.items(), start=1):
        markup.add(InlineKeyboardButton(f"🟢 سيرفر واتساب {idx}", callback_data=f"wa_srv_{srv_id}"))
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

def binance_amount_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("↩️ رجوع", callback_data="recharge_menu"))
    return markup

def binance_details_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📋 نسخ العنوان", callback_data="copy_binance_addr"))
    markup.add(InlineKeyboardButton("✅ تم الدفع (أدخل TXID)", callback_data="binance_enter_txid"))
    markup.add(InlineKeyboardButton("↩️ رجوع", callback_data="recharge_menu"))
    return markup

def binance_txid_input_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("↩️ رجوع", callback_data="binance_back_to_details"))
    return markup

def binance_txid_fail_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🔄 إعادة إدخال TXID", callback_data="binance_retry_txid"),
        InlineKeyboardButton("↩️ رجوع", callback_data="recharge_menu")
    )
    return markup

def servers_keyboard(user_id=None):
    markup = InlineKeyboardMarkup()
    for idx, (srv_id, srv_info) in enumerate(SERVERS.items(), start=1):
        markup.add(InlineKeyboardButton(f"⚙️ سيرفر الأرقام {idx}", callback_data=f"select_server_{srv_id}"))
    markup.add(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
    return markup

def services_keyboard(server_id):
    markup = InlineKeyboardMarkup()
    buttons = []
    for srv_code, srv_data in POPULAR_SERVICES.items():
        btn_text = f"{srv_data['icon']} {srv_data['name']}"
        buttons.append(InlineKeyboardButton(btn_text, callback_data=f"srv_app_{server_id}_{srv_code}"))
    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])
    markup.add(InlineKeyboardButton("🔙 العودة لقائمة السيرفرات", callback_data="buy_number"))
    return markup

def countries_keyboard_fast(server_id, service_code, page=0, origin=None):
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
    prev_cb = f"pg_{server_id}_{service_code}_{page-1}_{origin}" if origin else f"pg_{server_id}_{service_code}_{page-1}"
    next_cb = f"pg_{server_id}_{service_code}_{page+1}_{origin}" if origin else f"pg_{server_id}_{service_code}_{page+1}"

    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=prev_cb))
    nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="ignore"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=next_cb))

    markup.row(*nav_buttons)

    # زر الرجوع الذكي: يعود للسيرفرات فوراً إذا كان من عروض تيليجرام أو واتساب
    if origin == "tg":
        markup.add(InlineKeyboardButton("🔙 العودة لقائمة سيرفرات تليجرام", callback_data="fast_buy_tg_servers"))
    elif origin == "wa":
        markup.add(InlineKeyboardButton("🔙 العودة لقائمة سيرفرات واتساب", callback_data="fast_buy_wa"))
    else:
        markup.add(InlineKeyboardButton("🔙 العودة لاختيار التطبيق", callback_data=f"select_server_{server_id}"))

    return markup

def active_number_keyboard(tz_id, server_id, service_code='wa', phone=''):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🔄 تغيير الرقم", callback_data=f"change_num_{server_id}_{tz_id}"))
    markup.row(InlineKeyboardButton("📩 طلب الكود", callback_data=f"check_sms_{server_id}_{tz_id}"))
    
    clean_num = str(phone).replace("+", "").replace(" ", "").strip()
    if service_code.lower() == 'wa' and clean_num:
        markup.row(InlineKeyboardButton("↗️ تحقق من الرقم في WhatsApp", url=f"https://wa.me/{clean_num}"))
    elif service_code.lower() == 'tg' and clean_num:
        markup.row(InlineKeyboardButton("↗️ فتح الرقم في Telegram", url=f"tg://resolve?phone={clean_num}"))
        
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
