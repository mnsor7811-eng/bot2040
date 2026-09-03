import os
import sqlite3
import time
import threading
import json
import urllib.request
import urllib.parse
import ssl
try:
    import google.generativeai as genai
except ImportError:
    genai = None

# ==================== دوال HTTP قياسية باستخدام مكتبة urllib بدون الحاجة لمكتبات خارجية ====================
def http_get_json(url, headers=None, timeout=10, params=None):
    """تنفيذ طلب GET واسترجاع النتيجة كـ JSON بشكل موثوق وسريع"""
    try:
        if params:
            query = urllib.parse.urlencode(params)
            url = f"{url}?{query}" if '?' not in url else f"{url}&{query}"
        req_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        if headers:
            req_headers.update(headers)
        req = urllib.request.Request(url, headers=req_headers)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            data = resp.read().decode('utf-8', errors='ignore')
            return json.loads(data)
    except Exception as e:
        print(f"HTTP GET JSON Error ({url}): {e}")
        return None

def http_get_text(url, headers=None, timeout=10, params=None):
    """تنفيذ طلب GET واسترجاع النتيجة كنص خام"""
    try:
        if params:
            query = urllib.parse.urlencode(params)
            url = f"{url}?{query}" if '?' not in url else f"{url}&{query}"
        req_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        if headers:
            req_headers.update(headers)
        req = urllib.request.Request(url, headers=req_headers)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read().decode('utf-8', errors='ignore').strip()
    except Exception as e:
        return f"ERROR: {e}"

def http_post_form(url, data_dict, headers=None, timeout=12):
    """تنفيذ طلب POST ببيانات Form واسترجاع JSON"""
    try:
        encoded_data = urllib.parse.urlencode(data_dict).encode('utf-8')
        req_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        if headers:
            req_headers.update(headers)
        req = urllib.request.Request(url, data=encoded_data, headers=req_headers, method='POST')
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            data = resp.read().decode('utf-8', errors='ignore')
            return json.loads(data)
    except Exception as e:
        print(f"HTTP POST Error ({url}): {e}")
        return None

# ==================== الإعدادات الأساسية ====================
TOKEN = os.getenv('TOKEN', '8927305428:AAH7CGvaZRpXE7whw5dIr8B9UF-tePExmAk')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AQ.Ab8RN6IOLYCW3mnMh6H5le6Bc1pAG60TXO0IoxjpPcHvaFZHkg')
ADMIN_ID = int(os.getenv('ADMIN_ID', 6113734300))
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', '@Num_s7')

# ==================== روابط القنوات الرسمية ====================
CHANNEL_OFFICIAL_NAME = "قناة البوت الرسمية"
CHANNEL_OFFICIAL_ID = "-1003004681072"
CHANNEL_OFFICIAL_URL = "https://t.me/SM_SMS7"

CHANNEL_ORDERS_NAME = "قناة التفعيلات والطلبات"
CHANNEL_ORDERS_ID = "-1002987190358"
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
        'api_key': os.getenv('GRIZZLY_API_KEY', 'aed7993f2abbded229628261c56746d5'),
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

# ==================== قائمة الخدمات والتطبيقات الأكثر طلباً ====================
POPULAR_SERVICES = {
    'wa': {'name': 'واتساب (WhatsApp)', 'icon': '🟢'},
    'tg': {'name': 'تليجرام (Telegram)', 'icon': '🔵'},
    'go': {'name': 'جوجل / جيميل (Google)', 'icon': '🔴'},
    'fb': {'name': 'فيسبوك (Facebook)', 'icon': '👥'},
    'ig': {'name': 'إنستغرام (Instagram)', 'icon': '📸'},
    'lf': {'name': 'تيك توك (TikTok)', 'icon': '🎵'},
    'tw': {'name': 'تويتر / إكس (Twitter / X)', 'icon': '🐦'},
    'im': {'name': 'إيمو (IMO)', 'icon': '💬'},
    'ts': {'name': 'باي بال (PayPal)', 'icon': '💳'},
    'nf': {'name': 'نتفليكس (Netflix)', 'icon': '🎬'},
    'wx': {'name': 'أبل (Apple ID)', 'icon': '🍏'},
    'am': {'name': 'أمازون (Amazon)', 'icon': '📦'},
    'ub': {'name': 'أوبر (Uber)', 'icon': '🚗'},
    'ot': {'name': 'أي موقع أو تطبيق آخر (Other)', 'icon': '🌐'}
}

# ==================== خريطة الدول المعتمدة لمزودات الأرقام ====================
COUNTRY_MAP = {
    "0": {"name": "روسيا", "flag": "🇷🇺"}, "1": {"name": "أوكرانيا", "flag": "🇺🇦"},
    "2": {"name": "كازاخستان", "flag": "🇰🇿"}, "3": {"name": "الصين", "flag": "🇨🇳"},
    "4": {"name": "الفلبين", "flag": "🇵🇭"}, "5": {"name": "ميانمار", "flag": "🇲🇲"},
    "6": {"name": "إندونيسيا", "flag": "🇮🇩"}, "7": {"name": "ماليزيا", "flag": "🇲🇾"},
    "8": {"name": "كينيا", "flag": "🇰🇪"}, "9": {"name": "تنزانيا", "flag": "🇹🇿"},
    "10": {"name": "فيتنام", "flag": "🇻🇳"}, "11": {"name": "قيرغيزستان", "flag": "🇰🇬"},
    "12": {"name": "أمريكا (افتراضي)", "flag": "🇺🇸"}, "13": {"name": "إسرائيل", "flag": "🇮🇱"},
    "14": {"name": "هونغ كونغ", "flag": "🇭🇰"}, "15": {"name": "بولندا", "flag": "🇵🇱"},
    "16": {"name": "المملكة المتحدة", "flag": "🇬🇧"}, "17": {"name": "مدغشقر", "flag": "🇲🇬"},
    "18": {"name": "جمهورية الكونغو الديمقراطية", "flag": "🇨🇩"}, "19": {"name": "نيجيريا", "flag": "🇳🇬"},
    "20": {"name": "ماكاو", "flag": "🇲🇴"}, "21": {"name": "مصر", "flag": "🇪🇬"},
    "22": {"name": "الهند", "flag": "🇮🇳"}, "23": {"name": "أيرلندا", "flag": "🇮🇪"},
    "24": {"name": "كمبوديا", "flag": "🇰🇭"}, "25": {"name": "شعب لاو (لاوس)", "flag": "🇱🇦"},
    "26": {"name": "هايتي", "flag": "🇭🇹"}, "27": {"name": "ساحل العاج", "flag": "🇨🇮"},
    "28": {"name": "غامبيا", "flag": "🇬🇲"}, "29": {"name": "صربيا", "flag": "🇷🇸"},
    "30": {"name": "اليمن", "flag": "🇾🇪"}, "31": {"name": "جنوب أفريقيا", "flag": "🇿🇦"},
    "32": {"name": "رومانيا", "flag": "🇷🇴"}, "33": {"name": "كولومبيا", "flag": "🇨🇴"},
    "34": {"name": "إستونيا", "flag": "🇪🇪"}, "35": {"name": "أذربيجان", "flag": "🇦🇿"},
    "36": {"name": "كندا", "flag": "🇨🇦"}, "37": {"name": "المغرب", "flag": "🇲🇦"},
    "38": {"name": "غانا", "flag": "🇬🇭"}, "39": {"name": "الأرجنتين", "flag": "🇦🇷"},
    "40": {"name": "أوزبكستان", "flag": "🇺🇿"}, "41": {"name": "الكاميرون", "flag": "🇨🇲"},
    "42": {"name": "تشاد", "flag": "🇹🇩"}, "43": {"name": "ألمانيا", "flag": "🇩🇪"},
    "44": {"name": "ليتوانيا", "flag": "🇱🇹"}, "45": {"name": "كرواتيا", "flag": "🇭🇷"},
    "46": {"name": "السويد", "flag": "🇸🇪"}, "47": {"name": "العراق", "flag": "🇮🇶"},
    "48": {"name": "هولندا", "flag": "🇳🇱"}, "49": {"name": "لاتفيا", "flag": "🇱🇻"},
    "50": {"name": "النمسا", "flag": "🇦🇹"}, "51": {"name": "بيلاروسيا", "flag": "🇧🇾"},
    "52": {"name": "تايلاند", "flag": "🇹🇭"}, "53": {"name": "المملكة العربية السعودية", "flag": "🇸🇦"},
    "54": {"name": "المكسيك", "flag": "🇲🇽"}, "55": {"name": "تايوان", "flag": "🇹🇼"},
    "56": {"name": "إسبانيا", "flag": "🇪🇸"}, "57": {"name": "الجزائر", "flag": "🇩🇿"},
    "58": {"name": "الجزائر", "flag": "🇩🇿"}, "59": {"name": "سلوفينيا", "flag": "🇸🇮"},
    "60": {"name": "بنغلاديش", "flag": "🇧🇩"}, "61": {"name": "السنغال", "flag": "🇸🇳"},
    "62": {"name": "تركيا", "flag": "🇹🇷"}, "63": {"name": "جمهورية التشيك", "flag": "🇨🇿"},
    "64": {"name": "سري لانكا", "flag": "🇱🇰"}, "65": {"name": "بيرو", "flag": "🇵🇪"},
    "66": {"name": "باكستان", "flag": "🇵🇰"}, "67": {"name": "نيوزيلندا", "flag": "🇳🇿"},
    "68": {"name": "غينيا", "flag": "🇬🇳"}, "69": {"name": "مالي", "flag": "🇲🇱"},
    "70": {"name": "فنزويلا", "flag": "🇻🇪"}, "71": {"name": "إثيوبيا", "flag": "🇪🇹"},
    "72": {"name": "منغوليا", "flag": "🇲🇳"}, "73": {"name": "البرازيل", "flag": "🇧🇷"},
    "74": {"name": "أفغانستان", "flag": "🇦🇫"}, "75": {"name": "أوغندا", "flag": "🇺🇬"},
    "76": {"name": "أنغولا", "flag": "🇦🇴"}, "77": {"name": "قبرص", "flag": "🇨🇾"},
    "78": {"name": "فرنسا", "flag": "🇫🇷"}, "79": {"name": "بابوا غينيا الجديدة", "flag": "🇵🇬"},
    "80": {"name": "موزامبيق", "flag": "🇲🇿"}, "81": {"name": "نيبال", "flag": "🇳🇵"},
    "82": {"name": "بلجيكا", "flag": "🇧🇪"}, "83": {"name": "بلغاريا", "flag": "🇧🇬"},
    "84": {"name": "هنغاريا (المجر)", "flag": "🇭🇺"}, "85": {"name": "مولدوفا", "flag": "🇲🇩"},
    "86": {"name": "إيطاليا", "flag": "🇮🇹"}, "87": {"name": "باراغواي", "flag": "🇵🇾"},
    "88": {"name": "هندوراس", "flag": "🇭🇳"}, "89": {"name": "تونس", "flag": "🇹🇳"},
    "90": {"name": "نيكاراغوا", "flag": "🇳🇮"}, "91": {"name": "تيمور-ليشتي", "flag": "🇹🇱"},
    "92": {"name": "بوليفيا", "flag": "🇧🇴"}, "93": {"name": "كوستاريكا", "flag": "🇨🇷"},
    "94": {"name": "غواتيمالا", "flag": "🇬🇹"}, "95": {"name": "الإمارات العربية المتحدة", "flag": "🇦🇪"},
    "96": {"name": "زيمبابوي", "flag": "🇿🇼"}, "97": {"name": "بورتوريكو", "flag": "🇵🇷"},
    "98": {"name": "السودان", "flag": "🇸🇩"}, "99": {"name": "توغو", "flag": "🇹🇬"},
    "100": {"name": "الكويت", "flag": "🇰🇼"}, "101": {"name": "السلفادور", "flag": "🇸🇻"},
    "102": {"name": "ليبيا", "flag": "🇱🇾"}, "103": {"name": "جامايكا", "flag": "🇯🇲"},
    "104": {"name": "ترينيداد وتوباغو", "flag": "🇹🇹"}, "105": {"name": "الإكوادور", "flag": "🇪🇨"},
    "106": {"name": "سوازيلند (إسواتيني)", "flag": "🇸🇿"}, "107": {"name": "عمان", "flag": "🇴🇲"},
    "108": {"name": "البوسنة والهرسك", "flag": "🇧🇦"}, "109": {"name": "الجمهورية الدومينيكية", "flag": "🇩🇴"},
    "110": {"name": "سوريا", "flag": "🇸🇾"}, "111": {"name": "قطر", "flag": "🇶🇦"},
    "112": {"name": "بنما", "flag": "🇵🇦"}, "113": {"name": "كوبا", "flag": "🇨🇺"},
    "114": {"name": "موريتانيا", "flag": "🇲🇷"}, "115": {"name": "سيراليون", "flag": "🇸🇱"},
    "116": {"name": "الأردن", "flag": "🇯🇴"}, "117": {"name": "البرتغال", "flag": "🇵🇹"},
    "118": {"name": "بربادوس", "flag": "🇧🇧"}, "119": {"name": "بوروندي", "flag": "🇧🇮"},
    "120": {"name": "بنين", "flag": "🇧🇯"}, "121": {"name": "بروني دار السلام", "flag": "🇧🇳"},
    "122": {"name": "جزر البهاما", "flag": "🇧🇸"}, "123": {"name": "بوتسوانا", "flag": "🇧🇼"},
    "124": {"name": "بليز", "flag": "🇧🇿"}, "125": {"name": "جمهورية أفريقيا الوسطى", "flag": "🇨🇫"},
    "126": {"name": "دومينيكا", "flag": "🇩🇲"}, "127": {"name": "غرينادا", "flag": "🇬🇩"},
    "128": {"name": "جورجيا", "flag": "🇬🇪"}, "129": {"name": "اليونان", "flag": "🇬🇷"},
    "130": {"name": "غينيا-بيساو", "flag": "🇬🇼"}, "131": {"name": "غيانا", "flag": "🇬🇾"},
    "132": {"name": "آيسلندا", "flag": "🇮🇸"}, "133": {"name": "جزر القمر", "flag": "🇰🇲"},
    "134": {"name": "سانت كيتس ونيفيس", "flag": "🇰🇳"}, "135": {"name": "ليبيريا", "flag": "🇱🇷"},
    "136": {"name": "ليسوتو", "flag": "🇱🇸"}, "137": {"name": "ملاوي", "flag": "🇲🇼"},
    "138": {"name": "نامبيا", "flag": "🇳🇦"}, "139": {"name": "النيجر", "flag": "🇳🇪"},
    "140": {"name": "رواندا", "flag": "🇷🇼"}, "141": {"name": "سلوفاكيا", "flag": "🇸🇰"},
    "142": {"name": "سورينام", "flag": "🇸🇷"}, "143": {"name": "طاجيكستان", "flag": "🇹🇯"},
    "144": {"name": "موناكو", "flag": "🇲🇨"}, "145": {"name": "البحرين", "flag": "🇧🇭"},
    "146": {"name": "لم الشمل (ريونيون)", "flag": "🇷🇪"}, "147": {"name": "زامبيا", "flag": "🇿🇲"},
    "148": {"name": "أرمينيا", "flag": "🇦🇲"}, "149": {"name": "الصومال", "flag": "🇸🇴"},
    "150": {"name": "جمهورية الكونغو", "flag": "🇨🇬"}, "151": {"name": "شيلي (تشيلي)", "flag": "🇨🇱"},
    "152": {"name": "بوركينا فاسو", "flag": "🇧🇫"}, "153": {"name": "لبنان", "flag": "🇱🇧"},
    "154": {"name": "غابون", "flag": "🇬🇦"}, "155": {"name": "ألبانيا", "flag": "🇦🇱"},
    "156": {"name": "أوروغواي", "flag": "🇺🇾"}, "157": {"name": "موريشيوس", "flag": "🇲🇺"},
    "158": {"name": "بوتان", "flag": "🇧🇹"}, "159": {"name": "ملديف", "flag": "🇲🇻"},
    "160": {"name": "غوادلوب", "flag": "🇬🇵"}, "161": {"name": "تركمانستان", "flag": "🇹🇲"},
    "162": {"name": "غيانا الفرنسية", "flag": "🇬🇫"}, "163": {"name": "فنلندا", "flag": "🇫🇮"},
    "164": {"name": "سانت لوسيا", "flag": "🇱🇨"}, "165": {"name": "لوكسمبورغ", "flag": "🇱🇺"},
    "166": {"name": "سانت فنسنت", "flag": "🇻🇨"}, "167": {"name": "غينيا الاستوائية", "flag": "🇬🇶"},
    "168": {"name": "جيبوتي", "flag": "🇩🇯"}, "170": {"name": "جزر كايمان", "flag": "🇰🇾"},
    "173": {"name": "سويسرا", "flag": "🇨🇭"}, "174": {"name": "النرويج", "flag": "🇳🇴"},
    "177": {"name": "جنوب السودان", "flag": "🇸🇸"}, "178": {"name": "سان تومي وبرينسيبي", "flag": "🇸🇹"},
    "180": {"name": "مونتسيرات", "flag": "🇲🇸"}, "182": {"name": "اليابان", "flag": "🇯🇵"},
    "183": {"name": "مقدونيا الشمالية", "flag": "🇲🇰"}, "184": {"name": "سيشيل", "flag": "🇸🇨"},
    "185": {"name": "كاليدونيا الجديدة", "flag": "🇳🇨"}, "187": {"name": "الولايات المتحدة الأمريكية", "flag": "🇺🇸"},
    "188": {"name": "فلسطين", "flag": "🇵🇸"}, "189": {"name": "فيجي", "flag": "🇫🇯"},
    "199": {"name": "مالطا", "flag": "🇲🇹"}, "201": {"name": "جبل طارق", "flag": "🇬🇮"},
    "203": {"name": "كوسوفو", "flag": "🇽🇰"}, "204": {"name": "نيوي", "flag": "🇳🇺"},
    "1003": {"name": "برمودا", "flag": "🇧🇲"}, "1007": {"name": "فانواتو", "flag": "🇻🇺"},
    "1008": {"name": "جرينلاند", "flag": "🇬🇱"}, "1011": {"name": "مارتينيك", "flag": "🇲🇶"},
    "1012": {"name": "بولينيزيا الفرنسية", "flag": "🇵🇫"}, "1062": {"name": "أندورا", "flag": "🇦🇩"},
    "10161": {"name": "ساموا الأمريكية", "flag": "🇦🇸"}, "10227": {"name": "تونغا", "flag": "🇹🇴"},
    "10231": {"name": "ساموا", "flag": "🇼🇸"}, "10348": {"name": "ليختنشتاين", "flag": "🇱🇮"},
    "10349": {"name": "سانت مارتن", "flag": "🇲🇫"}, "10350": {"name": "كوريا الجنوبية", "flag": "🇰🇷"},
    "10351": {"name": "سنغافورة", "flag": "🇸🇬"}
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

# ==================== قاعدة البيانات الدائمة وشاملة الحفظ ====================
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(_BASE_DIR, 'bot_database.db')
if not os.path.exists(DB_FILE) and os.path.exists('bot_database.db'):
    DB_FILE = os.path.abspath('bot_database.db')

def get_db():
    conn = sqlite3.connect(DB_FILE, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def setup_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. جدول المستخدمين الدائم والشامل
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        name TEXT,
                        username TEXT,
                        balance REAL DEFAULT 0.0,
                        spent_balance REAL DEFAULT 0.0,
                        orders_count INTEGER DEFAULT 0,
                        ai_balance INTEGER DEFAULT 5, 
                        is_banned INTEGER DEFAULT 0,
                        is_agent INTEGER DEFAULT 0,
                        agent_discount REAL DEFAULT 0.0,
                        referred_by INTEGER DEFAULT 0,
                        referrals_count INTEGER DEFAULT 0,
                        referrals_earnings REAL DEFAULT 0.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )''')

    # إضافة الأعمدة الجديدة إذا كانت القاعدة قديمة
    for col_def in [
        ("spent_balance", "REAL DEFAULT 0.0"),
        ("orders_count", "INTEGER DEFAULT 0"),
        ("is_agent", "INTEGER DEFAULT 0"),
        ("agent_discount", "REAL DEFAULT 0.0"),
        ("referrals_count", "INTEGER DEFAULT 0"),
        ("referrals_earnings", "REAL DEFAULT 0.0"),
        ("last_active", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ]:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_def[0]} {col_def[1]}")
        except Exception:
            pass

    # 2. جدول الإعدادات العامة القابلة للتحكم من لوحة الإدارة
    cursor.execute('''CREATE TABLE IF NOT EXISTS bot_settings (
                        setting_key TEXT PRIMARY KEY,
                        setting_value TEXT
                    )''')

    # 3. جدول طرق الدفع الديناميكية
    cursor.execute('''CREATE TABLE IF NOT EXISTS payment_methods (
                        method_id TEXT PRIMARY KEY,
                        name TEXT,
                        acc_number TEXT,
                        min_amount TEXT,
                        exchange_rate TEXT,
                        is_active INTEGER DEFAULT 1
                    )''')

    # 4. جدول المزودين ومفاتيح API
    cursor.execute('''CREATE TABLE IF NOT EXISTS providers (
                        provider_id TEXT PRIMARY KEY,
                        name TEXT,
                        category TEXT,
                        type TEXT,
                        api_key TEXT,
                        url TEXT,
                        user_id TEXT,
                        is_active INTEGER DEFAULT 1
                    )''')

    # 5. جدول الوكلاء
    cursor.execute('''CREATE TABLE IF NOT EXISTS agents (
                        user_id INTEGER PRIMARY KEY,
                        name TEXT,
                        discount_percent REAL DEFAULT 5.0,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )''')

    # 6. جدول مخزون الحسابات القديمة والمعتقة (السيرفر 3)
    cursor.execute('''CREATE TABLE IF NOT EXISTS aged_stock (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        year_label TEXT,
                        country_code TEXT,
                        phone TEXT,
                        two_fa_pass TEXT,
                        session_data TEXT,
                        price REAL,
                        is_sold INTEGER DEFAULT 0,
                        sold_to INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )''')

    # 7. جدول مشتريات الأرقام
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

    # 8. جدول طلبات الرشق
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

    # 9. جدول طلبات الحسابات الجاهزة والمعتقة
    cursor.execute('''CREATE TABLE IF NOT EXISTS ready_accounts_orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        server_id TEXT,
                        country_name TEXT,
                        phone TEXT,
                        two_fa TEXT,
                        session_file TEXT,
                        cost REAL,
                        status TEXT DEFAULT 'COMPLETED',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )''')

    # تهيئة الإعدادات الافتراضية
    default_settings = {
        'profit_margin_numbers': '0.10',
        'profit_margin_ready': '0.10',
        'profit_margin_smm': '0.10',
        'reward_per_invite': '0.05',
        'min_invite_withdraw': '1.0',
        'min_transfer_amount': '1.0',
        'transfer_fee_percent': '0.0',
        'maintenance_mode': '0',
        'force_sub_active': '1',
        'channel_official_url': 'https://t.me/SM_SMS7',
        'channel_official_id': '-1003004681072',
        'channel_orders_url': 'https://t.me/numbuersms',
        'channel_orders_id': '-1002987190358',
        'support_admin_1': '@Num_s7',
        'support_admin_2': '@Support_SMS7',
        'section_numbers_active': '1',
        'section_ready_active': '1',
        'section_smm_active': '1',
        'section_recharge_active': '1',
        'section_transfer_active': '1',
        'section_free_active': '1',
        'section_store_active': '1',
        'section_ai_active': '1'
    }

    for k, v in default_settings.items():
        cursor.execute("INSERT OR IGNORE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)", (k, v))

    # تهيئة طرق الدفع الافتراضية
    default_payments = [
        ('kuraimi', '🏦 بنك الكريمي', '3134706987', '100 ريال', '1$ = 550 ريال', 1),
        ('jeeb', '📱 محفظة جيب', '374468', '50 ريال', '1$ = 550 ريال', 1),
        ('onecash', '💳 محفظة ون كاش', '140601836', '100 ريال', '1$ = 550 ريال', 1),
        ('binance', '🟡 Binance Pay', '979808293', '0.5 $', '1$ = 1$', 1)
    ]
    for p in default_payments:
        cursor.execute("INSERT OR IGNORE INTO payment_methods (method_id, name, acc_number, min_amount, exchange_rate, is_active) VALUES (?, ?, ?, ?, ?, ?)", p)

    # تهيئة المزودين الافتراضيين
    default_providers = [
        ('ready_1', 'السيرفر 1 (TG-Lion)', 'ready', 'tglion', 'ncgw41immHj3Cadmxy', 'https://TG-Lion.net', '6113734300', 1),
        ('ready_2', 'السيرفر 2 (Spider)', 'ready', 'spider', 'a3ea1259e871e8477ffdf7859b8c2ff5', 'https://api.spider-service.com', '6113734300', 1),
        ('ready_3', 'السيرفر 3 (معتقة بالسنوات)', 'ready', 'aged_custom', 'internal', 'https://t.me/SM_SMS7', '6113734300', 1),
        ('smm_1', 'سيرفر الرشق (SMMxStar)', 'smm', 'smm', '13cb06a01b5a7259c14c1727c2f5591d', 'https://smmxstar.com/api/v2', '', 1),
        ('num_grizzly', 'سيرفر الأرقام 1 (Grizzly)', 'numbers', 'grizzly', 'Aed7993f2abbded229628261c56746d5', 'https://grizzlysms.com/stubs/handler_api.php', '', 1),
        ('num_smsman', 'سيرفر الأرقام 2 (SMS-Man)', 'numbers', 'smsman', 'y-PEwx3CbW00xho3rU2XobIia195Oobo', 'https://api.sms-man.com/control/', '', 1)
    ]
    for prv in default_providers:
        cursor.execute("INSERT OR IGNORE INTO providers (provider_id, name, category, type, api_key, url, user_id, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", prv)

    conn.commit()
    conn.close()

setup_db()

# ==================== دوال الإعدادات الدائمة والمحفوظة ====================
def get_setting(key, default=""):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT setting_value FROM bot_settings WHERE setting_key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else str(default)
    except Exception:
        return str(default)
    finally:
        conn.close()

def set_setting(key, value):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR REPLACE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)", (key, str(value)))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error set_setting {key}: {e}")
        return False
    finally:
        conn.close()

def is_section_enabled(section_name):
    """التحقق من حالة تشغيل أي قسم (1 مفعل، 0 معطل)"""
    key = f"section_{section_name}_active"
    return get_setting(key, '1') == '1'

def toggle_section(section_name):
    """عكس حالة القسم بين تشغيل وإيقاف"""
    key = f"section_{section_name}_active"
    curr = get_setting(key, '1')
    new_val = '0' if curr == '1' else '1'
    set_setting(key, new_val)
    return new_val == '1'

def get_profit_margin(category='numbers'):
    """جلب نسبة الربح المحددة لأي قسم"""
    key = f"profit_margin_{category}"
    try:
        return float(get_setting(key, '0.10'))
    except:
        return 0.10

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

def get_or_create_user(user_id, name, username=""):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute('''INSERT INTO users 
            (user_id, name, username, balance, spent_balance, orders_count, ai_balance, is_banned, is_agent, agent_discount, referred_by, referrals_count, referrals_earnings) 
            VALUES (?, ?, ?, 0.0, 0.0, 0, 5, 0, 0, 0.0, 0, 0, 0.0)''', (user_id, name, username or ""))
        conn.commit()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
    else:
        # تحديث الاسم والمعرف وتاريخ آخر تفاعل
        cursor.execute('UPDATE users SET name = ?, username = COALESCE(NULLIF(?, ""), username), last_active = CURRENT_TIMESTAMP WHERE user_id = ?', (name, username or "", user_id))
        conn.commit()
    conn.close()
    return user

def record_user_purchase(user_id, amount):
    """تسجيل عملية شراء وخصم رصيد وإضافة للمصروفات وعدد الطلبات بشكل دائم ومحمي"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''UPDATE users 
                          SET balance = MAX(0.0, balance - ?), 
                              spent_balance = spent_balance + ?, 
                              orders_count = orders_count + 1,
                              last_active = CURRENT_TIMESTAMP 
                          WHERE user_id = ?''', (amount, amount, user_id))
        conn.commit()
    except Exception as e:
        print(f"Error recording purchase for {user_id}: {e}")
    finally:
        conn.close()

def add_user_balance(user_id, amount):
    """إضافة رصيد للمستخدم مع الحفظ الدائم"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE users SET balance = balance + ?, last_active = CURRENT_TIMESTAMP WHERE user_id = ?', (amount, user_id))
        conn.commit()
        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        res = cursor.fetchone()
        return res[0] if res else 0.0
    finally:
        conn.close()

def deduct_user_balance(user_id, amount):
    """خصم رصيد من المستخدم مع الحفظ الدائم"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE users SET balance = MAX(0.0, balance - ?), last_active = CURRENT_TIMESTAMP WHERE user_id = ?', (amount, user_id))
        conn.commit()
        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        res = cursor.fetchone()
        return res[0] if res else 0.0
    finally:
        conn.close()

def set_user_ban_status(user_id, is_banned):
    """حظر أو فك حظر المستخدم"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE users SET is_banned = ? WHERE user_id = ?', (1 if is_banned else 0, user_id))
        conn.commit()
    finally:
        conn.close()

# ==================== إدارة طرق الدفع الديناميكية ====================
def get_payment_methods_db():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT method_id, name, acc_number, min_amount, exchange_rate, is_active FROM payment_methods")
        rows = cursor.fetchall()
        methods = {}
        for r in rows:
            methods[r[0]] = {
                'id': r[0],
                'name': r[1],
                'acc': r[2],
                'min': r[3],
                'rate': r[4],
                'is_active': bool(r[5])
            }
        return methods
    finally:
        conn.close()

def update_payment_method_db(method_id, acc_number=None, min_amount=None, exchange_rate=None, name=None):
    conn = get_db()
    cursor = conn.cursor()
    try:
        if acc_number is not None:
            cursor.execute("UPDATE payment_methods SET acc_number = ? WHERE method_id = ?", (acc_number, method_id))
        if min_amount is not None:
            cursor.execute("UPDATE payment_methods SET min_amount = ? WHERE method_id = ?", (min_amount, method_id))
        if exchange_rate is not None:
            cursor.execute("UPDATE payment_methods SET exchange_rate = ? WHERE method_id = ?", (exchange_rate, method_id))
        if name is not None:
            cursor.execute("UPDATE payment_methods SET name = ? WHERE method_id = ?", (name, method_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating payment method {method_id}: {e}")
        return False
    finally:
        conn.close()

def toggle_payment_method_db(method_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT is_active FROM payment_methods WHERE method_id = ?", (method_id,))
        row = cursor.fetchone()
        if row:
            new_st = 0 if row[0] == 1 else 1
            cursor.execute("UPDATE payment_methods SET is_active = ? WHERE method_id = ?", (new_st, method_id))
            conn.commit()
            return new_st == 1
        return False
    finally:
        conn.close()

# ==================== إدارة المزودين ومفاتيح API ====================
def get_providers_db():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT provider_id, name, category, type, api_key, url, user_id, is_active FROM providers")
        rows = cursor.fetchall()
        prvs = {}
        for r in rows:
            prvs[r[0]] = {
                'id': r[0],
                'name': r[1],
                'category': r[2],
                'type': r[3],
                'api_key': r[4],
                'url': r[5],
                'user_id': r[6],
                'is_active': bool(r[7])
            }
        return prvs
    finally:
        conn.close()

def update_provider_api_key_db(provider_id, new_api_key):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE providers SET api_key = ? WHERE provider_id = ?", (new_api_key, provider_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating provider key: {e}")
        return False
    finally:
        conn.close()

def add_provider_db(provider_id, name, category, p_type, api_key, url, user_id=""):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR REPLACE INTO providers (provider_id, name, category, type, api_key, url, user_id, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
                       (provider_id, name, category, p_type, api_key, url, user_id))
        conn.commit()
        return True
    finally:
        conn.close()

def delete_provider_db(provider_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM providers WHERE provider_id = ?", (provider_id,))
        conn.commit()
        return True
    finally:
        conn.close()

# ==================== إدارة الوكلاء والموزعين ====================
def get_agents_db():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id, name, discount_percent, added_at FROM agents")
        return cursor.fetchall()
    finally:
        conn.close()

def add_agent_db(user_id, name, discount_percent=5.0):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR REPLACE INTO agents (user_id, name, discount_percent) VALUES (?, ?, ?)", (user_id, name, discount_percent))
        cursor.execute("UPDATE users SET is_agent = 1, agent_discount = ? WHERE user_id = ?", (discount_percent, user_id))
        conn.commit()
        return True
    finally:
        conn.close()

def remove_agent_db(user_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM agents WHERE user_id = ?", (user_id,))
        cursor.execute("UPDATE users SET is_agent = 0, agent_discount = 0.0 WHERE user_id = ?", (user_id,))
        conn.commit()
        return True
    finally:
        conn.close()

def get_user_agent_discount(user_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT agent_discount FROM users WHERE user_id = ? AND is_agent = 1", (user_id,))
        res = cursor.fetchone()
        return float(res[0]) if res and res[0] else 0.0
    except:
        return 0.0
    finally:
        conn.close()

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
            res = http_get_json(url, timeout=7)
            if res and isinstance(res, dict):
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
    return http_get_text(url, timeout=10, params=params)

# ==================== دالة جلب دول وأسعار الحسابات الجاهزة عبر API الحقيقي ====================
READY_ACCOUNTS_CACHE = {}
READY_CACHE_TIME = {}
READY_CACHE_LOCK = threading.Lock()

def get_aged_accounts_catalog(age='2021'):
    """توليد وجلب قائمة الحسابات القديمة والمعتقة حسب السنة/العمر بدقة وبأسعار واقعية وتوزيع دول مستقل لكل سنة"""
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

    # توزيع مخصص ومستقل لكل سنة حتى لا تظهر نفس الدول لكل الأعوام
    year_seeds = {
        '2014': ['UA', 'RU', 'KZ', 'US', 'DE', 'GB', 'FR', 'ES', 'IT', 'NL', 'SE', 'CH'],
        '2015': ['UA', 'RU', 'KZ', 'BY', 'US', 'GB', 'DE', 'FR', 'PL', 'RO', 'CZ', 'AT'],
        '2016': ['UA', 'KZ', 'EG', 'SA', 'IQ', 'KW', 'AE', 'US', 'TR', 'ID', 'MY', 'BR'],
        '2017': ['EG', 'SA', 'IQ', 'SY', 'JO', 'DZ', 'MA', 'TN', 'YE', 'KW', 'QA', 'OM'],
        '2018': ['UA', 'KZ', 'UZ', 'ID', 'IN', 'PK', 'BD', 'VN', 'PH', 'TH', 'MY', 'NG'],
        '2019': ['TR', 'EG', 'DZ', 'MA', 'IQ', 'SY', 'LB', 'SD', 'LY', 'SO', 'MR', 'YE'],
        '2020': ['UZ', 'KZ', 'RU', 'ID', 'IN', 'PK', 'BD', 'VN', 'BR', 'CO', 'PE', 'AR'],
        '2021': ['UA', 'KZ', 'EG', 'IQ', 'ES', 'SY', 'RS', 'BO', 'KW', 'SG', 'ID', 'TR', 'BD', 'MY', 'PK', 'NG', 'US', 'RU', 'UZ', 'SA', 'MA', 'DZ', 'BR', 'VN'],
        '2022': ['ID', 'VN', 'PH', 'TH', 'MY', 'IN', 'PK', 'BD', 'NG', 'GH', 'KE', 'ZA', 'BR', 'MX', 'CO', 'CL'],
        '2023': ['EG', 'DZ', 'MA', 'IQ', 'YE', 'SY', 'JO', 'TR', 'UZ', 'KZ', 'ID', 'BD', 'IN', 'PK', 'NG', 'BR'],
        '2024': ['UZ', 'RU', 'KZ', 'BD', 'ID', 'US', 'EG', 'YE', 'SA', 'TR', 'IT', 'FR', 'DE', 'ES', 'GB', 'IN', 'PK', 'VN', 'BR', 'MA'],
        '2025': ['UZ', 'RU', 'KZ', 'BD', 'ID', 'US', 'EG', 'YE', 'SA', 'TR', 'IN', 'PK', 'VN', 'BR', 'NG', 'PH', 'CO', 'KH', 'LA', 'TZ'],
        '60-180day': ['UZ', 'RU', 'KZ', 'BD', 'ID', 'US', 'EG', 'TR', 'IN', 'PK', 'VN', 'BR', 'MA', 'DZ', 'IQ', 'JO'],
        '5-60day': ['UZ', 'RU', 'KZ', 'BD', 'ID', 'US', 'EG', 'YE', 'SA', 'TR', 'IN', 'PK', 'VN', 'BR', 'NG', 'PH', 'CO', 'KH', 'LA', 'TZ']
    }

    selected_codes = year_seeds.get(age_str, year_seeds['2021'])
    result = []

    for idx, c_code in enumerate(selected_codes):
        info = ISO_COUNTRY_MAP.get(c_code)
        if info:
            name_str = f"{info['flag']} {info['name']}"
        else:
            clean_info = get_clean_country_info(c_code)
            name_str = f"{clean_info['flag']} {clean_info['name']}" if clean_info else f"🌍 {c_code}"
            
        factor = 0.85 + ((idx % 7) * 0.05)
        raw_price = round(base_mult * factor, 2)
        price_with_profit = round(raw_price * (1 + PROFIT_MARGIN), 2)
        qty = max(3, (len(selected_codes) * 3 - idx * 2) + ((idx * 7) % 15))
        
        result.append({
            'code': c_code,
            'name': name_str,
            'price': price_with_profit,
            'count': qty,
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
        
        # 1. السيرفر 1 (TG-Lion)
        if p_type == 'tglion':
            try:
                url = f"https://TG-Lion.net?action=available_countries&apiKey={api_key}&YourID={user_id}"
                data = http_get_json(url, timeout=8)
                if data and data.get('status') == 'ok' and isinstance(data.get('countries'), dict):
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
                                    c_name, c_flag = get_clean_country_info(c_code)
                                    name_str = f"{c_flag} {c_name}" if c_name != "دولة" else cinfo.get('name', f"🌍 {c_code}")
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
                data = http_get_json(url, timeout=8)
                if data and data.get('ok') and isinstance(data.get('result'), dict):
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
                                c_name, c_flag = get_clean_country_info(c_code)
                                name_str = f"{c_flag} {c_name}" if c_name != "دولة" else f"🌍 {c_code}"
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
    # السيرفر 3 (حسابات قديمة - معتقة): مزودات API الفورية لا تدعم جلب الحسابات المعتقة بالسنوات
    if str(server_id) == '3':
        return {
            'ok': False,
            'error': '⚠️ الحسابات القديمة (المعتقة) يتم تجهيزها يدوياً.\nيرجى استخدام [السيرفر 1] أو [السيرفر 2] للشراء الفوري التلقائي 100%، أو التواصل مع الإدارة للتسليم الفوري.'
        }

    srv = READY_ACCOUNTS_PROVIDERS.get(str(server_id))
    if not srv:
        return {'ok': False, 'error': 'سيرفر غير موجود'}
    
    p_type = srv.get('type')
    api_key = srv['api_key']
    user_id = srv.get('user_id', ADMIN_ID)
    
    try:
        if p_type == 'tglion':
            url = f"https://TG-Lion.net?action=getNumber&apiKey={api_key}&YourID={user_id}&country_code={country_code.lower()}"
            res = http_get_json(url, timeout=12)
            if res and res.get('status') == 'ok' and res.get('Number'):
                return {
                    'ok': True,
                    'number': res.get('Number'),
                    'name': res.get('name'),
                    'cost': float(res.get('price', 0)),
                    'provider': 'tglion'
                }
            else:
                raw_err = (res.get('message') if res else None) or (res.get('error') if res else None) or 'خطأ في السيرفر'
                if 'balance' in str(raw_err).lower() or 'رصيد' in str(raw_err):
                    err_msg = '⚠️ رصيد السيرفر غير كافٍ مؤقتاً، يرجى تجربة سيرفر آخر أو المحاولة لاحقاً.'
                elif 'stock' in str(raw_err).lower() or 'no number' in str(raw_err).lower():
                    err_msg = '⚠️ نفد مخزون هذه الدولة حالياً في السيرفر، يرجى اختيار دولة أخرى أو المحاولة لاحقاً.'
                elif 'banned' in str(raw_err).lower():
                    err_msg = '⚠️ تعذر حجز الرقم حالياً، يرجى اختيار دولة أخرى.'
                else:
                    err_msg = f"⚠️ تعذر إتمام الطلب من السيرفر حالياً."
                return {'ok': False, 'error': err_msg}
        elif p_type == 'spider':
            url = f"https://api.spider-service.com?apiKay={api_key}&action=getNumber&country={country_code.upper()}"
            res = http_get_json(url, timeout=12)
            if res and res.get('ok') and isinstance(res.get('result'), dict):
                num = res['result'].get('number') or res['result'].get('Number')
                hash_code = res['result'].get('hash_code')
                return {
                    'ok': True,
                    'number': num,
                    'hash_code': hash_code,
                    'provider': 'spider'
                }
            else:
                raw_err = (res.get('error') if res else None) or (res.get('msg') if res else None) or 'خطأ في السيرفر'
                if 'balance' in str(raw_err).lower() or 'رصيد' in str(raw_err):
                    err_msg = '⚠️ رصيد السيرفر غير كافٍ مؤقتاً، يرجى تجربة سيرفر آخر أو المحاولة لاحقاً.'
                elif 'stock' in str(raw_err).lower() or 'available' in str(raw_err).lower():
                    err_msg = '⚠️ نفد مخزون هذه الدولة في السيرفر، يرجى اختيار دولة أخرى.'
                else:
                    err_msg = '⚠️ تعذر إتمام العملية من السيرفر، يرجى المحاولة لاحقاً.'
                    err_msg = f"⚠️ رد المزود: {raw_err}"
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
    
    try:
        if p_type == 'tglion':
            url = f"https://TG-Lion.net?action=getCode&number={number_or_hash}&apiKey={api_key}&YourID={user_id}"
            res = http_get_json(url, timeout=12)
            if res and res.get('status') == 'ok':
                return {
                    'ok': True,
                    'code': res.get('code'),
                    'password': res.get('pass'),
                    'number': res.get('Number')
                }
            else:
                return {'ok': False, 'error': (res.get('message') if res else 'لم يصل الكود بعد')}
        elif p_type == 'spider':
            url = f"https://api.spider-service.com?apiKay={api_key}&action=getCode&hash_code={number_or_hash}"
            res = http_get_json(url, timeout=12)
            if res and res.get('ok') and isinstance(res.get('result'), dict):
                return {
                    'ok': True,
                    'code': res['result'].get('code'),
                    'password': res['result'].get('pass') or res['result'].get('password'),
                    'number': res['result'].get('number')
                }
            else:
                return {'ok': False, 'error': (res.get('error') if res else 'لم يصل الكود بعد')}
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

