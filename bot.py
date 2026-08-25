import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import requests
import time
import google.generativeai as genai

# ==================== 1. الإعدادات الأساسية ====================
TOKEN = '8927305428:AAFok7iKK0S4D3px-kdgW1WvAIZjXr3dWH8'
GEMINI_API_KEY = 'AQ.Ab8RN6IOLYCW3mnMh6H5le6Bc1pAG60TXO0IoxjpPcHvaFZHkg'
ADMIN_ID = 6113734300
ADMIN_USERNAME = "@Num_s7"

PROFIT_MARGIN = 0.10  # نسبة الربح 10%

SERVERS = {
    'grizzly': {
        'name': '🐻 سيرفر Grizzly SMS',
        'api_key': 'Hosamaed7993f2abbded229628261c56746d5',
        'url': 'https://api.grizzlysms.com/stubs/handler_api.php',
        'type': 'grizzly'
    },
    '5sim': {
        'name': '🌐 سيرفر 5sim.biz',
        'api_key': 'ضع_مفتاح_5SIM_هنا',
        'url': 'https://5sim.biz/v1/user/',
        'type': '5sim'
    }
}

# خريطة توحيد الدول بين Grizzly و 5sim
COUNTRIES_DATA = {
    "0": {"name": "🇷🇺 روسيا", "5sim": "russia"},
    "187": {"name": "🇺🇸 أمريكا", "5sim": "usa"},
    "16": {"name": "🇬🇧 بريطانيا", "5sim": "england"},
    "21": {"name": "🇪🇬 مصر", "5sim": "egypt"},
    "19": {"name": "🇳🇬 نيجيريا", "5sim": "nigeria"},
    "4": {"name": "🇵🇭 الفلبين", "5sim": "philippines"},
    "22": {"name": "🇮🇳 الهند", "5sim": "india"},
    "6": {"name": "🇮🇩 إندونيسيا", "5sim": "indonesia"},
    "13": {"name": "🇩🇪 ألمانيا", "5sim": "germany"},
    "15": {"name": "🇵🇱 بولندا", "5sim": "poland"},
    "36": {"name": "🇨🇦 كندا", "5sim": "canada"}
}

# خريطة توحيد التطبيقات
SERVICES_DATA = {
    "wa": {"name": "واتساب", "5sim": "whatsapp"},
    "tg": {"name": "تليجرام", "5sim": "telegram"},
    "ig": {"name": "إنستغرام", "5sim": "instagram"},
    "imo": {"name": "إيمو", "5sim": "imo"},
    "tk": {"name": "تيك توك", "5sim": "tiktok"}
}

PRICES_CACHE = {}
CACHE_LAST_UPDATE = {}
CACHE_DURATION = 300 

bot = telebot.TeleBot(TOKEN)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# ==================== 2. دالة جلب الأسعار الذكية ====================
def fetch_server_prices(server_id, app_code):
    key = f"{server_id}_{app_code}"
    now = time.time()
    
    if key in PRICES_CACHE and (now - CACHE_LAST_UPDATE.get(key, 0)) < CACHE_DURATION:
        return PRICES_CACHE[key]

    srv = SERVERS.get(server_id)
    srv_type = srv.get('type')
    prices = {}

    try:
        if srv_type == 'grizzly':
            url = f"{srv['url']}?api_key={srv['api_key']}&action=getPrices&service={app_code}"
            res = requests.get(url, timeout=5).json()
            for code, data in res.items():
                if app_code in data:
                    cost = float(data[app_code]['cost'])
                    prices[str(code)] = round(cost * (1 + PROFIT_MARGIN), 2)

        elif srv_type == '5sim':
            s_5sim = SERVICES_DATA.get(app_code, {}).get('5sim', app_code)
            headers = {'Authorization': f'Bearer {srv["api_key"]}', 'Accept': 'application/json'}
            url = f"{srv['url']}guest/prices?product={s_5sim}"
            res = requests.get(url, headers=headers, timeout=5).json()

            for code, info in COUNTRIES_DATA.items():
                c_5sim = info.get('5sim')
                if c_5sim in res and s_5sim in res[c_5sim]:
                    # اختيار أقل سعر متوفر من مزودي 5sim
                    providers = res[c_5sim][s_5sim]
                    costs = [p['cost'] for p in providers.values() if 'cost' in p]
                    if costs:
                        min_cost = min(costs)
                        prices[code] = round(min_cost * (1 + PROFIT_MARGIN), 2)

        PRICES_CACHE[key] = prices
        CACHE_LAST_UPDATE[key] = now
    except Exception as e:
        print(f"Error fetching prices: {e}")

    return PRICES_CACHE.get(key, {})

# ==================== 3. لوحة الأزرار ====================
def countries_keyboard_fast(server_id, service_code):
    markup = InlineKeyboardMarkup()
    prices = fetch_server_prices(server_id, service_code)

    for code, info in COUNTRIES_DATA.items():
        name = info['name']
        if code in prices:
            btn_text = f"{name} - ${prices[code]:.2f}"
        else:
            btn_text = f"{name} - غير متوفر"
        
        markup.add(InlineKeyboardButton(btn_text, callback_data=f"b_{server_id}_{service_code}_{code}"))

    markup.add(InlineKeyboardButton("🔙 العودة لاختيار التطبيق", callback_data=f"select_server_{server_id}"))
    return markup
