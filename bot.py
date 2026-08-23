import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3

# ==================== 1. الإعدادات الأساسية ====================
TOKEN = '8927305428:AAHlCPINlpyeymiPL7WnxxZtjufvZxd6--Y'
ADMIN_ID = 6113734300  # أيدي الأدمن الخاص بك

bot = telebot.TeleBot(TOKEN)

# ==================== 2. قاعدة البيانات المتقدمة ====================
def setup_db():
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    # جدول المستخدمين
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        name TEXT,
                        balance REAL DEFAULT 0.0,
                        is_banned INTEGER DEFAULT 0
                    )''')
    # جدول الدول والخدمات
    cursor.execute('''CREATE TABLE IF NOT EXISTS services (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        price REAL
                    )''')
    # جدول إعدادات الأقسام (مفتوح أو مقفل)
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
        cursor.execute('INSERT INTO users (user_id, name, balance, is_banned) VALUES (?, ?, 0.0, 0)', (user_id, name))
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
    return res[0] if res else "open"  # افتراضياً القسم مفتوح

# ==================== 3. الواجهات والأزرار ====================
def main_keyboard(user_id):
    markup = InlineKeyboardMarkup()
    
    btn_buy_num = InlineKeyboardButton("📞 شراء رقم افتراضي", callback_data="buy_number")
    btn_wa = InlineKeyboardButton("🟢 عروض WhatsApp", callback_data="wa_offers")
    btn_tg = InlineKeyboardButton("🔵 جاهز Telegram", callback_data="tg_ready")
    btn_best_selling = InlineKeyboardButton("🔥 السيرفرات الأكثر مبيعاً", callback_data="best_selling")
    btn_recharge = InlineKeyboardButton("🎳 شحن الرصيد", callback_data="recharge")
    btn_most_offer = InlineKeyboardButton("🎲 الأكثر توفراً", callback_data="most_available")
    btn_games = InlineKeyboardButton("🔭 الرشق وشحن الألعاب والبرامج", callback_data="games_boost")
    btn_ruble = InlineKeyboardButton("💎 اربح روبل مجاناً", callback_data="free_ruble")
    btn_support = InlineKeyboardButton("🎧 الدعم", callback_data="support")
    btn_transfer = InlineKeyboardButton("🔄 تحويل الرصيد", callback_data="transfer")
    btn_stats = InlineKeyboardButton("✔ إحصائيات الشراء الناجح", callback_data="purchase_stats")
    btn_account = InlineKeyboardButton("👤 حسابي", callback_data="my_account")
    btn_other = InlineKeyboardButton("🛸 خدمات وميزات أخرى", callback_data="other_services")
    
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

def admin_keyboard():
    markup = InlineKeyboardMarkup()
    btn1 = InlineKeyboardButton("➕ إضافة رصيد", callback_data="adm_add_bal")
    btn2 = InlineKeyboardButton("⛔ خصم رصيد", callback_data="adm_sub_bal")
    btn3 = InlineKeyboardButton("➕ إضافة دولة/خدمة", callback_data="adm_add_service")
    btn4 = InlineKeyboardButton("➖ حذف دولة/خدمة", callback_data="adm_del_service")
    btn5 = InlineKeyboardButton("📊 عدد المشتركين", callback_data="adm_users_count")
    btn6 = InlineKeyboardButton("📢 إذاعة نشر", callback_data="adm_broadcast")
    btn7 = InlineKeyboardButton("🔒 فتح وقفل الأقسام", callback_data="adm_sections")
    btn8 = InlineKeyboardButton("🚫 تقييد/فك تقييد عضو", callback_data="adm_ban_user")
    btn9 = InlineKeyboardButton("💰 كشف رصيد مستخدم", callback_data="adm_check_user")
    btn10 = InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main")
    
    markup.row(btn1, btn2)
    markup.row(btn3, btn4)
    markup.row(btn5, btn6)
    markup.row(btn7, btn8)
    markup.row(btn9)
    markup.row(btn10)
    return markup

# ==================== 4. المعالجات والأوامر ====================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or "المستخدم"
    
    if is_user_banned(user_id):
        bot.send_message(message.chat.id, "🚫 عذراً، لقد تم حظرك من استخدام هذا البوت بواسطة الإدارة.")
        return
        
    user_data = get_or_create_user(user_id, name)
    balance = user_data[2]
    
    text = (f"💠 أهلاً بك عزيزي في بوت (NUMBER SMS) 💠\n\n"
            f"👤 حسابك: {name}\n"
            f"💰 رصيدك الحالي: ${balance:.2f}\n\n"
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

    back_markup = InlineKeyboardMarkup()
    back_markup.add(InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_main"))

    if call.data == "back_main":
        user_data = get_or_create_user(user_id, call.from_user.first_name)
        text = (f"💠 أهلاً بك عزيزي في بوت (NUMBER SMS) 💠\n\n"
                f"👤 حسابك: {call.from_user.first_name}\n"
                f"💰 رصيدك الحالي: ${user_data[2]:.2f}\n\n"
                f"📌 استخدم الأزرار بالأسفل لتنفيذ طلباتك:")
        bot.edit_message_text(text, chat_id, message_id, reply_markup=main_keyboard(user_id))

    elif call.data == "my_account":
        user_data = get_or_create_user(user_id, call.from_user.first_name)
        text = f"👤 **معلومات حسابك الشخصي:**\n\n🆔 الأيدي: `{user_id}`\n💰 الرصيد: ${user_data[2]:.2f}"
        bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=back_markup)

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
        bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=back_markup)

    elif call.data == "recharge":
        text = "💳 **شحن الرصيد:**\nلشحن رصيدك، يرجى التواصل مع الإدارة أو تحويل المبلغ وإرسال إيصال التحويل للدعم."
        bot.edit_message_text(text, chat_id, message_id, reply_markup=back_markup)

    elif call.data == "support":
        text = "🎧 **الدعم الفني:**\nلأي مشكلة أو استفسار، تواصل معنا عبر معرف الإدارة الأساسي."
        bot.edit_message_text(text, chat_id, message_id, reply_markup=back_markup)

    # ==================== لوحة التحكم الإدارية ====================
    elif call.data == "admin_panel":
        if str(user_id) == str(ADMIN_ID):
            bot.edit_message_text("⚙️ **أهلاً بك في لوحة الإدارة الكبرى:**\nاختر العملية المطلوبة:", chat_id, message_id, reply_markup=admin_keyboard(), parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "عفواً، هذه اللوحة للمشرفين فقط!", show_alert=True)

    elif call.data == "adm_add_bal":
        msg = bot.send_message(chat_id, "➕ أرسل أيدي المستخدم والمبلغ المراد إضافته بالشكل التالي:\n`أيدي_المستخدم المبلغ`\nمثال:\n`6113734300 10`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_admin_add_balance)

    elif call.data == "adm_sub_bal":
        msg = bot.send_message(chat_id, "⛔ أرسل أيدي المستخدم والمبلغ المراد خصمه بالشكل التالي:\n`أيدي_المستخدم المبلغ`\nمثال:\n`6113734300 5`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_admin_sub_balance)

    elif call.data == "adm_add_service":
        msg = bot.send_message(chat_id, "➕ أرسل اسم الدولة أو الخدمة مع السعر بالشكل التالي:\n`اسم_الدولة السعر`\nمثال:\n`واتساب_أمريكي 1.5`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_admin_add_service)

    elif call.data == "adm_users_count":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        count = cursor.fetchone()[0]
        conn.close()
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 رجوع للإدارة", callback_data="admin_panel"))
        bot.edit_message_text(f"📊 إحصائيات البوت:\n👥 إجمالي عدد المشتركين المسجلين: `{count}` مستخدم", chat_id, message_id, parse_mode="Markdown", reply_markup=markup)

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

# ==================== دوال تنفيذ عمليات الأدمن ====================
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
        try:
            bot.send_message(target_id, f"🎉 تمت إضافة ${amount} إلى رصيدك بواسطة الإدارة.")
        except:
            pass
    except:
        bot.send_message(message.chat.id, "❌ خطأ في الإدخال. تأكد من كتابة الأيدي والمبلغ بشكل صحيح.")

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
        bot.send_message(message.chat.id, f"✅ تم خصم ${amount} بنجاح من رصيد المستخدم `{target_id}`", parse_mode="Markdown")
    except:
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
    except:
        bot.send_message(message.chat.id, "❌ خطأ في الصيغة. مثال: `واتساب_أمريكي 1.5`", parse_mode="Markdown")

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
            bot.send_message(u[0], f"📢 **إعلان إداري:**\n\n{text_to_send}", parse_mode="Markdown")
            success += 1
        except:
            pass
    bot.send_message(message.chat.id, f"✅ تم إرسال الإذاعة بنجاح إلى `{success}` مستخدم.")

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
            bot.send_message(message.chat.id, f"✅ تم تغيير حالة المستخدم `{target_id}` إلى: **{status_text}**", parse_mode="Markdown")
        else:
            conn.close()
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود في قاعدة البيانات.")
    except:
        bot.send_message(message.chat.id, "❌ أيدي غير صالح.")

def process_check_user(message):
    try:
        target_id = int(message.text.strip())
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT name, balance, is_banned FROM users WHERE user_id = ?', (target_id,))
        user = cursor.fetchone()
        conn.close()
        if user:
            ban_str = "نعم 🚫" if user[2] == 1 else "لا ✅"
            bot.send_message(message.chat.id, f"👤 **معلومات المستخدم:**\n\n🆔 الأيدي: `{target_id}`\n🏷️ الاسم: {user[0]}\n💰 الرصيد: ${user[1]:.2f}\n⛔ محظور: {ban_str}", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "❌ المستخدم غير مسجل في البوت.")
    except:
        bot.send_message(message.chat.id, "❌ أيدي غير صالح.")

bot.infinity_polling()
