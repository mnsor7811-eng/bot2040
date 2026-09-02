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
        'type': 'tglion',
        'api_key': 'ncgw41immHj3Cadmxy',
        'user_id': '6113734300',
        'url': 'https://TG-Lion.net'
    },
    '2': {
        'name': 'السيرفر 2',
        'type': 'spider',
        'api_key': 'ok8vshh5hwz7zdjjclzb',
        'url': 'https://api.spider-service.com'
    },
    '3': {
        'name': 'السيرفر 3 (حسابات قديمة)',
        'type': 'tglion',
        'api_key': 'ncgw41immHj3Cadmxy',
        'user_id': '6113734300',
        'url': 'https://TG-Lion.net',
        'is_aged': True
    }
}

# ==================== خريطة رموز الدول ISO الشاملة ====================
ISO_COUNTRY_MAP = {
    'UZ': {'name': 'أوزبكستان', 'flag': '🇺🇿'},
    'BD': {'name': 'بنغلاديش', 'flag': '🇧🇩'},
    'SA': {'name': 'السعودية', 'flag': '🇸🇦'},
    'RU': {'name': 'روسيا', 'flag': '🇷🇺'},
    'IT': {'name': 'إيطاليا', 'flag': '🇮🇹'},
    'MX': {'name': 'المكسيك', 'flag': '🇲🇽'},
    'KZ': {'name': 'كازاخستان', 'flag': '🇰🇿'},
    'UA': {'name': 'أوكرانيا', 'flag': '🇺🇦'},
    'YE': {'name': 'اليمن', 'flag': '🇾🇪'},
    'PT': {'name': 'البرتغال', 'flag': '🇵🇹'},
    'KG': {'name': 'قيرغيزستان', 'flag': '🇰🇬'},
    'TJ': {'name': 'طاجيكستان', 'flag': '🇹🇯'},
    'US': {'name': 'أمريكا', 'flag': '🇺🇸'},
    'EG': {'name': 'مصر', 'flag': '🇪🇬'},
    'TR': {'name': 'تركيا', 'flag': '🇹🇷'},
    'VE': {'name': 'فنزويلا', 'flag': '🇻🇪'},
    'CO': {'name': 'كولومبيا', 'flag': '🇨🇴'},
    'FR': {'name': 'فرنسا', 'flag': '🇫🇷'},
    'AR': {'name': 'الأرجنتين', 'flag': '🇦🇷'},
    'GB': {'name': 'بريطانيا', 'flag': '🇬🇧'},
    'HK': {'name': 'هونغ كونغ', 'flag': '🇭🇰'},
    'TH': {'name': 'تايلاند', 'flag': '🇹🇭'},
    'WS': {'name': 'ساموا', 'flag': '🇼🇸'},
    'ES': {'name': 'إسبانيا', 'flag': '🇪🇸'},
    'TN': {'name': 'تونس', 'flag': '🇹🇳'},
    'DZ': {'name': 'الجزائر', 'flag': '🇩🇿'},
    'MA': {'name': 'المغرب', 'flag': '🇲🇦'},
    'IQ': {'name': 'العراق', 'flag': '🇮🇶'},
    'SY': {'name': 'سوريا', 'flag': '🇸🇾'},
    'JO': {'name': 'الأردن', 'flag': '🇯🇴'},
    'AE': {'name': 'الإمارات', 'flag': '🇦🇪'},
    'KW': {'name': 'الكويت', 'flag': '🇰🇼'},
    'QA': {'name': 'قطر', 'flag': '🇶🇦'},
    'OM': {'name': 'عمان', 'flag': '🇴🇲'},
    'BH': {'name': 'البحرين', 'flag': '🇧🇭'},
    'PS': {'name': 'فلسطين', 'flag': '🇵🇸'},
    'LB': {'name': 'لبنان', 'flag': '🇱🇧'},
    'SD': {'name': 'السودان', 'flag': '🇸🇩'},
    'LY': {'name': 'ليبيا', 'flag': '🇱🇾'},
    'DE': {'name': 'ألمانيا', 'flag': '🇩🇪'},
    'IN': {'name': 'الهند', 'flag': '🇮🇳'},
    'ID': {'name': 'إندونيسيا', 'flag': '🇮🇩'},
    'MY': {'name': 'ماليزيا', 'flag': '🇲🇾'},
    'PH': {'name': 'الفلبين', 'flag': '🇵🇭'},
    'VN': {'name': 'فيتنام', 'flag': '🇻🇳'},
    'BR': {'name': 'البرازيل', 'flag': '🇧🇷'},
    'CL': {'name': 'تشيلي', 'flag': '🇨🇱'},
    'PE': {'name': 'بيرو', 'flag': '🇵🇪'},
    'CA': {'name': 'كندا', 'flag': '🇨🇦'},
    'PL': {'name': 'بولندا', 'flag': '🇵🇱'},
    'RO': {'name': 'رومانيا', 'flag': '🇷🇴'},
    'NL': {'name': 'هولندا', 'flag': '🇳🇱'},
    'SE': {'name': 'السويد', 'flag': '🇸🇪'},
    'NO': {'name': 'النرويج', 'flag': '🇳🇴'},
    'AF': {'name': 'أفغانستان', 'flag': '🇦🇫'},
    'IR': {'name': 'إيران', 'flag': '🇮🇷'},
    'CN': {'name': 'الصين', 'flag': '🇨🇳'},
    'JP': {'name': 'اليابان', 'flag': '🇯🇵'},
    'KR': {'name': 'كوريا الجنوبية', 'flag': '🇰🇷'},
    'TW': {'name': 'تايوان', 'flag': '🇹🇼'},
    'SG': {'name': 'سنغافورة', 'flag': '🇸🇬'},
    'AU': {'name': 'أستراليا', 'flag': '🇦🇺'},
    'NZ': {'name': 'نيوزيلندا', 'flag': '🇳🇿'},
    'NG': {'name': 'نيجيريا', 'flag': '🇳🇬'},
    'KE': {'name': 'كينيا', 'flag': '🇰🇪'},
    'ZA': {'name': 'جنوب أفريقيا', 'flag': '🇿🇦'},
    'GH': {'name': 'غانا', 'flag': '🇬🇭'},
    'CM': {'name': 'الكاميرون', 'flag': '🇨🇲'},
    'CI': {'name': 'ساحل العاج', 'flag': '🇨🇮'},
    'ET': {'name': 'إثيوبيا', 'flag': '🇪🇹'},
    'GE': {'name': 'جورجيا', 'flag': '🇬🇪'},
    'AM': {'name': 'أرمينيا', 'flag': '🇦🇲'},
    'AZ': {'name': 'أذربيجان', 'flag': '🇦🇿'},
    'BY': {'name': 'بيلاروسيا', 'flag': '🇧🇾'},
    'MD': {'name': 'مولدوفا', 'flag': '🇲🇩'},
    'GR': {'name': 'اليونان', 'flag': '🇬🇷'},
    'CY': {'name': 'قبرص', 'flag': '🇨🇾'},
    'CZ': {'name': 'التشيك', 'flag': '🇨🇿'},
    'SK': {'name': 'سلوفاكيا', 'flag': '🇸🇰'},
    'HU': {'name': 'المجر', 'flag': '🇭🇺'},
    'AT': {'name': 'النمسا', 'flag': '🇦🇹'},
    'CH': {'name': 'سويسرا', 'flag': '🇨🇭'},
    'BE': {'name': 'بلجيكا', 'flag': '🇧🇪'},
    'DK': {'name': 'الدنمارك', 'flag': '🇩🇰'},
    'FI': {'name': 'فنلندا', 'flag': '🇫🇮'},
    'IE': {'name': 'أيرلندا', 'flag': '🇮🇪'},
    'BG': {'name': 'بلغاريا', 'flag': '🇧🇬'},
    'HR': {'name': 'كرواتيا', 'flag': '🇭🇷'},
    'RS': {'name': 'صربيا', 'flag': '🇷🇸'},
    'BA': {'name': 'البوسنة', 'flag': '🇧🇦'},
    'AL': {'name': 'ألبانيا', 'flag': '🇦🇱'},
    'LT': {'name': 'ليتوانيا', 'flag': '🇱🇹'},
    'LV': {'name': 'لاتفيا', 'flag': '🇱🇻'},
    'EE': {'name': 'إستونيا', 'flag': '🇪🇪'},
    'IL': {'name': 'إسرائيل', 'flag': '🇮🇱'},
    'MG': {'name': 'مدغشقر', 'flag': '🇲🇬'},
    'CU': {'name': 'كوبا', 'flag': '🇨🇺'},
    'BO': {'name': 'بوليفيا', 'flag': '🇧🇴'},
    'KH': {'name': 'كمبوديا', 'flag': '🇰🇭'},
    'LA': {'name': 'لاوس', 'flag': '🇱🇦'},
    'HT': {'name': 'هايتي', 'flag': '🇭🇹'},
    'GM': {'name': 'غامبيا', 'flag': '🇬🇲'},
    'TD': {'name': 'تشاد', 'flag': '🇹🇩'},
    'CD': {'name': 'الكونغو', 'flag': '🇨🇩'},
    'CG': {'name': 'الكونغو برازافيل', 'flag': '🇨🇬'},
    'UG': {'name': 'أوغندا', 'flag': '🇺🇬'},
    'TZ': {'name': 'تنزانيا', 'flag': '🇹🇿'},
    'SN': {'name': 'السنغال', 'flag': '🇸🇳'},
    'RW': {'name': 'رواندا', 'flag': '🇷🇼'},
    'SO': {'name': 'الصومال', 'flag': '🇸🇴'},
    'MR': {'name': 'موريتانيا', 'flag': '🇲🇷'},
    'DJ': {'name': 'جيبوتي', 'flag': '🇩🇯'},
    'KM': {'name': 'جزر القمر', 'flag': '🇰🇲'},
    'LK': {'name': 'سريلانكا', 'flag': '🇱🇰'},
    'NP': {'name': 'نيبال', 'flag': '🇳🇵'},
    'MM': {'name': 'ميانمار', 'flag': '🇲🇲'},
    'MN': {'name': 'منغوليا', 'flag': '🇲🇳'},
    'BT': {'name': 'بوتان', 'flag': '🇧🇹'},
    'MV': {'name': 'المالديف', 'flag': '🇲🇻'},
    'PK': {'name': 'باكستان', 'flag': '🇵🇰'},
    'PA': {'name': 'بنما', 'flag': '🇵🇦'},
    'CR': {'name': 'كوستاريكا', 'flag': '🇨🇷'},
    'NI': {'name': 'نيكاراغوا', 'flag': '🇳🇮'},
    'HN': {'name': 'هندوراس', 'flag': '🇭🇳'},
    'SV': {'name': 'السلفادور', 'flag': '🇸🇻'},
    'GT': {'name': 'غواتيمالا', 'flag': '🇬🇹'},
    'JM': {'name': 'جامايكا', 'flag': '🇯🇲'},
    'DO': {'name': 'الدومينيكان', 'flag': '🇩🇴'},
    'PR': {'name': 'بورتوريكو', 'flag': '🇵🇷'},
    'TT': {'name': 'ترينيداد وتوباغو', 'flag': '🇹🇹'},
    'BS': {'name': 'البهاما', 'flag': '🇧🇸'},
    'EC': {'name': 'الإكوادور', 'flag': '🇪🇨'},
    'PY': {'name': 'باراغواي', 'flag': '🇵🇾'},
    'UY': {'name': 'أوروغواي', 'flag': '🇺🇾'},
    'GY': {'name': 'غيانا', 'flag': '🇬🇾'},
    'SR': {'name': 'سورينام', 'flag': '🇸🇷'},
    'SI': {'name': 'سلوفينيا', 'flag': '🇸🇮'},
    'MK': {'name': 'مقدونيا', 'flag': '🇲🇰'},
    'ME': {'name': 'الجبل الأسود', 'flag': '🇲🇪'},
    'XK': {'name': 'كوسوفو', 'flag': '🇽🇰'},
    'MT': {'name': 'مالطا', 'flag': '🇲🇹'},
    'IS': {'name': 'آيسلندا', 'flag': '🇮🇸'},
    'LU': {'name': 'لوكسمبورغ', 'flag': '🇱🇺'},
    'MC': {'name': 'موناكو', 'flag': '🇲🇨'},
    'SM': {'name': 'سان مارينو', 'flag': '🇸🇲'},
    'LI': {'name': 'ليختنشتاين', 'flag': '🇱🇮'},
    'AD': {'name': 'أندورا', 'flag': '🇦🇩'},
    'MO': {'name': 'ماكاو', 'flag': '🇲🇴'}
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

def get_aged_accounts_catalog(age='2021'):
    """توليد وجلب قائمة الحسابات القديمة والمعتقة حسب السنة/العمر بدقة وبأسعار واقعية مستقلة تماماً عن السيرفر 1"""
    age_str = str(age) if age else '2021'
    
    # المعامل السعري التقريبي بحسب عمر الحساب (الحسابات الأقدم سعرها أعلى)
    price_multipliers = {
        '2014': 12.5,
        '2015': 11.5,
        '2016': 10.0,
        '2017': 8.5,
        '2018': 7.2,
        '2019': 6.0,
        '2020': 5.0,
        '2021': 4.0,
        '2022': 3.2,
        '2023': 2.5,
        '2024': 1.8,
        '2025': 1.3,
        '60-180day': 1.15,
        '5-60day': 0.95
    }
    base_mult = price_multipliers.get(age_str, 4.0)

    # قائمة الدول الشائعة في قسم الحسابات القديمة مع أسعارها وتوفرها
    base_countries = [
        {'code': 'UA', 'factor': 1.05, 'qty': 24},
        {'code': 'KZ', 'factor': 1.00, 'qty': 31},
        {'code': 'EG', 'factor': 0.95, 'qty': 18},
        {'code': 'IQ', 'factor': 1.05, 'qty': 15},
        {'code': 'ES', 'factor': 1.02, 'qty': 12},
        {'code': 'SY', 'factor': 0.96, 'qty': 14},
        {'code': 'RS', 'factor': 0.98, 'qty': 9},
        {'code': 'BO', 'factor': 1.02, 'qty': 11},
        {'code': 'KW', 'factor': 1.04, 'qty': 16},
        {'code': 'SG', 'factor': 1.05, 'qty': 8},
        {'code': 'ID', 'factor': 0.88, 'qty': 27},
        {'code': 'TR', 'factor': 0.93, 'qty': 20},
        {'code': 'BD', 'factor': 0.80, 'qty': 35},
        {'code': 'MY', 'factor': 0.97, 'qty': 17},
        {'code': 'PK', 'factor': 0.85, 'qty': 22},
        {'code': 'NG', 'factor': 0.82, 'qty': 29},
        {'code': 'US', 'factor': 1.20, 'qty': 10},
        {'code': 'RU', 'factor': 1.04, 'qty': 26},
        {'code': 'UZ', 'factor': 1.08, 'qty': 19},
        {'code': 'SA', 'factor': 1.25, 'qty': 7},
        {'code': 'MA', 'factor': 0.92, 'qty': 14},
        {'code': 'DZ', 'factor': 0.91, 'qty': 16},
        {'code': 'BR', 'factor': 0.99, 'qty': 18},
        {'code': 'VN', 'factor': 0.89, 'qty': 21}
    ]

    result = []
    for item in base_countries:
        c_code = item['code']
        info = ISO_COUNTRY_MAP.get(c_code)
        if info:
            name_str = f"{info['flag']} {info['name']}"
        else:
            clean_info = get_clean_country_info(c_code)
            name_str = f"{clean_info['flag']} {clean_info['name']}" if clean_info else f"🌍 {c_code}"
            
        raw_price = round(base_mult * item['factor'], 2)
        price_with_profit = round(raw_price * (1 + PROFIT_MARGIN), 2)
        
        result.append({
            'code': c_code,
            'name': name_str,
            'price': price_with_profit,
            'count': item['qty'],
            'raw_price': raw_price,
            'age': age_str
        })
    
    return result

def fetch_ready_accounts_api(server_id='1', age=None, force_refresh=False):
    server_id = str(server_id)
    cache_key = f"{server_id}_{age}" if age else server_id
    now = time.time()
    
    # استخدام الكاش السريع (صلاحية 180 ثانية لسرعة فائقة)
    if not force_refresh:
        with READY_CACHE_LOCK:
            if cache_key in READY_ACCOUNTS_CACHE and (now - READY_CACHE_TIME.get(cache_key, 0) < 180):
                return READY_ACCOUNTS_CACHE[cache_key]

    # السيرفر 3 (حسابات قديمة - معتقة) له كتالوج وأسعار ومخزون خاص مستقل كلياً
    if server_id == '3' or age:
        countries_data = get_aged_accounts_catalog(age or '2021')
        with READY_CACHE_LOCK:
            READY_ACCOUNTS_CACHE[cache_key] = countries_data
            READY_CACHE_TIME[cache_key] = now
        return countries_data

    srv = READY_ACCOUNTS_PROVIDERS.get(server_id)
    countries_data = []

    if srv and srv.get('api_key') and srv.get('url'):
        p_type = srv.get('type')
        api_key = srv['api_key']
        user_id = srv.get('user_id', ADMIN_ID)
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        # 1. السيرفر 1 (TG-Lion)
        if p_type == 'tglion':
            try:
                url = f"https://TG-Lion.net?action=available_countries&apiKey={api_key}&YourID={user_id}"
                res = requests.get(url, headers=headers, timeout=8)
                if res.status_code == 200:
                    data = res.json()
                    if data.get('status') == 'ok' and isinstance(data.get('countries'), dict):
                        for code, cinfo in data['countries'].items():
                            if isinstance(cinfo, dict):
                                qty = int(cinfo.get('qty', 0))
                                raw_p = float(cinfo.get('price', 0))
                                if qty > 0 and raw_p > 0:
                                    c_code = str(code).upper()
                                    info = ISO_COUNTRY_MAP.get(c_code)
                                    if info:
                                        name_str = f"{info['flag']} {info['name']}"
                                    else:
                                        clean_info = get_clean_country_info(c_code)
                                        name_str = f"{clean_info['flag']} {clean_info['name']}" if clean_info else cinfo.get('name', f"🌍 {c_code}")
                                    price_with_profit = round(raw_p * (1 + PROFIT_MARGIN), 2)
                                    countries_data.append({
                                        'code': c_code,
                                        'name': name_str,
                                        'price': price_with_profit,
                                        'count': qty,
                                        'raw_price': raw_p
                                    })
            except Exception as e:
                print(f"Error fetching TG-Lion ready accounts: {e}")

        # 2. السيرفر 2 (Spider Service)
        elif p_type == 'spider':
            try:
                url = f"https://api.spider-service.com?apiKay={api_key}&action=getCountrys"
                res = requests.get(url, headers=headers, timeout=8)
                if res.status_code == 200:
                    data = res.json()
                    if data.get('ok') and isinstance(data.get('result'), dict):
                        countries_dict = data['result'].get('countries', {}).get('1', {})
                        cuantity_dict = data['result'].get('cuantity', {}).get('1', {})
                        for code, p_str in countries_dict.items():
                            c_code = str(code).upper()
                            try:
                                raw_p = float(p_str)
                                qty = int(cuantity_dict.get(code, 0))
                            except:
                                continue
                            if qty > 0 and raw_p > 0:
                                info = ISO_COUNTRY_MAP.get(c_code)
                                if info:
                                    name_str = f"{info['flag']} {info['name']}"
                                else:
                                    clean_info = get_clean_country_info(c_code)
                                    name_str = f"{clean_info['flag']} {clean_info['name']}" if clean_info else f"🌍 {c_code}"
                                price_with_profit = round(raw_p * (1 + PROFIT_MARGIN), 2)
                                countries_data.append({
                                    'code': c_code,
                                    'name': name_str,
                                    'price': price_with_profit,
                                    'count': qty,
                                    'raw_price': raw_p
                                })
            except Exception as e:
                print(f"Error fetching Spider ready accounts: {e}")

    # الترتيب حسب الكمية الأكثر توفراً
    if countries_data:
        countries_data.sort(key=lambda x: x['count'], reverse=True)

    with READY_CACHE_LOCK:
        if countries_data:
            READY_ACCOUNTS_CACHE[cache_key] = countries_data
            READY_CACHE_TIME[cache_key] = now
        elif cache_key not in READY_ACCOUNTS_CACHE:
            READY_ACCOUNTS_CACHE[cache_key] = []
            READY_CACHE_TIME[cache_key] = now

    return READY_ACCOUNTS_CACHE.get(cache_key, [])

def buy_ready_account_api(server_id, country_code):
    """شراء حساب تيليجرام جاهز عبر API المزود الحقيقي"""
    srv = READY_ACCOUNTS_PROVIDERS.get(str(server_id))
    if not srv:
        return {'ok': False, 'error': 'سيرفر غير موجود'}
    
    p_type = srv.get('type')
    api_key = srv['api_key']
    user_id = srv.get('user_id', ADMIN_ID)
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        if p_type == 'tglion':
            url = f"https://TG-Lion.net?action=getNumber&apiKey={api_key}&YourID={user_id}&country_code={country_code.lower()}"
            res = requests.get(url, headers=headers, timeout=12).json()
            if res.get('status') == 'ok' and res.get('Number'):
                return {
                    'ok': True,
                    'number': res.get('Number'),
                    'name': res.get('name'),
                    'cost': float(res.get('price', 0)),
                    'provider': 'tglion'
                }
            else:
                err_msg = res.get('message') or res.get('error') or 'خطأ في المزود'
                return {'ok': False, 'error': err_msg}
        elif p_type == 'spider':
            url = f"https://api.spider-service.com?apiKay={api_key}&action=getNumber&country={country_code.upper()}"
            res = requests.get(url, headers=headers, timeout=12).json()
            if res.get('ok') and isinstance(res.get('result'), dict):
                num = res['result'].get('number') or res['result'].get('Number')
                hash_code = res['result'].get('hash_code')
                return {
                    'ok': True,
                    'number': num,
                    'hash_code': hash_code,
                    'provider': 'spider'
                }
            else:
                err_msg = res.get('error') or res.get('msg') or 'خطأ في المزود'
                return {'ok': False, 'error': err_msg}
    except Exception as e:
        return {'ok': False, 'error': str(e)}

def get_ready_account_code_api(server_id, number_or_hash):
    """جلب كود التفعيل وكلمة السر للحساب الجاهز من المزود"""
    srv = READY_ACCOUNTS_PROVIDERS.get(str(server_id))
    if not srv:
        return {'ok': False, 'error': 'سيرفر غير موجود'}
    
    p_type = srv.get('type')
    api_key = srv['api_key']
    user_id = srv.get('user_id', ADMIN_ID)
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        if p_type == 'tglion':
            url = f"https://TG-Lion.net?action=getCode&number={number_or_hash}&apiKey={api_key}&YourID={user_id}"
            res = requests.get(url, headers=headers, timeout=12).json()
            if res.get('status') == 'ok':
                return {
                    'ok': True,
                    'code': res.get('code'),
                    'password': res.get('pass'),
                    'number': res.get('Number')
                }
            else:
                return {'ok': False, 'error': res.get('message', 'لم يصل الكود بعد')}
        elif p_type == 'spider':
            url = f"https://api.spider-service.com?apiKay={api_key}&action=getCode&hash_code={number_or_hash}"
            res = requests.get(url, headers=headers, timeout=12).json()
            if res.get('ok') and isinstance(res.get('result'), dict):
                return {
                    'ok': True,
                    'code': res['result'].get('code'),
                    'password': res['result'].get('pass') or res['result'].get('password'),
                    'number': res['result'].get('number')
                }
            else:
                return {'ok': False, 'error': res.get('error', 'لم يصل الكود بعد')}
    except Exception as e:
        return {'ok': False, 'error': str(e)}

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

