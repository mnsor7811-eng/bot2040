import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import requests
import time
import google.generativeai as genai

# ==================== 1. الإعدادات الأساسية ====================
TOKEN = '8927305428:AAHKVgxelqI1aEqeSE7wlKM6hkm5Y2JqUgs'
GEMINI_API_KEY = ''  # ضع مفتاح Gemini الصحيح هنا إذا توفر (يبدأ بـ AIzaSy)
ADMIN_ID = 6113734300
ADMIN_USERNAME = "@Num_s7"

PROFIT_MARGIN = 0.10      # نسبة الربح 10%
DEFAULT_PRICE = 0.50      # سعر افتراضي
REWARD_PER_INVITE = 0.05  # قيمة مكافأة الدعوة ($0.05)

# بيانات طرق الدفع وشحن الرصيد
PAYMENT_DETAILS = {
    'kuraimi': {
        'name': '🏦 بنك الكريمي',
        'acc': '3134706987',
        'min': '100 ريال',
        'rate': '1$ = 550 ريال'
    },
    'jeeb': {
        'name': '📱 محفظة جيب',
        'acc': '374468',
        'min': '50 ريال',
        'rate': '1$ = 550 ريال'
    },
    'onecash': {
        'name': '💳 محفظة ون كاش',
        'acc': '140601836',
        'min': '100 ريال',
        'rate': '1$ = 550 ريال'
    },
    'binance': {
        'name': '🟡 بايننس باي (Binance Pay)',
        'acc': '979808293',
        'min': '0.5 $',
        'rate': '1$ = 1$'
    }
}

# سيرفرات الأرقام
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

# سيرفرات الرشق وشحن الألعاب (SMM Panels)
SMM_PANELS = {
    "1": {"name": "SMM X Star", "url": "https://smmxstar.com/api/v2", "api_key": "ضع_مفتاح_API_هنا"},
    "2": {"name": "Yemen Damkom", "url": "https://yemendamkom.com/api/v2", "api_key": "ضع_مفتاح_API_هنا"},
    "3": {"name": "SMM Stone", "url": "https://Smmstone.com/api/v2", "api_key": "ضع_مفتاح_API_هنا"}
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

PRICES_CACHE = {}
CACHE_LAST_UPDATE = {}
CACHE_DURATION = 600

USER_STEPS = {}

bot = telebot.TeleBot(TOKEN)

# تهيئة Gemini بشكل أمان لمنع إيقاف البوت
model = None
if GEMINI_API_KEY.startswith("AIzaSy"):
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        print(f"Gemini Init Error: {e}")

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

# ==================== 3. جلب الأسعار والدوال المساعدة ====================
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
            res = requests.get(url, timeout=7).json()
            
            for c_code, services in res.items():
                if isinstance(services, dict) and service_code in services:
                    raw_cost = float(services[service_code].get('cost', 0))
                    if raw_cost > 0:
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
    try:
        response = requests.get(url, params=params, timeout=10)
        return response.text
    except Exception as e:
        return f"ERROR: {e}"

# ==================== 4. القوائم والأزرار ====================
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

def recharge_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🏦 بنك الكريمي", callback_data="pay_kuraimi"))
    markup.row(InlineKeyboardButton("📱 محفظة جيب", callback_data="pay_jeeb"))
    markup.row(InlineKeyboardButton("💳 محفظة ون كاش", callback_data="pay_onecash"))
    markup.row(InlineKeyboardButton("🟡 بايننس باي (Binance Pay)", callback_data="pay_binance"))
    markup.row(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
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

def countries_keyboard_fast(server_id, service_code):
    markup = InlineKeyboardMarkup()
    prices = fetch_server_prices(server_id, service_code)

    for code, name in POPULAR_COUNTRIES:
        p_val = prices.get(str(code), DEFAULT_PRICE)
        btn_text = f"{name} - ${p_val:.2f}"
        markup.add(InlineKeyboardButton(btn_text, callback_data=f"b_{server_id}_{service_code}_{code}"))

    markup.add(InlineKeyboardButton("🔙 العودة لاختيار التطبيق", callback_data=f"select_server_{server_id}"))
    return markup

def active_number_keyboard(tz_id, server_id):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("📩 الحصول على الكود", callback_data=f"check_sms_{server_id}_{tz_id}"))
    markup.row(InlineKeyboardButton("❌ إلغاء الرقم واسترجاع المبلغ", callback_data=f"cancel_num_{server_id}_{tz_id}"))
    return markup

def smm_panel_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("👥 أعضاء وقنوات تليجرام", callback_data="smm_order_101"))
    markup.add(InlineKeyboardButton("❤️ متابعين ومشاهدات إنستغرام", callback_data="smm_order_102"))
    markup.add(InlineKeyboardButton("🎮 شحن شدات ببجي / جوهر", callback_data="smm_order_103"))
    markup.add(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
    return markup

# ==================== 5. الأوامر والإدارة ====================
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
        
        bot.reply_to(message, f"✅ **تمت إضافة ${amount:.2f} بنجاح إلى حساب المعرف:** `{target_id}`", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, "❌ **طريقة الاستخدام الخاطئة!**\nارسل الأمر كالتالي:\n`/add_bal USER_ID AMOUNT`", parse_mode="Markdown")

@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or "المستخدم"
    
    if user_id in USER_STEPS:
        del USER_STEPS[user_id]
        
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
                bot.send_message(ref_id, f"🎉 **قام شخص جديد بالانضمام عبر رابطك!**\n🎁 تم إضافة `${REWARD_PER_INVITE:.2f}` إلى رصيدك بنجاح.")
            except:
                pass
    conn.close()

    user_data = get_or_create_user(user_id, name)
    text = (f"💠 أهلاً بك عزيزي في البوت الشامل 💠\n\n"
            f"👤 حسابك: {ADMIN_USERNAME}\n"
            f"🆔 معرف حسابك: `{user_id}`\n"
            f"💰 رصيدك الحالي: ${user_data[2]:.2f}\n"
            f"🤖 رصيد أسئلة الذكاء: {user_data[3]} سؤال\n\n"
            f"📌 استخدم الأزرار بالأسفل لتنفيذ طلباتك:")
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=main_keyboard(user_id))

# ==================== 6. معالجة الأزرار (Callback Queries) ====================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    if user_id in USER_STEPS:
        del USER_STEPS[user_id]
    
    if is_user_banned(user_id) and str(user_id) != str(ADMIN_ID):
        try:
            bot.answer_callback_query(call.id, "أنت محظور!", show_alert=True)
        except:
            pass
        return

    try:
        bot.answer_callback_query(call.id)
    except:
        pass

    if call.data == "back_main":
        user_data = get_or_create_user(user_id, call.from_user.first_name)
        text = (f"💠 أهلاً بك عزيزي في البوت الشامل 💠\n\n"
                f"👤 حسابك: {ADMIN_USERNAME}\n"
                f"🆔 معرف حسابك: `{user_id}`\n"
                f"💰 رصيدك الحالي: ${user_data[2]:.2f}\n"
                f"🤖 رصيد أسئلة الذكاء: {user_data[3]} سؤال\n\n"
                f"📌 استخدم الأزرار بالأسفل لتنفيذ طلباتك:")
        bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=main_keyboard(user_id))

    # === قسم طرق الدفع وشحن الرصيد ===
    elif call.data == "recharge_menu":
        text = "🎳 **قسم شحن الرصيد / الاشتراكات**\n\nاختر وسيلة الدفع التي تناسبك من القائمة أدناه:"
        bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=recharge_keyboard())

    elif call.data in ["pay_kuraimi", "pay_jeeb", "pay_onecash", "pay_binance"]:
        pay_key = call.data.replace("pay_", "")
        pay_info = PAYMENT_DETAILS.get(pay_key)
        
        if pay_info:
            msg = (f"{pay_info['name']}\n\n"
                   f"📌 **رقم الحساب / المعرف:** `{pay_info['acc']}`\n"
                   f"💵 **أقل مبلغ للتحويل:** {pay_info['min']}\n"
                   f"💱 **سعر الصرف:** {pay_info['rate']}\n\n"
                   f"⚠️ **خطوات الشحن:**\n"
                   f"1. قم بالتحويل إلى رقم الحساب الموضح أعلاه.\n"
                   f"2. قم بإرسال صورة إشعار التحويل (الوصل) ومعرف حسابك (`{user_id}`) إلى حساب الإدارة:\n"
                   f"👤 **الإدارة:** {ADMIN_USERNAME}\n\n"
                   f"سيتم مراجعة الدفع وشحن رصيدك فوراً!")
            
            back_markup = InlineKeyboardMarkup()
            back_markup.add(InlineKeyboardButton("🔙 العودة لوسائل الدفع", callback_data="recharge_menu"))
            bot.edit_message_text(msg, chat_id, message_id, parse_mode="Markdown", reply_markup=back_markup)

    # === قسم تحويل الرصيد (عمولة 0%) ===
    elif call.data == "transfer":
        USER_STEPS[user_id] = {'step': 'WAITING_TRANSFER_DATA'}
        msg = ("🔄 **خدمة تحويل الرصيد (عمولة 0%)**\n\n"
               "يرجى إرسال **معرف المستلم (ID)** و **المبلغ المطلوب تحويله** بالشكل التالي:\n\n"
               "`المعرف المبلغ`\n\n"
               "💡 **مثال:**\n"
               "`6113734300 5`\n"
               "(لتحويل 5 دولار إلى المعرف الموضح)\n\n"
               "⚠️ *إذا أردت إلغاء العملية قم بإرسال /start*")
        bot.send_message(chat_id, msg, parse_mode="Markdown")

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
        prices = fetch_server_prices(server_id, srv_code)
        price = prices.get(str(country_code), DEFAULT_PRICE)
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        balance = cursor.fetchone()[0]
        
        if balance < price:
            bot.send_message(chat_id, f"❌ **رصيدك غير كافٍ!**\nسعر هذا الرقم: ${price:.2f}\nرصيدك الحالي: ${balance:.2f}")
            conn.close()
            return

        srv = SERVERS.get(server_id)
        res = grizzly_request({'action': 'getNumber', 'service': srv_code, 'country': country_code}, srv['api_key'], srv['url'])
        
        if "ACCESS_NUMBER" in res:
            parts = res.split(":")
            tz_id, phone = parts[1], parts[2]
            
            cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (price, user_id))
            cursor.execute('INSERT INTO purchases (user_id, tz_id, phone, service, cost) VALUES (?, ?, ?, ?, ?)',
                           (user_id, tz_id, phone, srv_code, price))
            conn.commit()
            conn.close()
            
            msg = (f"✅ **تم شراء الرقم بنجاح!**\n\n"
                   f"📱 **الرقم:** `{phone}`\n"
                   f"🆔 **معرف العملية:** `{tz_id}`\n"
                   f"💵 **السعر:** ${price:.2f}\n\n"
                   f"📥 قم بإدخال الرقم ثم اضغط على **الحصول على الكود**:")
            bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=active_number_keyboard(tz_id, server_id))
        else:
            conn.close()
            bot.send_message(chat_id, f"❌ **لم يكتمل الطلب:** الرد من السيرفر: `{res}`", parse_mode="Markdown")

    elif call.data.startswith("check_sms_"):
        parts = call.data.split("_")
        server_id, tz_id = parts[2], parts[3]
        srv = SERVERS.get(server_id)
        res = grizzly_request({'action': 'getStatus', 'id': tz_id}, srv['api_key'], srv['url'])
        
        if "STATUS_OK" in res:
            code = res.split(":")[1]
            bot.send_message(chat_id, f"🎉 **وصل كود التفعيل الخاص بك!**\n\n🔑 **الكود:** `{code}`", parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "⏳ لم يتم استلام الكود بعد. حاول مجدداً بعد قليل.", show_alert=True)

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
            bot.answer_callback_query(call.id, "العملية ملغاة مسبقاً.", show_alert=True)

    elif call.data == "smm_main":
        bot.edit_message_text("🚀 **قسم خدمات الرشق وشحن الألعاب**\n\nاختر الخدمة التي تود طلبها:", chat_id, message_id, reply_markup=smm_panel_keyboard())

    elif call.data.startswith("smm_order_"):
        service_id = call.data.split("_")[2]
        USER_STEPS[user_id] = {'step': 'WAITING_LINK', 'service_id': service_id}
        bot.send_message(chat_id, "🔗 **يرجى إرسال رابط الحساب / القناة / المعرف المطلوب للرشق:**")

    elif call.data == "free_ruble":
        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,))
        invite_count = cursor.fetchone()[0]
        conn.close()
        
        earned_total = invite_count * REWARD_PER_INVITE
        
        msg = (f"💎 **نظام اربح رصيد مجاني** 💎\n\n"
               f"قم بنشر رابط الإحالة الخاص بك بين أصدقائك، واحصل على رصيد مجاني عند انضمامهم!\n\n"
               f"🎁 **المكافأة لكل شخص:** `${REWARD_PER_INVITE:.2f}`\n"
               f"👥 **عدد الذين دعوتهم:** `{invite_count}` شخص\n"
               f"💵 **إجمالي أرباحك:** `${earned_total:.2f}`\n\n"
               f"🔗 **رابط الدعوة الخاص بك:**\n`{ref_link}`")
               
        bot.send_message(chat_id, msg, parse_mode="Markdown")

    elif call.data == "ai_landing":
        bot.send_message(chat_id, "🤖 **قسم خدمات الذكاء الاصطناعي**\n\nيمكنك كتابة سؤالك مباشرة للبوت للحصول على إجابة ذكية فورية.")

    elif call.data in ["fast_buy_tg", "fast_buy_wa"]:
        srv_code = "tg" if "tg" in call.data else "wa"
        markup = countries_keyboard_fast("grizzly", srv_code)
        bot.edit_message_text(f"⚡ **عروض سريعة لتطبيق ({srv_code.upper()}):**", chat_id, message_id, reply_markup=markup)

    elif call.data == "best_selling":
        bot.send_message(chat_id, "🔥 **السيرفرات الأكثر مبيعاً حالياً:**\n1. Grizzly SMS - تليجرام روسيا\n2. Tiger SMS - واتساب نيجيريا")

    elif call.data == "most_available":
        bot.send_message(chat_id, "🎲 **الأكثر توفراً حالياً:** أرقام نيجيريا وروسيا متوفرة بكثرة وبكود سريع.")

    elif call.data == "support":
        bot.send_message(chat_id, f"🎧 **الدعم الفني المباشر:**\nراسلنا عبر الحساب: {ADMIN_USERNAME}")

    elif call.data == "purchase_stats":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM purchases WHERE status='COMPLETED' OR status='PENDING'")
        count = cursor.fetchone()[0]
        conn.close()
        bot.send_message(chat_id, f"✔ **إحصائيات الشراء الناجح:**\nتم تفعيل أكثر من {count + 150} رقم عبر البوت بنجاح!")

    elif call.data == "my_account":
        user_data = get_or_create_user(user_id, call.from_user.first_name)
        msg = (f"👤 **معلومات حسابك:**\n\n"
               f"🆔 معرف الحساب: `{user_data[0]}`\n"
               f"💰 الرصيد: ${user_data[2]:.2f}\n"
               f"🤖 رصيد AI: {user_data[3]} أسئلة")
        bot.send_message(chat_id, msg, parse_mode="Markdown")

    elif call.data == "other_services":
        bot.send_message(chat_id, "🛸 **خدمات وميزات أخرى:**\nقريباً سيتم إطلاق المزيد من الخدمات الحصرية.")

    elif call.data == "admin_panel" and str(user_id) == str(ADMIN_ID):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        u_count = cursor.fetchone()[0]
        conn.close()
        bot.send_message(chat_id, f"⚙️ **لوحة الإدارة الكبرى:**\n\n👥 عدد مستخدمي البوت: {u_count}\n\n💡 لشحن رصيد أي مستخدم ارسل:\n`/add_bal USER_ID AMOUNT`", parse_mode="Markdown")

# ==================== 7. استقبال المدخلات والتحويل والذكاء الاصطناعي ====================
@bot.message_handler(func=lambda msg: msg.from_user.id in USER_STEPS and not msg.text.startswith('/'))
def handle_user_steps(message):
    user_id = message.from_user.id
    step_data = USER_STEPS.get(user_id)
    
    if step_data.get('step') == 'WAITING_TRANSFER_DATA':
        try:
            parts = message.text.strip().split()
            if len(parts) != 2:
                bot.send_message(message.chat.id, "❌ **صيغة خاطئة!**\nارسل المعرف ثم المبلغ مفصولين بمسافة.\nمثال: `6113734300 5`", parse_mode="Markdown")
                return

            target_id = int(parts[0])
            amount = float(parts[1])

            if amount <= 0:
                bot.send_message(message.chat.id, "❌ **يرجى إدخال مبلغ أكبر من صفر.**")
                return

            if target_id == user_id:
                bot.send_message(message.chat.id, "❌ **لا يمكنك تحويل الرصيد لنفسك!**")
                return

            conn = get_db()
            cursor = conn.cursor()

            cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            sender_bal = cursor.fetchone()[0]

            if sender_bal < amount:
                bot.send_message(message.chat.id, f"❌ **رصيدك غير كافٍ!**\nرصيدك الحالي: ${sender_bal:.2f}")
                conn.close()
                del USER_STEPS[user_id]
                return

            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (target_id,))
            receiver = cursor.fetchone()

            if not receiver:
                bot.send_message(message.chat.id, "❌ **لم يتم العثور على مستخدم بهذا المعرف (ID) في البوت.**")
                conn.close()
                del USER_STEPS[user_id]
                return

            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_id))
            conn.commit()
            conn.close()

            bot.send_message(message.chat.id, f"✅ **تم تحويل ${amount:.2f} بنجاح!**\n➡️ **إلى المعرف:** `{target_id}`\n💸 **العمولة:** $0.00", parse_mode="Markdown")

            try:
                bot.send_message(target_id, f"🎉 **وصلك تحويل رصيد جديد!**\n💵 **المبلغ:** `${amount:.2f}`\n👤 **من المعرف:** `{user_id}`", parse_mode="Markdown")
            except:
                pass

        except Exception as e:
            bot.send_message(message.chat.id, "❌ **حدث خطأ أثناء تنفيذ الطلب.** يرجى التأكد من كتابة الرقم والمبلغ بصورة صحيحة.")
        
        del USER_STEPS[user_id]
        return

    elif step_data.get('step') == 'WAITING_LINK':
        step_data['link'] = message.text
        step_data['step'] = 'WAITING_QTY'
        bot.send_message(message.chat.id, "🔢 **قم بإرسال الكمية المطلوبة الآن (مثال: 1000):**")
        
    elif step_data.get('step') == 'WAITING_QTY':
        if not message.text.isdigit():
            bot.send_message(message.chat.id, "❌ **يرجى كتابة الكمية بالأرقام فقط.**")
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
            bot.send_message(message.chat.id, f"❌ **رصيدك غير كافٍ!**\nتكلفة الطلب: ${total_cost:.2f}\nرصيدك: ${balance:.2f}")
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
                bot.send_message(message.chat.id, f"✅ **تم إرسال طلب الرشق بنجاح!**\n\n🆔 **رقم الطلب:** `{order_id}`\n🔗 **الرابط:** `{link}`\n🔢 **الكمية:** {qty}\n💵 **المبلغ:** ${total_cost:.2f}", parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, f"❌ **خطأ من المورد:** {res.get('error', 'تعذر الطلب')}")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ **حدث خطأ أثناء الاتصال بالسيرفر:** {e}")
            
        conn.close()
        del USER_STEPS[user_id]

# الرد بـ Gemini AI للرسائل النصية العامة
@bot.message_handler(func=lambda msg: True, content_types=['text'])
def handle_ai_chat(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        return

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT ai_balance FROM users WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    
    if res and res[0] > 0:
        if model is None:
            bot.reply_to(message, "⚠️ خدمة الذكاء الاصطناعي غير مفعلة حالياً.")
            conn.close()
            return
            
        cursor.execute("UPDATE users SET ai_balance = ai_balance - 1 WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()
        
        try:
            response = model.generate_content(message.text)
            bot.reply_to(message, response.text)
        except Exception as e:
            bot.reply_to(message, "⚠️ حدث خطأ أثناء الاتصال بنموذج الذكاء الاصطناعي.")
    else:
        conn.close()
        bot.reply_to(message, "❌ **نفد رصيد أسئلة الذكاء الاصطناعي المتاحة لك.**")

bot.infinity_polling()
