import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import google.generativeai as genai

# ==================== 1. الإعدادات الأساسية ====================
TOKEN = '8927305428:AAFok7iKK0S4D3px-kdgW1WvAIZjXr3dWH8'
GEMINI_API_KEY = 'AQ.Ab8RN6IOLYCW3mnMh6H5le6Bc1pAG60TXO0IoxjpPcHvaFZHkg'
ADMIN_ID = 6113734300
ADMIN_USERNAME = "@Num_s7"

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
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN ai_balance INTEGER DEFAULT 5')
    except:
        pass
        
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

# ==================== 3. لوحات الأزرار ====================
def main_keyboard(user_id):
    markup = InlineKeyboardMarkup()
    
    btn_ai = InlineKeyboardButton("🤖 اشتراكات برامج AI", callback_data="ai_landing")
    btn_buy_num = InlineKeyboardButton("📞 شراء رقم افتراضي", callback_data="buy_number")
    btn_wa = InlineKeyboardButton("🟢 عروض WhatsApp", callback_data="wa_offers")
    btn_tg = InlineKeyboardButton("🔵 جاهز Telegram", callback_data="tg_ready")
    btn_best_selling = InlineKeyboardButton("🔥 السيرفرات الأكثر مبيعاً", callback_data="best_selling")
    btn_most_offer = InlineKeyboardButton("🎲 الأكثر توفراً", callback_data="most_available")
    btn_recharge = InlineKeyboardButton("🎳 شحن الرصيد / الاشتراكات", callback_data="recharge_menu")
    btn_games = InlineKeyboardButton("🔭 الرشق وشحن الألعاب والبرامج", callback_data="games_boost")
    btn_ruble = InlineKeyboardButton("💎 اربح روبل مجاناً", callback_data="free_ruble")
    btn_support = InlineKeyboardButton("🎧 الدعم", callback_data="support")
    btn_transfer = InlineKeyboardButton("🔄 تحويل الرصيد", callback_data="transfer")
    btn_stats = InlineKeyboardButton("✔ إحصائيات الشراء الناجح", callback_data="purchase_stats")
    btn_account = InlineKeyboardButton("👤 حسابي", callback_data="my_account")
    btn_other = InlineKeyboardButton("🛸 خدمات وميزات أخرى", callback_data="other_services")
    
    markup.row(btn_ai)
    markup.row(btn_buy_num)
    markup.row(btn_tg, btn_wa)
    markup.row(btn_best_selling)
    markup.row(btn_recharge, btn_most_offer)
    markup.row(btn_games)
    markup.row(btn_ruble)
    markup.row(btn_support, btn_transfer)
    markup.row(btn_stats)
    markup.row(btn_account)
    markup.row(btn_other)
    
    if str(user_id) == str(ADMIN_ID):
        btn_admin = InlineKeyboardButton("⚙️ لوحة الإدارة الكبرى", callback_data="admin_panel")
        markup.row(btn_admin)
        
    return markup

def ai_section_keyboard():
    markup = InlineKeyboardMarkup()
    btn_start_ask = InlineKeyboardButton("❓ اسأل الذكاء الاصطناعي الآن", callback_data="ask_ai_direct")
    btn_buy_pkg = InlineKeyboardButton("💳 شحن رصيد / شراء باقة", callback_data="recharge_menu")
    btn_back = InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main")
    
    markup.row(btn_start_ask)
    markup.row(btn_buy_pkg)
    markup.row(btn_back)
    return markup

def payment_methods_keyboard():
    markup = InlineKeyboardMarkup()
    btn_kuraimi = InlineKeyboardButton("🏛️ بنك الكريمي", callback_data="pay_kuraimi")
    btn_jeeb = InlineKeyboardButton("📱 محفظة جيب", callback_data="pay_jeeb")
    btn_onecash = InlineKeyboardButton("💳 ون كاش (One Cash)", callback_data="pay_onecash")
    btn_binance = InlineKeyboardButton("🟡 بايننس (Binance)", callback_data="pay_binance")
    btn_back = InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main")
    
    markup.row(btn_kuraimi)
    markup.row(btn_jeeb)
    markup.row(btn_onecash)
    markup.row(btn_binance)
    markup.row(btn_back)
    return markup

def admin_keyboard():
    markup = InlineKeyboardMarkup()
    btn1 = InlineKeyboardButton("➕ إضافة رصيد ($)", callback_data="adm_add_bal")
    btn2 = InlineKeyboardButton("⛔ خصم رصيد ($)", callback_data="adm_sub_bal")
    btn_ai1 = InlineKeyboardButton("➕ إضافة أسئلة AI", callback_data="adm_add_ai")
    btn_ai2 = InlineKeyboardButton("⛔ خصم أسئلة AI", callback_data="adm_sub_ai")
    btn3 = InlineKeyboardButton("➕ إضافة دولة/خدمة", callback_data="adm_add_service")
    btn4 = InlineKeyboardButton("➖ حذف دولة/خدمة", callback_data="adm_del_service")
    btn5 = InlineKeyboardButton("📊 عدد المشتركين", callback_data="adm_users_count")
    btn6 = InlineKeyboardButton("📢 إذاعة نشر", callback_data="adm_broadcast")
    btn7 = InlineKeyboardButton("🔒 فتح وقفل الأقسام", callback_data="adm_sections")
    btn8 = InlineKeyboardButton("🚫 تقييد/فك تقييد عضو", callback_data="adm_ban_user")
    btn9 = InlineKeyboardButton("💰 كشف رصيد مستخدم", callback_data="adm_check_user")
    btn10 = InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main")
    
    markup.row(btn1, btn2)
    markup.row(btn_ai1, btn_ai2)
    markup.row(btn3, btn4)
    markup.row(btn5, btn6)
    markup.row(btn7, btn8)
    markup.row(btn9)
    markup.row(btn10)
    return markup

# ==================== 4. الأوامر والمعالجة ====================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or "المستخدم"
    
    if is_user_banned(user_id):
        bot.send_message(message.chat.id, "🚫 عذراً، لقد تم حظرك من استخدام هذا البوت بواسطة الإدارة.")
        return
        
    user_data = get_or_create_user(user_id, name)
    balance = user_data[2]
    ai_balance = user_data[3]
    
    text = (f"💠 أهلاً بك عزيزي في بوت (NUMBER SMS) 💠\n\n"
            f"👤 حسابك: {ADMIN_USERNAME}\n"
            f"💰 رصيدك الحالي: ${balance:.2f}\n"
            f"🤖 رصيد أسئلة الذكاء: {ai_balance} سؤال\n\n"
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
    except Exception:
        pass

    back_markup = InlineKeyboardMarkup()
    back_markup.add(InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_main"))

    if call.data == "back_main":
        user_data = get_or_create_user(user_id, call.from_user.first_name)
        text = (f"💠 أهلاً بك عزيزي في بوت (NUMBER SMS) 💠\n\n"
                f"👤 حسابك: {ADMIN_USERNAME}\n"
                f"💰 رصيدك الحالي: ${user_data[2]:.2f}\n"
                f"🤖 رصيد أسئلة الذكاء: {user_data[3]} سؤال\n\n"
                f"📌 استخدم الأزرار بالأسفل لتنفيذ طلباتك:")
        bot.edit_message_text(text, chat_id, message_id, reply_markup=main_keyboard(user_id))

    # ---------------- قسم الذكاء الاصطناعي ----------------
    elif call.data == "ai_landing":
        user_data = get_or_create_user(user_id, call.from_user.first_name)
        ai_balance = user_data[3]
        
        promo_text = (
            f"🚀 **مرحباً بك في عالم الذكاء الاصطناعي الفائق!** ⚡\n\n"
            f"استمتع بأحدث التقنيات لمساعدتك في كتابة المحتوى، الترجمة، حل المسائل، البرمجة، والتخطيط لأعمالك بدقة وسرعة مذهلة!\n\n"
            f"📊 **رصيدك الحالي:** {ai_balance} أسئلة مجانية/متاحة.\n\n"
            f"💎 **باقات وااشتراكات الذكاء الاصطناعي المتاحة:**\n"
            f"🔹 **الباقة الاقتصادية:** 50 سؤال = $1.00\n"
            f"🔹 **الباقة الاحترافية:** 150 سؤال = $2.50\n"
            f"🔹 **الباقة المفتوحة:** أسئلة غير محدودة = $5.00 شهرياً\n\n"
            f"👇 اختر ماذا تريد أن تفعل الآن:"
        )
        bot.edit_message_text(promo_text, chat_id, message_id, reply_markup=ai_section_keyboard())

    elif call.data == "ask_ai_direct":
        user_data = get_or_create_user(user_id, call.from_user.first_name)
        ai_balance = user_data[3]
        if ai_balance > 0:
            msg = bot.send_message(chat_id, "🧠 **جاهز لاستقبال سؤالك!**\nارسل أي سؤال أو نص تريد صياغته الآن وسأجيبك فوراً:")
            bot.register_next_step_handler(msg, process_ai_question)
        else:
            bot.send_message(chat_id, f"❌ **انتهى رصيدك المجاني!**\nاشحن حسابك واشترك في إحدى الباقات للاستمرار في الاستفادة من المساعد الذكي. للتواصل: {ADMIN_USERNAME}")

    # ---------------- قائمة الطرق الدفع المنفصلة ----------------
    elif call.data == "recharge_menu":
        text = (f"💳 **قسم شحن الرصيد والاشتراكات**\n\n"
                f"اختر طريقة الدفع المناسبة لك من الأزرار أدناه للحصول على تفاصيل التحويل:")
        bot.edit_message_text(text, chat_id, message_id, reply_markup=payment_methods_keyboard())

    elif call.data == "pay_kuraimi":
        text = (f"🏛️ **الدفع عبر بنك الكريمي**\n\n"
                f"📌 رقم الحساب: `3134706987`\n\n"
                f"📩 **طريقة التفعيل:**\n"
                f"بعد التحويل، قم بتصوير إشعار التحويل وإرساله إلى الدعم الفني مرفقاً بالأيدي الخاص بك (`{user_id}`):\n"
                f"👉 **الدعم الفني:** {ADMIN_USERNAME}")
        
        pay_back = InlineKeyboardMarkup()
        pay_back.add(InlineKeyboardButton("🔙 العودة لوسائل الدفع", callback_data="recharge_menu"))
        bot.edit_message_text(text, chat_id, message_id, reply_markup=pay_back)

    elif call.data == "pay_jeeb":
        text = (f"📱 **الدفع عبر محفظة جيب**\n\n"
                f"📌 رقم المحفظة: `374468`\n\n"
                f"📩 **طريقة التفعيل:**\n"
                f"بعد التحويل، قم بتصوير إشعار التحويل وإرساله إلى الدعم الفني مرفقاً بالأيدي الخاص بك (`{user_id}`):\n"
                f"👉 **الدعم الفني:** {ADMIN_USERNAME}")
        
        pay_back = InlineKeyboardMarkup()
        pay_back.add(InlineKeyboardButton("🔙 العودة لوسائل الدفع", callback_data="recharge_menu"))
        bot.edit_message_text(text, chat_id, message_id, reply_markup=pay_back)

    elif call.data == "pay_onecash":
        text = (f"💳 **الدفع عبر ون كاش (One Cash)**\n\n"
                f"📌 رقم الحساب: `140601836`\n\n"
                f"📩 **طريقة التفعيل:**\n"
                f"بعد التحويل، قم بتصوير إشعار التحويل وإرساله إلى الدعم الفني مرفقاً بالأيدي الخاص بك (`{user_id}`):\n"
                f"👉 **الدعم الفني:** {ADMIN_USERNAME}")
        
        pay_back = InlineKeyboardMarkup()
        pay_back.add(InlineKeyboardButton("🔙 العودة لوسائل الدفع", callback_data="recharge_menu"))
        bot.edit_message_text(text, chat_id, message_id, reply_markup=pay_back)

    elif call.data == "pay_binance":
        text = (f"🟡 **الدفع عبر بايننس (Binance)**\n\n"
                f"📌 Binance Pay / ID: `979808293`\n\n"
                f"📩 **طريقة التفعيل:**\n"
                f"بعد التحويل، قم بتصوير إشعار التحويل وإرساله إلى الدعم الفني مرفقاً بالأيدي الخاص بك (`{user_id}`):\n"
                f"👉 **الدعم الفني:** {ADMIN_USERNAME}")
        
        pay_back = InlineKeyboardMarkup()
        pay_back.add(InlineKeyboardButton("🔙 العودة لوسائل الدفع", callback_data="recharge_menu"))
        bot.edit_message_text(text, chat_id, message_id, reply_markup=pay_back)

    # ---------------- باقي أزرار الحساب والدعم ----------------
    elif call.data == "my_account":
        user_data = get_or_create_user(user_id, call.from_user.first_name)
        text = (f"👤 **معلومات حسابك الشخصي:**\n\n"
                f"🆔 الأيدي: {user_id}\n"
                f"💰 رصيد الخدمات: ${user_data[2]:.2f}\n"
                f"🤖 رصيد أسئلة الذكاء: {user_data[3]} سؤال")
        bot.edit_message_text(text, chat_id, message_id, reply_markup=back_markup)

    elif call.data == "support":
        text = f"🎧 **الدعم الفني:**\nلأي مشكلة أو استفسار، تواصل مع الإدارة عبر المعرف:\n{ADMIN_USERNAME}"
        bot.edit_message_text(text, chat_id, message_id, reply_markup=back_markup)

    elif call.data == "buy_number":
        if check_section_status("buy_number") == "closed" and str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "عذراً، هذا القسم مقفل مؤخراً من قبل الإدارة.", show_alert=True)
            return
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT name, price FROM services')
        services = cursor.fetchall()
        conn.close()
        text = "📞 **قسم شراء الأرقام الافتراضية والدول المتاحة:**\n\n"
        if services:
            for s in services:
                text += f"🔹 {s.name} - السعر: ${s.price}\n"
        else:
            text += "لا توجد دول مضافة حالياً. سيتم إضافتها قريباً من قبل الإدارة."
        bot.edit_message_text(text, chat_id, message_id, reply_markup=back_markup)

    # ---------------- لوحة التحكم الإدارية ----------------
    elif call.data == "admin_panel":
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("⚙️ **أهلاً بك في لوحة الإدارة الكبرى:**\nاختر العملية المطلوبة:", chat_id, message_id, reply_markup=admin_keyboard())
        else:
            bot.answer_callback_query(call.id, "عفواً، هذه اللوحة للمشرفين فقط!", show_alert=True)

    elif call.data == "adm_add_bal":
        msg = bot.send_message(chat_id, "➕ أرسل أيدي المستخدم والمبلغ ($) المراد إضافته بالشكل التالي:\nأيدي المبلغ\nمثال: 6113734300 10")
        bot.register_next_step_handler(msg, process_admin_add_balance)

    elif call.data == "adm_sub_bal":
        msg = bot.send_message(chat_id, "⛔ أرسل أيدي المستخدم والمبلغ المراد خصمه بالشكل التالي:\nأيدي المبلغ")
        bot.register_next_step_handler(msg, process_admin_sub_balance)

    elif call.data == "adm_add_ai":
        msg = bot.send_message(chat_id, "➕ أرسل أيدي المستخدم وعدد الأسئلة المراد إضافتها بالشكل التالي:\nأيدي عدد_الأسئلة\nمثال: 6113734300 100")
        bot.register_next_step_handler(msg, process_admin_add_ai)
        
    elif call.data == "adm_sub_ai":
        msg = bot.send_message(chat_id, "⛔ أرسل أيدي المستخدم وعدد الأسئلة المراد خصمها بالشكل التالي:\nأيدي عدد_الأسئلة")
        bot.register_next_step_handler(msg, process_admin_sub_ai)

    elif call.data == "adm_add_service":
        msg = bot.send_message(chat_id, "➕ أرسل اسم الدولة أو الخدمة مع السعر بالشكل التالي:\nاسم_الدولة السعر")
        bot.register_next_step_handler(msg, process_admin_add_service)

    elif call.data == "adm_users_count":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        count = cursor.fetchone()[0]
        conn.close()
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 رجوع للإدارة", callback_data="admin_panel"))
        bot.edit_message_text(f"📊 إحصائيات البوت:\n👥 إجمالي عدد المشتركين المسجلين: {count} مستخدم", chat_id, message_id, reply_markup=markup)

    elif call.data == "adm_broadcast":
        msg = bot.send_message(chat_id, "📢 أرسل الرسالة التي تريد إذاعتها لجميع مشتركي البوت الآن:")
        bot.register_next_step_handler(msg, process_broadcast)

    elif call.data == "adm_ban_user":
        msg = bot.send_message(chat_id, "🚫 أرسل أيدي المستخدم لحظره أو فك حظره:")
        bot.register_next_step_handler(msg, process_ban_toggle)

    elif call.data == "adm_check_user":
        msg = bot.send_message(chat_id, "💰 أرسل أيدي المستخدم للكشف عن رصيده وحسابه:")
        bot.register_next_step_handler(msg, process_check_user)

    else:
        bot.edit_message_text("🚧 هذا القسم قيد التفعيل.", chat_id, message_id, reply_markup=back_markup)

# ==================== معالجة الوظائف ====================
def process_ai_question(message):
    user_id = message.from_user.id
    question = message.text
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT ai_balance FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    
    if user and user[0] > 0:
        bot.send_message(message.chat.id, "⏳ جاري المعالجة والإجابة...")
        try:
            response = model.generate_content(question)
            reply = response.text
            cursor.execute('UPDATE users SET ai_balance = ai_balance - 1 WHERE user_id = ?', (user_id,))
            conn.commit()
            
            back_ai = InlineKeyboardMarkup()
            back_ai.add(InlineKeyboardButton("❓ سؤال آخر", callback_data="ask_ai_direct"))
            back_ai.add(InlineKeyboardButton("🔙 العودة لقائمة AI", callback_data="ai_landing"))
            
            bot.send_message(message.chat.id, f"🤖 **الرد:**\n\n{reply}", reply_markup=back_ai)
        except Exception:
            bot.send_message(message.chat.id, "❌ حدث خطأ أثناء الاتصال بالخادم. حاول لاحقاً.")
    else:
        bot.send_message(message.chat.id, f"❌ عذراً، رصيدك من الأسئلة انتهى. تواصل مع الإدارة {ADMIN_USERNAME} لشحن باقة جديدة.")
    conn.close()

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
        bot.send_message(message.chat.id, f"✅ تمت إضافة ${amount} بنجاح إلى رصيد المستخدم {target_id}")
    except Exception:
        bot.send_message(message.chat.id, "❌ خطأ في الإدخال.")

def process_admin_sub_balance(message):
    try:
        parts = message.text.split()
        target_id = int(parts[0])
        amount = float(parts[1])
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (amount, target_id))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"✅ تم خصم ${amount} بنجاح من رصيد المستخدم {target_id}")
    except Exception:
        bot.send_message(message.chat.id, "❌ خطأ في الإدخال.")

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
        bot.send_message(message.chat.id, f"✅ تمت إضافة {questions} سؤال بنجاح للمستخدم {target_id}")
    except Exception:
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
        bot.send_message(message.chat.id, f"✅ تم خصم {questions} سؤال من المستخدم {target_id}")
    except Exception:
        bot.send_message(message.chat.id, "❌ خطأ في الإدخال.")

def process_admin_add_service(message):
    try:
        parts = message.text.rsplit(' ', 1)
        name = parts[0]
        price = float(parts[1])
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO services (name, price) VALUES (?, ?)', (name, price))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"✅ تمت إضافة الخدمة/الدولة ({name}) بسعر (${price}) بنجاح!")
    except Exception:
        bot.send_message(message.chat.id, "❌ خطأ في الصيغة.")

def process_broadcast(message):
    text_to_send = message.text
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    conn.close()
    
    success = 0
    for u in users:
        try:
            bot.send_message(u[0], f"📢 **إعلان إداري:**\n\n{text_to_send}")
            success += 1
        except Exception:
            pass
    bot.send_message(message.chat.id, f"✅ تم إرسال الإذاعة بنجاح إلى {success} مستخدم.")

def process_ban_toggle(message):
    try:
        target_id = int(message.text.strip())
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT is_banned FROM users WHERE user_id = ?', (target_id,))
        res = cursor.fetchone()
        if res:
            new_status = 0 if res[0] == 1 else 1
            cursor.execute('UPDATE users SET is_banned = ? WHERE user_id = ?', (new_status, target_id))
            conn.commit()
            conn.close()
            status_text = "حظر" if new_status == 1 else "فك حظر"
            bot.send_message(message.chat.id, f"✅ تم تغيير حالة المستخدم {target_id} إلى: {status_text}")
        else:
            conn.close()
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود في قاعدة البيانات.")
    except Exception:
        bot.send_message(message.chat.id, "❌ أيدي غير صالح.")

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
            bot.send_message(message.chat.id, f"👤 **معلومات المستخدم:**\n\n🆔 الأيدي: {target_id}\n🏷️ الاسم: {user[0]}\n💰 رصيد $: ${user[1]:.2f}\n🤖 رصيد AI: {user[2]} سؤال\n⛔ محظور: {ban_str}")
        else:
            bot.send_message(message.chat.id, "❌ المستخدم غير مسجل في البوت.")
    except Exception:
        bot.send_message(message.chat.id, "❌ أيدي غير صالح.")

bot.infinity_polling()
