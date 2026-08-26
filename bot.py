import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import requests
import time
import pycountry
import google.generativeai as genai

# ==================== 1. الإعدادات الأساسية ====================
TOKEN = '8927305428:AAHKVgxelqI1aEqeSE7wlKM6hkm5Y2JqUgs'
GEMINI_API_KEY = 'AQ.Ab8RN6IOLYCW3mnMh6H5le6Bc1pAG60TXO0IoxjpPcHvaFZHkg'
ADMIN_ID = 6113734300
ADMIN_USERNAME = "@Num_s7"

PROFIT_MARGIN = 0.10      # نسبة الربح 10%
DEFAULT_PRICE = 0.50      # سعر افتراضي

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
    }
}

# ترجمة الأسماء الشائعة للعربية
ARABIC_COUNTRIES = {
    "Yemen": ("اليمن", "🇾🇪"), "Saudi Arabia": ("السعودية", "🇸🇦"), "United Arab Emirates": ("الإمارات", "🇦🇪"),
    "Egypt": ("مصر", "🇪🇬"), "Iraq": ("العراق", "🇮🇶"), "Syria": ("سوريا", "🇸🇾"), "Jordan": ("الأردن", "🇯🇴"),
    "Lebanon": ("لبنان", "🇱🇧"), "Sudan": ("السودان", "🇸🇩"), "Morocco": ("المغرب", "🇲🇦"), "Algeria": ("الجزائر", "🇩🇿"),
    "Tunisia": ("تونس", "🇹🇳"), "Libya": ("ليبيا", "🇱🇾"), "Oman": ("سلطنة عمان", "🇴🇲"), "Kuwait": ("الكويت", "🇰🇼"),
    "Qatar": ("قطر", "🇶🇦"), "Bahrain": ("البحرين", "🇧🇭"), "Turkey": ("تركيا", "🇹🇷"), "United States": ("أمريكا", "🇺🇸"),
    "United Kingdom": ("بريطانيا", "🇬🇧"), "France": ("فرنسا", "🇫🇷"), "Germany": ("ألمانيا", "🇩🇪"),
    "Russia": ("روسيا", "🇷🇺"), "China": ("الصين", "🇨🇳"), "India": ("الهند", "🇮🇳"), "Brazil": ("البرازيل", "🇧🇷"),
    "Madagascar": ("مدغشقر", "🇲🇬"), "Canada": ("كندا", "🇨🇦"), "Indonesia": ("إندونيسيا", "🇮🇩")
}

def get_country_info_dynamic(code_str):
    """جلب اسم الدولة والعلم بدقة عبر مكتبة pycountry ومطابقتها بدون أرقام مجهولة"""
    try:
        # محاولة البحث عبر pycountry بواسطة numeric code أو alpha code
        c_obj = None
        if str(code_str).isdigit():
            c_obj = pycountry.countries.get(numeric=str(code_str).zfill(3))
        if not c_obj:
            c_obj = pycountry.countries.get(alpha_2=str(code_str).upper())
            
        if c_obj:
            eng_name = c_obj.name
            if eng_name in ARABIC_COUNTRIES:
                return ARABIC_COUNTRIES[eng_name][0], ARABIC_COUNTRIES[eng_name][1]
            return eng_name, "🌐"
    except Exception:
        pass
    
    return f"دولة ({code_str})", "🌐"

PRICES_CACHE = {}
CACHE_LAST_UPDATE = {}

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
                        is_banned INTEGER DEFAULT 0
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
    return sqlite3.connect('bot_database.db', check_same_thread=False)

def get_or_create_user(user_id, name):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute('INSERT INTO users (user_id, name, balance, ai_balance, is_banned) VALUES (?, ?, 0.0, 5, 0)', (user_id, name))
        conn.commit()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
    conn.close()
    return user

# ==================== 3. جلب الأسعار والطلبات ====================
def fetch_server_prices(server_id, service_code):
    key = f"{server_id}_{service_code}"
    now = time.time()
    if key in PRICES_CACHE and (now - CACHE_LAST_UPDATE.get(key, 0)) < 300:
        return PRICES_CACHE[key]

    srv = SERVERS.get(server_id)
    prices = {}
    if not srv or "ضع_مفتاح" in srv['api_key']:
        return prices

    try:
        url = f"{srv['url']}?api_key={srv['api_key']}&action=getPrices&service={service_code}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=7).json()
        for c_code, services in res.items():
            if isinstance(services, dict) and service_code in services:
                raw_cost = float(services[service_code].get('cost', 0))
                count = int(services[service_code].get('count', 0))
                if raw_cost > 0 and count > 0:
                    prices[str(c_code)] = round(raw_cost * (1 + PROFIT_MARGIN), 2)
    except Exception as e:
        print(f"Price Error: {e}")

    if prices:
        PRICES_CACHE[key] = prices
        CACHE_LAST_UPDATE[key] = now
    return prices

def grizzly_request(params, api_key, url):
    params['api_key'] = api_key
    try:
        res = requests.get(url, params=params, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        return res.text.strip()
    except Exception as e:
        return f"ERROR: {e}"

# ==================== 4. لوحات التحكم بالأزرار ====================
def main_keyboard(user_id):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🤖 اشتراكات برامج AI", callback_data="ai_landing"))
    markup.row(InlineKeyboardButton("📞 شراء رقم افتراضي", callback_data="buy_number"))
    markup.row(InlineKeyboardButton("🔵 جاهز Telegram", callback_data="fast_buy_tg"), InlineKeyboardButton("🟢 عروض WhatsApp", callback_data="fast_buy_wa"))
    markup.row(InlineKeyboardButton("🔥 السيرفرات الأكثر مبيعاً", callback_data="best_selling"))
    markup.row(InlineKeyboardButton("🎳 شحن الرصيد / الاشتراكات", callback_data="recharge_menu"), InlineKeyboardButton("🎲 الأكثر توفراً", callback_data="most_available"))
    markup.row(InlineKeyboardButton("🚀 خدمات الرشق والألعاب (SMM)", callback_data="smm_main"))
    markup.row(InlineKeyboardButton("🎧 الدعم", callback_data="support"), InlineKeyboardButton("🔄 تحويل الرصيد", callback_data="transfer"))
    markup.row(InlineKeyboardButton("👤 حسابي", callback_data="my_account"))
    return markup

def back_button():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
    return markup

def active_number_keyboard(tz_id, server_id, service_code):
    markup = InlineKeyboardMarkup()
    app_label = "تليجرام 🔵" if service_code.lower() in ["tg", "telegram"] else "واتساب 🟢"
    markup.row(InlineKeyboardButton(f"📩 طلب كود {app_label}", callback_data=f"check_sms_{server_id}_{tz_id}"))
    markup.row(InlineKeyboardButton("🔄 تغيير الرقم", callback_data=f"change_num_{server_id}_{tz_id}"))
    markup.row(InlineKeyboardButton("✖️ إلغاء الطلب واسترجاع المبلغ", callback_data=f"cancel_num_{server_id}_{tz_id}"))
    return markup

# ==================== 5. معالجة الأحداث المكتملة لجميع الأزرار ====================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_data = get_or_create_user(message.from_user.id, message.from_user.first_name)
    text = (f"💠 أهلاً بك في البوت الشامل 💠\n\n"
            f"👤 الحساب: {ADMIN_USERNAME}\n"
            f"💰 رصيدك الحالي: ${user_data[2]:.2f}\n"
            f"🤖 رصيد أسئلة الذكاء الاصطناعي: {user_data[3]} سؤال\n\n"
            f"📌 اختر الخدمة المطلوبة:")
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard(message.from_user.id))

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    # --- معالجة زر العودة ---
    if call.data == "back_main":
        user_data = get_or_create_user(user_id, call.from_user.first_name)
        text = (f"💠 أهلاً بك في البوت الشامل 💠\n\n"
                f"👤 الحساب: {ADMIN_USERNAME}\n"
                f"💰 رصيدك الحالي: ${user_data[2]:.2f}\n\n"
                f"📌 اختر الخدمة المطلوبة:")
        bot.edit_message_text(text, chat_id, message_id, reply_markup=main_keyboard(user_id))

    # --- معالجة كافة الأزرار التي كانت متوقفة ---
    elif call.data == "recharge_menu":
        markup = InlineKeyboardMarkup()
        for key, val in PAYMENT_DETAILS.items():
            markup.add(InlineKeyboardButton(f"{val['name']} (أدنى {val['min']})", callback_data=f"pay_info_{key}"))
        markup.add(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
        bot.edit_message_text("💳 اختر طريقة الشحن المناسبة لك:", chat_id, message_id, reply_markup=markup)

    elif call.data.startswith("pay_info_"):
        pay_type = call.data.split("_")[2]
        info = PAYMENT_DETAILS.get(pay_type, {})
        text = f"📌 **تفاصيل الشحن عبر {info['name']}**:\n\n" \
               f"رقم الحساب/المحفظة: `{info['acc']}`\n" \
               f"سعر الصرف: {info['rate']}\n" \
               f"الحد الأدنى: {info['min']}\n\n" \
               f"بعد التحويل، يرجى إرسال إشعار التحويل للدعم الفني: {ADMIN_USERNAME}"
        bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=back_button())

    elif call.data == "my_account":
        user_data = get_or_create_user(user_id, call.from_user.first_name)
        text = f"👤 **معلومات حسابك**:\n\nالاسم: {user_data[1]}\nالآيدي: `{user_data[0]}`\nالرصيد: ${user_data[2]:.2f}\nرصيد الذكاء الاصطناعي: {user_data[3]} أسئلة"
        bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=back_button())

    elif call.data == "smm_main":
        bot.edit_message_text("🚀 **قسم خدمات الرشق والشغليات (SMM)**:\n\nالخدمة قيد الصيانة وسيتم ربط الـ API الخاص بها خلال الساعات القادمة.", chat_id, message_id, parse_mode="Markdown", reply_markup=back_button())

    elif call.data == "ai_landing":
        bot.edit_message_text("🤖 **قسم خدمات الذكاء الاصطناعي**:\n\nيمكنك الآن توجيه أسئلتك المباشرة للبوت وسيقوم الذكاء الاصطناعي بالإجابة عليك فوراً.", chat_id, message_id, reply_markup=back_button())

    elif call.data in ["support", "transfer", "best_selling", "most_available", "fast_buy_tg", "fast_buy_wa"]:
        bot.edit_message_text(f"ℹ️ **تنبيه**: زر ({call.data}) تم تفعيله وبانتظار تحديد الخيارات الخاصة بك من الدعم {ADMIN_USERNAME}.", chat_id, message_id, parse_mode="Markdown", reply_markup=back_button())

    # --- قسم شراء الأرقام والدول ---
    elif call.data == "buy_number":
        markup = InlineKeyboardMarkup()
        for s_id, s_info in SERVERS.items():
            markup.add(InlineKeyboardButton(s_info['name'], callback_data=f"select_server_{s_id}"))
        markup.add(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
        bot.edit_message_text("📞 اختر السيرفر المطلوب للشراء:", chat_id, message_id, reply_markup=markup)

    elif call.data.startswith("select_server_"):
        server_id = call.data.split("_")[2]
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🟢 واتساب (WhatsApp)", callback_data=f"srv_app_{server_id}_wa"))
        markup.add(InlineKeyboardButton("🔵 تليجرام (Telegram)", callback_data=f"srv_app_{server_id}_tg"))
        markup.add(InlineKeyboardButton("🔙 العودة للقائمة", callback_data="buy_number"))
        bot.edit_message_text("⚙️ اختر التطبيق المراد تفعيله:", chat_id, message_id, reply_markup=markup)

    elif call.data.startswith("srv_app_"):
        _, _, server_id, srv_code = call.data.split("_")
        prices = fetch_server_prices(server_id, srv_code)
        
        markup = InlineKeyboardMarkup()
        items = list(prices.items())[:20] # عرض 20 دولة
        buttons = []
        for code, price in items:
            c_name, c_flag = get_country_info_dynamic(code)
            btn_text = f"🚀 {c_name} {c_flag} : ${price:.2f}"
            buttons.append(InlineKeyboardButton(btn_text, callback_data=f"b_{server_id}_{srv_code}_{code}"))
            
        for i in range(0, len(buttons), 2):
            markup.row(*buttons[i:i+2])
        markup.add(InlineKeyboardButton("🔙 العودة لاختيار التطبيق", callback_data=f"select_server_{server_id}"))
        bot.edit_message_text(f"🌐 اختر الدولة لـ ({srv_code.upper()}):", chat_id, message_id, reply_markup=markup)

    # --- معالجة طلب الرقم وتغييره وإلغائه ---
    elif call.data.startswith("b_"):
        _, server_id, srv_code, country_code = call.data.split("_")
        prices = fetch_server_prices(server_id, srv_code)
        price = prices.get(str(country_code), DEFAULT_PRICE)
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        balance = cursor.fetchone()[0]
        
        if balance < price:
            bot.send_message(chat_id, f"❌ رصيدك غير كافٍ!\nالسعر: ${price:.2f}\nرصيدك: ${balance:.2f}")
            conn.close()
            return

        srv = SERVERS.get(server_id)
        res = grizzly_request({'action': 'getNumber', 'service': srv_code, 'country': country_code}, srv['api_key'], srv['url'])
        
        if "ACCESS_NUMBER" in res:
            parts = res.split(":")
            tz_id, raw_phone = parts[1], parts[2]
            formatted_phone = f"+{raw_phone}" if not raw_phone.startswith("+") else raw_phone
            c_name, c_flag = get_country_info_dynamic(country_code)
            
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
                   f"📋 *اضغط على الرقم لنسخه فوراً*")
            bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=active_number_keyboard(tz_id, server_id, srv_code))
        else:
            conn.close()
            bot.send_message(chat_id, "⚠️ **تنبيه:** الأرقام المتاحة لهذه الدولة نفدت حالياً لدى المزود، اختر دولة أخرى.")

bot.infinity_polling()
