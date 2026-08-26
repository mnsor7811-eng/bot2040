import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import requests
import time
import google.generativeai as genai

# ==================== 1. الإعدادات الأساسية ====================
TOKEN = '8927305428:AAGQD4noM2KqUeiOSUyVC7qJO-K8o2CIR8Q'
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

# ==================== قاموس الدول المصحح والمضبوط ====================
COUNTRY_MAP = {
    "0": {"name": "روسيا", "flag": "🇷🇺"},
    "1": {"name": "أوكرانيا", "flag": "🇺🇦"},
    "2": {"name": "كازاخستان", "flag": "🇰🇿"},
    "3": {"name": "الصين", "flag": "🇨🇳"},
    "4": {"name": "الفلبين", "flag": "🇵🇭"},
    "5": {"name": "ميانمار", "flag": "🇲🇲"},
    "6": {"name": "إندونيسيا", "flag": "🇮🇩"},
    "7": {"name": "ماليزيا", "flag": "🇲🇾"},
    "8": {"name": "كينيا", "flag": "🇰🇪"},
    "9": {"name": "فيتنام", "flag": "🇻🇳"},
    "10": {"name": "قيرغيزستان", "flag": "🇰🇬"},
    "11": {"name": "أمريكا", "flag": "🇺🇸"},
    "12": {"name": "إسرائيل", "flag": "🇮🇱"},
    "13": {"name": "هونغ كونغ", "flag": "🇭🇰"},
    "14": {"name": "بولندا", "flag": "🇵🇱"},
    "15": {"name": "بريطانيا", "flag": "🇬🇧"},
    "16": {"name": "مدغشقر", "flag": "🇲🇬"},
    "17": {"name": "الكونغو", "flag": "🇨🇩"},
    "18": {"name": "نيجيريا", "flag": "🇳🇬"},
    "19": {"name": "ماكاو", "flag": "🇲🇴"},
    "20": {"name": "مصر", "flag": "🇪🇬"},
    "21": {"name": "الهند", "flag": "🇮🇳"},
    "22": {"name": "أيرلندا", "flag": "🇮🇪"},
    "23": {"name": "كمبوديا", "flag": "🇰🇭"},
    "24": {"name": "لاوس", "flag": "🇱🇦"},
    "25": {"name": "هايتي", "flag": "🇭🇹"},
    "26": {"name": "ساحل العاج", "flag": "🇨🇮"},
    "27": {"name": "غامبيا", "flag": "🇬🇲"},
    "28": {"name": "صربيا", "flag": "🇷🇸"},
    "29": {"name": "اليمن", "flag": "🇾🇪"},
    "30": {"name": "كولومبيا", "flag": "🇨🇴"},
    "31": {"name": "جنوب أفريقيا", "flag": "🇿🇦"},
    "32": {"name": "رومانيا", "flag": "🇷🇴"},
    "34": {"name": "إستونيا", "flag": "🇪🇪"},
    "35": {"name": "أذربيجان", "flag": "🇦🇿"},
    "36": {"name": "كندا", "flag": "🇨🇦"},
    "37": {"name": "المغرب", "flag": "🇲🇦"},
    "38": {"name": "غانا", "flag": "🇬🇭"},
    "39": {"name": "الأرجنتين", "flag": "🇦🇷"},
    "40": {"name": "أوزبكستان", "flag": "🇺🇿"},
    "41": {"name": "الكاميرون", "flag": "🇨🇲"},
    "42": {"name": "تشاد", "flag": "🇹🇩"},
    "43": {"name": "ألمانيا", "flag": "🇩🇪"},
    "44": {"name": "ليتوانيا", "flag": "🇱🇹"},
    "45": {"name": "كرواتيا", "flag": "🇭🇷"},
    "46": {"name": "السويد", "flag": "🇸🇪"},
    "47": {"name": "العراق", "flag": "🇮🇶"},
    "48": {"name": "هولندا", "flag": "🇳🇱"},
    "49": {"name": "لاتفيا", "flag": "🇱🇻"},
    "50": {"name": "النمسا", "flag": "🇦🇹"},
    "51": {"name": "بيلاروسيا", "flag": "🇧🇾"},
    "52": {"name": "تايلاند", "flag": "🇹🇭"},
    "53": {"name": "السعودية", "flag": "🇸🇦"},
    "54": {"name": "المكسيك", "flag": "🇲🇽"},
    "55": {"name": "تايوان", "flag": "🇹🇼"},
    "56": {"name": "إسبانيا", "flag": "🇪🇸"},
    "57": {"name": "الجزائر", "flag": "🇩🇿"},
    "58": {"name": "سلوفينيا", "flag": "🇸🇮"},
    "59": {"name": "بنغلاديش", "flag": "🇧🇩"},
    "60": {"name": "البرتغال", "flag": "🇵🇹"},
    "61": {"name": "السنغال", "flag": "🇸🇳"},
    "62": {"name": "تركيا", "flag": "🇹🇷"},
    "63": {"name": "تونس", "flag": "🇹🇳"},
    "64": {"name": "أوكرانيا", "flag": "🇺🇦"},
    "65": {"name": "السودان", "flag": "🇸🇩"},
    "66": {"name": "أستراليا", "flag": "🇦🇺"},
    "67": {"name": "فنلندا", "flag": "🇫🇮"},
    "68": {"name": "فرنسا", "flag": "🇫🇷"},
    "69": {"name": "بلجيكا", "flag": "🇧🇪"},
    "73": {"name": "البرازيل", "flag": "🇧🇷"},
    "86": {"name": "إيطاليا", "flag": "🇮🇹"},
    "96": {"name": "عمان", "flag": "🇴🇲"},
    "97": {"name": "الكويت", "flag": "🇰🇼"},
    "98": {"name": "قطر", "flag": "🇶🇦"},
    "101": {"name": "الإمارات", "flag": "🇦🇪"},
    "102": {"name": "الأردن", "flag": "🇯🇴"},
    "103": {"name": "لبنان", "flag": "🇱🇧"},
    "104": {"name": "فلسطين", "flag": "🇵🇸"},
    "105": {"name": "سوريا", "flag": "🇸🇾"}
}

# ==================== دالة استخراج معلومات الدولة الدقيقة ====================
def get_clean_country_info(code_str):
    code_str = str(code_str).strip()
    if code_str in COUNTRY_MAP:
        return COUNTRY_MAP[code_str]['name'], COUNTRY_MAP[code_str]['flag']
    return "دولة", "🌐"

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

# ==================== 3. جلب الأسعار والطلبات من السيرفر ====================
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
    markup.row(InlineKeyboardButton("💎 اربح رصيد مجاناً", callback_data="free_ruble"))
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
    start_idx = page * per_page
    end_idx = start_idx + per_page
    current_items = formatted_list[start_idx:end_idx]

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
    markup.add(InlineKeyboardButton("🔙 العودة لااختيار التطبيق", callback_data=f"select_server_{server_id}"))
    return markup

# ==================== أزرار الرقم الفعّال مع زر التحقق المباشر ====================
def active_number_keyboard(tz_id, server_id, phone, service_code):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🔄 تغيير الرقم", callback_data=f"change_num_{server_id}_{tz_id}"))
    markup.row(InlineKeyboardButton("📩 طلب الكود", callback_data=f"check_sms_{server_id}_{tz_id}"))
    
    # إضافة زر تحقق فعال لتطبيق WhatsApp أو تطبيقات أخرى
    clean_num = phone.replace("+", "").strip()
    if service_code.lower() == "wa":
        wa_url = f"https://api.whatsapp.com/send?phone={clean_num}"
        markup.row(InlineKeyboardButton("• تحقق من الرقم في WhatsApp •", url=wa_url))
        
    markup.row(InlineKeyboardButton("✖️ إلغاء الطلب واسترجاع المبلغ", callback_data=f"cancel_num_{server_id}_{tz_id}"))
    return markup

def smm_panel_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("👥 أعضاء وقنوات تليجرام", callback_data="smm_order_101"))
    markup.add(InlineKeyboardButton("❤️ متابعين ومشاهدات إنستغرام", callback_data="smm_order_102"))
    markup.add(InlineKeyboardButton("🎮 شحن شدات ببجي / جوهر", callback_data="smm_order_103"))
    markup.add(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
    return markup

# ==================== 5. الأوامر الخاصة بالأدمن ====================
@bot.message_handler(commands=['add_bal'])
def add_balance_cmd(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
        
    try:
        parts = message.text.split()
        target_id = int(parts[1])
        amount = float(parts[2])
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_id))
        conn.commit()
        conn.close()
        
        bot.reply_to(message, f"✅ تمت إضافة ${amount:.2f} بنجاح إلى حساب المعرف: {target_id}")
    except Exception:
        bot.reply_to(message, "❌ طريقة الاستخدام الخاطئة!\nارسل الأمر كالتالي:\n/add_bal USER_ID AMOUNT")

# ==================== 6. معالجة الأحداث والطلبات ====================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or "المستخدم"
    
    if is_user_banned(user_id):
        bot.send_message(message.chat.id, "🚫 عذراً، لقد تم حظرك من استخدام هذا البوت بواسطة الإدارة.")
        return

    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()

    if not user:
        ref_id = referrer_id if (referrer_id and referrer_id != user_id) else 0
        cursor.execute('INSERT INTO users (user_id, name, balance, ai_balance, is_banned, referred_by) VALUES (?, ?, 0.0, 5, 0, ?)', (user_id, name, ref_id))
        conn.commit()
        
        if ref_id != 0:
            cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (REWARD_PER_INVITE, ref_id))
            conn.commit()
            try:
                bot.send_message(ref_id, f"🎉 قام شخص جديد بالانضمام عبر رابطك!\n🎁 تم إضافة ${REWARD_PER_INVITE:.2f} إلى رصيدك بنجاح.")
            except:
                pass
    conn.close()

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

    if call.data == "ignore":
        return

    if is_user_banned(user_id) and str(user_id) != str(ADMIN_ID):
        bot.send_message(chat_id, "أنت محظور من استخدام البوت.")
        return

    if call.data == "back_main":
        if user_id in USER_STEPS:
            del USER_STEPS[user_id]
        user_data = get_or_create_user(user_id, call.from_user.first_name)
        text = (f"💠 أهلاً بك عزيزي في البوت الشامل 💠\n\n"
                f"👤 حسابك: {ADMIN_USERNAME}\n"
                f"💰 رصيدك الحالي: ${user_data[2]:.2f}\n"
                f"🤖 رصيد أسئلة الذكاء: {user_data[3]} سؤال\n\n"
                f"📌 استخدم الأزرار بالأسفل لتنفيذ طلباتك:")
        bot.edit_message_text(text, chat_id, message_id, reply_markup=main_keyboard(user_id))

    elif call.data == "transfer":
        USER_STEPS[user_id] = {'step': 'TRANSFER_TARGET'}
        text = (f"🔄 قسم تحويل الرصيد بين الحسابات\n\n"
                f"✨ الميزات: عمولة التحويل 0% (مجاناً)\n"
                f"💵 أقل مبلغ للتحويل: $1.00\n\n"
                f"📌 يرجى إرسال آيدي (User ID) الشخص المراد التحويل إليه الآن:")
        bot.edit_message_text(text, chat_id, message_id, reply_markup=back_button())

    elif call.data == "recharge_menu":
        text = "🎳 قسم شحن الرصيد / الاشتراكات\n\nاختر وسيلة الدفع التي تناسبك من القائمة أدناه:"
        bot.edit_message_text(text, chat_id, message_id, reply_markup=recharge_keyboard())

    elif call.data.startswith("pay_"):
        pay_key = call.data.replace("pay_", "")
        pay_info = PAYMENT_DETAILS.get(pay_key)
        
        if pay_info:
            msg = (f"{pay_info['name']}\n\n"
                   f"📌 رقم الحساب / المعرف: `{pay_info['acc']}`\n"
                   f"💵 أقل مبلغ للتحويل: {pay_info['min']}\n"
                   f"💱 سعر الصرف: {pay_info['rate']}\n\n"
                   f"⚠️ خطوات الشحن:\n"
                   f"1. قم بالتحويل إلى رقم الحساب الموضح أعلاه.\n"
                   f"2. قم بإرسال صورة إشعار التحويل (الوصل) ومعرف حسابك [`{user_id}`] إلى حساب الإدارة:\n"
                   f"👤 الإدارة: {ADMIN_USERNAME}\n\n"
                   f"سيتم مراجعة الدفع وشحن رصيدك فوراً!")
            
            back_markup = InlineKeyboardMarkup()
            back_markup.add(InlineKeyboardButton("🔙 العودة لوسائل الدفع", callback_data="recharge_menu"))
            bot.edit_message_text(msg, chat_id, message_id, reply_markup=back_markup, parse_mode="Markdown")

    elif call.data == "buy_number":
        text = "📞 قسم شراء الأرقام الافتراضية\n\nاختر السيرفر / الموقع الذي تريد الشراء منه:"
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
        page = int(page)
        markup = countries_keyboard_fast(server_id, srv_code, page=page)
        text = f"🌐 اختر الدولة المطلوبة لـ ({srv_code.upper()}):"
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
        except Exception:
            pass

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
            
            # ضمان إضافة علامة + في البداية بدقة
            formatted_phone = f"+{raw_phone}" if not raw_phone.startswith("+") else raw_phone
            c_name, c_flag = get_clean_country_info(country_code)
            
            cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (price, user_id))
            cursor.execute('INSERT INTO purchases (user_id, tz_id, phone, service, cost, country_code) VALUES (?, ?, ?, ?, ?, ?)',
                           (user_id, tz_id, formatted_phone, srv_code, price, country_code))
            conn.commit()
            conn.close()
            
            # تعديل الجملة التوضيحية وحذف كلمة "رقم الطلب"
            msg = (f"🆔 **رقم الطلب** : `{tz_id}`\n"
                   f"🌐 **الدولة** : {c_name} {c_flag}\n"
                   f"📞 **الرقم** : `{formatted_phone}`\n"
                   f"📩 **الكود** : `قيد الانتظار... ⏳`\n"
                   f"🔍 **الحالة** : `WAITING_CODE`\n"
                   f"🛍️ **التطبيق** : `{srv_code.upper()}`\n"
                   f"💵 **السعر** : `${price:.2f}`\n\n"
                   f"📋 *اضغط على الرقم لنسخه فوراً*")
            
            bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=active_number_keyboard(tz_id, server_id, formatted_phone, srv_code))
        else:
            conn.close()
            bot.send_message(chat_id, f"❌ لم يكتمل الطلب: الرد من السيرفر: {res}")

    elif call.data.startswith("check_sms_"):
        parts = call.data.split("_")
        server_id, tz_id = parts[2], parts[3]
        srv = SERVERS.get(server_id)
        res = grizzly_request({'action': 'getStatus', 'id': tz_id}, srv['api_key'], srv['url'])
        
        if "STATUS_OK" in res:
            code = res.split(":")[1]
            try:
                bot.answer_callback_query(call.id, text="🎉 تم وصول الكود بنجاح!", show_alert=False)
            except Exception:
                pass
            bot.send_message(chat_id, f"🎉 **تم استلام كود التفعيل بنجاح!**\n\n🔑 **الكود** : `{code}`\n\n(اضغط على الكود لنسخه)", parse_mode="Markdown")
        else:
            # إظهار الإشعار المنبثق في أعلى الشاشة (Popup Header Notification)
            try:
                bot.answer_callback_query(call.id, text="لم يتم العثور على رسالة الكود... انتظر قليلاً ⏳", show_alert=False)
            except Exception:
                pass

    elif call.data.startswith("cancel_num_") or call.data.startswith("change_num_"):
        parts = call.data.split("_")
        action_type = parts[0]
        server_id, tz_id = parts[2], parts[3]
        srv = SERVERS.get(server_id)
        grizzly_request({'action': 'setStatus', 'status': '8', 'id': tz_id}, srv['api_key'], srv['url'])
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, cost, status, service, country_code FROM purchases WHERE tz_id = ?', (tz_id,))
        purchase = cursor.fetchone()
        
        if purchase and purchase[2] == 'PENDING':
            cost, srv_code, country_code = purchase[1], purchase[3], purchase[4]
            cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (cost, user_id))
            cursor.execute('UPDATE purchases SET status = "CANCELLED" WHERE tz_id = ?', (tz_id,))
            conn.commit()
            conn.close()
            
            if action_type == "change_num":
                bot.edit_message_text(f"🔄 تم إلغاء الرقم السابق وإعادة مبلغ (${cost:.2f}) لحسابك. جاري طلب رقم جديد...", chat_id, message_id)
                prices = fetch_server_prices(server_id, srv_code)
                price = prices.get(str(country_code), DEFAULT_PRICE)
                res = grizzly_request({'action': 'getNumber', 'service': srv_code, 'country': country_code}, srv['api_key'], srv['url'])
                if "ACCESS_NUMBER" in res:
                    parts = res.split(":")
                    new_tz_id, new_raw_phone = parts[1], parts[2]
                    formatted_phone = f"+{new_raw_phone}" if not new_raw_phone.startswith("+") else new_raw_phone
                    c_name, c_flag = get_clean_country_info(country_code)
                    
                    conn2 = get_db()
                    cursor2 = conn2.cursor()
                    cursor2.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (price, user_id))
                    cursor2.execute('INSERT INTO purchases (user_id, tz_id, phone, service, cost, country_code) VALUES (?, ?, ?, ?, ?, ?)',
                                   (user_id, new_tz_id, formatted_phone, srv_code, price, country_code))
                    conn2.commit()
                    conn2.close()
                    
                    msg = (f"🆔 **رقم الطلب الجديد** : `{new_tz_id}`\n"
                           f"🌐 **الدولة** : {c_name} {c_flag}\n"
                           f"📞 **الرقم** : `{formatted_phone}`\n"
                           f"📩 **الكود** : `قيد الانتظار... ⏳`\n"
                           f"🔍 **الحالة** : `WAITING_CODE`\n"
                           f"🛍️ **التطبيق** : `{srv_code.upper()}`\n"
                           f"💵 **السعر** : `${price:.2f}`\n\n"
                           f"📋 *اضغط على الرقم لنسخه فوراً*")
                    bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=active_number_keyboard(new_tz_id, server_id, formatted_phone, srv_code))
                else:
                    bot.send_message(chat_id, "❌ تعذر تلقي رقم جديد حالياً.")
            else:
                try:
                    bot.answer_callback_query(call.id, text="❌ تم إلغاء الرقم وإعادة الرصيد", show_alert=False)
                except Exception:
                    pass
                bot.edit_message_text(f"❌ تم إلغاء الرقم بنجاح وإعادة مبلغ (${cost:.2f}) إلى رصيدك.", chat_id, message_id, reply_markup=back_button())
        else:
            conn.close()
            try:
                bot.answer_callback_query(call.id, text="العملية ملغاة أو منتهية مسبقاً.", show_alert=True)
            except Exception:
                pass

    elif call.data == "smm_main":
        bot.edit_message_text("🚀 قسم خدمات الرشق وشحن الألعاب\n\nاختر الخدمة التي تود طلبها:", chat_id, message_id, reply_markup=smm_panel_keyboard())

    elif call.data.startswith("smm_order_"):
        service_id = call.data.split("_")[2]
        USER_STEPS[user_id] = {'step': 'WAITING_LINK', 'service_id': service_id}
        bot.send_message(chat_id, "🔗 يرجى إرسال رابط الحساب / القناة / المعرف المطلوب للرشق:")

    elif call.data == "free_ruble":
        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,))
        invite_count = cursor.fetchone()[0]
        conn.close()
        
        earned_total = invite_count * REWARD_PER_INVITE
        
        msg = (f"💎 نظام اربح رصيد مجاني 💎\n\n"
               f"قم بنشر رابط الإحالة الخاص بك بين أصدقائك، واحصل على رصيد مجاني لكل شخص ينضم عبر رابطك!\n\n"
               f"🎁 المكافأة لكل شخص: ${REWARD_PER_INVITE:.2f}\n"
               f"👥 عدد الذين دعوتهم: {invite_count} شخص\n"
               f"💵 إجمالي أرباحك: ${earned_total:.2f}\n\n"
               f"🔗 رابط الدعوة الخاص بك:\n`{ref_link}`")
               
        bot.edit_message_text(msg, chat_id, message_id, parse_mode="Markdown", reply_markup=back_button())

    elif call.data == "ai_landing":
        bot.edit_message_text("🤖 قسم خدمات الذكاء الاصطناعي\n\nيمكنك كتابة سؤالك مباشرة هنا للبوت للحصول على إجابة ذكية فورية.", chat_id, message_id, reply_markup=back_button())

    elif call.data in ["fast_buy_tg", "fast_buy_wa"]:
        srv_code = "tg" if "tg" in call.data else "wa"
        markup = countries_keyboard_fast("grizzly", srv_code, page=0)
        bot.edit_message_text(f"⚡ عروض سريعة لتطبيق ({srv_code.upper()}):", chat_id, message_id, reply_markup=markup)

    elif call.data == "best_selling":
        bot.edit_message_text("🔥 السيرفرات الأكثر مبيعاً حالياً:\n1. Grizzly SMS - تليجرام روسيا\n2. Tiger SMS - واتساب نيجيريا", chat_id, message_id, reply_markup=back_button())

    elif call.data == "most_available":
        bot.edit_message_text("🎲 الأكثر توفراً حالياً: أرقام نيجيريا وروسيا متوفرة بكثرة وبكود سريع.", chat_id, message_id, reply_markup=back_button())

    elif call.data == "support":
        bot.edit_message_text(f"🎧 الدعم الفني المباشر:\nراسلنا عبر الحساب: {ADMIN_USERNAME}", chat_id, message_id, reply_markup=back_button())

    elif call.data == "purchase_stats":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM purchases WHERE status='COMPLETED' OR status='PENDING'")
        count = cursor.fetchone()[0]
        conn.close()
        bot.edit_message_text(f"✔ إحصائيات الشراء الناجح:\nتم تفعيل أكثر من {count + 150} رقم عبر البوت بنجاح!", chat_id, message_id, reply_markup=back_button())

    elif call.data == "my_account":
        user_data = get_or_create_user(user_id, call.from_user.first_name)
        msg = (f"👤 معلومات حسابك:\n\n"
               f"🆔 ID: `{user_data[0]}`\n"
               f"💰 الرصيد: ${user_data[2]:.2f}\n"
               f"🤖 رصيد AI: {user_data[3]} أسئلة")
        bot.edit_message_text(msg, chat_id, message_id, parse_mode="Markdown", reply_markup=back_button())

    elif call.data == "other_services":
        bot.edit_message_text("🛸 خدمات وميزات أخرى:\nقريباً سيتم إطلاق المزيد من الخدمات الحصرية.", chat_id, message_id, reply_markup=back_button())

    elif call.data == "admin_panel" and str(user_id) == str(ADMIN_ID):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        u_count = cursor.fetchone()[0]
        conn.close()
        bot.edit_message_text(f"⚙️ لوحة الإدارة الكبرى:\n\n👥 عدد مستخدمي البوت: {u_count}\n\n💡 لشحن رصيد أي مستخدم:\n`/add_bal USER_ID AMOUNT`", chat_id, message_id, parse_mode="Markdown", reply_markup=back_button())

# ==================== 7. استقبال المدخلات وتدفق العمليات ====================
@bot.message_handler(func=lambda msg: msg.from_user.id in USER_STEPS)
def handle_user_steps(message):
    user_id = message.from_user.id
    step_data = USER_STEPS.get(user_id)
    
    if step_data['step'] == 'TRANSFER_TARGET':
        target_input = message.text.strip()
        if not target_input.isdigit():
            bot.send_message(message.chat.id, "❌ يرجى إرسال الآيدي (User ID) بالأرقام فقط.")
            return
            
        target_id = int(target_input)
        if target_id == user_id:
            bot.send_message(message.chat.id, "❌ لا يمكنك تحويل الرصيد لنفسك!")
            return
            
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM users WHERE user_id = ?', (target_id,))
        target_user = cursor.fetchone()
        conn.close()
        
        if not target_user:
            bot.send_message(message.chat.id, "❌ هذا المستخدم غير موجود في البوت!")
            return
            
        step_data['target_id'] = target_id
        step_data['target_name'] = target_user[0]
        step_data['step'] = 'TRANSFER_AMOUNT'
        
        bot.send_message(message.chat.id, f"👤 المستلم: {target_user[0]} ({target_id})\n\n💵 أرسل المبلغ المراد تحويله بالدولار (أقل مبلغ هو $1.00):")

    elif step_data['step'] == 'TRANSFER_AMOUNT':
        try:
            amount = float(message.text.strip())
        except ValueError:
            bot.send_message(message.chat.id, "❌ يرجى كتابة المبلغ بالأرقام فقط (مثال: 1.5).")
            return
            
        if amount < MIN_TRANSFER_AMOUNT:
            bot.send_message(message.chat.id, f"❌ أقل مبلغ للتحويل هو ${MIN_TRANSFER_AMOUNT:.2f}")
            return
            
        target_id = step_data['target_id']
        target_name = step_data['target_name']
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        my_balance = cursor.fetchone()[0]
        
        if my_balance < amount:
            bot.send_message(message.chat.id, f"❌ رصيدك غير كافٍ!\nرصيدك الحالي: ${my_balance:.2f}\nالمبلغ المطلوب: ${amount:.2f}")
            del USER_STEPS[user_id]
            conn.close()
            return
            
        cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (amount, user_id))
        cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, target_id))
        conn.commit()
        conn.close()
        
        del USER_STEPS[user_id]
        
        bot.send_message(message.chat.id, f"✅ تم تحويل ${amount:.2f} بنجاح إلى {target_name} ({target_id})\n✨ العمولة: $0.00", reply_markup=back_button())
        
        try:
            bot.send_message(target_id, f"🎉 وصلك تحويل رصيد بقيمة ${amount:.2f} من المستخدم ({user_id})!")
        except Exception:
            pass

    elif step_data['step'] == 'WAITING_LINK':
        step_data['link'] = message.text
        step_data['step'] = 'WAITING_QTY'
        bot.send_message(message.chat.id, "🔢 قم بإرسال الكمية المطلوبة الآن (مثال: 1000):")
        
    elif step_data['step'] == 'WAITING_QTY':
        if not message.text.isdigit():
            bot.send_message(message.chat.id, "❌ يرجى كتابة الكمية بالأرقام فقط.")
            return
            
        qty = int(message.text)
        link = step_data['link']
        srv_id = step_data['service_id']
        price_per_1000 = 1.50
        total_cost = round((price_per_1000 / 1000) * qty, 2)
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        balance = cursor.fetchone()[0]
        
        if balance < total_cost:
            bot.send_message(message.chat.id, f"❌ رصيدك غير كافٍ!\nتكلفة الطلب: ${total_cost:.2f}\nرصيدك: ${balance:.2f}")
            del USER_STEPS[user_id]
            conn.close()
            return

        panel = SMM_PANELS["1"]
        try:
            req_data = {'key': panel['api_key'], 'action': 'add', 'service': srv_id, 'link': link, 'quantity': qty}
            res = requests.post(panel['url'], data=req_data, timeout=10).json()
            
            if 'order' in res:
                order_id = res['order']
                cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (total_cost, user_id))
                cursor.execute('INSERT INTO smm_orders (user_id, order_id, service_name, link, quantity, cost) VALUES (?, ?, ?, ?, ?, ?)',
                               (user_id, order_id, f"Service-{srv_id}", link, qty, total_cost))
                conn.commit()
                bot.send_message(message.chat.id, f"✅ تم إرسال طلب الرشق بنجاح!\n\n🆔 رقم الطلب: `{order_id}`\n🔗 الرابط: {link}\n🔢 الكمية: {qty}\n💵 المبلغ: ${total_cost:.2f}", parse_mode="Markdown", reply_markup=back_button())
            else:
                bot.send_message(message.chat.id, f"❌ خطأ من المورد: {res.get('error', 'تعذر الطلب')}")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ حدث خطأ أثناء الاتصال بالسيرفر: {e}")
            
        conn.close()
        del USER_STEPS[user_id]

@bot.message_handler(func=lambda msg: not msg.text.startswith('/'), content_types=['text'])
def handle_ai_chat(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        return

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT ai_balance FROM users WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    
    if res and res[0] > 0:
        cursor.execute("UPDATE users SET ai_balance = ai_balance - 1 WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()
        
        try:
            response = model.generate_content(message.text)
            bot.reply_to(message, response.text)
        except Exception:
            bot.reply_to(message, "⚠️ حدث خطأ أثناء الاتصال بنموذج الذكاء الاصطناعي.")
    else:
        conn.close()
        bot.reply_to(message, "❌ نفد رصيد أسئلة الذكاء الاصطناعي المتاحة لك.")

bot.infinity_polling()
