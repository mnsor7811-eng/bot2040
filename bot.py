import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3

# ==================== 1. الإعدادات ====================
TOKEN = '8927305428:AAHlCPINlpyeymiPL7WnxxZtjufvZxd6--Y'
ADMIN_ID = 6113734300

bot = telebot.TeleBot(TOKEN)

# ==================== 2. قاعدة البيانات ====================
def setup_db():
    conn = sqlite3.connect('users_data.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        name TEXT,
                        balance REAL DEFAULT 0.0
                    )''')
    conn.commit()
    conn.close()

setup_db()

def get_or_create_user(user_id, name):
    conn = sqlite3.connect('users_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute('INSERT INTO users (user_id, name, balance) VALUES (?, ?, 0.0)', (user_id, name))
        conn.commit()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
    conn.close()
    return user

def get_total_users():
    conn = sqlite3.connect('users_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    count = cursor.fetchone()[0]
    conn.close()
    return count

def add_user_balance(target_id, amount):
    conn = sqlite3.connect('users_data.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, target_id))
    conn.commit()
    conn.close()

# ==================== 3. لوحات التحكم والبرمجية ====================
def main_keyboard(user_id):
    markup = InlineKeyboardMarkup()
    btn_deposit = InlineKeyboardButton("💳 شحن رصيد (Binance)", callback_data="deposit")
    btn_buy = InlineKeyboardButton("📱 شراء أرقام", callback_data="buy_numbers")
    btn_account = InlineKeyboardButton("👤 حسابي", callback_data="my_account")
    
    markup.row(btn_deposit, btn_buy)
    markup.row(btn_account)
    
    # إظهار زر لوحة الإدارة فقط للأدمن صاحب الأيدي المحدد
    if str(user_id) == str(ADMIN_ID):
        btn_admin = InlineKeyboardButton("⚙️ لوحة الإدارة", callback_data="admin_panel")
        markup.row(btn_admin)
        
    return markup

def admin_keyboard():
    markup = InlineKeyboardMarkup()
    btn_stats = InlineKeyboardButton("📊 إحصائيات المستخدمين", callback_data="admin_stats")
    btn_add_bal = InlineKeyboardButton("➕ إضافة رصيد لمستخدم", callback_data="admin_add_bal")
    btn_back = InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main")
    
    markup.row(btn_stats)
    markup.row(btn_add_bal)
    markup.row(btn_back)
    return markup

# ==================== 4. الأوامر والاستجابات ====================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or "المستخدم"
    user_data = get_or_create_user(user_id, name)
    balance = user_data[2]
    
    text = f"مرحباً بك يا {name}!\n\n💰 رصيدك الحالي: ${balance:.2f}\n👇 اختر الخدمة التي تريدها:"
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard(user_id))

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    try:
        bot.answer_callback_query(call.id)
    except:
        pass

    if call.data == "back_main":
        user_data = get_or_create_user(user_id, call.from_user.first_name)
        balance = user_data[2]
        text = f"مرحباً بك يا {call.from_user.first_name}!\n\n💰 رصيدك الحالي: ${balance:.2f}\n👇 اختر الخدمة التي تريدها:"
        bot.edit_message_text(text, chat_id, message_id, reply_markup=main_keyboard(user_id))

    elif call.data == "my_account":
        user_data = get_or_create_user(user_id, call.from_user.first_name)
        text = f"معلومات حسابك:\n🆔 الأيدي: `{user_id}`\n💰 الرصيد: ${user_data[2]:.2f}"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_main"))
        bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=markup)

    elif call.data == "deposit":
        text = "لشحن رصيدك عبر Binance P2P أو Pay، يرجى التواصل مع الإدارة مباشرة."
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_main"))
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)

    elif call.data == "buy_numbers":
        text = "🌐 جاري الاتصال بمزود الأرقام...\nلا توجد أرقام متوفرة حالياً، يرجى المحاولة لاحقاً."
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_main"))
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)

    elif call.data == "admin_panel":
        if str(user_id) == str(ADMIN_ID):
            text = "⚙️ أهلاً بك في لوحة تحكم الإدارة:\nاختر من الخيارات أدناه ما تريد القيام به:"
            bot.edit_message_text(text, chat_id, message_id, reply_markup=admin_keyboard())
        else:
            bot.send_message(chat_id, "❌ عفواً، هذه اللوحة مخصصة للأدمن فقط.")

    elif call.data == "admin_stats":
        if str(user_id) == str(ADMIN_ID):
            total_users = get_total_users()
            text = f"📊 **إحصائيات البوت:**\n\n👥 إجمالي عدد المسجلين: {total_users} مستخدم"
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔙 رجوع للوحة الإدارة", callback_data="admin_panel"))
            bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=markup)

    elif call.data == "admin_add_bal":
        if str(user_id) == str(ADMIN_ID):
            msg = bot.send_message(chat_id, "أرسل أيدي المستخدم والمبلغ بالشكل التالي:\n`الأيدي المبلغ`\nمثال:\n`6113734300 10`", parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_add_balance)

def process_add_balance(message):
    try:
        data = message.text.split()
        target_id = int(data[0])
        amount = float(data[1])
        add_user_balance(target_id, amount)
        bot.send_message(message.chat.id, f"✅ تم إضافة ${amount} إلى حساب المستخدم `{target_id}` بنجاح!", parse_mode="Markdown")
        try:
            bot.send_message(target_id, f"🎉 تم إضافة ${amount} إلى رصيدك بواسطة الإدارة!")
        except:
            pass
    except Exception:
        bot.send_message(message.chat.id, "❌ صيغة خاطئة! يرجى إرسال الأيدي ثم مسافة ثم المبلغ.")

bot.infinity_polling()
