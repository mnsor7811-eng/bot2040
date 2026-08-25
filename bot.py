import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import requests
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
        'url': 'https://api.grizzlysms.com/stubs/handler_api.php'
    },
    '5sim': {
        'name': '🌐 سيرفر 5sim.biz',
        'api_key': 'ضع_مفتاح_5SIM_هنا',
        'url': 'https://5sim.biz/v1/user/'
    },
    'smsman': {
        'name': '🟢 سيرفر SMS-Man',
        'api_key': 'ضع_مفتاح_SMSMAN_هنا',
        'url': 'https://api.sms-man.com/control/'
    },
    'tigersms': {
        'name': '🐯 سيرفر Tiger SMS',
        'api_key': 'ضع_مفتاح_TIGER_هنا',
        'url': 'https://tiger-sms.com/stubs/handler_api.php'
    }
}

POPULAR_COUNTRIES = [
    ("0", "🇷🇺 روسيا"),
    ("187", "🇺🇸 أمريكا"),
    ("16", "🇬🇧 بريطانيا"),
    ("21", "🇪🇬 مصر"),
    ("19", "🇳🇬 نيجيريا"),
    ("4", "🇵🇭 الفلبين"),
    ("22", "🇮🇳 الهند"),
    ("6", "🇮🇩 إندونيسيا"),
    ("13", "🇩🇪 ألمانيا"),
    ("15", "🇵🇱 بولندا"),
    ("36", "🇨🇦 كندا"),
    ("32", "🇷🇴 رومانيا"),
    ("73", "🇧🇷 البرازيل"),
    ("86", "🇮🇹 إيطاليا"),
    ("78", "🇫🇷 فرنسا")
]

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

def is_user_banned(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT is_banned FROM users WHERE user_id = ?', (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else 0

# ==================== 3. طلبات API ====================
def grizzly_request(params, api_key, url):
    params['api_key'] = api_key
    try:
        response = requests.get(url, params=params, timeout=10)
        return response.text
    except Exception as e:
        return f"ERROR: {e}"

def get_real_price(server_id, service_code, country_code):
    srv = SERVERS.get(server_id)
    try:
        url = f"{srv['url']}?api_key={srv['api_key']}&action=getPrices&service={service_code}&country={country_code}"
        res = requests.get(url, timeout=5).json()
        raw_price = float(res[str(country_code)][service_code]['cost'])
        return round(raw_price * (1 + PROFIT_MARGIN), 2)
    except:
        return 0.50

# ==================== 4. لوحات الأزرار ====================
def main_keyboard(user_id):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🤖 اشتراكات برامج AI", callback_data="ai_landing"))
    markup.row(InlineKeyboardButton("📞 شراء رقم افتراضي", callback_data="buy_number"))
    markup.row(InlineKeyboardButton("🔵 جاهز Telegram", callback_data="fast_buy_tg"), InlineKeyboardButton("🟢 عروض WhatsApp", callback_data="fast_buy_wa"))
    markup.row(InlineKeyboardButton("🔥 السيرفرات الأكثر مبيعاً", callback_data="best_selling"))
    markup.row(InlineKeyboardButton("🎳 شحن الرصيد / الاشتراكات", callback_data="recharge_menu"), InlineKeyboardButton("🎲 الأكثر توفراً", callback_data="most_available"))
    markup.row(InlineKeyboardButton("🔭 الرشق وشحن الألعاب والبرامج", callback_data="games_boost"))
    markup.row(InlineKeyboardButton("💎 اربح روبل مجاناً", callback_data="free_ruble"))
    markup.row(InlineKeyboardButton("🎧 الدعم", callback_data="support"), InlineKeyboardButton("🔄 تحويل الرصيد", callback_data="transfer"))
    markup.row(InlineKeyboardButton("✔ إحصائيات الشراء الناجح", callback_data="purchase_stats"))
    markup.row(InlineKeyboardButton("👤 حسابي", callback_data="my_account"))
    markup.row(InlineKeyboardButton("🛸 خدمات وميزات أخرى", callback_data="other_services"))
    
    if str(user_id) == str(ADMIN_ID):
        markup.row(InlineKeyboardButton("⚙️ لوحة الإدارة الكبرى", callback_data="admin_panel"))
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
    markup.add(InlineKeyboardButton("🟡 إيمو (IMO)", callback_data=f"srv_app_{server_id}_imo"))
    markup.add(InlineKeyboardButton("🎵 تيك توك (TikTok)", callback_data=f"srv_app_{server_id}_tk"))
    markup.add(InlineKeyboardButton("🔙 العودة لقائمة السيرفرات", callback_data="buy_number"))
    return markup

def countries_keyboard_fast(server_id, service_code):
    markup = InlineKeyboardMarkup()
    srv = SERVERS.get(server_id)
    
    prices_data = {}
    try:
        url = f"{srv['url']}?api_key={srv['api_key']}&action=getPrices&service={service_code}"
        res = requests.get(url, timeout=7).json()
        prices_data = res
    except:
        pass

    for code, name in POPULAR_COUNTRIES:
        price = 0.50
        if code in prices_data and service_code in prices_data[code]:
            cost = float(prices_data[code][service_code]['cost'])
            price = round(cost * (1 + PROFIT_MARGIN), 2)
        
        # اختصار callback_data لتفادي تجاوز حد 64 بايت
        markup.add(InlineKeyboardButton(f"{name} - ${price}", callback_data=f"b_{server_id}_{service_code}_{code}"))

    markup.add(InlineKeyboardButton("🔙 العودة لاختيار التطبيق", callback_data=f"select_server_{server_id}"))
    return markup

def active_number_keyboard(tz_id, server_id):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("📩 الحصول على الكود", callback_data=f"check_sms_{server_id}_{tz_id}"))
    markup.row(InlineKeyboardButton("❌ إلغاء الرقم واسترجاع المبلغ", callback_data=f"cancel_num_{server_id}_{tz_id}"))
    return markup

# ==================== 5. الأوامر والمعالجة ====================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or "المستخدم"
    if is_user_banned(user_id):
        bot.send_message(message.chat.id, "🚫 عذراً، لقد تم حظرك من استخدام هذا البوت بواسطة الإدارة.")
        return
        
    user_data = get_or_create_user(user_id, name)
    text = (f"💠 أهلاً بك عزيزي في بوت (NUMBER SMS) 💠\n\n"
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
    
    if is_user_banned(user_id) and str(user_id) != str(ADMIN_ID):
        bot.answer_callback_query(call.id, "أنت محظور!", show_alert=True)
        return

    try:
        bot.answer_callback_query(call.id)
    except:
        pass

    if call.data == "back_main":
        user_data = get_or_create_user(user_id, call.from_user.first_name)
        text = (f"💠 أهلاً بك عزيزي في بوت (NUMBER SMS) 💠\n\n"
                f"👤 حسابك: {ADMIN_USERNAME}\n"
                f"💰 رصيدك الحالي: ${user_data[2]:.2f}\n"
                f"🤖 رصيد أسئلة الذكاء: {user_data[3]} سؤال\n\n"
                f"📌 استخدم الأزرار بالأسفل لتنفيذ طلباتك:")
        bot.edit_message_text(text, chat_id, message_id, reply_markup=main_keyboard(user_id))

    elif call.data == "buy_number":
        text = "📞 **قسم شراء الأرقام الافتراضية**\n\nاختر السيرفر / الموقع الذي تريد الشراء منه:"
        bot.edit_message_text(text, chat_id, message_id, reply_markup=servers_keyboard())

    elif call.data.startswith("select_server_"):
        server_id = call.data.split("_")[2]
        server_name = SERVERS[server_id]['name']
        text = f"⚙️ **تم اختيار:** {server_name}\n\nاختر التطبيق المراد تفعيله:"
        bot.edit_message_text(text, chat_id, message_id, reply_markup=services_keyboard(server_id))

    elif call.data.startswith("srv_app_"):
        _, _, server_id, srv_code = call.data.split("_")
        markup = countries_keyboard_fast(server_id, srv_code)
        text = f"🌐 **اختر الدولة المطلوبة لـ ({srv_code.upper()}):**"
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)

    elif call.data.startswith("b_"):
        _, server_id, srv_code, country_code = call.data.split("_")
        price = get_real_price(server_id, srv_code, country_code)
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        balance = cursor.fetchone()[0]
        
        if balance < price:
            bot.send_message(chat_id, f"❌ **رصيدك غير كافٍ!**\nسعر الرقم: ${price:.2f}\nرصيدك الحالي: ${balance:.2f}\n\nيرجى شحن حسابك أولاً.")
            conn.close()
            return

        srv = SERVERS.get(server_id)
        res = grizzly_request({'action': 'getNumber', 'service': srv_code, 'country': country_code}, srv['api_key'], srv['url'])
        
        if "ACCESS_NUMBER" in res:
            parts = res.split(":")
            tz_id = parts[1]
            phone = parts[2]
            
            cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (price, user_id))
            cursor.execute('INSERT INTO purchases (user_id, tz_id, phone, service, cost) VALUES (?, ?, ?, ?, ?)',
                           (user_id, tz_id, phone, srv_code, price))
            conn.commit()
            conn.close()
            
            msg = (f"✅ **تم شراء الرقم بنجاح!**\n\n"
                   f"📱 **الرقم:** `{phone}`\n"
                   f"🆔 **معرف العملية:** `{tz_id}`\n"
                   f"💵 **السعر:** ${price:.2f}\n\n"
                   f"📥 قم بإدخال الرقم في التطبيق ثم اضغط زر **الحصول على الكود**:")
            bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=active_number_keyboard(tz_id, server_id))
        else:
            conn.close()
            bot.send_message(chat_id, "❌ **تنبيه:** لا توجد أرقام متاحة حالياً لهذه الدولة أو رصيدك في سيرفر الموقع غير كافٍ.")

    elif call.data.startswith("check_sms_"):
        parts = call.data.split("_")
        server_id, tz_id = parts[2], parts[3]
        srv = SERVERS.get(server_id)
        res = grizzly_request({'action': 'getStatus', 'id': tz_id}, srv['api_key'], srv['url'])
        
        if "STATUS_OK" in res:
            code = res.split(":")[1]
            bot.send_message(chat_id, f"🎉 **وصل كود التفعيل الخاص بك!**\n\n🔑 **الكود:** `{code}`", parse_mode="Markdown")
        elif "STATUS_WAIT_CODE" in res:
            bot.answer_callback_query(call.id, "⏳ جاري انتظار وصول الرسالة... حاول مجدداً بعد ثوانٍ.", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "لم يتم استلام الكود بعد.", show_alert=True)

    elif call.data.startswith("cancel_num_"):
        parts = call.data.split("_")
        server_id, tz_id = parts[2], parts[3]
        srv = SERVERS.get(server_id)
        grizzly_request({'action': 'setStatus', 'status': '8', 'id': tz_id}, srv['api_key'], srv['url'])
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, cost, status FROM purchases WHERE tz_id = ?', (tz_id,))
        purchase = cursor.fetchone()
        
        if purchase and purchase[2] == 'PENDING':
            cost = purchase[1]
            cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (cost, user_id))
            cursor.execute('UPDATE purchases SET status = "CANCELLED" WHERE tz_id = ?', (tz_id,))
            conn.commit()
            conn.close()
            bot.edit_message_text(f"❌ **تم إلغاء الرقم بنجاح وإعادة مبلغ (${cost:.2f}) إلى رصيدك.**", chat_id, message_id)
        else:
            conn.close()
            bot.answer_callback_query(call.id, "العملية ملغاة أو منتهية مسبقاً.", show_alert=True)

bot.infinity_polling()
