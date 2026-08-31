import time
import datetime
import requests
import sqlite3
import hmac
import hashlib
from urllib.parse import urlencode

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand

from config import (
    TOKEN, ADMIN_ID, ADMIN_USERNAME, REWARD_PER_INVITE, MIN_TRANSFER_AMOUNT, 
    DEFAULT_PRICE, PAYMENT_DETAILS, SERVERS, USER_STEPS, ai_model,
    get_db, get_or_create_user, is_user_banned, fetch_server_prices, 
    grizzly_request, get_clean_country_info
)

from keyboards import (
    main_keyboard, back_button, admin_back_button, recharge_keyboard,
    servers_keyboard, services_keyboard, countries_keyboard_fast,
    active_number_keyboard, smm_main_keyboard, games_keyboard, boost_keyboard,
    dynamic_smm_keyboard, smm_detail_grid_keyboard, smm_cancel_link_keyboard,
    smm_confirm_keyboard, smm_order_status_keyboard, translate_text
)

bot = telebot.TeleBot(TOKEN)

# ==================== حل مشكلة تعارض الويب هوك (خطأ 409) ====================
try:
    bot.remove_webhook()
    print("تم حذف الويب هوك القديم بنجاح.")
except Exception as e:
    print(f"حدث خطأ أثناء حذف الويب هوك: {e}")

# ==================== إعدادات بايننس باي (Binance Pay) ====================
BINANCE_PAY_ID = "979808293"
API_KEY = "Q2BSm09k0oVAaSwlWK415h9EfMHKnwwDYZEr9wSGXhnSJN2amXgJBYMa0COSM7QN"
SECRET_KEY = "Ld01qxgadxLjYKosPjFOANXTD7x6CM1GHWX3RpbC32kqqmlzvlApGMiR5ILBteCQ"

def get_binance_signature(query_string, secret_key):
    return hmac.new(
        secret_key.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def verify_binance_txid(txid, expected_amount):
    url = "https://api.binance.com/sapi/v1/pay/transactions"
    timestamp = int(time.time() * 1000)
    params = {"timestamp": timestamp, "txId": txid}
    query_string = urlencode(params)
    signature = get_binance_signature(query_string, SECRET_KEY)
    headers = {"X-MBX-APIKEY": API_KEY}
    full_url = f"{url}?{query_string}&signature={signature}"

    try:
        response = requests.get(full_url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                tx_info = data["data"][0]
                tx_amount = float(tx_info.get("amount", 0))
                if tx_amount >= float(expected_amount):
                    return True
        return False
    except Exception as e:
        print(f"Error checking transaction: {e}")
        return False

# ==================== تعيين قائمة الأوامر (Menu Commands) ====================
def set_bot_commands():
    commands = [
        BotCommand("num", "🏡 القائمة الرئيسية"),
        BotCommand("ai", "🤖 اشتراكات برامج AI"),
        BotCommand("buynum", "📞 شراء رقم افتراضي"),
        BotCommand("whats", "🟢 عروض WhatsApp"),
        BotCommand("tele", "🔵 جاهز Telegram"),
        BotCommand("best", "🔥 السيرفرات الأكثر مبيعاً"),
        BotCommand("more", "🎲 الأكثر توفراً"),
        BotCommand("recharge", "🎳 شحن الرصيد / الاشتراكات"),
        BotCommand("smm", "🚀 الرشق وشحـن الألعاب والبرامج"),
        BotCommand("free", "💎 اربح رصيد مجاناً"),
        BotCommand("transfer", "🔄 تحويل الرصيد"),
        BotCommand("support", "🎧 الدعم"),
        BotCommand("mart", "✔ إحصائيات الشراء الناجح"),
        BotCommand("account", "👤 حسابي"),
        BotCommand("other", "🛸 خدمات وميزات أخرى"),
        BotCommand("admin", "⚙️ لوحة الإدارة الكبرى")
    ]
    try:
        bot.set_my_commands(commands)
    except Exception as e:
        print(f"Error setting commands: {e}")

# ==================== إعدادات قاعدة البيانات ====================
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                username TEXT,
                balance REAL DEFAULT 0.0,
                ai_balance INTEGER DEFAULT 5,
                is_banned INTEGER DEFAULT 0,
                referred_by INTEGER DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                tz_id TEXT,
                phone TEXT,
                service TEXT,
                cost REAL,
                country_code TEXT,
                status TEXT DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS smm_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT,
                user_id INTEGER,
                service_id TEXT,
                service_name TEXT,
                category_name TEXT,
                link TEXT,
                quantity INTEGER,
                cost REAL,
                status TEXT DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
    finally:
        conn.close()

init_db()

# ==================== إعدادات API سيرفر الرشق (SMM Server 2) ====================
SMM_SERVERS = {
    '2': {
        'url': 'https://smmxstar.com/api/v2',
        'key': '13cb06a01b5a7259c14c1727c2f5591d'
    }
}

SMM_SERVICES_CACHE = {}
SMM_CACHE_TIME = {}

def smm_request(server_id, action, **kwargs):
    srv = SMM_SERVERS.get(str(server_id), SMM_SERVERS['2'])
    payload = {'key': srv['key'], 'action': action}
    payload.update(kwargs)
    try:
        response = requests.post(srv['url'], data=payload, timeout=12)
        return response.json()
    except Exception as e:
        print(f"SMM API Error ({server_id}): {e}")
        return None

def get_cached_smm_services(server_id='2'):
    global SMM_SERVICES_CACHE, SMM_CACHE_TIME
    server_id = str(server_id)
    now = time.time()

    if server_id in SMM_SERVICES_CACHE and (now - SMM_CACHE_TIME.get(server_id, 0) < 300):
        return SMM_SERVICES_CACHE[server_id]

    data = smm_request(server_id, 'services')
    if data and isinstance(data, list):
        SMM_SERVICES_CACHE[server_id] = data
        SMM_CACHE_TIME[server_id] = now
        return data
    return []

CATEGORY_TITLES = {
    'telegram': 'رشق تيليجرام . telegram',
    'instagram': 'رشق انستا . instagram',
    'youtube': 'رشق يوتيوب . youtube',
    'twitter': 'رشق تويتر . twitter',
    'facebook': 'رشق فيسبوك . facebook',
    'tiktok': 'رشق تيك توك . tiktok',
    'threads': 'رشق ثريدز . threads',
    'whatsapp': 'واتس اب . whatsapp',
    'others': 'خدمات اخرى . other services'
}

def filter_smm_services(target_type, server_id='2'):
    services = get_cached_smm_services(server_id)
    filtered = []

    arabic_keywords = {
        'telegram': ['تيليجرام', 'تليجرام', 'تلي', 'telegram', 'tg'],
        'instagram': ['انستقرام', 'انستجرام', 'انستا', 'instagram', 'ig'],
        'youtube': ['يوتيوب', 'youtube', 'yt'],
        'twitter': ['تويتر', 'إكس', 'twitter', 'x'],
        'facebook': ['فيسبوك', 'فيس بوك', 'facebook', 'fb'],
        'tiktok': ['تيك توك', 'تيك', 'tiktok'],
        'threads': ['ثريدز', 'threads'],
        'whatsapp': ['واتساب', 'واتس', 'whatsapp', 'wa'],
        'others': []
    }

    keys = arabic_keywords.get(target_type, [])

    for srv in services:
        name = str(srv.get('name', '')).lower()
        category = str(srv.get('category', '')).lower()
        combined_text = f"{name} {category}"

        if target_type == 'others':
            all_main_keys = [k for sublist in arabic_keywords.values() for k in sublist]
            if not any(k in combined_text for k in all_main_keys):
                filtered.append(srv)
        else:
            if any(k in combined_text for k in keys):
                filtered.append(srv)

    return filtered

def get_arabic_datetime():
    days_ar = {
        'Monday': 'الاثنين', 'Tuesday': 'الثلاثاء', 'Wednesday': 'الأربعاء',
        'Thursday': 'الخميس', 'Friday': 'الجمعة', 'Saturday': 'السبت', 'Sunday': 'الأحد'
    }
    months_ar = {
        1: 'يناير', 2: 'فبراير', 3: 'مارس', 4: 'أبريل', 5: 'مايو', 6: 'يونيو',
        7: 'يوليو', 8: 'أغسطس', 9: 'سبتمبر', 10: 'أكتوبر', 11: 'نوفمبر', 12: 'ديسمبر'
    }
    now = datetime.datetime.now()
    day_name = days_ar.get(now.strftime('%A'), now.strftime('%A'))
    month_name = months_ar.get(now.month, str(now.month))
    hour_12 = now.strftime('%I:%M').lstrip('0')
    period = 'م' if now.strftime('%p') == 'PM' else 'ص'
    return f"{day_name}، {now.day} {month_name} {hour_12} {period}"

# ==================== أوامر البدء ====================
@bot.message_handler(commands=['start', 'num'])
def start_cmd(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or "المستخدم"
    username = f"@{message.from_user.username}" if message.from_user.username else "لا يوجد"

    if is_user_banned(user_id):
        bot.send_message(message.chat.id, "🚫 عذراً، لقد تم حظرك من استخدام هذا البوت بواسطة الإدارة.")
        return

    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None

    conn = get_db()
    cursor = conn.cursor()

    try:
        try: cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
        except Exception: pass

        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()

        if not user:
            ref_id = referrer_id if (referrer_id and referrer_id != user_id) else 0
            cursor.execute('INSERT INTO users (user_id, name, username, balance, ai_balance, is_banned, referred_by) VALUES (?, ?, ?, 0.0, 5, 0, ?)', 
                           (user_id, name, username, ref_id))
            conn.commit()

            if ref_id != 0:
                cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (REWARD_PER_INVITE, ref_id))
                conn.commit()
                try:
                    bot.send_message(ref_id, f"🎉 قام شخص جديد بالانضمام عبر رابطك!\n🎁 تم إضافة ${REWARD_PER_INVITE:.2f} إلى رصيدك بنجاح.")
                except Exception:
                    pass
        else:
            cursor.execute('UPDATE users SET name = ?, username = ? WHERE user_id = ?', (name, username, user_id))
            conn.commit()
    finally:
        conn.close()

    user_data = get_or_create_user(user_id, name)
    try: balance = float(user_data[2]) if user_data[2] is not None else 0.0
    except: balance = 0.0

    try: ai_bal = int(user_data[3]) if user_data[3] is not None else 5
    except: ai_bal = 5

    text = (f"💠 أهلاً بك عزيزي في البوت الشامل 💠\n\n"
            f"👤 حسابك: {ADMIN_USERNAME}\n"
            f"💰 رصيدك الحالي: ${balance:.2f}\n"
            f"🤖 رصيد أسئلة الذكاء: {ai_bal} سؤال\n\n"
            f"📌 استخدم الأزرار بالأسفل لتنفيذ طلباتك:")
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard(user_id))

@bot.message_handler(commands=['ai'])
def ai_cmd(message):
    bot.send_message(message.chat.id, "🤖 قسم خدمات واشتراكات الذكاء الاصطناعي\n\nاطرح سؤالك مباشرة في المحادثة وسيجيبك البوت.", reply_markup=back_button())

@bot.message_handler(commands=['buynum'])
def buynum_cmd(message):
    bot.send_message(message.chat.id, "📞 قسم شراء الأرقام الافتراضية\n\nاختر السيرفر المناسب لك:", reply_markup=servers_keyboard())

@bot.message_handler(commands=['whats'])
def whats_cmd(message):
    markup = countries_keyboard_fast("grizzly", "wa", page=0)
    bot.send_message(message.chat.id, "🟢 عروض WhatsApp المتاحة:", reply_markup=markup)

@bot.message_handler(commands=['tele'])
def tele_cmd(message):
    markup = countries_keyboard_fast("grizzly", "tg", page=0)
    bot.send_message(message.chat.id, "🔵 جاهز Telegram المتاح:", reply_markup=markup)

@bot.message_handler(commands=['best'])
def best_cmd(message):
    bot.send_message(message.chat.id, "🔥 السيرفرات الأكثر مبيعاً: Grizzly SMS", reply_markup=back_button())

@bot.message_handler(commands=['more'])
def more_cmd(message):
    bot.send_message(message.chat.id, "🎲 الأرقام الأكثر توفراً حالياً: روسيا، نيجيريا، وأوكرانيا.", reply_markup=back_button())

@bot.message_handler(commands=['recharge'])
def recharge_cmd(message):
    bot.send_message(message.chat.id, "🎳 شحن الرصيد / الاشتراكات\n\nاختر وسيلة الدفع التي تناسبك:", reply_markup=recharge_keyboard())

@bot.message_handler(commands=['smm'])
def smm_cmd(message):
    bot.send_message(message.chat.id, "🚀 الرشق وشحـن الألعاب والبرامج 🔭\n▫️ زيادة متابعين وتفاعلات\n▫️ شحن الألعاب المختلفة", reply_markup=smm_main_keyboard())

@bot.message_handler(commands=['free'])
def free_cmd(message):
    user_id = message.from_user.id
    bot_info = bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,))
        invite_count = cursor.fetchone()[0]
    finally:
        conn.close()

    earned_total = invite_count * REWARD_PER_INVITE
    bot.send_message(message.chat.id, f"💎 نظام اربح رصيد مجاناً 💎\n\nرابط إحالتك:\n`{ref_link}`\n👥 المدعوين: {invite_count}\n💵 إجمالي الأرباح: ${earned_total:.2f}", parse_mode="Markdown", reply_markup=back_button())

@bot.message_handler(commands=['transfer'])
def transfer_cmd(message):
    user_id = message.from_user.id
    USER_STEPS[user_id] = {'step': 'TRANSFER_TARGET'}
    text = ("🔄 قسم تحويل الرصيد بين الحسابات\n\n✨ الميزات: عمولة 0%\n💵 أقل مبلغ: $1.00\n\n📌 يرجى إرسال آيدي (User ID) الشخص المستلم الآن:")
    bot.send_message(message.chat.id, text, reply_markup=back_button())

@bot.message_handler(commands=['support'])
def support_cmd(message):
    bot.send_message(message.chat.id, f"🎧 الدعم الفني: {ADMIN_USERNAME}", reply_markup=back_button())

@bot.message_handler(commands=['mart'])
def mart_cmd(message):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM purchases")
        count = cursor.fetchone()[0]
    finally:
        conn.close()
    bot.send_message(message.chat.id, f"✔ إحصائيات الشراء الناجح لهذا اليوم: تم تنفيذ أكثر من {count + 50} عملية بنجاح.", reply_markup=back_button())

@bot.message_handler(commands=['account'])
def account_cmd(message):
    user_id = message.from_user.id
    user_data = get_or_create_user(user_id, message.from_user.first_name)
    try: balance = float(user_data[2]) if user_data[2] is not None else 0.0
    except: balance = 0.0
    try: ai_bal = int(user_data[3]) if user_data[3] is not None else 5
    except: ai_bal = 5

    msg = f"👤 حسابك:\n🆔: `{user_data[0]}`\n💰 الرصيد: ${balance:.2f}\n🤖 رصيد AI: {ai_bal}"
    bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=back_button())

@bot.message_handler(commands=['other'])
def other_cmd(message):
    bot.send_message(message.chat.id, "🛸 خدمات وميزات أخرى قادمة قريباً.", reply_markup=back_button())

@bot.message_handler(commands=['admin'])
def admin_cmd(message):
    user_id = message.from_user.id
    if str(user_id) != str(ADMIN_ID):
        bot.send_message(message.chat.id, f"❌ عذراً، هذه اللوحة للمشرف فقط. آيديك: {user_id}")
        return

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats"), InlineKeyboardButton("🔍 البحث عن مستخدم", callback_data="admin_search_user"))
    markup.row(InlineKeyboardButton("📋 عرض أحدث المستخدمين", callback_data="admin_recent_users"))
    markup.row(InlineKeyboardButton("💰 إضافة رصيد (بالآيدي)", callback_data="admin_add_balance"), InlineKeyboardButton("➖ خصم رصيد (بالآيدي)", callback_data="admin_deduct_balance"))
    markup.row(InlineKeyboardButton("🤖 شحن أسئلة AI", callback_data="admin_add_ai"), InlineKeyboardButton("🚫 حظر / فك حظر", callback_data="admin_ban_menu"))
    markup.row(InlineKeyboardButton("📢 إرسال رسالة للجميع (إذاعة)", callback_data="admin_broadcast"))
    markup.row(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))

    bot.send_message(message.chat.id, "⚙️ **أهلاً بك في لوحة الإدارة الكبرى**\n\nاختر العملية التي تريد تنفيذها:", parse_mode="Markdown", reply_markup=markup)

# ==================== معالجة الأزرار (Callbacks) ====================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if call.data == "ignore":
        try: bot.answer_callback_query(call.id)
        except: pass
        return

    if is_user_banned(user_id) and str(user_id) != str(ADMIN_ID):
        bot.send_message(chat_id, "أنت محظور من استخدام البوت.")
        return

    if call.data == "admin_panel":
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, f"❌ عذراً، هذه اللوحة للمشرف فقط. آيديك: {user_id}", show_alert=True)
            return

        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats"), InlineKeyboardButton("🔍 البحث عن مستخدم", callback_data="admin_search_user"))
        markup.row(InlineKeyboardButton("📋 عرض أحدث المستخدمين", callback_data="admin_recent_users"))
        markup.row(InlineKeyboardButton("💰 إضافة رصيد (بالآيدي)", callback_data="admin_add_balance"), InlineKeyboardButton("➖ خصم رصيد (بالآيدي)", callback_data="admin_deduct_balance"))
        markup.row(InlineKeyboardButton("🤖 شحن أسئلة AI", callback_data="admin_add_ai"), InlineKeyboardButton("🚫 حظر / فك حظر", callback_data="admin_ban_menu"))
        markup.row(InlineKeyboardButton("📢 إرسال رسالة للجميع (إذاعة)", callback_data="admin_broadcast"))
        markup.row(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))

        try: bot.edit_message_text("⚙️ **أهلاً بك في لوحة الإدارة الكبرى**\n\nاختر العملية التي تريد تنفيذها:", chat_id, message_id, parse_mode="Markdown", reply_markup=markup)
        except Exception: bot.send_message(chat_id, "⚙️ **أهلاً بك في لوحة الإدارة الكبرى**\n\nاختر العملية التي تريد تنفيذها:", parse_mode="Markdown", reply_markup=markup)
        return

    elif call.data == "admin_stats":
        if str(user_id) != str(ADMIN_ID): return
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*), SUM(cost) FROM purchases")
            p_data = cursor.fetchone()
            total_purchases = p_data[0] or 0
            total_spent = p_data[1] or 0.0
        finally:
            conn.close()

        msg = (f"📊 **إحصائيات البوت الشاملة:**\n\n"
               f"👥 إجمالي المستخدمين: `{total_users}`\n"
               f"🛍️ إجمالي عمليات شراء الأرقام: `{total_purchases}`\n"
               f"💵 إجمالي مبالغ العمليات: `${total_spent:.2f}`")
        try: bot.edit_message_text(msg, chat_id, message_id, parse_mode="Markdown", reply_markup=admin_back_button())
        except Exception: bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data == "admin_search_user":
        if str(user_id) != str(ADMIN_ID): return
        USER_STEPS[user_id] = {'step': 'ADMIN_SEARCH_USER'}
        bot.send_message(chat_id, "🔍 أرسل اسم المستخدم أو المعرف (@username) أو الآيدي الخاص به للبحث عنه:", reply_markup=admin_back_button())
        return

    elif call.data == "admin_recent_users":
        if str(user_id) != str(ADMIN_ID): return
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT user_id, name, username, balance, ai_balance, is_banned FROM users ORDER BY rowid DESC LIMIT 10")
            users = cursor.fetchall()
        finally:
            conn.close()

        if not users:
            bot.send_message(chat_id, "❌ لا يوجد مستخدمين مسجلين حتى الآن.", reply_markup=admin_back_button())
            return
        bot.send_message(chat_id, "📋 قائمة أحدث 10 مستخدمين مسجلين:")
        for u in users:
            u_id, u_name, u_uname, u_bal, u_ai, u_ban = u
            status = "محظور 🚫" if u_ban == 1 else "نشط ✅"
            card_msg = (f"👤 الاسم: {u_name}\n🏷️ اليوزر: {u_uname}\n🆔 الآيدي: {u_id}\n💰 الرصيد: ${u_bal:.2f}\n🤖 أسئلة AI: {u_ai}\n📌 الحالة: {status}")
            mk = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("➕ شحن رصيد", callback_data=f"act_add_{u_id}"), InlineKeyboardButton("➖ خصم رصيد", callback_data=f"act_deduct_{u_id}"))
            mk.row(InlineKeyboardButton("🤖 شحن AI", callback_data=f"act_ai_{u_id}"), InlineKeyboardButton("🚫 حظر / فك", callback_data=f"act_ban_{u_id}"))
            bot.send_message(chat_id, card_msg, reply_markup=mk)
        return

    elif call.data.startswith("act_add_"):
        target_id = call.data.replace("act_add_", "")
        USER_STEPS[user_id] = {'step': 'ADMIN_ADD_BALANCE_DIRECT', 'target_id': target_id}
        bot.send_message(chat_id, f"💰 أرسل المبلغ المراد إضافته لحساب المستخدم (`{target_id}`):", parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data.startswith("act_deduct_"):
        target_id = call.data.replace("act_deduct_", "")
        USER_STEPS[user_id] = {'step': 'ADMIN_DEDUCT_BALANCE_DIRECT', 'target_id': target_id}
        bot.send_message(chat_id, f"➖ أرسل المبلغ المراد خصمه من حساب المستخدم (`{target_id}`):", parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data.startswith("act_ai_"):
        target_id = call.data.replace("act_ai_", "")
        USER_STEPS[user_id] = {'step': 'ADMIN_ADD_AI_DIRECT', 'target_id': target_id}
        bot.send_message(chat_id, f"🤖 أرسل عدد أسئلة الذكاء الاصطناعي لإضافتها للمستخدم (`{target_id}`):", parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data.startswith("act_ban_"):
        target_id = int(call.data.replace("act_ban_", ""))
        if target_id == ADMIN_ID: return
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (target_id,))
            res = cursor.fetchone()
            if res:
                new_status = 0 if res[0] == 1 else 1
                cursor.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (new_status, target_id))
                conn.commit()
                bot.send_message(chat_id, "🚫 تم الحظر." if new_status == 1 else "🟢 تم فك الحظر.", reply_markup=admin_back_button())
        finally:
            conn.close()
        return

    elif call.data == "admin_deduct_balance":
        if str(user_id) != str(ADMIN_ID): return
        USER_STEPS[user_id] = {'step': 'ADMIN_DEDUCT_BALANCE'}
        bot.send_message(chat_id, "➖ أرسل الآيدي والمبلغ المراد خصمه:\n`ID المبلغ`", parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data == "admin_add_ai":
        if str(user_id) != str(ADMIN_ID): return
        USER_STEPS[user_id] = {'step': 'ADMIN_ADD_AI'}
        bot.send_message(chat_id, "🤖 أرسل الآيدي وعدد الأسئلة:\n`ID العدد`", parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data == "admin_broadcast":
        if str(user_id) != str(ADMIN_ID): return
        USER_STEPS[user_id] = {'step': 'ADMIN_BROADCAST'}
        bot.send_message(chat_id, "📢 أرسل النص أو الوسائط التي تريد إذاعتها لجميع المستخدمين الآن:", reply_markup=admin_back_button())
        return

    elif call.data == "admin_add_balance":
        if str(user_id) != str(ADMIN_ID): return
        USER_STEPS[user_id] = {'step': 'ADMIN_ADD_BALANCE'}
        bot.send_message(chat_id, "💰 أرسل الآيدي والمبلغ:\n`ID المبلغ`", parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data == "admin_ban_menu":
        if str(user_id) != str(ADMIN_ID): return
        USER_STEPS[user_id] = {'step': 'ADMIN_BAN_USER'}
        bot.send_message(chat_id, "🚫 أرسل آيدي المستخدم المراد حظره أو إلغاء حظره:", reply_markup=admin_back_button())
        return

    elif call.data == "back_main":
        if user_id in USER_STEPS:
            del USER_STEPS[user_id]
        user_data = get_or_create_user(user_id, call.from_user.first_name)
        try: balance = float(user_data[2]) if user_data[2] is not None else 0.0
        except: balance = 0.0
        try: ai_bal = int(user_data[3]) if user_data[3] is not None else 5
        except: ai_bal = 5

        text = (f"💠 أهلاً بك عزيزي في البوت الشامل 💠\n\n👤 حسابك: {ADMIN_USERNAME}\n💰 رصيدك الحالي: ${balance:.2f}\n🤖 رصيد أسئلة الذكاء: {ai_bal} سؤال\n\n📌 استخدم الأزرار بالأسفل لتنفيذ طلباتك:")

        try: bot.edit_message_text(text, chat_id, message_id, reply_markup=main_keyboard(user_id))
        except Exception:
            try: bot.delete_message(chat_id, message_id)
            except Exception: pass
            bot.send_message(chat_id, text, reply_markup=main_keyboard(user_id))

    elif call.data == "deposit_binance" or call.data == "pay_binance":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="recharge_menu"))

        bot.send_message(
            chat_id,
            "🟡 **شحن رصيد عبر Binance (تلقائي)**\n\n"
            "⚠️ تنبيه مهم ‼️\n"
            "• هذه بوابة دفع تلقائية عبر Binance Pay.\n"
            "• سيتم إضافة الرصيد تلقائياً بعد التحقق من المعاملة.\n"
            "• تأكد من إدخال نفس المبلغ الذي اخترته عند التحويل.\n"
            "• لا تشارك TXID مع أي شخص آخر.\n\n"
            "💵 ارسل المبلغ الذي تريد شحنه (بالدولار USDT):\n"
            "مثال: 10",
            reply_markup=markup
        )
        USER_STEPS[user_id] = {"step": "waiting_binance_amount"}

    elif call.data == "enter_txid":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="recharge_menu"))

        bot.send_message(
            chat_id,
            "🟡 **أدخل TXID (رقم المعاملة)**\n\n"
            "⚠️ تأكد من:\n"
            "• إدخال TXID الصحيح من محفظتك.\n"
            "• أن المبلغ المرسل يساوي المبلغ الذي اخترته.\n"
            "• انتظر دقيقة بعد التحويل قبل إدخال TXID.\n\n"
            "أرسل TXID الآن:",
            reply_markup=markup
        )
        if user_id in USER_STEPS and "amount" in USER_STEPS[user_id]:
            USER_STEPS[user_id]["step"] = "waiting_binance_txid"
        else:
            USER_STEPS[user_id] = {"step": "waiting_binance_txid"}

    elif call.data == "copy_id":
        bot.answer_callback_query(call.id, text=f"Pay ID: {BINANCE_PAY_ID} (تم النسخ افتراضياً)")

    elif call.data == "recharge_menu":
        bot.answer_callback_query(call.id)
        if user_id in USER_STEPS:
            USER_STEPS.pop(user_id, None)
        try:
            bot.edit_message_text("🎳 شحن الرصيد / الاشتراكات\n\nاختر وسيلة الدفع التي تناسبك:", chat_id, message_id, reply_markup=recharge_keyboard())
        except Exception:
            bot.send_message(chat_id, "🎳 شحن الرصيد / الاشتراكات\n\nاختر وسيلة الدفع التي تناسبك:", reply_markup=recharge_keyboard())

    elif call.data.startswith("pay_"):
        pay_key = call.data.replace("pay_", "")
        pay_info = PAYMENT_DETAILS.get(pay_key)
        if pay_info:
            msg = (f"📌 تفاصيل الدفع عبر {pay_info['name']}\n\n🏷️ رقم الحساب: {pay_info['acc']}\n💵 أقل مبلغ: {pay_info['min']}\n💱 سعر الصرف: {pay_info['rate']}\n\n⚠️ حوّل المبلغ وأرسل صورة الإشعار مع الآيدي ({user_id}) للإدارة: {ADMIN_USERNAME}")
            back_markup = InlineKeyboardMarkup()
            back_markup.add(InlineKeyboardButton("🔙 العودة لوسائل الدفع", callback_data="recharge_menu"))
            try: bot.send_message(chat_id, msg, reply_markup=back_markup)
            except: pass

    elif call.data == "transfer":
        USER_STEPS[user_id] = {'step': 'TRANSFER_TARGET'}
        text = ("🔄 قسم تحويل الرصيد بين الحسابات\n\n✨ الميزات: عمولة 0%\n💵 أقل مبلغ: $1.00\n\n📌 يرجى إرسال آيدي (User ID) الشخص المستلم الآن:")
        bot.edit_message_text(text, chat_id, message_id, reply_markup=back_button())

    elif call.data == "buy_number":
        bot.edit_message_text("📞 قسم شراء الأرقام الافتراضية\n\nاختر السيرفر المناسب لك:", chat_id, message_id, reply_markup=servers_keyboard())

    elif call.data.startswith("select_server_"):
        server_id = call.data.split("_")[2]
        server_display_name = f"سيرفر الأرقام {server_id}" if str(server_id).isdigit() else f"سيرفر الأرقام {list(SERVERS.keys()).index(server_id) + 1 if server_id in SERVERS else '1'}"
        bot.edit_message_text(f"⚙️ تم اختيار: {server_display_name}\n\nاختر التطبيق المطلوب:", chat_id, message_id, reply_markup=services_keyboard(server_id))

    elif call.data.startswith("srv_app_"):
        _, _, server_id, srv_code = call.data.split("_")
        markup = countries_keyboard_fast(server_id, srv_code, page=0)
        bot.edit_message_text(f"🌐 اختر الدولة المطلوبة لـ ({srv_code.upper()}):", chat_id, message_id, reply_markup=markup)

    elif call.data.startswith("pg_"):
        _, server_id, srv_code, page = call.data.split("_")
        markup = countries_keyboard_fast(server_id, srv_code, page=int(page))
        try: bot.edit_message_text(f"🌐 اختر الدولة المطلوبة لـ ({srv_code.upper()}):", chat_id, message_id, reply_markup=markup)
        except: pass

    elif call.data.startswith("b_"):
        bot.answer_callback_query(call.id, "جاري طلب الرقم، يرجى الانتظار...")
        _, server_id, srv_code, country_code = call.data.split("_")
        prices = fetch_server_prices(server_id, srv_code)
        price = prices.get(str(country_code), DEFAULT_PRICE)

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
            balance = cursor.fetchone()[0]

            if balance < price:
                bot.send_message(chat_id, f"❌ رصيدك غير كافٍ!\nسعر هذا الرقم: ${price:.2f}\nرصيدك الحالي: ${balance:.2f}")
                return

            srv = SERVERS.get(server_id)
            res = grizzly_request({'action': 'getNumber', 'service': srv_code, 'country': country_code}, srv['api_key'], srv['url'])

            if "ACCESS_NUMBER" in res:
                parts = res.split(":")
                tz_id, raw_phone = parts[1], parts[2]
                formatted_phone = f"+{raw_phone}" if not raw_phone.startswith("+") else raw_phone
                c_name, c_flag = get_clean_country_info(country_code)

                cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (price, user_id))
                cursor.execute('INSERT INTO purchases (user_id, tz_id, phone, service, cost, country_code) VALUES (?, ?, ?, ?, ?, ?)',
                               (user_id, tz_id, formatted_phone, srv_code, price, country_code))
                conn.commit()

                msg = (f"🆔 **رقم الطلب** : `{tz_id}`\n🌐 **الدولة** : {c_name} {c_flag}\n📞 **الرقم** : `{formatted_phone}`\n"
                       f"📩 **الكود** : `قيد الانتظار... ⏳`\n🛍️ **التطبيق** : `{srv_code.upper()}`\n💵 **السعر** : `${price:.2f}`")
                bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=active_number_keyboard(tz_id, server_id))
            else:
                bot.send_message(chat_id, f"❌ لم يكتمل الطلب: الرد من السيرفر: {res}")
        finally:
            conn.close()

    elif call.data.startswith("check_sms_"):
        parts = call.data.split("_")
        server_id, tz_id = parts[2], parts[3]
        srv = SERVERS.get(server_id)
        res = grizzly_request({'action': 'getStatus', 'id': tz_id}, srv['api_key'], srv['url'])
        if "STATUS_OK" in res:
            code = res.split(":")[1]
            bot.send_message(chat_id, f"🎉 **تم استلام كود التفعيل بنجاح!**\n\n🔑 **الكود** : `{code}`", parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "⏳ لم يتم استلام الكود بعد. يرجى الانتظار...", show_alert=True)

    elif call.data.startswith("cancel_num_") or call.data.startswith("change_num_"):
        parts = call.data.split("_")
        action_type, server_id, tz_id = parts[0], parts[2], parts[3]
        srv = SERVERS.get(server_id)
        grizzly_request({'action': 'setStatus', 'status': '8', 'id': tz_id}, srv['api_key'], srv['url'])

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT cost, status, service, country_code FROM purchases WHERE tz_id = ?', (tz_id,))
            purchase = cursor.fetchone()

            if purchase and purchase[1] == 'PENDING':
                cost = purchase[0]
                cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (cost, user_id))
                cursor.execute('UPDATE purchases SET status = "CANCELLED" WHERE tz_id = ?', (tz_id,))
                conn.commit()

                if action_type == "change_num":
                    bot.edit_message_text(f"🔄 تم إلغاء الرقم وإعادة (${cost:.2f}).", chat_id, message_id)
                    bot.send_message(chat_id, "تم استرجاع الرصيد، يرجى طلب رقم جديد من القائمة.", reply_markup=back_button())
                else:
                    bot.edit_message_text(f"❌ تم إلغاء الرقم بنجاح وإعادة مبلغ (${cost:.2f}) إلى رصيدك.", chat_id, message_id, reply_markup=back_button())
            else:
                bot.answer_callback_query(call.id, "العملية ملغاة مسبقاً.", show_alert=True)
        finally:
            conn.close()

    # ==================== أقسام الرشق (SMM) ====================
    elif call.data == "smm_main":
        text = ("🚀 الرشق وشحن الألعاب والبرامج 🔭\n▫️ زيادة متابعين وتفاعلات\n▫️ شحن الألعاب المختلفة")
        try: bot.edit_message_text(text, chat_id, message_id, reply_markup=smm_main_keyboard())
        except Exception: bot.send_message(chat_id, text, reply_markup=smm_main_keyboard())

    elif call.data == "smm_servers_menu":
        try:
            bot.edit_message_text("توفر خدمات متابعين وإعجابات ومشاهدات بأسعار مناسبة\n\n🧛‍♂️ الرجاء إختيار الخدمة:", chat_id, message_id, reply_markup=boost_keyboard("2"))
        except Exception:
            bot.send_message(chat_id, "توفر خدمات متابعين وإعجابات ومشاهدات بأسعار مناسبة\n\n🧛‍♂️ الرجاء إختيار الخدمة:", reply_markup=boost_keyboard("2"))

    elif call.data == "games_menu":
        try: bot.edit_message_text("🎮 شحن الألعاب وبرامج بلاس 🕹️", chat_id, message_id, reply_markup=games_keyboard())
        except Exception: bot.send_message(chat_id, "🎮 شحن الألعاب وبرامج بلاس 🕹️", reply_markup=games_keyboard())

    elif call.data.startswith("smmc_"):
        bot.answer_callback_query(call.id, "جاري جلب الخدمات وتحديث الأسعار...")
        parts = call.data.split("_")
        server_id = parts[1]
        category_code = parts[2]

        filtered_services = filter_smm_services(category_code, server_id)

        if not filtered_services:
            bot.send_message(chat_id, "❌ عذراً، لا توجد خدمات متاحة لهذا القسم حالياً.", reply_markup=back_button())
            return

        markup = dynamic_smm_keyboard(filtered_services, category_code, page=0, smm_server_id=server_id)
        msg_text = "✅ : جميع الخدمات المتوفرة في هذا القسم 👇\n☑️ : يرجى اختيار الخدمة المناسبة لك 👇\n⚠️ ملاحظة يتم عرض الخدمات كالتالي: اسم الخدمة ▻ السعر لكل 1000"
        try:
            bot.edit_message_text(msg_text, chat_id, message_id, reply_markup=markup)
        except Exception:
            bot.send_message(chat_id, msg_text, reply_markup=markup)

    elif call.data.startswith("smmp_"):
        parts = call.data.split("_")
        server_id = parts[1]
        category_code = parts[2]
        page = int(parts[3])

        filtered_services = filter_smm_services(category_code, server_id)
        markup = dynamic_smm_keyboard(filtered_services, category_code, page=page, smm_server_id=server_id)
        try: bot.edit_message_text("✅ : جميع الخدمات المتوفرة في هذا القسم 👇\n☑️ : يرجى اختيار الخدمة المناسبة لك 👇\n⚠️ ملاحظة يتم عرض الخدمات كالتالي: اسم الخدمة ▻ السعر لكل 1000", chat_id, message_id, reply_markup=markup)
        except: pass

    # ==================== عرض تفاصيل الخدمة (مطابق للصورة 1) ====================
    elif call.data.startswith("smmbuy_"):
        parts = call.data.split("_")
        server_id = parts[1]
        service_id = parts[2]
        category_code = parts[3] if len(parts) > 3 else "others"

        services = get_cached_smm_services(server_id)
        selected_srv = next((s for s in services if str(s.get('service')) == str(service_id)), None)

        if not selected_srv:
            bot.answer_callback_query(call.id, "❌ حدث خطأ في جلب بيانات الخدمة.", show_alert=True)
            return

        name = translate_text(str(selected_srv.get('name', 'خدمة غير محددة')))
        category_display = CATEGORY_TITLES.get(category_code, selected_srv.get('category', 'عام'))
        min_q = selected_srv.get('min', '10')
        max_q = selected_srv.get('max', '1000000')
        rate = float(selected_srv.get('rate', 0))
        price_profit = round(rate * 1.10, 4)

        # استخراج أو تعيين الضمان والسرعة والجودة بشكل ذكي
        speed = "سريعة" if "fast" in name.lower() or "سريع" in name else "فورية ⚡"
        quality = "عالية ✅" if "hq" in name.lower() or "جودة" in name else "ممتازة ⭐️"
        guarantee = "30 يوم" if "30" in name else ("90 يوم" if "90" in name else ("ضمان تعويض ♻️" if "refill" in name.lower() or "ضمان" in name else "بدون ضمان ⚠️"))

        msg_text = (
            f"📁 : اسم القسم: - {category_display}\n"
            f"🛍️ : الخدمة: {name}\n\n"
            f"✳️ : المعلومات الأكثر تفاصيل تجدها اسفل👇\n"
            f"🏷️ : يمكنك طلب الخدمة عبر الضغط على زر ( طلب الخدمة ) 🆔 ID الخدمة: {service_id}"
        )

        grid_markup = smm_detail_grid_keyboard(
            service_id=service_id,
            price=price_profit,
            speed=speed,
            quality=quality,
            guarantee=guarantee,
            min_q=min_q,
            max_q=max_q,
            category_code=category_code,
            smm_server_id=server_id
        )

        try: bot.edit_message_text(msg_text, chat_id, message_id, reply_markup=grid_markup)
        except Exception: bot.send_message(chat_id, msg_text, reply_markup=grid_markup)

    elif call.data.startswith("fav_add_"):
        srv_id = call.data.split("_")[2]
        bot.answer_callback_query(call.id, f"⭐ تم إضافة الخدمة {srv_id} إلى المفضلة بنجاح!", show_alert=True)

    # ==================== الضغط على زر طلب الخدمة -> طلب الرابط (مطابق للصورة 2) ====================
    elif call.data.startswith("smm_order_"):
        parts = call.data.split("_")
        server_id = parts[2]
        service_id = parts[3]
        category_code = parts[4] if len(parts) > 4 else "others"

        services = get_cached_smm_services(server_id)
        selected_srv = next((s for s in services if str(s.get('service')) == str(service_id)), None)

        if not selected_srv:
            bot.answer_callback_query(call.id, "❌ خطأ في الخدمة.", show_alert=True)
            return

        name = translate_text(str(selected_srv.get('name', 'خدمة غير محددة')))
        category_display = CATEGORY_TITLES.get(category_code, selected_srv.get('category', 'عام'))
        min_q = int(selected_srv.get('min', 10))
        max_q = int(selected_srv.get('max', 1000000))
        rate = float(selected_srv.get('rate', 0))
        price_1k = round(rate * 1.10, 4)

        # حفظ بيانات الخدمة في جلسة المستخدم
        USER_STEPS[user_id] = {
            'step': 'WAITING_LINK',
            'service_id': service_id,
            'server_id': server_id,
            'category_code': category_code,
            'category_display': category_display,
            'service_name': name,
            'min_q': min_q,
            'max_q': max_q,
            'price_1k': price_1k,
            'raw_service': selected_srv
        }

        desc_text = (
            f"📜🚀 خدمة {name} عالية الجودة، تبدأ خلال وقت قصير من تقديم الطلب ⌛️، "
            f"مع تنفيذ سريع يناسب جميع الكميات. 📈 تساعد على تعزيز نمو الحساب وزيادة المصداقية، "
            f"وتتميز بثبات جيد، وجودة ممتازة، وأداء مستقر لتحقيق أفضل النتائج. ✅"
        )

        msg_text = (
            f"🚀 : انشاء طلب جديد\n\n"
            f"♻️ : اسم الخدمة: {name}\n"
            f"💰 : السعر لكل 1000: ${price_1k:.3f} لكل 1000\n"
            f"📊 : الحد الأدنى: {min_q}\n"
            f"📉 : الحد الأقصى: {max_q}\n\n"
            f"{desc_text}\n\n"
            f"🔗 : الآن من فضلك أرسل رابط الطلب:"
        )

        try:
            bot.edit_message_text(msg_text, chat_id, message_id, reply_markup=smm_cancel_link_keyboard(service_id, category_code))
        except Exception:
            bot.send_message(chat_id, msg_text, reply_markup=smm_cancel_link_keyboard(service_id, category_code))

    # ==================== تأكيد الطلب بعد إدخال الكمية (مطابق للصورة 4) ====================
    elif call.data.startswith("smm_confirm_"):
        parts = call.data.split("_")
        server_id = parts[2]
        service_id = parts[3]
        qty = int(parts[4])
        total_cost = float(parts[5])
        category_code = parts[6] if len(parts) > 6 else "others"

        step_info = USER_STEPS.get(user_id, {})
        link = step_info.get('link', '')
        service_name = step_info.get('service_name', f"خدمة #{service_id}")
        category_name = step_info.get('category_display', 'عام')

        if not link:
            bot.send_message(chat_id, "❌ انتهت الجلسة، يرجى إعادة اختيار الخدمة وإرسال الرابط مجدداً.", reply_markup=back_button())
            return

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
            balance_row = cursor.fetchone()
            balance = balance_row[0] if balance_row else 0.0

            if balance < total_cost:
                bot.answer_callback_query(call.id, "❌ رصيدك غير كافٍ لإتمام الطلب!", show_alert=True)
                if user_id in USER_STEPS: del USER_STEPS[user_id]
                return

            # إرسال الطلب لموقع الرشق عبر API
            order_response = smm_request(server_id, 'add', service=service_id, link=link, quantity=qty)

            if order_response and 'order' in order_response:
                order_id = str(order_response['order'])
                new_balance = balance - total_cost

                # خصم الرصيد وحفظ الطلب في قاعدة البيانات
                cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (total_cost, user_id))
                cursor.execute('''
                    INSERT INTO smm_orders (order_id, user_id, service_id, service_name, category_name, link, quantity, cost, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
                ''', (order_id, user_id, service_id, service_name, category_name, link, qty, total_cost))
                conn.commit()

                # إرسال رسالة النجاح المطابقة للصورة 4
                success_msg = (
                    f"✅ - تم تنفيذ الطلب بنجاح !\n\n"
                    f"♻️ : الخدمة: {service_name}\n"
                    f"📦 : الكمية: {qty}\n"
                    f"💰 : السعر الكلي: ${total_cost:.5f}\n"
                    f"🧾 : رقم الطلب: #{order_id}\n"
                    f"🆔 : الرقم السري: {user_id}\n"
                    f"🔗 : الرابط: [{link}]\n\n"
                    f"⬇️⬇️ - حالة الطلب في الاسفل -\n\n"
                    f"🏷️ : العدد المطلوب: {qty}\n"
                    f"📊 : العدد المكتمل: 0\n"
                    f"🅿️ : العدد المتبقي: {qty}\n"
                    f"🔘 : الحاله: في الأنتظار⌛️\n\n"
                    f"🔄 : تحديث حالة الطلب عبر زر [ ♻️ التحديث ] في الاسفل."
                )

                markup = smm_order_status_keyboard(order_id, service_id, qty, total_cost, link, category_name, service_name)
                try: bot.edit_message_text(success_msg, chat_id, message_id, reply_markup=markup)
                except Exception: bot.send_message(chat_id, success_msg, reply_markup=markup)

            else:
                err_msg = order_response.get('error', 'فشل إرسال الطلب للمزود') if order_response else 'فشل الاتصال بالسيرفر'
                bot.edit_message_text(f"❌ لم يتم تنفيذ الطلب: {err_msg}\nلم يتم خصم أي رصيد من حسابك.", chat_id, message_id, reply_markup=back_button())
        finally:
            conn.close()
            if user_id in USER_STEPS: del USER_STEPS[user_id]

    # ==================== زر تحديث حالة الطلب (مطابق للصورة 5) ====================
    elif call.data.startswith("smm_stat_"):
        order_id = call.data.split("_")[2]
        bot.answer_callback_query(call.id, "جاري فحص حالة الطلب من السيرفر...")

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT service_name, category_name, link, quantity, cost, status FROM smm_orders WHERE order_id = ?', (order_id,))
            order_data = cursor.fetchone()
        finally:
            conn.close()

        if not order_data:
            bot.send_message(chat_id, "❌ لم يتم العثور على بيانات الطلب.")
            return

        srv_name, cat_name, link, qty, cost, db_status = order_data

        # الاستعلام عن الحالة من الـ API
        status_res = smm_request('2', 'status', order=order_id)
        api_status = status_res.get('status', db_status) if status_res else db_status
        remains = status_res.get('remains', '0') if status_res else '0'
        try: remains_num = int(remains)
        except: remains_num = 0

        completed_count = max(0, qty - remains_num)
        date_str = get_arabic_datetime()

        status_lower = str(api_status).lower()

        if status_lower in ['completed', 'مكتمل']:
            # رسالة الاكتمال التامة (مطابقة للصورة 5)
            done_msg = (
                f"✅ : تم اكتمال طلبك بنجاح💙\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📦 : رقم الطلب : #{order_id}\n"
                f"📁 : القسم : {cat_name}\n"
                f"🛒 : الخدمة : {srv_name}\n"
                f"🔗 : الرابط : [{link}]\n"
                f"🔢 : الكمية : {qty}\n"
                f"📊 : تم التنفيذ : {qty}\n"
                f"⌛️ : المتبقي : 0\n"
                f"📌 : الحالة : مكتمل ✅\n"
                f"⏰ : الوقت : {date_str}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🎉 : تم تنفيذ طلبك بالكامل بنجاح\n"
                f"💙 : شكراً لاستخدامك خدماتنا"
            )
            try: bot.edit_message_text(done_msg, chat_id, message_id, reply_markup=back_button())
            except: bot.send_message(chat_id, done_msg, reply_markup=back_button())
        else:
            status_arabic = "قيد التنفيذ 🔄" if "progress" in status_lower else ("في الأنتظار ⌛️" if "pending" in status_lower else status_api)
            update_msg = (
                f"📊 - تفاصيل حالة الطلب الحالية -\n\n"
                f"🧾 : رقم الطلب: #{order_id}\n"
                f"🛒 : الخدمة: {srv_name}\n"
                f"🔗 : الرابط: [{link}]\n"
                f"🏷️ : العدد المطلوب: {qty}\n"
                f"📊 : العدد المكتمل: {completed_count}\n"
                f"🅿️ : العدد المتبقي: {remains_num}\n"
                f"🔘 : الحاله: {status_arabic}\n"
                f"⏰ : آخر فحص: {date_str}\n\n"
                f"🔄 يمكنك الضغط على زر التحديث مرة أخرى لاحقاً."
            )
            markup = smm_order_status_keyboard(order_id, "", qty, cost, link, cat_name, srv_name)
            try: bot.edit_message_text(update_msg, chat_id, message_id, reply_markup=markup)
            except: bot.send_message(chat_id, update_msg, reply_markup=markup)

    elif call.data == "free_ruble":
        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,))
            invite_count = cursor.fetchone()[0]
        finally:
            conn.close()

        earned_total = invite_count * REWARD_PER_INVITE
        bot.edit_message_text(f"💎 نظام اربح رصيد مجاني 💎\n\nرابط إحالتك:\n`{ref_link}`\n👥 المدعوين: {invite_count}\n💵 إجمالي الأرباح: ${earned_total:.2f}", chat_id, message_id, parse_mode="Markdown", reply_markup=back_button())

    elif call.data == "ai_landing":
        bot.edit_message_text("🤖 قسم خدمات الذكاء الاصطناعي\n\nاطرح سؤالك مباشرة في المحادثة وسيجيبك البوت.", chat_id, message_id, reply_markup=back_button())

    elif call.data in ["fast_buy_tg", "fast_buy_wa"]:
        srv_code = "tg" if "tg" in call.data else "wa"
        markup = countries_keyboard_fast("grizzly", srv_code, page=0)
        bot.edit_message_text(f"⚡ عروض سريعة لـ ({srv_code.upper()}):", chat_id, message_id, reply_markup=markup)

    elif call.data == "best_selling":
        bot.edit_message_text("🔥 أكثر السيرفرات طلباً: Grizzly SMS", chat_id, message_id, reply_markup=back_button())

    elif call.data == "most_available":
        bot.edit_message_text("🎲 الأرقام الأكثر توفراً حالياً: روسيا، نيجيريا، وأوكرانيا.", chat_id, message_id, reply_markup=back_button())

    elif call.data == "support":
        bot.edit_message_text(f"🎧 الدعم الفني: {ADMIN_USERNAME}", chat_id, message_id, reply_markup=back_button())

    elif call.data == "purchase_stats":
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM purchases")
            count = cursor.fetchone()[0]
        finally:
            conn.close()
        bot.edit_message_text(f"✔ إحصائيات العمليات: تم تنفيذ أكثر من {count + 100} عملية بنجاح.", chat_id, message_id, reply_markup=back_button())

    elif call.data == "my_account":
        user_data = get_or_create_user(user_id, call.from_user.first_name)
        try: balance = float(user_data[2]) if user_data[2] is not None else 0.0
        except: balance = 0.0
        try: ai_bal = int(user_data[3]) if user_data[3] is not None else 5
        except: ai_bal = 5
        msg = f"👤 حسابك:\n🆔: `{user_data[0]}`\n💰 الرصيد: ${balance:.2f}\n🤖 رصيد AI: {ai_bal}"
        bot.edit_message_text(msg, chat_id, message_id, parse_mode="Markdown", reply_markup=back_button())

    elif call.data == "other_services":
        bot.edit_message_text("🛸 خدمات وميزات أخرى قادمة قريباً.", chat_id, message_id, reply_markup=back_button())

# ==================== استقبال الرسائل والخطوات ====================
@bot.message_handler(func=lambda msg: msg.from_user.id in USER_STEPS)
def handle_user_steps(message):
    user_id = message.from_user.id
    step_data = USER_STEPS.get(user_id, {})
    step = step_data.get('step')

    # --- خطوات شحن Binance ---
    if step == "waiting_binance_amount":
        try:
            amount = float(message.text.strip())
            if amount <= 0: raise ValueError()

            USER_STEPS[user_id] = {"step": "waiting_binance_txid", "amount": amount}
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("📋 نسخ العنوان", callback_data="copy_id"))
            markup.add(InlineKeyboardButton("✅ تم الدفع (أدخل TXID)", callback_data="enter_txid"))
            markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="recharge_menu"))

            bot.send_message(
                message.chat.id,
                f"🟡 **تفاصيل الدفع عبر Binance (تلقائي)**\n\n"
                f"💵 المبلغ المطلوب: {amount} USDT\n"
                f"📍 عنوان المحفظة (Pay ID):\n`{BINANCE_PAY_ID}`\n\n"
                f"📋 الخطوات:\n"
                f"1️⃣ حول المبلغ المطلوب إلى العنوان أعلاه.\n"
                f"2️⃣ تأكد من إرسال المبلغ نفسه الذي اخترته.\n"
                f"3️⃣ بعد الانتهاء، اضغط على زر (تم الدفع) وأرسل رقم المعاملة (TXID).\n\n"
                f"⚠️ ملاحظة: سيتم التحقق من المعاملة تلقائياً عبر Binance API.",
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="recharge_menu"))
            bot.send_message(message.chat.id, "❌ خطأ: يرجى إرسال رقم صحيح للمبلغ (مثال: 10 أو 5.5):", reply_markup=markup)
        return

    elif step == "waiting_binance_txid":
        txid = message.text.strip()
        expected_amount = step_data.get("amount", 0)

        wait_msg = bot.send_message(message.chat.id, "🔄 جاري التحقق من المعاملة... يرجى الانتظار لحظة.")
        is_valid = verify_binance_txid(txid, expected_amount)
        bot.delete_message(message.chat.id, wait_msg.message_id)

        if is_valid:
            conn = get_db()
            cursor = conn.cursor()
            try:
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (expected_amount, user_id))
                conn.commit()
            finally:
                conn.close()

            bot.send_message(message.chat.id, f"✅ **تم التحقق بنجاح!**\nتمت إضافة مبلغ {expected_amount} USDT إلى رصيدك بنجاح.")
            del USER_STEPS[user_id]
        else:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔄 إعادة إدخال TXID", callback_data="enter_txid"))
            markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="recharge_menu"))
            bot.send_message(message.chat.id, "❌ **فشل التحقق من المعاملة**\n\nلم يتم العثور على المعاملة، تأكد من صحة TXID وانتظر دقيقة ثم حاول مرة أخرى.", reply_markup=markup)
        return

    # --- معالجة عمليات تحويل الرصيد ---
    elif step == 'TRANSFER_TARGET':
        target_id_str = message.text.strip()
        if not target_id_str.isdigit():
            bot.send_message(message.chat.id, "❌ يرجى إرسال آيدي المستلم بالأرقام فقط.")
            return

        target_id = int(target_id_str)
        if target_id == user_id:
            bot.send_message(message.chat.id, "❌ لا يمكنك تحويل الرصيد لنفسك!")
            return

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT name FROM users WHERE user_id = ?", (target_id,))
            target_user = cursor.fetchone()
        finally:
            conn.close()

        if not target_user:
            bot.send_message(message.chat.id, "❌ هذا المستخدم غير موجود في البوت.")
            return

        USER_STEPS[user_id] = {'step': 'TRANSFER_AMOUNT', 'target_id': target_id, 'target_name': target_user[0]}
        bot.send_message(message.chat.id, f"👤 المستلم: {target_user[0]} (`{target_id}`)\n💵 أدخل المبلغ المراد تحويله بالدولار (أقل مبلغ ${MIN_TRANSFER_AMOUNT:.2f}):", parse_mode="Markdown")
        return

    elif step == 'TRANSFER_AMOUNT':
        try:
            amount = float(message.text.strip())
            if amount < MIN_TRANSFER_AMOUNT:
                bot.send_message(message.chat.id, f"❌ أقل مبلغ للتحويل هو ${MIN_TRANSFER_AMOUNT:.2f}.")
                return

            target_id = step_data['target_id']
            target_name = step_data['target_name']

            conn = get_db()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
                sender_balance = cursor.fetchone()[0]

                if sender_balance < amount:
                    bot.send_message(message.chat.id, f"❌ رصيدك غير كافٍ!\nرصيدك الحالي: ${sender_balance:.2f}")
                    del USER_STEPS[user_id]
                    return

                cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_id))
                conn.commit()
            finally:
                conn.close()

            del USER_STEPS[user_id]
            bot.send_message(message.chat.id, f"✅ تم تحويل ${amount:.2f} بنجاح إلى {target_name} (`{target_id}`).", parse_mode="Markdown", reply_markup=back_button())
            try: bot.send_message(target_id, f"🎉 وصلك تحويل رصيد بقيمة ${amount:.2f} من مستخدم آخر!")
            except: pass
            return
        except:
            bot.send_message(message.chat.id, "❌ يرجى إدخال مبلغ صحيح بالأرقام.")
            return

    # --- خطوات طلب خدمات SMM (الرابط ثم الكمية) ---
    # الخطوة 1: استلام الرابط وحساب أقصى كمية يمكن طلبها (مطابق للصورة 2 و 3)
    elif step == 'WAITING_LINK':
        link = message.text.strip()
        if not link:
            bot.send_message(message.chat.id, "❌ يرجى إرسال الرابط الصحيح.")
            return

        step_data['link'] = link
        step_data['step'] = 'WAITING_QTY'

        price_1k = step_data.get('price_1k', 0.5)
        single_price = price_1k / 1000
        min_q = step_data.get('min_q', 10)
        max_q = step_data.get('max_q', 1000000)

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
            user_bal = cursor.fetchone()[0] or 0.0
        finally:
            conn.close()

        # حساب عدد المتابعين/الأعضاء المتاح رشقهم برصيد المستخدم الحالي
        possible_qty = int(user_bal / single_price) if single_price > 0 else 0

        ask_qty_msg = (
            f"☑️ : يرجى إرسال عدد الأعضاء تذكر أقل عدد للطلب {min_q}، وأقصى عدد للطلب {max_q} 👤\n\n"
            f"💰 : سعر العضو الواحد: ${single_price:.6f}\n\n"
            f"🏆 : يمكنك رشق {possible_qty} عضو 👥"
        )
        bot.send_message(message.chat.id, ask_qty_msg)
        return

    # الخطوة 2: استلام الكمية وعرض بطاقة تأكيد الطلب (مطابق للصورة 3)
    elif step == 'WAITING_QTY':
        if not message.text.strip().isdigit():
            bot.send_message(message.chat.id, "❌ يرجى إرسال الكمية بالأرقام فقط.")
            return

        qty = int(message.text.strip())
        min_q = step_data.get('min_q', 10)
        max_q = step_data.get('max_q', 1000000)
        price_1k = step_data.get('price_1k', 0.5)
        service_id = step_data.get('service_id')
        server_id = step_data.get('server_id', '2')
        category_code = step_data.get('category_code', 'others')
        category_display = step_data.get('category_display', 'عام')
        service_name = step_data.get('service_name', 'خدمة')
        link = step_data.get('link', '')

        if qty < min_q or qty > max_q:
            bot.send_message(message.chat.id, f"❌ الكمية غير مسموحة.\n📉 الحد الأدنى: {min_q}\n📈 الحد الأقصى: {max_q}\n\nأرسل كمية صحيحة:")
            return

        total_cost = round((qty / 1000) * price_1k, 5)

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
            balance = cursor.fetchone()[0] or 0.0
        finally:
            conn.close()

        if balance < total_cost:
            bot.send_message(message.chat.id, f"❌ رصيدك غير كافٍ!\n💵 تكلفة الطلب: ${total_cost:.5f}\n💰 رصيدك الحالي: ${balance:.2f}", reply_markup=back_button())
            del USER_STEPS[user_id]
            return

        # رسالة تأكيد الطلب المطابقة تماماً للصورة 3
        confirm_text = (
            f"✅ - معلومات تأكيد الطلب .\n\n"
            f"🌀 - القسم: - {category_display}\n"
            f"🛍️ - الخدمة: {service_name}\n"
            f"💰 - السعر 1K: ${price_1k:.3f}\n"
            f"💸 - السعر الكلي: ${total_cost:.5f}\n"
            f"🔥 - الجودة: عالية جداً 🏆\n"
            f"🚀 - السرعة: سريعة وفورية 🚀\n"
            f"🧿 - الضمان: ضمان تعويض تلقائي 🔰\n\n"
            f"🏷️ - الوصف: 🚀 خدمة {service_name} عالية الجودة، تبدأ خلال وقت قصير من تقديم الطلب ⌛️، مع تنفيذ سريع يناسب جميع الكميات. ✅\n\n"
            f"🔗 - الرابط: [{link}]\n\n"
            f"♻️ - هل تريد المتابعة وتأكيد الطلب؟"
        )

        markup = smm_confirm_keyboard(service_id, qty, total_cost, category_code=category_code, smm_server_id=server_id)
        bot.send_message(message.chat.id, confirm_text, reply_markup=markup)
        return

# ==================== تشغيل البوت ====================
if __name__ == '__main__':
    set_bot_commands()
    print("🤖 Bot is running...")
    bot.infinity_polling(skip_pending=True)
