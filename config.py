import os
import sqlite3
import requests
import time
import google.generativeai as genai

# ==================== الإعدادات الأساسية ====================
TOKEN = os.getenv('TOKEN', '8927305428:AAFio91c9845hfuhIR0Ft2Ng1t-OSkuVjUo')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AQ.Ab8RN6IOLYCW3mnMh6H5le6Bc1pAG60TXO0IoxjpPcHvaFZHkg')
ADMIN_ID = int(os.getenv('ADMIN_ID', 6113734300))
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', '@Num_s7')

# ==================== الإعدادات المالية والنسب ====================
PROFIT_MARGIN = 0.10      # نسبة الربح 10%
DEFAULT_PRICE = 0.50      # سعر افتراضي
REWARD_PER_INVITE = 0.05  # قيمة مكافأة الدعوة ($0.05)
MIN_TRANSFER_AMOUNT = 1.0  # الحد الأدنى لتحويل الرصيد ($1)

# ==================== تفاصيل وسائل الدفع ====================
PAYMENT_DETAILS = {
    'kuraimi': {'name': '🏦 بنك الكريمي', 'acc': '3134706987', 'min': '100 ريال', 'rate': '1$ = 550 ريال'},
    'jeeb': {'name': '📱 محفظة جيب', 'acc': '374468', 'min': '50 ريال', 'rate': '1$ = 550 ريال'},
    'onecash': {'name': '💳 محفظة ون كاش', 'acc': '140601836', 'min': '100 ريال', 'rate': '1$ = 550 ريال'},
    'binance': {'name': '🟡 بايننس باي (Binance Pay)', 'acc': '979808293', 'min': '0.5 $', 'rate': '1$ = 1$'}
}

# ==================== مزودو خدمات الرشق (SMM Panel API) ====================
SMM_PROVIDERS = {
    'server_1': {
        'name': '🌟 السيرفر الأول (SMMXStar)',
        'url': 'https://smmxstar.com/api/v2',
        'key': 'ضع_مفتاح_SMMXSTAR_هنا',
        'active': False
    },
    'server_2': {
        'name': '🚀 السيرفر الثاني (SMMFollows)',
        'url': 'https://smmfollows.com/api/v2',
        'key': os.getenv('SMMFOLLOWS_API_KEY', 'Dd396e6fb10365de859bb57dff7f94ba'),
        'active': True
    }
}

DEFAULT_SMM_PROVIDER = 'server_2'

# ==================== سيرفرات الأرقام المؤقتة ====================
SERVERS = {
    'grizzly': {
        'name': '🐻 سيرفر Grizzly SMS',
        'api_key': os.getenv('GRIZZLY_API_KEY', 'Aed7993f2abbded229628261c56746d5'),
        'url': 'https://grizzlysms.com/stubs/handler_api.php'
    },
    'smsman': {
        'name': '🟢 سيرفر SMS-Man',
        'api_key': os.getenv('SMSMAN_API_KEY', 'y-PEwx3CbW00xho3rU2XobIia195Oobo'),
        'url': 'https://api.sms-man.com/control/'
    },
    '5sim': {
        'name': '🌐 سيرفر 5sim.biz',
        'api_key': os.getenv('SIM5_API_KEY', 'ضع_مفتاح_5SIM_هنا'),
        'url': 'https://5sim.biz/v1/user/'
    },
    'tigersms': {
        'name': '🐯 سيرفر Tiger SMS',
        'api_key': os.getenv('TIGER_API_KEY', 'ضع_مفتاح_TIGER_هنا'),
        'url': 'https://tiger-sms.com/stubs/handler_api.php'
    }
}

# ==================== خريطة الدول ====================
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
    "61": {"name": "البرازيل", "flag": "🇧🇷"},
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
    "105": {"name": "سوريا", "flag": "🇸🇾"},
    "181": {"name": "إثيوبيا", "flag": "🇪🇹"},
    "182": {"name": "تنزانيا", "flag": "🇹🇿"},
    "183": {"name": "أوغندا", "flag": "🇺🇬"},
    "184": {"name": "زامبيا", "flag": "🇿🇲"},
    "185": {"name": "زيمبابوي", "flag": "🇿🇼"},
    "186": {"name": "موزمبيق", "flag": "🇲🇿"},
    "188": {"name": "أنغولا", "flag": "🇦🇴"}
}

PRICES_CACHE = {}
CACHE_LAST_UPDATE = {}
CACHE_DURATION = 300 
USER_STEPS = {}

# تهيئة الذكاء الاصطناعي
genai.configure(api_key=GEMINI_API_KEY)
ai_model = genai.GenerativeModel('gemini-1.5-flash')

# ==================== الدوال المساعدة ====================
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

def setup_db():
    conn = sqlite3.connect('bot_database.db', timeout=15, check_same_thread=False)
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
    conn.commit()
    conn.close()

setup_db()

def get_db():
    return sqlite3.connect('bot_database.db', timeout=15, check_same_thread=False)

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
