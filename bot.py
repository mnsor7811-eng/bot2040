import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import google.generativeai as genai

# ==================== 1. الإعدادات الأساسية ====================
TOKEN = '8927305428:AAHlCPINlpyeymiPL7WnxxZtjufvZxd6--Y'
GEMINI_API_KEY = 'AQ.Ab8RN6IOLYCW3mnMh6H5le6Bc1pAG60TXO0IoxjpPcHvaFZHkg'
ADMIN_ID = 6113734300  # أيدي الأدمن الخاص بك
ADMIN_USERNAME = "@Num_s7"

bot = telebot.TeleBot(TOKEN)
genai.configure(api_key=GEMINI_API_KEY)
# استخدام نموذج سريع واقتصادي
model = genai.GenerativeModel('gemini-1.5-flash')

# ==================== 2. قاعدة البيانات المتقدمة ====================
def setup_db():
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    # تم إضافة عمود ai_balance لأسئلة الذكاء الاصطناعي
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        name TEXT,
                        balance REAL DEFAULT 0.0,
                        ai_balance INTEGER DEFAULT 5, 
                        is_banned INTEGER DEFAULT 0
                    )''')
    # إضافة العمود إذا كانت القاعدة قديمة (تجنب الخطأ)
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN ai_balance INTEGER DEFAULT 5')
    except:
        pass # العمود موجود مسبقاً
        
    cursor.execute('''CREATE TABLE IF NOT EXISTS services (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        price REAL
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT
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
        # منح 5 أسئلة مجانية لكل مستخدم جديد كفترة تجريبية
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

def check_section_status(section_key):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = ?', (section_key,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else "open"

# ==================== 3. الواجهات والأزرار ====================
def main_keyboard(user_id):
    markup = InlineKeyboardMarkup()
    
    # الزر الجديد للذكاء الاصطناعي
    btn_ai = InlineKeyboardButton("🤖 الذكاء الاصطناعي (مساعدك الذكي)", callback_data="chat_ai")
    
    btn_buy_num = InlineKeyboardButton("📞 شراء رقم افتراضي", callback_data="buy_number")
    btn_wa = InlineKeyboardButton("🟢 عروض WhatsApp", callback_data="wa_offers")
    btn_tg = InlineKeyboardButton("🔵 جاهز Telegram", callback_data="tg_ready")
    btn_best_selling = InlineKeyboardButton("🔥 السيرفرات الأكثر مبيعاً", callback_data="best_selling")
    btn_recharge = InlineKeyboardButton("💳 شحن الرصيد / الاشتراكات", callback_data="recharge")
    btn_games = InlineKeyboardButton("🔭 الرشق وشحن الألعاب", callback_data="games_boost")
    btn_support = InlineKeyboardButton("🎧 الدعم الفني", callback_data="support")
    btn_account = InlineKeyboardButton("👤 حسابي", callback_data="my_account")
    
    markup.row(btn_ai) # قسم الذكاء الاصطناعي في الأعلى
    markup.row(btn_buy_num)
    markup.row(btn_tg, btn_wa)
    markup.row(btn_best_selling)
    markup.row(btn_recharge, btn_games)
    markup.row(btn_support, btn_account)
    
    if str(user_id) == str(ADMIN_ID):
        btn_admin = InlineKeyboardButton("⚙️ لوحة الإدارة الكبرى", callback_data="admin_panel")
        markup.row(btn_admin)
        
    return markup

def admin_keyboard():
    markup = InlineKeyboardMarkup()
    btn1 = InlineKeyboardButton("➕ إضافة رصيد ($)", callback_data="adm_add_bal")
    btn2 = InlineKeyboardButton("⛔ خصم رصيد ($)", callback_data="adm_sub_bal")
    # أزرار الإدارة الجديدة للذكاء الاصطناعي
    btn_ai1 = InlineKeyboardButton("➕ إضافة أسئلة AI", callback_data="adm_add_ai")
    btn_ai2 = InlineKeyboardButton("⛔ خصم أسئلة AI", callback_data="adm_sub_ai")
    
    btn3 = InlineKeyboardButton("➕ إضافة دولة/خدمة", callback_data="adm_add_service")
    btn5 = InlineKeyboardButton("📊 إحصائيات البوت", callback_data="adm_users_count")
    btn6 = InlineKeyboardButton("📢 إذاعة نشر", callback_data="adm_broadcast")
    btn8 = InlineKeyboardButton("🚫 حظر/فك حظر", callback_data="adm_ban_user")
    btn9 = InlineKeyboardButton("💰 كشف حساب عضو", callback_data="adm_check_user")
    btn10 = InlineKeyboardButton("🔙 العودة", callback_data="back_main")
    
    markup.row(btn1, btn2)
    markup.row(btn_ai1, btn_ai2) # إدارة الـ AI
    markup.row(btn3, btn5)
    markup.row(btn6, btn8)
    markup.row(btn9)
    markup.row(btn10)
    return markup

# ==================== 4. المعالجات والأوامر ====================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or "المستخدم"
    
    if is_user_banned(user_id):
        bot.send_message(message.chat.id, "🚫 عذراً، لقد تم حظرك من استخدام هذا البوت.")
        return
        
    user_data = get_or_create_user(user_id, name)
    balance = user_data[2]
    ai_balance = user_data[3]
    
    text = (f"💠 أهلاً بك عزيزي في بوت الخدمات الشامل 💠\n\n"
            f"👤 حسابك: {name}\n"
            f"💰 رصيد الخدمات: ${balance:.2f}\n"
            f"🤖 رصيد أسئلة الذكاء: {ai_balance} سؤال\n\n"
            f"📌 اختر الخدمة التي تريدها من الأسفل:")
    
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

    back_markup = InlineKeyboardMarkup()
    back_markup.add(InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_main"))

    if call.data == "back_main":
        user_data = get_or_create_user(user_id, call.from_user.first_name)
        text = (f"💠 أهلاً بك عزيزي في بوت الخدمات الشامل 💠\n\n"
                f"👤 حسابك: {call.from_user.first_name}\n"
                f"💰 رصيد الخدمات: ${user_data[2]:.2f}\n"
                f"🤖 رصيد أسئلة الذكاء: {user_data[3]} سؤال\n\n"
                f"📌 اختر الخدمة التي تريدها من الأسفل:")
        bot.edit_message_text(text, chat_id, message_id, reply_markup=main_keyboard(user_id))

    elif call.data == "my_account":
        user_data = get_or_create_user(user_id, call.from_user.first_name)
        text = (f"👤 **معلومات حسابك الشخصي:**\n\n"
                f"🆔 الأيدي: `{user_id}`\n"
                f"💰 رصيد الدولار: ${user_data[2]:.2f}\n"
                f"🤖 رصيد الأسئلة: {user_data[3]} سؤال")
        bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=back_markup)

    # ---------------- قسم الدفع المعدل ----------------
    elif call.data == "recharge":
        text = (f"💳 **طرق شحن الرصيد وشراء الاشتراكات:**\n\n"
                f"لشحن رصيدك أو تفعيل باقات الذكاء الاصطناعي، يرجى التحويل إلى أحد الحسابات التالية:\n\n"
                f"🏦 **بنك الكريمي:** `3134706987`\n"
                f"📱 **محفظة جيب:** `374468`\n"
                f"💸 **ون كاش:** `140601836`\n"
                f"🟡 **بايننس (Binance ID):** `979808293`\n\n"
                f"⚠️ **ملاحظة هامة:** بعد التحويل، يجب تصوير السند وإرساله مع رقم الـ ID الخاص بك (`{user_id}`) إلى الإدارة للتفعيل الفوري عبر المعرف:\n"
                f"👉 {ADMIN_USERNAME}")
        bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=back_markup)

    elif call.data == "support":
        text = f"🎧 **الدعم الفني:**\nلأي مشكلة أو استفسار، تواصل مع الإدارة عبر المعرف:\n{ADMIN_USERNAME}"
        bot.edit_message_text(text, chat_id, message_id, reply_markup=back_markup)
        
    # ---------------- قسم الذكاء الاصطناعي ----------------
    elif call.data == "chat_ai":
        user_data = get_or_create_user(user_id, call.from_user.first_name)
        ai_balance = user_data[3]
        if ai_balance > 0:
            msg = bot.send_message(chat_id, f"🤖 مرحباً بك في قسم الذكاء الاصطناعي.\nرصيدك: {ai_balance} سؤال.\n\nالرجاء كتابة سؤالك الآن:")
            bot.register_next_step_handler(msg, process_ai_question)
        else:
            bot.send_message(chat_id, f"❌ رصيدك من الأسئلة انتهى. يرجى الاشتراك أو شحن الرصيد عبر قسم الشحن ثم التواصل مع الإدارة {ADMIN_USERNAME}.")

    # ==================== لوحة التحكم الإدارية المعدلة ====================
    elif call.data == "admin_panel":
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("⚙️ **أهلاً بك في لوحة الإدارة الكبرى:**\nاختر العملية المطلوبة:", chat_id, message_id, reply_markup=admin_keyboard(), parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "عفواً، هذه اللوحة للمشرفين فقط!", show_alert=True)

    elif call.data == "adm_add_bal":
        msg = bot.send_message(chat_id, "➕ أرسل أيدي المستخدم والمبلغ ($) المراد إضافته بالشكل التالي:\n`أيدي المبلغ`\nمثال: `6113734300 10`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_admin_add_balance)

    # دوال إدارة الـ AI الجديدة
    elif call.data == "adm_add_ai":
        msg = bot.send_message(chat_id, "➕ أرسل أيدي المستخدم وعدد الأسئلة المراد إضافتها بالشكل التالي:\n`أيدي عدد_الأسئلة`\nمثال: `6113734300 100`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_admin_add_ai)
        
    elif call.data == "adm_sub_ai":
        msg = bot.send_message(chat_id, "⛔ أرسل أيدي المستخدم وعدد الأسئلة المراد خصمها بالشكل التالي:\n`أيدي عدد_الأسئلة`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_admin_sub_ai)

    elif call.data == "adm_check_user":
        msg = bot.send_message(chat_id, "💰 أرسل أيدي المستخدم للكشف عن رصيده وحسابه:")
        bot.register_next_step_handler(msg, process_check_user)
        
    else:
        # للإبقاء على الأقسام الأخرى التي لم نعدلها وتعمل بشكل سليم
        pass 

# ==================== دوال المعالجة (AI & Admin) ====================

def process_ai_question(message):
    user_id = message.from_user.id
    question = message.text
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT ai_balance FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    
    if user and user[0] > 0:
        bot.send_message(message.chat.id, "⏳ جاري التفكير...")
        try:
            # استدعاء الذكاء الاصطناعي
            response = model.generate_content(question)
            reply = response.text
            
            # خصم سؤال واحد من الرصيد
            cursor.execute('UPDATE users SET ai_balance = ai_balance - 1 WHERE user_id = ?', (user_id,))
            conn.commit()
            
            # إرسال الرد للمستخدم
            bot.send_message(message.chat.id, f"🤖 **الرد:**\n\n{reply}", parse_mode="Markdown")
        except Exception as e:
            bot.send_message(message.chat.id, "❌ حدث خطأ أثناء الاتصال بالخادم. لم يتم خصم رصيدك. حاول لاحقاً.")
    else:
        bot.send_message(message.chat.id, f"❌ عذراً، رصيدك من الأسئلة انتهى. تواصل مع الإدارة {ADMIN_USERNAME} لشحن باقة جديدة.")
    conn.close()

# دوال إدارة رصيد الدولار (كما هي في كودك الأصلي)
def process_admin_add_balance(message):
    try:
        parts = message.text.split()
        target_id = int(parts[0])
        amount = float(parts[1])
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, target_id))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"✅ تمت إضافة ${amount} بنجاح إلى رصيد المستخدم `{target_id}`", parse_mode="Markdown")
        bot.send_message(target_id, f"🎉 تمت إضافة ${amount} إلى رصيدك بواسطة الإدارة.")
    except:
        bot.send_message(message.chat.id, "❌ خطأ في الإدخال.")

# دوال إدارة رصيد الذكاء الاصطناعي (جديدة)
def process_admin_add_ai(message):
    try:
        parts = message.text.split()
        target_id = int(parts[0])
        questions = int(parts[1])
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET ai_balance = ai_balance + ? WHERE user_id = ?', (questions, target_id))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"✅ تمت إضافة {questions} سؤال بنجاح للمستخدم `{target_id}`", parse_mode="Markdown")
        bot.send_message(target_id, f"🤖🎉 تم تفعيل باقة ذكاء اصطناعي لك وتمت إضافة {questions} سؤال إلى رصيدك!")
    except:
        bot.send_message(message.chat.id, "❌ خطأ في الإدخال.")
        
def process_admin_sub_ai(message):
    try:
        parts = message.text.split()
        target_id = int(parts[0])
        questions = int(parts[1])
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET ai_balance = ai_balance - ? WHERE user_id = ?', (questions, target_id))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"✅ تم خصم {questions} سؤال من المستخدم `{target_id}`", parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "❌ خطأ في الإدخال.")

def process_check_user(message):
    try:
        target_id = int(message.text.strip())
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT name, balance, ai_balance, is_banned FROM users WHERE user_id = ?', (target_id,))
        user = cursor.fetchone()
        conn.close()
        if user:
            ban_str = "نعم 🚫" if user[3] == 1 else "لا ✅"
            bot.send_message(message.chat.id, f"👤 **معلومات المستخدم:**\n\n🆔 الأيدي: `{target_id}`\n🏷️ الاسم: {user[0]}\n💰 رصيد $: ${user[1]:.2f}\n🤖 رصيد AI: {user[2]} سؤال\n⛔ محظور: {ban_str}", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "❌ المستخدم غير مسجل في البوت.")
    except:
        bot.send_message(message.chat.id, "❌ أيدي غير صالح.")

bot.infinity_polling()
