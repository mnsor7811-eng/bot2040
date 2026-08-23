import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3

# ================= 1. الإعدادات =================
TOKEN = '8927305428:AAHlCPINlpyeymiPL7WnxxZtjufvZxd6--Y'
ADMIN_ID = 6113734300  # 

bot = telebot.TeleBot(TOKEN)

# ================= 2. قاعدة البيانات =================
def setup_db():
    conn = sqlite3.connect('users_data.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users
                      (user_id INTEGER PRIMARY KEY, name TEXT, balance REAL)''')
    conn.commit()
    conn.close()

def get_or_create_user(user_id, name):
    conn = sqlite3.connect('users_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    if result is None:
        cursor.execute("INSERT INTO users (user_id, name, balance) VALUES (?, ?, ?)", (user_id, name, 0.0))
        conn.commit()
        balance = 0.0
    else:
        balance = result[0]
    conn.close()
    return balance

# ================= 3. الأوامر والقوائم =================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    balance = get_or_create_user(user_id, name)
    
    markup = InlineKeyboardMarkup(row_width=2)
    btn_numbers = InlineKeyboardButton("📱 شراء أرقام", callback_data="buy_numbers")
    btn_binance = InlineKeyboardButton("💳 شحن رصيد (Binance)", callback_data="add_funds")
    btn_account = InlineKeyboardButton("👤 حسابي", callback_data="my_account")
    
    markup.add(btn_numbers, btn_binance, btn_account)
    
    if user_id == ADMIN_ID:
        btn_admin = InlineKeyboardButton("⚙️ لوحة الإدارة", callback_data="admin_panel")
        markup.add(btn_admin)

    text = f"مرحباً بك يا {name}!\n\nرصيدك الحالي: {balance}$ 💰\nاختر الخدمة التي تريدها 👇"
    bot.reply_to(message, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    user_id = call.from_user.id
    if call.data == "buy_numbers":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🌐 جاري الاتصال بمزود الأرقام...")
    elif call.data == "add_funds":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "لشحن رصيدك عبر Binance P2P أو Pay، تواصل مع الإدارة.")
    elif call.data == "my_account":
        balance = get_or_create_user(user_id, call.from_user.first_name)
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"معلومات حسابك:\nالأيدي: `{user_id}`\nالرصيد: {balance}$")

# ================= 4. التشغيل =================
if __name__ == '__main__':
    setup_db()
    bot.infinity_polling()
