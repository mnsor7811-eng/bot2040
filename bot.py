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

# إعدادات API موقع Grizzly SMS
GRIZZLY_API_KEY = 'Hosamaed7993f2abbded229628261c56746d5'
GRIZZLY_URL = 'https://api.grizzlysms.com/stubs/handler_api.php'
PROFIT_MARGIN = 0.10  # نسبة الربح 10%

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

# ==================== 3. دالة التعامل مع API Grizzly SMS ====================
def grizzly_request(params):
    params['api_key'] = GRIZZLY_API_KEY
    try:
        response = requests.get(GRIZZLY_URL, params=params, timeout=10)
        return response.text
    except Exception as e:
        return f"ERROR: {e}"

def get_grizzly_price(service_code, country_code='0'):
    # جلب أسعار الخدمة حسابياً مع تطبيق نسبة ربح 10%
    res = grizzly_request({'action': 'getPrices', 'service': service_code, 'country': country_code})
    try:
        data = requests.get(f"{GRIZZLY_URL}?api_key={GRIZZLY_API_KEY}&action=getPrices&service={service_code}&country={country_code}").json()
        raw_price = float(data[country_code][service_code]['cost'])
        final_price = raw_price * (1 + PROFIT_MARGIN)
        return round(final_price, 2)
    except:
        return 0.50  # سعر افتراضي مقدر بالدولار عند تعذر جلب السعر اللحظي

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

def services_keyboard():
    markup = InlineKeyboardMarkup()
    btn_wa = InlineKeyboardButton("🟢 واتساب (WhatsApp)", callback_data="select_srv_wa")
    btn_tg = InlineKeyboardButton("🔵 تليجرام (Telegram)", callback_data="select_srv_tg")
    btn_ig = InlineKeyboardButton("📸 إنستغرام (Instagram)", callback_data="select_srv_ig")
    btn_imo = InlineKeyboardButton("🟡 إيمو (IMO)", callback_data="select_srv_imo")
    btn_tk = InlineKeyboardButton("🎵 تيك توك (TikTok)", callback_data="select_srv_tk")
    btn_back = InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main")
    
    markup.row(btn_wa)
    markup.row(btn_tg)
    markup.row(btn_ig)
    markup.row(btn_imo, btn_tk)
    markup.row(btn_back)
    return markup

def countries_keyboard(service_code):
    markup = InlineKeyboardMarkup()
    # أهم الدول الشائعة لتفعيل الأرقام
    countries = [
        ("🇺🇸 أمريكا", "187"),
        ("🇷🇺 روسيا", "0"),
        ("🇬🇧 بريطانيا", "16"),
        ("🇳🇬 نيجيريا", "19"),
        ("🇵🇭 الفلبين", "4"),
        ("🇪🇬 مصر", "21")
    ]
    for name, code in countries:
        price = get_grizzly_price(service_code, code)
        markup.add(InlineKeyboardButton(f"{name} - ${price}", callback_data=f"buy_num_{service_code}_{code}_{price}"))
        
    markup.add(InlineKeyboardButton("🔙 العودة لاختيار التطبيق", callback_data="buy_number"))
    return markup

def active_number_keyboard(tz_id):
    markup = InlineKeyboardMarkup()
    btn_code = InlineKeyboardButton("📩 الحصول على الكود", callback_data=f"check_sms_{tz_id}")
    btn_cancel = InlineKeyboardButton("❌ إلغاء الرقم واسترجاع المبلغ", callback_data=f"cancel_num_{tz_id}")
    markup.row(btn_code)
    markup.row(btn_cancel)
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

    # ---------------- قسم شراء أرقام افتراضية ----------------
    elif call.data == "buy_number":
        text = "📞 **قسم شراء الأرقام الافتراضية**\n\nاختر التطبيق أو الخدمة التي تريد تفعيلها:"
        bot.edit_message_text(text, chat_id, message_id, reply_markup=services_keyboard())

    elif call.data.startswith("select_srv_"):
        srv_code = call.data.split("_")[2]
        text = f"🌐 **اختر الدولة المطلوبة للخدمة ({srv_code.upper()}):**\n\n*الأسعار تشمل التفعيل المباشر مع ضمان الاسترجاع عند عدم وصول الكود*"
        bot.edit_message_text(text, chat_id, message_id, reply_markup=countries_keyboard(srv_code))

    elif call.data.startswith("buy_num_"):
        _, _, srv_code, country_code, price = call.data.split("_")
        price = float(price)
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        balance = cursor.fetchone()[0]
        
        if balance < price:
            bot.send_message(chat_id, f"❌ **رصيدك غير كافٍ!**\nسعر الرقم: ${price:.2f}\nرصيدك الحلي: ${balance:.2f}\n\nيرجى شحن حسابك أولاً.")
            conn.close()
            return

        # طلب شراء الرقم عبر API Grizzly
        res = grizzly_request({'action': 'getNumber', 'service': srv_code, 'country': country_code})
        
        if "ACCESS_NUMBER" in res:
            parts = res.split(":")
            tz_id = parts[1]
            phone = parts[2]
            
            # خصم الرصيد وتسجيل العملية
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
            bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=active_number_keyboard(tz_id))
        else:
            conn.close()
            bot.send_message(chat_id, "❌ **تنبيه:** لا توجد أرقام متاحة حالياً لهذه الدولة/الخدمة. اختر دولة أخرى أو حاول لاحقاً.")

    elif call.data.startswith("check_sms_"):
        tz_id = call.data.split("_")[2]
        res = grizzly_request({'action': 'getStatus', 'id': tz_id})
        
        if "STATUS_OK" in res:
            code = res.split(":")[1]
            bot.send_message(chat_id, f"🎉 **وصل كود التفعيل الخاص بك!**\n\n🔑 **الكود:** `{code}`", parse_mode="Markdown")
        elif "STATUS_WAIT_CODE" in res:
            bot.answer_callback_query(call.id, "⏳ جاري انتظار وصول الرسالة... حاول مجدداً بعد ثوانٍ.", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "لم يتم استلام الكود بعد.", show_alert=True)

    elif call.data.startswith("cancel_num_"):
        tz_id = call.data.split("_")[2]
        grizzly_request({'action': 'setStatus', 'status': '8', 'id': tz_id})
        
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
