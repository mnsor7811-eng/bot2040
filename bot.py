import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import requests
import time
import google.generativeai as genai

# ==================== 1. الإعدادات الأساسية ====================
TOKEN = '8927305428:AAHKVgxelqI1aEqeSE7wlKM6hkm5Y2JqUgs'
GEMINI_API_KEY = 'AQ.Ab8RN6IOLYCW3mnMh6H5le6Bc1pAG60TXO0IoxjpPcHvaFZHkg'
ADMIN_ID = 6113734300
ADMIN_USERNAME = "@Num_s7"

PROFIT_MARGIN = 0.10      # نسبة الربح 10%
DEFAULT_PRICE = 0.50      # سعر افتراضي
REWARD_PER_INVITE = 0.05  # قيمة مكافأة الدعوة ($0.05)
MIN_TRANSFER_AMOUNT = 1.0  # الحد الأدنى لتحويل الرصيد ($1)

PAYMENT_DETAILS = {
    'kuraimi': {'name': '🏦 بنك الكريمي', 'acc': '3134706987', 'min': '100 ريال', 'rate': '1$ = 550 ريال'},
    'jeeb': {'name': '📱 محفظة جيب', 'acc': '374468', 'min': '50 ريال', 'rate': '1$ = 550 ريال'},
    'onecash': {'name': '💳 محفظة ون كاش', 'acc': '140601836', 'min': '100 ريال', 'rate': '1$ = 550 ريال'},
    'binance': {'name': '🟡 بايننس باي (Binance Pay)', 'acc': '979808293', 'min': '0.5 $', 'rate': '1$ = 1$'}
}

SERVERS = {
    'grizzly': {
        'name': '🐻 سيرفر Grizzly SMS',
        'api_key': 'Aed7993f2abbded229628261c56746d5',
        'url': 'https://grizzlysms.com/stubs/handler_api.php'
    },
    'smsman': {
        'name': '🟢 سيرفر SMS-Man',
        'api_key': 'y-PEwx3CbW00xho3rU2XobIia195Oobo',
        'url': 'https://api.sms-man.com/control/'
    },
    '5sim': {
        'name': '🌐 سيرفر 5sim.biz',
        'api_key': 'ضع_مفتاح_5SIM_هنا',
        'url': 'https://5sim.biz/v1/user/'
    },
    'tigersms': {
        'name': '🐯 سيرفر Tiger SMS',
        'api_key': 'ضع_مفتاح_TIGER_هنا',
        'url': 'https://tiger-sms.com/stubs/handler_api.php'
    }
}

SMM_PANELS = {
    "1": {"name": "SMM X Star", "url": "https://smmxstar.com/api/v2", "api_key": "ضع_مفتاح_API_هنا"},
    "2": {"name": "Yemen Damkom", "url": "https://yemendamkom.com/api/v2", "api_key": "ضع_مفتاح_API_هنا"},
    "3": {"name": "SMM Stone", "url": "https://Smmstone.com/api/v2", "api_key": "ضع_مفتاح_API_هنا"}
}

# قاموس موسع وشامل مع دعم تحويل الأكواد
COUNTRY_MAP = {
    "0": {"name": "روسيا", "flag": "🇷🇺"}, "1": {"name": "أوكرانيا", "flag": "🇺🇦"},
    "2": {"name": "كازاخستان", "flag": "🇰🇿"}, "3": {"name": "الصين", "flag": "🇨🇳"},
    "4": {"name": "الفلبين", "flag": "🇵🇭"}, "5": {"name": "ميانمار", "flag": "🇲🇲"},
    "6": {"name": "إندونيسيا", "flag": "🇮🇩"}, "7": {"name": "ماليزيا", "flag": "🇲🇾"},
    "8": {"name": "كينيا", "flag": "🇰🇪"}, "9": {"name": "فيتنام", "flag": "🇻🇳"},
    "10": {"name": "قيرغيزستان", "flag": "🇰🇬"}, "11": {"name": "أوزبكستان", "flag": "🇺🇿"},
    "12": {"name": "كمبوديا", "flag": "🇰🇭"}, "13": {"name": "ألمانيا", "flag": "🇩🇪"},
    "14": {"name": "ليتوانيا", "flag": "🇱🇹"}, "15": {"name": "بولندا", "flag": "🇵🇱"},
    "16": {"name": "بريطانيا", "flag": "🇬🇧"}, "17": {"name": "مدغشقر", "flag": "🇲🇬"},
    "18": {"name": "سويسرا", "flag": "🇨🇭"}, "19": {"name": "نيجيريا", "flag": "🇳🇬"},
    "20": {"name": "هولندا", "flag": "🇳🇱"}, "21": {"name": "مصر", "flag": "🇪🇬"},
    "22": {"name": "الهند", "flag": "🇮🇳"}, "23": {"name": "ايرلندا", "flag": "🇮🇪"},
    "24": {"name": "لاتفيا", "flag": "🇱🇻"}, "25": {"name": "المغرب", "flag": "🇲🇦"},
    "26": {"name": "غانا", "flag": "🇬🇭"}, "27": {"name": "إسبانيا", "flag": "🇪🇸"},
    "28": {"name": "بلجيكا", "flag": "🇧🇪"}, "29": {"name": "باكستان", "flag": "🇵🇰"},
    "30": {"name": "ألبانيا", "flag": "🇦🇱"}, "31": {"name": "السويد", "flag": "🇸🇪"},
    "32": {"name": "رومانيا", "flag": "🇷🇴"}, "33": {"name": "كولومبيا", "flag": "🇨🇴"},
    "34": {"name": "إستونيا", "flag": "🇪🇪"}, "35": {"name": "أذربيجان", "flag": "🇦🇿"},
    "36": {"name": "كندا", "flag": "🇨🇦"}, "37": {"name": "مالي", "flag": "🇲🇱"},
    "38": {"name": "إثيوبيا", "flag": "🇪🇹"}, "39": {"name": "البرتغال", "flag": "🇵🇹"},
    "40": {"name": "بنغلاديش", "flag": "🇧🇩"}, "41": {"name": "تركيا", "flag": "🇹🇷"},
    "42": {"name": "التشيك", "flag": "🇨🇿"}, "43": {"name": "سريلانكا", "flag": "🇱🇰"},
    "44": {"name": "البيرو", "flag": "🇵🇪"}, "46": {"name": "تايلاند", "flag": "🇹🇭"},
    "47": {"name": "السعودية", "flag": "🇸🇦"}, "48": {"name": "العراق", "flag": "🇮🇶"},
    "49": {"name": "جنوب إفريقيا", "flag": "🇿🇦"}, "50": {"name": "ساحل العاج", "flag": "🇨🇮"},
    "51": {"name": "الأرجنتين", "flag": "🇦🇷"}, "52": {"name": "الأردن", "flag": "🇯🇴"},
    "53": {"name": "بيلاروسيا", "flag": "🇧🇾"}, "54": {"name": "نيبال", "flag": "🇳🇵"},
    "55": {"name": "فنلندا", "flag": "🇫🇮"}, "56": {"name": "المجر", "flag": "🇭🇺"},
    "57": {"name": "المكسيك", "flag": "🇲🇽"}, "58": {"name": "الجزائر", "flag": "🇩🇿"},
    "59": {"name": "أنغولا", "flag": "🇦🇴"}, "73": {"name": "البرازيل", "flag": "🇧🇷"},
    "78": {"name": "فرنسا", "flag": "🇫🇷"}, "86": {"name": "إيطاليا", "flag": "🇮🇹"},
    "95": {"name": "السودان", "flag": "🇸🇩"}, "101": {"name": "سوريا", "flag": "🇸🇾"},
    "110": {"name": "جورجيا", "flag": "🇬🇪"}, "111": {"name": "اليونان", "flag": "🇬🇷"},
    "112": {"name": "بوليفيا", "flag": "🇧🇴"}, "113": {"name": "تنزانيا", "flag": "🇹🇿"},
    "114": {"name": "الإمارات", "flag": "🇦🇪"}, "115": {"name": "أرمينيا", "flag": "🇦🇲"},
    "116": {"name": "البحرين", "flag": "🇧🇭"}, "117": {"name": "البرتغال", "flag": "🇵🇹"},
    "118": {"name": "سلطنة عمان", "flag": "🇴🇲"}, "119": {"name": "الكويت", "flag": "🇰🇼"},
    "120": {"name": "قطر", "flag": "🇶🇦"}, "121": {"name": "نيوزيلندا", "flag": "🇳🇿"},
    "122": {"name": "سنغافورة", "flag": "🇸🇬"}, "123": {"name": "تونس", "flag": "🇹🇳"},
    "124": {"name": "تشيلي", "flag": "🇨🇱"}, "154": {"name": "السنغال", "flag": "🇸🇳"},
    "161": {"name": "اليمن", "flag": "🇾🇪"}, "187": {"name": "أمريكا", "flag": "🇺🇸"}
}

def get_country_info(code_str):
    code_str = str(code_str)
    if code_str in COUNTRY_MAP:
        return COUNTRY_MAP[code_str]['name'], COUNTRY_MAP[code_str]['flag']
    
    # تحويل الأكواد الإضافية المجهولة
    sub_code = str(int(code_str) % 100) if code_str.isdigit() else code_str
    if sub_code in COUNTRY_MAP:
        return COUNTRY_MAP[sub_code]['name'], COUNTRY_MAP[sub_code]['flag']
        
    return f"دولة ممتازة ({code_str})", "🌐"

PRICES_CACHE = {}
CACHE_LAST_UPDATE = {}
CACHE_DURATION = 300 

USER_STEPS = {}

bot = telebot.TeleBot(TOKEN)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# ==================== 2. قاعدة البيانات ====================
def setup_db():
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        name TEXT,
                        balance REAL DEFAULT 0.0,
                        ai_balance INTEGER DEFAULT 5, 
                        is_banned INTEGER DEFAULT 0,
                        referred_by INTEGER DEFAULT 0
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS purchases (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        tz_id TEXT,
                        phone TEXT,
                        service TEXT,
                        cost REAL,
                        country_code TEXT,
                        status TEXT DEFAULT 'PENDING'
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS smm_orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        order_id TEXT,
                        service_name TEXT,
                        link TEXT,
                        quantity INTEGER,
                        cost REAL
                    )''')
    conn.commit()
    conn.close()

setup_db()

def get_db():
    return sqlite3.connect('bot_database.db', check_same_thread=False)

def get_or_create_user(user_id, name):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute('INSERT INTO users (user_id, name, balance, ai_balance, is_banned, referred_by) VALUES (?, ?, 0.0, 5, 0, 0)', (user_id, name))
        conn.commit()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
    conn.close()
    return user

def is_user_banned(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT is_banned FROM users WHERE user_id = ?', (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else 0

# ==================== 3. جلب الأسعار والطلبات ====================
def fetch_server_prices(server_id, service_code):
    key = f"{server_id}_{service_code}"
    now = time.time()
    
    if key in PRICES_CACHE and PRICES_CACHE[key] and (now - CACHE_LAST_UPDATE.get(key, 0)) < CACHE_DURATION:
        return PRICES_CACHE[key]

    srv = SERVERS.get(server_id)
    prices = {}
    
    if not srv or "ضع_مفتاح" in srv['api_key']:
        return prices

    try:
        if server_id in ['grizzly', 'tigersms']:
            url = f"{srv['url']}?api_key={srv['api_key']}&action=getPrices&service={service_code}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            res = requests.get(url, headers=headers, timeout=7).json()
            
            for c_code, services in res.items():
                if isinstance(services, dict) and service_code in services:
                    raw_cost = float(services[service_code].get('cost', 0))
                    count = int(services[service_code].get('count', 0))
                    if raw_cost > 0 and count > 0:
                        prices[str(c_code)] = round(raw_cost * (1 + PROFIT_MARGIN), 2)
    except Exception as e:
        print(f"Error fetching prices: {e}")
        return PRICES_CACHE.get(key, {})

    if prices:
        PRICES_CACHE[key] = prices
        CACHE_LAST_UPDATE[key] = now
        
    return prices

def grizzly_request(params, api_key, url):
    params['api_key'] = api_key
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        return response.text.strip()
    except Exception as e:
        return f"ERROR: {e}"

# ==================== 4. لوحات الأزرار ====================
def main_keyboard(user_id):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🤖 اشتراكات برامج AI", callback_data="ai_landing"))
    markup.row(InlineKeyboardButton("📞 شراء رقم افتراضي", callback_data="buy_number"))
    markup.row(InlineKeyboardButton("🔵 جاهز Telegram", callback_data="fast_buy_tg"), InlineKeyboardButton("🟢 عروض WhatsApp", callback_data="fast_buy_wa"))
    markup.row(InlineKeyboardButton("🔥 السيرفرات الأكثر مبيعاً", callback_data="best_selling"))
    markup.row(InlineKeyboardButton("🎳 شحن الرصيد / الاشتراكات", callback_data="recharge_menu"), InlineKeyboardButton("🎲 الأكثر توفراً", callback_data="most_available"))
    markup.row(InlineKeyboardButton("🚀 خدمات الرشق والألعاب (SMM)", callback_data="smm_main"))
    markup.row(InlineKeyboardButton("💎 اربح روبل مجاناً", callback_data="free_ruble"))
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

def recharge_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🏦 بنك الكريمي", callback_data="pay_kuraimi"))
    markup.add(InlineKeyboardButton("📱 محفظة جيب", callback_data="pay_jeeb"))
    markup.add(InlineKeyboardButton("💳 محفظة ون كاش", callback_data="pay_onecash"))
    markup.add(InlineKeyboardButton("🟡 بايننس باي (Binance Pay)", callback_data="pay_binance"))
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
    markup = InlineKeyboardMarkup()
    prices = fetch_server_prices(server_id, service_code)

    items = list(prices.items())
    per_page = 20
    total_pages = (len(items) + per_page - 1) // per_page if items else 1
    
    page = max(0, min(page, total_pages - 1))
    start_idx = page * per_page
    end_idx = start_idx + per_page
    current_items = items[start_idx:end_idx]

    buttons = []
    for code, price in current_items:
        c_name, c_flag = get_country_info(code)
        btn_text = f"🚀 {c_name} {c_flag} : ${price:.2f}"
        buttons.append(InlineKeyboardButton(btn_text, callback_data=f"b_{server_id}_{service_code}_{code}"))

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

def active_number_keyboard(tz_id, server_id, service_code="wa"):
    markup = InlineKeyboardMarkup()
    app_label = "تليجرام 🔵" if service_code.lower() == "tg" else "واتساب 🟢"
    
    markup.row(InlineKeyboardButton(f"📩 طلب كود {app_label}", callback_data=f"check_sms_{server_id}_{tz_id}"))
    markup.row(InlineKeyboardButton("🔄 تغيير الرقم", callback_data=f"change_num_{server_id}_{tz_id}"))
    markup.row(InlineKeyboardButton("✖️ إلغاء الطلب واسترجاع المبلغ", callback_data=f"cancel_num_{server_id}_{tz_id}"))
    return markup

# ==================== 5. معالجة الطلبات والأحداث ====================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or "المستخدم"
    
    if is_user_banned(user_id):
        bot.send_message(message.chat.id, "🚫 عذراً، لقد تم حظرك من استخدام هذا البوت.")
        return

    user_data = get_or_create_user(user_id, name)
    text = (f"💠 أهلاً بك عزيزي في البوت الشامل 💠\n\n"
            f"👤 حسابك: {ADMIN_USERNAME}\n"
            f"💰 رصيدك الحالي: ${user_data[2]:.2f}\n"
            f"🤖 رصيد أسئلة الذكاء: {user_data[3]} سؤال\n\n"
            f"📌 استخدم الأزرار بالأسفل لتنفيذ طلباتك:")
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard(user_id))

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    if call.data == "back_main":
        user_data = get_or_create_user(user_id, call.from_user.first_name)
        text = (f"💠 أهلاً بك عزيزي في البوت الشامل 💠\n\n"
                f"👤 حسابك: {ADMIN_USERNAME}\n"
                f"💰 رصيدك الحالي: ${user_data[2]:.2f}\n\n"
                f"📌 استخدم الأزرار بالأسفل لتنفيذ طلباتك:")
        bot.edit_message_text(text, chat_id, message_id, reply_markup=main_keyboard(user_id))

    elif call.data == "buy_number":
        text = "📞 قسم شراء الأرقام الافتراضية\n\nاختر السيرفر الذي تريد الشراء منه:"
        bot.edit_message_text(text, chat_id, message_id, reply_markup=servers_keyboard())

    elif call.data.startswith("select_server_"):
        server_id = call.data.split("_")[2]
        server_name = SERVERS[server_id]['name']
        text = f"⚙️ تم اختيار: {server_name}\n\nاختر التطبيق المراد تفعيله:"
        bot.edit_message_text(text, chat_id, message_id, reply_markup=services_keyboard(server_id))

    elif call.data.startswith("srv_app_"):
        _, _, server_id, srv_code = call.data.split("_")
        markup = countries_keyboard_fast(server_id, srv_code, page=0)
        text = f"🌐 اختر الدولة المطلوبة لـ ({srv_code.upper()}):"
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)

    elif call.data.startswith("pg_"):
        _, server_id, srv_code, page = call.data.split("_")
        markup = countries_keyboard_fast(server_id, srv_code, page=int(page))
        bot.edit_message_text(f"🌐 اختر الدولة المطلوبة لـ ({srv_code.upper()}):", chat_id, message_id, reply_markup=markup)

    # --- شراء الرقم وعلاج أخطاء السيرفر والتنسيق ---
    elif call.data.startswith("b_"):
        _, server_id, srv_code, country_code = call.data.split("_")
        prices = fetch_server_prices(server_id, srv_code)
        price = prices.get(str(country_code), DEFAULT_PRICE)
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        balance = cursor.fetchone()[0]
        
        if balance < price:
            bot.send_message(chat_id, f"❌ رصيدك غير كافٍ!\nسعر هذا الرقم: ${price:.2f}\nرصيدك الحالي: ${balance:.2f}")
            conn.close()
            return

        srv = SERVERS.get(server_id)
        res = grizzly_request({'action': 'getNumber', 'service': srv_code, 'country': country_code}, srv['api_key'], srv['url'])
        
        if "ACCESS_NUMBER" in res:
            parts = res.split(":")
            tz_id, raw_phone = parts[1], parts[2]
            
            formatted_phone = f"+{raw_phone}" if not raw_phone.startswith("+") else raw_phone
            c_name, c_flag = get_country_info(country_code)
            
            cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (price, user_id))
            cursor.execute('INSERT INTO purchases (user_id, tz_id, phone, service, cost, country_code) VALUES (?, ?, ?, ?, ?, ?)',
                           (user_id, tz_id, formatted_phone, srv_code, price, country_code))
            conn.commit()
            conn.close()
            
            msg = (f"🆔 **رقم الطلب** : `{tz_id}`\n"
                   f"🌐 **الدولة** : {c_name} {c_flag}\n"
                   f"📞 **الرقم** : `{formatted_phone}`\n"
                   f"📩 **الكود** : `قيد الانتظار... ⏳`\n"
                   f"🔍 **الحالة** : `WAITING_CODE`\n"
                   f"🛍️ **التطبيق** : `{srv_code.upper()}`\n"
                   f"💵 **السعر** : `${price:.2f}`\n\n"
                   f"📋 *اضغط على الرقم أو رقم الطلب لنسخه فوراً*")
            
            bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=active_number_keyboard(tz_id, server_id, srv_code))
        
        elif "NO_NUMBERS" in res:
            conn.close()
            bot.send_message(chat_id, "⚠️ **تنبيه:** الأرقام المتاحة لهذه الدولة نفدت حالياً لدى المزود. يرجى اختيار دولة أخرى أو تجربة التحديث بعد قليل.")
        else:
            conn.close()
            bot.send_message(chat_id, f"❌ تعذر استكمال الطلب. رد السيرفر: {res}")

    # --- معالجة فحص واستلام الكود ---
    elif call.data.startswith("check_sms_"):
        parts = call.data.split("_")
        server_id, tz_id = parts[2], parts[3]
        srv = SERVERS.get(server_id)
        res = grizzly_request({'action': 'getStatus', 'id': tz_id}, srv['api_key'], srv['url'])
        
        if "STATUS_OK" in res:
            code = res.split(":")[1]
            bot.send_message(chat_id, f"🎉 **تم استلام كود التفعيل بنجاح!**\n\n🔑 **الكود الخاص بك** : `{code}`\n\n(اضغط على الكود لنسخه)", parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "⏳ لم يصل الكود بعد، تأكد من إدخال الرقم في التطبيق والمحاولة مجدداً.", show_alert=True)

    # --- معالجة تغيير الرقم والإلغاء وتصحيح التغيير التلقائي ---
    elif call.data.startswith("cancel_num_") or call.data.startswith("change_num_"):
        parts = call.data.split("_")
        action_type = parts[0]
        server_id, tz_id = parts[2], parts[3]
        srv = SERVERS.get(server_id)
        
        # إلغاء الرقم لدى المزود
        grizzly_request({'action': 'setStatus', 'status': '8', 'id': tz_id}, srv['api_key'], srv['url'])
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, cost, status, service, country_code FROM purchases WHERE tz_id = ?', (tz_id,))
        purchase = cursor.fetchone()
        
        if purchase and purchase[2] == 'PENDING':
            cost, srv_code, country_code = purchase[1], purchase[3], purchase[4]
            # إعادة المبلغ للحساب
            cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (cost, user_id))
            cursor.execute('UPDATE purchases SET status = "CANCELLED" WHERE tz_id = ?', (tz_id,))
            conn.commit()
            
            if action_type == "change_num":
                # شراء رقم جديد تلقائياً
                prices = fetch_server_prices(server_id, srv_code)
                price = prices.get(str(country_code), DEFAULT_PRICE)
                
                res = grizzly_request({'action': 'getNumber', 'service': srv_code, 'country': country_code}, srv['api_key'], srv['url'])
                
                if "ACCESS_NUMBER" in res:
                    parts_new = res.split(":")
                    new_tz_id, new_raw_phone = parts_new[1], parts_new[2]
                    formatted_phone = f"+{new_raw_phone}" if not new_raw_phone.startswith("+") else new_raw_phone
                    c_name, c_flag = get_country_info(country_code)
                    
                    cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (price, user_id))
                    cursor.execute('INSERT INTO purchases (user_id, tz_id, phone, service, cost, country_code) VALUES (?, ?, ?, ?, ?, ?)',
                                   (user_id, new_tz_id, formatted_phone, srv_code, price, country_code))
                    conn.commit()
                    conn.close()
                    
                    msg = (f"🔄 **تم تغيير الرقم بنجاح!**\n\n"
                           f"🆔 **رقم الطلب الجديد** : `{new_tz_id}`\n"
                           f"🌐 **الدولة** : {c_name} {c_flag}\n"
                           f"📞 **الرقم الجديد** : `{formatted_phone}`\n"
                           f"📩 **الكود** : `قيد الانتظار... ⏳`\n"
                           f"🔍 **الحالة** : `WAITING_CODE`\n"
                           f"🛍️ **التطبيق** : `{srv_code.upper()}`\n"
                           f"💵 **السعر** : `${price:.2f}`\n\n"
                           f"📋 *اضغط على الرقم لنسخه فوراً*")
                    bot.edit_message_text(msg, chat_id, message_id, parse_mode="Markdown", reply_markup=active_number_keyboard(new_tz_id, server_id, srv_code))
                else:
                    conn.close()
                    bot.edit_message_text(f"⚠️ تم إلغاء الرقم وإرجاع (${cost:.2f}) إلى رصيدك.\nتعذر توفير رقم جديد حالياً بسبب نفاد أرقام هذه الدولة لدى المزود.", chat_id, message_id, reply_markup=back_button())
            else:
                conn.close()
                bot.edit_message_text(f"❌ تم إلغاء الطلب وإعادة مبلغ (${cost:.2f}) إلى رصيدك بنجاح.", chat_id, message_id, reply_markup=back_button())
        else:
            conn.close()
            bot.answer_callback_query(call.id, "الطلب ملغى أو مكتمل مسبقاً.", show_alert=True)

bot.infinity_polling()
