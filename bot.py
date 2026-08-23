import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3

# ==================== 1. الإعدادات ====================
TOKEN = ' 8927305428:AAHlCPINlpyeymiPL7WnxxZtjufvZxd6--Y'
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

# ==================== 3. الواجهة والأزرار المتكاملة ====================
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
    
    # لوحة الإدارة تظهر للأدمن فقط
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
        text = "📞 **قسم شراء الأرقام الافتراضية:**\nاختر الدولة أو التطبيق المطلوب من القائمة أدناه (قريباً سيتم توفير الأرقام)."
        bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=back_markup)

    elif call.data == "wa_offers":
        text = "🟢 **عروض أرقام واتساب:**\nأرقام مميزة ونظيفة لتفعيل الواتساب متوفرة عبر الإدارة."
        bot.edit_message_text(text, chat_id, message_id, reply_markup=back_markup)

    elif call.data == "tg_ready":
        text = "🔵 **حسابات وتليجرام جاهزة:**\nحسابات تيليجرام قديمة وموثقة وجاهزة للاستخدام."
        bot.edit_message_text(text, chat_id, message_id, reply_markup=back_markup)

    elif call.data == "recharge":
        text = "💳 **شحن الرصيد:**\nلشحن رصيدك عبر Binance Pay أو تحويل رصيد، يرجى التواصل مع الدعم أو الإدارة."
        bot.edit_message_text(text, chat_id, message_id, reply_markup=back_markup)

    elif call.data == "support":
        text = "🎧 **الدعم الفني:**\nلأي مشكلة أو استفسار، تواصل معنا مباشرة عبر الإدارة."
        bot.edit_message_text(text, chat_id, message_id, reply_markup=back_markup)

    elif call.data == "admin_panel":
        if str(user_id) == str(ADMIN_ID):
            text = "⚙️ أهلاً بك في لوحة تحكم الإدارة:"
            bot.edit_message_text(text, chat_id, message_id, reply_markup=admin_keyboard())
        else:
            bot.answer_callback_query(call.id, "عفواً، هذه اللوحة للمشرفين فقط!", show_alert=True)

    elif call.data == "admin_stats":
        if str(user_id) == str(ADMIN_ID):
            total_users = get_total_users()
            text = f"📊 إحصائيات البوت:\n👥 إجمالي المستخدمين: {total_users}"
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔙 رجوع للوحة الإدارة", callback_data="admin_panel"))
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)

    elif call.data == "admin_add_bal":
        if str(user_id) == str(ADMIN_ID):
            msg = bot.send_message(chat_id, "أرسل أيدي المستخدم والمبْلغ هكذا:\n`الأيدي المبلغ`\nمثال:\n`6113734300 15`", parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_add_balance)
    else:
        bot.edit_message_text("🚧 هذا القسم تحت التحديث وسيتم تفعيله قريباً.", chat_id, message_id, reply_markup=back_markup)

def process_add_balance(message):
    try:
        data = message.text.split()
        target_id = int(data[0])
        amount = float(data[1])
        add_user_balance(target_id, amount)
        bot.send_message(message.chat.id, f"✅ تم إضافة ${amount} بنجاح إلى الأيدي `{target_id}`", parse_mode="Markdown")
        try:
            bot.send_message(target_id, f"🎉 مبروك! تمت إضافة ${amount} إلى رصيدك من قبل الإدارة.")
        except:
            pass
    except:
        bot.send_message(message.chat.id, "❌ خطأ في الصيغة! أرسل الأيدي ثم مسافة ثم المبلغ بشكل صحيح.")

bot.infinity_polling()
