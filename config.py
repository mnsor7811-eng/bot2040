import os
import sqlite3
import requests
import time
import threading
import google.generativeai as genai

# ==================== الإعدادات الأساسية ====================
TOKEN = os.getenv('TOKEN', '8927305428:AAH7CGvaZRpXE7whw5dIr8B9UF-tePExmAk')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AQ.Ab8RN6IOLYCW3mnMh6H5le6Bc1pAG60TXO0IoxjpPcHvaFZHkg')
ADMIN_ID = int(os.getenv('ADMIN_ID', 6113734300))
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', '@Num_s7')

# ==================== روابط القنوات الرسمية ====================
CHANNEL_OFFICIAL_NAME = "قناة البوت الرسمية"
CHANNEL_OFFICIAL_ID = "3004681072"
CHANNEL_OFFICIAL_URL = "https://t.me/SM_SMS7"

CHANNEL_ORDERS_NAME = "قناة التفعيلات والطلبات"
CHANNEL_ORDERS_ID = "2987190358"
CHANNEL_ORDERS_URL = "https://t.me/numbuersms"

# ==================== الإعدادات المالية والنسب ====================
PROFIT_MARGIN = 0.10      # نسبة الربح 10%
DEFAULT_PRICE = 0.50      # سعر افتراضي
REWARD_PER_INVITE = 0.05  # مكافأة الدعوة ($0.05)
MIN_TRANSFER_AMOUNT = 1.0  # الحد الأدنى لتحويل الرصيد ($1)

# ==================== تفاصيل وسائل الدفع ====================
PAYMENT_DETAILS = {
    'kuraimi': {'name': '🏦 بنك الكريمي', 'acc': '3134706987', 'min': '100 ريال', 'rate': '1$ = 550 ريال'},
    'jeeb': {'name': '📱 محفظة جيب', 'acc': '374468', 'min': '50 ريال', 'rate': '1$ = 550 ريال'},
    'onecash': {'name': '💳 محفظة ون كاش', 'acc': '140601836', 'min': '100 ريال', 'rate': '1$ = 550 ريال'},
    'binance': {'name': '🟡 Binance (تلقائي)', 'acc': '979808293', 'min': '0.5 $', 'rate': '1$ = 1$'}
}

# ==================== مزودو خدمات الرشق (SMM API) ====================
SMM_SERVERS = {
    '2': {
        'name': 'سيرفر الرشق 1',
        'url': 'https://smmxstar.com/api/v2',
        'key': '13cb06a01b5a7259c14c1727c2f5591d',
        'active': True
    }
}

# ==================== مزودو الحسابات الجاهزة ====================
READY_ACCOUNTS_PROVIDERS = {
    '1': {
        'name': 'السيرفر 1',
        'api_key': 'ncgw41immHj3Cadmxy',
        'url': 'https://tglion.com/api/'
    },
    '2': {
        'name': 'السيرفر 2',
        'api_key': 'ok8vshh5hwz7zdjjclzb',
        'url': 'https://services-tg.com/api/'
    }
}

# ==================== سيرفرات الأرقام الوهمية ====================
SERVERS = {
    'grizzly': {
        'name': 'سيرفر الأرقام 1',
        'api_key': os.getenv('GRIZZLY_API_KEY', 'Aed7993f2abbded229628261c56746d5'),
        'url': 'https://grizzlysms.com/stubs/handler_api.php'
    },
    'smsman': {
        'name': 'سيرفر الأرقام 2',
        'api_key': os.getenv('SMSMAN_API_KEY', 'y-PEwx3CbW00xho3rU2XobIia195Oobo'),
        'url': 'https://api.sms-man.com/control/'
    },
    '5sim': {
        'name': 'سيرفر الأرقام 3',
        'api_key': os.getenv('SIM5_API_KEY', 'ضع_مفتاح_5SIM_هنا'),
        'url': 'https://5sim.biz/v1/user/'
    },
    'tigersms': {
        'name': 'سيرفر الأرقام 4',
        'api_key': os.getenv('TIGER_API_KEY', 'ضع_مفتاح_TIGER_هنا'),
        'url': 'https://tiger-sms.com/stubs/handler_api.php'
    }
}

# ==================== خريطة الدول ====================
COUNTRY_MAP = {
    "0": {"name": "روسيا", "flag": "🇷🇺"}, "1": {"name": "أوكرانيا", "flag": "🇺🇦"},
    "2": {"name": "كازاخستان", "flag": "🇰🇿"}, "3": {"name": "الصين", "flag": "🇨🇳"},
    "4": {"name": "الفلبين", "flag": "🇵🇭"}, "5": {"name": "ميانمار", "flag": "🇲🇲"},
    "6": {"name": "إندونيسيا", "flag": "🇮🇩"}, "7": {"name": "ماليزيا", "flag": "🇲🇾"},
    "8": {"name": "كينيا", "flag": "🇰🇪"}, "9": {"name": "فيتنام", "flag": "🇻🇳"},
    "10": {"name": "قيرغيزستان", "flag": "🇰🇬"}, "11": {"name": "أمريكا", "flag": "🇺🇸"},
    "12": {"name": "إسرائيل", "flag": "🇮🇱"}, "13": {"name": "هونغ كونغ", "flag": "🇭🇰"},
    "14": {"name": "بولندا", "flag": "🇵🇱"}, "15": {"name": "بريطانيا", "flag": "🇬🇧"},
    "16": {"name": "مدغشقر", "flag": "🇲🇬"}, "17": {"name": "الكونغو", "flag": "🇨🇩"},
    "18": {"name": "نيجيريا", "flag": "🇳🇬"}, "19": {"name": "ماكاو", "flag": "🇲🇴"},
    "20": {"name": "مصر", "flag": "🇪🇬"}, "21": {"name": "الهند", "flag": "🇮🇳"},
    "22": {"name": "أيرلندا", "flag": "🇮🇪"}, "23": {"name": "كمبوديا", "flag": "🇰🇭"},
    "24": {"name": "لاوس", "flag": "🇱🇦"}, "25": {"name": "هايتي", "flag": "🇭🇹"},
    "26": {"name": "ساحل العاج", "flag": "🇨🇮"}, "27": {"name": "غامبيا", "flag": "🇬🇲"},
    "28": {"name": "صربيا", "flag": "🇷🇸"}, "29": {"name": "اليمن", "flag": "🇾🇪"},
    "30": {"name": "كولومبيا", "flag": "🇨🇴"}, "31": {"name": "جنوب أفريقيا", "flag": "🇿🇦"},
    "32": {"name": "رومانيا", "flag": "🇷🇴"}, "34": {"name": "إستونيا", "flag": "🇪🇪"},
    "35": {"name": "أذربيجان", "flag": "🇦🇿"}, "36": {"name": "كندا", "flag": "🇨🇦"},
    "37": {"name": "المغرب", "flag": "🇲🇦"}, "38": {"name": "غانا", "flag": "🇬🇭"},
    "39": {"name": "الأرجنتين", "flag": "🇦🇷"}, "40": {"name": "أوزبكستان", "flag": "🇺🇿"},
    "41": {"name": "الكاميرون", "flag": "🇨🇲"}, "42": {"name": "تشاد", "flag": "🇹🇩"},
    "43": {"name": "ألمانيا", "flag": "🇩🇪"}, "44": {"name": "ليتوانيا", "flag": "🇱🇹"},
    "45": {"name": "كرواتيا", "flag": "🇭🇷"}, "46": {"name": "السويد", "flag": "🇸🇪"},
    "47": {"name": "العراق", "flag": "🇮🇶"}, "48": {"name": "هولندا", "flag": "🇳🇱"},
    "49": {"name": "لاتفيا", "flag": "🇱🇻"}, "50": {"name": "النمسا", "flag": "🇦🇹"},
    "51": {"name": "بيلاروسيا", "flag": "🇧🇾"}, "52": {"name": "تايلاند", "flag": "🇹🇭"},
    "53": {"name": "السعودية", "flag": "🇸🇦"}, "54": {"name": "المكسيك", "flag": "🇲🇽"},
    "55": {"name": "تايوان", "flag": "🇹🇼"}, "56": {"name": "إسبانيا", "flag": "🇪🇸"},
    "57": {"name": "الجزائر", "flag": "🇩🇿"}, "58": {"name": "سلوفينيا", "flag": "🇸🇮"},
    "59": {"name": "بنغلاديش", "flag": "🇧🇩"}, "60": {"name": "البرتغال", "flag": "🇵🇹"},
    "61": {"name": "البرازيل", "flag": "🇧🇷"}, "62": {"name": "تركيا", "flag": "🇹🇷"},
    "63": {"name": "تونس", "flag": "🇹🇳"}, "64": {"name": "أوكرانيا", "flag": "🇺🇦"},
    "65": {"name": "السودان", "flag": "🇸🇩"}, "66": {"name": "أستراليا", "flag": "🇦🇺"},
    "67": {"name": "فنلندا", "flag": "🇫🇮"}, "68": {"name": "فرنسا", "flag": "🇫🇷"},
    "69": {"name": "بلجيكا", "flag": "🇧🇪"}, "86": {"name": "إيطاليا", "flag": "🇮🇹"},
    "96": {"name": "عمان", "flag": "🇴🇲"}, "97": {"name": "الكويت", "flag": "🇰🇼"},
    "98": {"name": "قطر", "flag": "🇶🇦"}, "101": {"name": "الإمارات", "flag": "🇦🇪"},
    "102": {"name": "الأردن", "flag": "🇯🇴"}, "103": {"name": "لبنان", "flag": "🇱🇧"},
    "104": {"name": "فلسطين", "flag": "🇵🇸"}, "105": {"name": "سوريا", "flag": "🇸🇾"}
}

PRICES_CACHE = {}
CACHE_LAST_UPDATE = {}
CACHE_DURATION = 300 
USER_STEPS = {}
BOT_SETTINGS = {'maintenance': False, 'profit_margin': 0.10}

try:
    genai.configure(api_key=GEMINI_API_KEY)
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
except Exception:
    ai_model = None

# ==================== قاعدة البيانات الدائمة ====================
DB_FILE = 'bot_database.db'

def get_db():
    conn = sqlite3.connect(DB_FILE, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def setup_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        name TEXT,
                        username TEXT,
                        balance REAL DEFAULT 0.0,
                        ai_balance INTEGER DEFAULT 5, 
                        is_banned INTEGER DEFAULT 0,
                        referred_by INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS purchases (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        tz_id TEXT,
                        phone TEXT,
                        service TEXT,
                        cost REAL,
                        country_code TEXT,
                        status TEXT DEFAULT 'PENDING',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS smm_orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        order_id TEXT,
                        user_id INTEGER,
                        service_id TEXT,
                        service_name TEXT,
                        category_name TEXT,
                        link TEXT,
                        quantity INTEGER,
                        cost REAL,
                        status TEXT DEFAULT 'Pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS ready_accounts_orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        server_id TEXT,
                        country_name TEXT,
                        phone TEXT,
                        session_file TEXT,
                        cost REAL,
                        status TEXT DEFAULT 'COMPLETED',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )''')
    conn.commit()
    conn.close()

setup_db()

def get_clean_country_info(code_str):
    code_str = str(code_str).strip()
    if code_str in COUNTRY_MAP:
        name = COUNTRY_MAP[code_str]['name'].replace("(", "").replace(")", "").strip()
        return name, COUNTRY_MAP[code_str]['flag']
    if len(code_str) >= 4:
        clean_code = code_str.replace("100", "").replace("10", "")
        if clean_code in COUNTRY_MAP:
            name = COUNTRY_MAP[clean_code]['name'].replace("(", "").replace(")", "").strip()
            return name, COUNTRY_MAP[clean_code]['flag']
    if code_str.isdigit():
        tail_code = str(int(code_str) % 100)
        if tail_code in COUNTRY_MAP:
            name = COUNTRY_MAP[tail_code]['name'].replace("(", "").replace(")", "").strip()
            return name, COUNTRY_MAP[tail_code]['flag']
    return "دولة", "🌐"

def get_or_create_user(user_id, name):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute('INSERT INTO users (user_id, name, username, balance, ai_balance, is_banned, referred_by) VALUES (?, ?, "", 0.0, 5, 0, 0)', (user_id, name))
        conn.commit()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
    conn.close()
    return user

def is_user_banned(user_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT is_banned FROM users WHERE user_id = ?', (user_id,))
        res = cursor.fetchone()
        return res[0] if res else 0
    except:
        return 0
    finally:
        conn.close()

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

# ==================== دالة جلب دول وأسعار الحسابات الجاهزة عبر API الحقيقي ====================
READY_ACCOUNTS_CACHE = {}
READY_CACHE_TIME = {}
READY_CACHE_LOCK = threading.Lock()

def fetch_ready_accounts_api(server_id='1', force_refresh=False):
    server_id = str(server_id)
    now = time.time()
    
    # استخدام الكاش السريع إذا كان محدثاً خلال 5 دقائق (300 ثانية) ولم يطلب تحديث إجباري
    if not force_refresh:
        with READY_CACHE_LOCK:
            if server_id in READY_ACCOUNTS_CACHE and (now - READY_CACHE_TIME.get(server_id, 0) < 300):
                return READY_ACCOUNTS_CACHE[server_id]

    srv = READY_ACCOUNTS_PROVIDERS.get(server_id)
    countries_data = []

    if srv and srv.get('api_key') and srv.get('url'):
        api_key = srv['api_key']
        base_url = srv['url']
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        # محاولات متعددة لمختلف بروتوكولات وتنسيقات مزودي الحسابات الجاهزة
        actions = ['get_services', 'getServices', 'services', 'get_countries', 'getCountries', 'products']
        
        for act in actions:
            try:
                # تجربة GET
                params = {'api_key': api_key, 'key': api_key, 'action': act, 'service': 'telegram', 'type': 'telegram'}
                res = requests.get(base_url, params=params, headers=headers, timeout=5)
                
                if res.status_code != 200 or not res.text.strip():
                    # تجربة POST
                    res = requests.post(base_url, data=params, headers=headers, timeout=5)
                
                if res.status_code == 200 and res.text.strip():
                    try:
                        data = res.json()
                    except:
                        data = None

                    if data:
                        raw_list = []
                        if isinstance(data, list):
                            raw_list = data
                        elif isinstance(data, dict):
                            raw_list = (
                                data.get('countries') or 
                                data.get('services') or 
                                data.get('data') or 
                                data.get('products') or 
                                data.get('list') or 
                                list(data.values()) if any(isinstance(v, dict) for v in data.values()) else []
                            )

                        if isinstance(raw_list, list) and len(raw_list) > 0:
                            for item in raw_list:
                                if isinstance(item, dict):
                                    c_name = (
                                        item.get('country_name') or 
                                        item.get('name') or 
                                        item.get('country') or 
                                        item.get('title') or
                                        item.get('service_name')
                                    )
                                    raw_price = float(
                                        item.get('price') or 
                                        item.get('cost') or 
                                        item.get('rate') or 
                                        item.get('amount') or 
                                        0.0
                                    )
                                    count = int(
                                        item.get('count') or 
                                        item.get('available') or 
                                        item.get('quantity') or 
                                        item.get('stock') or 
                                        item.get('in_stock') or 
                                        0
                                    )
                                    if c_name and count > 0:
                                        price_with_profit = round(raw_price * (1 + PROFIT_MARGIN), 2)
                                        countries_data.append({
                                            "name": str(c_name),
                                            "price": price_with_profit,
                                            "count": count,
                                            "raw_price": raw_price
                                        })
                        if countries_data:
                            break
            except Exception as e:
                # خطأ في الاتصال لا يوقف الكود
                continue

    with READY_CACHE_LOCK:
        if countries_data:
            READY_ACCOUNTS_CACHE[server_id] = countries_data
            READY_CACHE_TIME[server_id] = now
        elif server_id not in READY_ACCOUNTS_CACHE:
            READY_ACCOUNTS_CACHE[server_id] = []
            READY_CACHE_TIME[server_id] = now

    return READY_ACCOUNTS_CACHE.get(server_id, [])

# ==================== خيط خلفي (Background Thread) لتحديث المخزون والأسعار كل 5 دقائق ====================
def background_stock_updater():
    """تحديث دوري في الخلفية كل 5 دقائق لمخزون وأسعار الحسابات الجاهزة وسيرفرات الأرقام بدون تجميد البوت"""
    while True:
        try:
            time.sleep(300) # انتظار 5 دقائق (300 ثانية)
            # تحديث مخزون الحسابات الجاهزة لكل السيرفرات
            for srv_id in READY_ACCOUNTS_PROVIDERS.keys():
                fetch_ready_accounts_api(srv_id, force_refresh=True)
            
            # تحديث أسعار الأرقام للتطبيقات الشائعة
            for srv_name in ['grizzly', 'tigersms']:
                fetch_server_prices(srv_name, 'tg')
                fetch_server_prices(srv_name, 'wa')
        except Exception as e:
            print(f"Stock updater background error: {e}")

# تشغيل الخيط الخلفي تلقائياً عند استيراد الملف
update_thread = threading.Thread(target=background_stock_updater, daemon=True)
update_thread.start()
