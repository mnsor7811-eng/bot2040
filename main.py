import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
import time
import requests
import sqlite3
import hmac
import hashlib
from urllib.parse import urlencode

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
    smm_service_detail_keyboard, dynamic_smm_keyboard, smm_confirm_keyboard
)

bot = telebot.TeleBot(TOKEN)

# ==================== إعدادات بايننس بايو (Binance Pay) ====================
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
    
    params = {
        "timestamp": timestamp,
        "txId": txid
    }
    
    query_string = urlencode(params)
    signature = get_binance_signature(query_string, SECRET_KEY)
    
    headers = {
        "X-MBX-APIKEY": API_KEY
    }
    
    full_url = f"{url}?{query_string}&signature={signature}"
    
    try:
        response = requests.get(full_url, headers=headers)
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
    conn.commit()
    conn.close()

init_db()

# ==================== إعدادات API موقع الرشق ====================
SMM_API_KEY = "Db5f57b29759abc91a56be0854b35e2e"
SMM_API_URL = "https://smmstone.com/api/v2"

SMM_SERVICES_CACHE = []
SMM_CACHE_TIME = 0

def smm_request(action, **kwargs):
    payload = {'key': SMM_API_KEY, 'action': action}
    payload.update(kwargs)
    try:
        response = requests.post(SMM_API_URL, data=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"SMM API Error: {e}")
        return None

def get_cached_smm_services():
    global SMM_SERVICES_CACHE, SMM_CACHE_TIME
    if time.time() - SMM_CACHE_TIME < 300 and SMM_SERVICES_CACHE:
        return SMM_SERVICES_CACHE
    
    data = smm_request('services')
    if data and isinstance(data, list):
        SMM_SERVICES_CACHE = data
        SMM_CACHE_TIME = time.time()
        return data
    return []

def filter_smm_services(target_type):
    services = get_cached_smm_services()
    filtered = []
    
    for srv in services:
        name_cat = (str(srv.get('name', '')) + " " + str(srv.get('category', ''))).lower()
        match = False
        
        if target_type == 'tg_mem':
            if any(k in name_cat for k in ['telegram', 'تيليجرام', 'تليجرام', 'قنات', 'أعضاء', 'اعضاء', 'مشترك', 'member', 'sub']):
                if not any(v in name_cat for v in ['view', 'مشاهد', 'poll', 'تفاعل']):
                    match = True
        elif target_type == 'tg_view':
            if any(k in name_cat for k in ['telegram', 'تيليجرام', 'تليجرام']) and any(v in name_cat for v in ['view', 'مشاهد', 'post', 'منشور']):
                match = True
        elif target_type == 'ig_fol':
            if any(k in name_cat for k in ['instagram', 'انستجرام', 'انستا', 'انستغرام']) and any(v in name_cat for v in ['follow', 'متابع', 'بروفايل']):
                if not any(l in name_cat for l in ['like', 'لايك', 'اعجاب']):
                    match = True
        elif target_type == 'ig_like':
            if any(k in name_cat for k in ['instagram', 'انستجرام', 'انستا', 'انستغرام']) and any(v in name_cat for v in ['like', 'لايك', 'اعجاب', 'إعجاب']):
                match = True
        elif target_type == 'tk_view':
            if any(k in name_cat for k in ['tiktok', 'تيك توك', 'تيكتوك']) and any(v in name_cat for v in ['view', 'مشاهد']):
                match = True
        elif target_type == 'tk_fol':
            if any(k in name_cat for k in ['tiktok', 'تيك توك', 'تيكتوك']) and any(v in name_cat for v in ['follow', 'متابع']):
                match = True
        elif target_type == 'fb_fol':
            if any(k in name_cat for k in ['facebook', 'فيسبوك', 'فيس بوك', 'فيس']) and any(v in name_cat for v in ['follow', 'like', 'متابع', 'اعجاب', 'إعجاب']):
                match = True
        elif target_type == 'yt_view':
            if any(k in name_cat for k in ['youtube', 'يوتيوب']) and any(v in name_cat for v in ['view', 'مشاهد']):
                match = True
        
        if match:
            filtered.append(srv)
            
    # نظام احتياطي شامل لضمان عدم ظهور رسالة "لا توجد خدمات" أبداً
    if not filtered and services:
        return services[:25]
        
    return filtered

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
        cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
    except Exception:
        pass

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

    conn.close()

    user_data = get_or_create_user(user_id, name)
    text = (f"💠 أهلاً بك عزيزي في البوت الشامل 💠\n\n"
            f"👤 حسابك: {ADMIN_USERNAME}\n"
            f"💰 رصيدك الحالي: ${user_data[2]:.2f}\n"
            f"🤖 رصيد أسئلة الذكاء: {user_data[3]} سؤال\n\n"
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
    cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,))
    invite_count = cursor.fetchone()[0]
    conn.close()
    earned_total = invite_count * REWARD_PER_INVITE
    bot.send_message(message.chat.id, f"💎 نظام اربح رصيد مجاناً 💎\n\nرابط إحالتك:\n`{ref_link}`\n👥 المدعوين: {invite_count}\n💵 إجمالي الأرباح: ${earned_total:.2f}", parse_mode="Markdown", reply_markup=back_button())

@bot.message_handler(commands=['transfer'])
def transfer_cmd(message):
    user_id = message.from_user.id
    USER_STEPS[user_id] = {'step': 'TRANSFER_TARGET'}
    text = (f"🔄 قسم تحويل الرصيد بين الحسابات\n\n✨ الميزات: عمولة 0%\n💵 أقل مبلغ: $1.00\n\n📌 يرجى إرسال آيدي (User ID) الشخص المستلم الآن:")
    bot.send_message(message.chat.id, text, reply_markup=back_button())

@bot.message_handler(commands=['support'])
def support_cmd(message):
    bot.send_message(message.chat.id, f"🎧 الدعم الفني: {ADMIN_USERNAME}", reply_markup=back_button())

@bot.message_handler(commands=['mart'])
def mart_cmd(message):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM purchases")
    count = cursor.fetchone()[0]
    conn.close()
    bot.send_message(message.chat.id, f"✔ إحصائيات الشراء الناجح لهذا اليوم: تم تنفيذ أكثر من {count + 50} عملية بنجاح.", reply_markup=back_button())

@bot.message_handler(commands=['account'])
def account_cmd(message):
    user_id = message.from_user.id
    user_data = get_or_create_user(user_id, message.from_user.first_name)
    msg = f"👤 حسابك:\n🆔: `{user_data[0]}`\n💰 الرصيد: ${user_data[2]:.2f}\n🤖 رصيد AI: {user_data[3]}"
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

    # لوحة الإدارة الكبرى
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
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*), SUM(cost) FROM purchases")
        p_data = cursor.fetchone()
        total_purchases = p_data[0] or 0
        total_spent = p_data[1] or 0.0
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
        cursor.execute("SELECT user_id, name, username, balance, ai_balance, is_banned FROM users ORDER BY rowid DESC LIMIT 10")
        users = cursor.fetchall()
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
        cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (target_id,))
        res = cursor.fetchone()
        if res:
            new_status = 0 if res[0] == 1 else 1
            cursor.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (new_status, target_id))
            conn.commit()
            bot.send_message(chat_id, "🚫 تم الحظر." if new_status == 1 else "🟢 تم فك الحظر.", reply_markup=admin_back_button())
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

    # التنقل العام والقائمة الرئيسية
    elif call.data == "back_main":
        if user_id in USER_STEPS:
            del USER_STEPS[user_id]
        user_data = get_or_create_user(user_id, call.from_user.first_name)
        text = (f"💠 أهلاً بك عزيزي في البوت الشامل 💠\n\n👤 حسابك: {ADMIN_USERNAME}\n💰 رصيدك الحالي: ${user_data[2]:.2f}\n🤖 رصيد أسئلة الذكاء: {user_data[3]} سؤال\n\n📌 استخدم الأزرار بالأسفل لتنفيذ طلباتك:")
        try: bot.edit_message_text(text, chat_id, message_id, reply_markup=main_keyboard(user_id))
        except: bot.send_message(chat_id, text, reply_markup=main_keyboard(user_id))

    # ==================== معالجة أزرار شحن الرصيد وبايننس ====================
    elif call.data == "deposit_binance" or call.data == "pay_binance":
        bot.answer_callback_query(call.id)
        if user_id in USER_STEPS:
            USER_STEPS.pop(user_id, None)
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="recharge_menu"))

        msg = bot.send_message(
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
        USER_STEPS[user_id] = {"step": "waiting_amount"}
        bot.register_next_step_handler(msg, process_amount)

    elif call.data == "enter_txid":
        bot.answer_callback_query(call.id)
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="recharge_menu"))
        
        msg = bot.send_message(
            chat_id,
            "🟡 **أدخل TXID (رقم المعاملة)**\n\n"
            "⚠️ تأكد من:\n"
            "• إدخال TXID الصحيح من محفظتك.\n"
            "• أن المبلغ المرسل يساوي المبلغ الذي اخترته.\n"
            "• انتظر دقيقة بعد التحويل قبل إدخال TXID.\n\n"
            "أرسل TXID الآن:",
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, process_txid)

    elif call.data == "copy_id":
        bot.answer_callback_query(call.id, text=f"Pay ID: {BINANCE_PAY_ID} (تم النسخ افتراضياً)")

    elif call.data == "recharge_menu":
        bot.answer_callback_query(call.id)
        if user_id in USER_STEPS:
            USER_STEPS.pop(user_id, None)
        try:
            bot.edit_message_text(
                "🎳 شحن الرصيد / الاشتراكات\n\nاختر وسيلة الدفع التي تناسبك:", 
                chat_id, 
                message_id, 
                reply_markup=recharge_keyboard()
            )
        except Exception:
            bot.send_message(
                chat_id, 
                "🎳 شحن الرصيد / الاشتراكات\n\nاختر وسيلة الدفع التي تناسبك:", 
                reply_markup=recharge_keyboard()
            )

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
        text = (f"🔄 قسم تحويل الرصيد بين الحسابات\n\n✨ الميزات: عمولة 0%\n💵 أقل مبلغ: $1.00\n\n📌 يرجى إرسال آيدي (User ID) الشخص المستلم الآن:")
        bot.edit_message_text(text, chat_id, message_id, reply_markup=back_button())

    elif call.data == "buy_number":
        bot.edit_message_text("📞 قسم شراء الأرقام الافتراضية\n\nاختر السيرفر:", chat_id, message_id, reply_markup=servers_keyboard())

    elif call.data.startswith("select_server_"):
        server_id = call.data.split("_")[2]
        bot.edit_message_text(f"⚙️ تم اختيار: {SERVERS[server_id]['name']}\n\nاختر التطبيق:", chat_id, message_id, reply_markup=services_keyboard(server_id))

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
        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        balance = cursor.fetchone()[0]
        
        if balance < price:
            bot.send_message(chat_id, f"❌ رصيدك غير كافٍ!\nسعر هذا الرقم: ${price:.2f}\nرصيدك الحالي: ${balance:.2f}")
            conn.close()
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
            conn.close()
            
            msg = (f"🆔 **رقم الطلب** : `{tz_id}`\n🌐 **الدولة** : {c_name} {c_flag}\n📞 **الرقم** : `{formatted_phone}`\n"
                   f"📩 **الكود** : `قيد الانتظار... ⏳`\n🛍️ **التطبيق** : `{srv_code.upper()}`\n💵 **السعر** : `${price:.2f}`")
            bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=active_number_keyboard(tz_id, server_id))
        else:
            conn.close()
            bot.send_message(chat_id, f"❌ لم يكتمل الطلب: الرد من السيرفر: {res}")

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
        cursor.execute('SELECT cost, status, service, country_code FROM purchases WHERE tz_id = ?', (tz_id,))
        purchase = cursor.fetchone()
        
        if purchase and purchase[1] == 'PENDING':
            cost = purchase[0]
            cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (cost, user_id))
            cursor.execute('UPDATE purchases SET status = "CANCELLED" WHERE tz_id = ?', (tz_id,))
            conn.commit()
            conn.close()
            
            if action_type == "change_num":
                bot.edit_message_text(f"🔄 تم إلغاء الرقم وإعادة (${cost:.2f}).", chat_id, message_id)
                bot.send_message(chat_id, "تم استرجاع الرصيد، يرجى طلب رقم جديد من القائمة.", reply_markup=back_button())
            else:
                bot.edit_message_text(f"❌ تم إلغاء الرقم بنجاح وإعادة مبلغ (${cost:.2f}) إلى رصيدك.", chat_id, message_id, reply_markup=back_button())
        else:
            conn.close()
            bot.answer_callback_query(call.id, "العملية ملغاة مسبقاً.", show_alert=True)

    # أقسام الرشق (SMM Stone)
    elif call.data == "smm_main":
        text = ("🚀 الرشق وشحن الألعاب والبرامج 🔭\n▫️ زيادة متابعين وتفاعلات\n▫️ شحن الألعاب المختلفة")
        bot.edit_message_text(text, chat_id, message_id, reply_markup=smm_main_keyboard())

    elif call.data == "games_menu":
        bot.edit_message_text("🎮 شحن الألعاب وبرامج بلاس 🕹️", chat_id, message_id, reply_markup=games_keyboard())

    elif call.data == "boost_menu":
        bot.edit_message_text("🐙 توفر خدمات متابعين وإعجابات ومشاهدات بأسعار مناسبة\n\n🧛‍♂️ الرجاء إختيار الخدمة:", chat_id, message_id, reply_markup=boost_keyboard())

    elif call.data.startswith("smmc_"):
        bot.answer_callback_query(call.id, "جاري جلب الخدمات وتحديث الأسعار...")
        category_code = call.data.split("_", 1)[1]
        filtered_services = filter_smm_services(category_code)
        
        if not filtered_services:
            bot.send_message(chat_id, "❌ عذراً، لا توجد خدمات متاحة لهذا القسم حالياً.", reply_markup=back_button())
            return
            
        markup = dynamic_smm_keyboard(filtered_services, category_code, page=0)
        bot.edit_message_text("✅ : جميع الخدمات المتوفرة في هذا القسم 👇\n☑️ : يرجى اختيار الخدمة المناسبة لك 👇\n⚠️ ملاحظة يتم عرض الخدمات كالتالي: اسم الخدمة ▻ السعر لكل 1000", chat_id, message_id, reply_markup=markup)

    elif call.data.startswith("smmp_"):
        parts = call.data.split("_")
        category_code = parts[1] + "_" + parts[2]
        page = int(parts[3])
        filtered_services = filter_smm_services(category_code)
        markup = dynamic_smm_keyboard(filtered_services, category_code, page=page)
        try: bot.edit_message_text("✅ : جميع الخدمات المتوفرة في هذا القسم 👇\n☑️ : يرجى اختيار الخدمة المناسبة لك 👇\n⚠️ ملاحظة يتم عرض الخدمات كالتالي: اسم الخدمة ▻ السعر لكل 1000", chat_id, message_id, reply_markup=markup)
        except: pass

    elif call.data.startswith("smmbuy_") or call.data.startswith("game_"):
        service_id = call.data.split("_")[1] if call.data.startswith("smmbuy_") else call.data
        
        if call.data.startswith("smmbuy_"):
            services = get_cached_smm_services()
            selected_srv = next((s for s in services if str(s.get('service')) == str(service_id)), None)
            
            if not selected_srv:
                bot.answer_callback_query(call.id, "❌ حدث خطأ في جلب بيانات الخدمة.", show_alert=True)
                return
                
            name = selected_srv.get('name')
            min_q = selected_srv.get('min')
            max_q = selected_srv.get('max')
            rate = float(selected_srv.get('rate', 0))
            price_profit = round(rate * 1.10, 3)
            
            msg = (f"📦 **تفاصيل الخدمة (ID: {service_id})**\n\n"
                   f"🏷️ **الاسم:** {name}\n"
                   f"💰 **السعر (1000):** `${price_profit}`\n"
                   f"📉 **الحد الأدنى:** {min_q}\n"
                   f"📈 **الحد الأقصى:** {max_q}\n\n"
                   f"📝 يرجى قراءة وصف الخدمة جيداً قبل الطلب.")
            
            bot.edit_message_text(msg, chat_id, message_id, reply_markup=smm_service_detail_keyboard(service_id), parse_mode="Markdown")
        else:
            USER_STEPS[user_id] = {'step': 'WAITING_LINK', 'service_id': service_id}
            bot.send_message(chat_id, "🔗 أرسل الرابط أو المعرف (ID) المطلوب للخدمة الآن:", parse_mode="Markdown")

    elif call.data.startswith("smm_order_"):
        service_id = call.data.split("_")[2]
        USER_STEPS[user_id] = {'step': 'WAITING_LINK', 'service_id': service_id}
        bot.send_message(chat_id, "🔗 أرسل الرابط أو المعرف (ID) المطلوب للخدمة الآن:", parse_mode="Markdown")

    elif call.data.startswith("smm_confirm_"):
        parts = call.data.split("_")
        service_id = parts[2]
        qty = int(parts[3])
        total_cost = float(parts[4])
        
        link = USER_STEPS.get(user_id, {}).get('link', '')
        if not link:
            USER_STEPS[user_id] = {'step': 'WAITING_LINK', 'service_id': service_id}
            bot.send_message(chat_id, "🔗 حدث خطأ في استرجاع الرابط، يرجى إرسال الرابط المطلوب مرة أخرى:")
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        balance = cursor.fetchone()[0]
        
        if balance < total_cost:
            bot.answer_callback_query(call.id, "❌ رصيدك غير كافٍ لإتمام الطلب!", show_alert=True)
            conn.close()
            if user_id in USER_STEPS: del USER_STEPS[user_id]
            return
            
        if str(service_id).startswith("game_"):
            cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (total_cost, user_id))
            conn.commit()
            conn.close()
            bot.edit_message_text(f"✅ **تم تسجيل طلب اللعبة بنجاح!**\n\n💵 التكلفة المخصومة: `${total_cost:.2f}`\n📌 الحالة: قيد التنفيذ 🔄", chat_id, message_id, parse_mode="Markdown", reply_markup=back_button())
            if user_id in USER_STEPS: del USER_STEPS[user_id]
            return

        order_response = smm_request('add', service=service_id, link=link, quantity=qty)
        
        if order_response and 'order' in order_response:
            order_id = order_response['order']
            cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (total_cost, user_id))
            conn.commit()
            bot.edit_message_text(f"✅ **تم تنفيذ طلبك بنجاح عبر السيرفر!**\n\n🆔 رقم الطلب: `{order_id}`\n🔗 الرابط: `{link}`\n📊 الكمية: {qty}\n💵 التكلفة المخصومة: `${total_cost:.3f}`", chat_id, message_id, parse_mode="Markdown", reply_markup=back_button())
        else:
            err_msg = order_response.get('error', 'خطأ غير معروف') if order_response else 'فشل الاتصال'
            bot.edit_message_text(f"❌ حدث خطأ من سيرفر الرشق: {err_msg}\n(لم يتم خصم أي مبلغ من رصيدك).", chat_id, message_id, parse_mode="Markdown", reply_markup=back_button())
            
        conn.close()
        if user_id in USER_STEPS: del USER_STEPS[user_id]

    elif call.data == "free_ruble":
        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,))
        invite_count = cursor.fetchone()[0]
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
        cursor.execute("SELECT COUNT(*) FROM purchases")
        count = cursor.fetchone()[0]
        conn.close()
        bot.edit_message_text(f"✔ إحصائيات العمليات: تم تنفيذ أكثر من {count + 100} عملية بنجاح.", chat_id, message_id, reply_markup=back_button())

    elif call.data == "my_account":
        user_data = get_or_create_user(user_id, call.from_user.first_name)
        msg = f"👤 حسابك:\n🆔: `{user_data[0]}`\n💰 الرصيد: ${user_data[2]:.2f}\n🤖 رصيد AI: {user_data[3]}"
        bot.edit_message_text(msg, chat_id, message_id, reply_markup=back_button())

    elif call.data == "other_services":
        bot.edit_message_text("🛸 خدمات وميزات أخرى قادمة قريبأً.", chat_id, message_id, reply_markup=back_button())

# ==================== دوال خطوات بايننس ====================
def process_amount(message):
    chat_id = message.chat.id
    try:
        amount = float(message.text)
        if amount <= 0:
            raise ValueError()
        
        USER_STEPS[chat_id] = {"step": "waiting_txid", "amount": amount}
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📋 نسخ العنوان", callback_data="copy_id"))
        markup.add(InlineKeyboardButton("✅ تم الدفع (أدخل TXID)", callback_data="enter_txid"))
        markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="recharge_menu"))

        bot.send_message(
            chat_id,
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
    except ValueError:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="recharge_menu"))
        msg = bot.send_message(chat_id, "❌ خطأ: يرجى إرسال رقم صحيح للمبلغ (مثال: 10 أو 5.5):", reply_markup=markup)
        bot.register_next_step_handler(msg, process_amount)

def process_txid(message):
    chat_id = message.chat.id
    txid = message.text.strip()
    
    if chat_id not in USER_STEPS or "amount" not in USER_STEPS[chat_id]:
        bot.send_message(chat_id, "❌ انتهت الجلسة. اضغط /start للبدء من جديد.")
        return
        
    expected_amount = USER_STEPS[chat_id]["amount"]
    
    wait_msg = bot.send_message(chat_id, "🔄 جاري التحقق من المعاملة... يرجى الانتظار لحظة.")
    
    is_valid = verify_binance_txid(txid, expected_amount)
    
    bot.delete_message(chat_id, wait_msg.message_id)
    
    if is_valid:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (expected_amount, chat_id))
        conn.commit()
        conn.close()

        bot.send_message(
            chat_id,
            f"✅ **تم التحقق بنجاح!**\n"
            f"تمت إضافة مبلغ {expected_amount} USDT إلى رصيدك بنجاح."
        )
        del USER_STEPS[chat_id]
    else:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔄 إعادة إدخال TXID", callback_data="enter_txid"))
        markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="recharge_menu"))
        
        bot.send_message(
            chat_id,
            "❌ **فشل التحقق من المعاملة**\n\n"
            "لم يتم العثور على المعاملة، تأكد من صحة TXID وانتظر دقيقة ثم حاول مرة أخرى أُخرى.\n\n"
            "يرجى التأكد من:\n"
            "• صحة TXID\n"
            "• أن المبلغ المرسل مطابق للمبلغ المطلوب",
            reply_markup=markup
        )

# ==================== استقبال الرسائل والخطوات ====================
@bot.message_handler(func=lambda msg: msg.from_user.id in USER_STEPS)
def handle_user_steps(message):
    user_id = message.from_user.id
    step_data = USER_STEPS.get(user_id)
    step = step_data.get('step')

    if step in ["waiting_amount", "waiting_txid"]:
        return

    if str(user_id) == str(ADMIN_ID):
        if step == 'ADMIN_BROADCAST':
            del USER_STEPS[user_id]
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users")
            all_users = cursor.fetchall()
            conn.close()
            success_count = fail_count = 0
            for (u_id,) in all_users:
                try:
                    bot.copy_message(u_id, message.chat.id, message.message_id)
                    success_count += 1
                    time.sleep(0.05)
                except: fail_count += 1
            bot.send_message(message.chat.id, f"📢 **تم الإرسال!**\n✅ نجاح: `{success_count}`\n❌ فشل: `{fail_count}`", parse_mode="Markdown", reply_markup=admin_back_button())
            return
        elif step == 'ADMIN_SEARCH_USER':
            del USER_STEPS[user_id]
            query = message.text.strip().replace("@", "")
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, name, username, balance, ai_balance, is_banned FROM users WHERE name LIKE ? OR username LIKE ? OR user_id = ?", ('%'+query+'%', '%'+query+'%', query))
            users = cursor.fetchall()
            conn.close()
            if not users:
                bot.send_message(message.chat.id, "❌ لم يتم العثور على مستخدم.", reply_markup=admin_back_button())
                return
            for u in users:
                status = "محظور 🚫" if u[5] == 1 else "نشط ✅"
                res = f"👤 الاسم: {u[1]}\n🏷️ اليوزر: {u[2]}\n🆔 الآيدي: {u[0]}\n💰 الرصيد: ${u[3]:.2f}\n🤖 أسئلة AI: {u[4]}\n📌 الحالة: {status}"
                mk = InlineKeyboardMarkup()
                mk.row(InlineKeyboardButton("➕ رصيد", callback_data=f"act_add_{u[0]}"), InlineKeyboardButton("➖ خصم", callback_data=f"act_deduct_{u[0]}"))
                mk.row(InlineKeyboardButton("🤖 شحن AI", callback_data=f"act_ai_{u[0]}"), InlineKeyboardButton("🚫 حظر / فك", callback_data=f"act_ban_{u[0]}"))
                bot.send_message(message.chat.id, res, reply_markup=mk)
            return
        elif step in ['ADMIN_ADD_BALANCE_DIRECT', 'ADMIN_DEDUCT_BALANCE_DIRECT']:
            target_id = step_data['target_id']
            amount = float(message.text.strip())
            conn = get_db()
            cursor = conn.cursor()
            if step == 'ADMIN_ADD_BALANCE_DIRECT':
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_id))
            else:
                cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, target_id))
            conn.commit()
            conn.close()
            del USER_STEPS[user_id]
            bot.send_message(message.chat.id, f"✅ تمت العملية بنجاح للمستخدم `{target_id}`.", parse_mode="Markdown", reply_markup=admin_back_button())
            return

    if step == 'WAITING_LINK':
        step_data['link'] = message.text
        step_data['step'] = 'WAITING_QTY'
        bot.send_message(message.chat.id, "🔢 أرسل الكمية المطلوبة بالأرقام فقط:")

    elif step == 'WAITING_QTY':
        if not message.text.isdigit():
            bot.send_message(message.chat.id, "❌ أرسل الكمية بالأرقام فقط.")
            return
            
        qty = int(message.text)
        service_id = step_data.get('service_id')
        link = step_data.get('link')
        
        if str(service_id).startswith("game_"):
            total_cost = round((1.00 / 1000) * qty, 2)
            markup = smm_confirm_keyboard(service_id, qty, total_cost)
            bot.send_message(
                message.chat.id,
                f"📋 **تأكيد تفاصيل الطلب:**\n\n"
                f"🔗 الرابط/المعرف: `{link}`\n"
                f"📊 الكمية: {qty}\n"
                f"💵 التكلفة الإجمالية: `${total_cost:.2f}`\n\n"
                f"اضغط على تأكيد لإرسال الطلب:",
                parse_mode="Markdown",
                reply_markup=markup
            )
            return
            
        services_data = get_cached_smm_services()
        service_rate = 0.0
        min_q = 1
        max_q = 1000000
        
        for srv in services_data:
            if str(srv.get('service')) == str(service_id):
                service_rate = float(srv.get('rate', 0))
                min_q = int(srv.get('min', 1))
                max_q = int(srv.get('max', 1000000))
                break
                    
        if service_rate == 0.0:
            bot.send_message(message.chat.id, "❌ حدث خطأ في النظام، الخدمة غير متاحة.")
            del USER_STEPS[user_id]
            return

        if qty < min_q or qty > max_q:
            bot.send_message(message.chat.id, f"❌ الكمية غير مسموحة.\n📉 الحد الأدنى: {min_q}\n📈 الحد الأقصى: {max_q}\n\nأرسل الكمية الصحيحة مجدداً:")
            return

        original_cost = (qty / 1000) * service_rate
        total_cost_with_profit = round(original_cost * 1.10, 3) 

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        balance = cursor.fetchone()[0]
        conn.close()
        
        if balance < total_cost_with_profit:
            bot.send_message(message.chat.id, f"❌ رصيدك غير كافٍ.\n💵 تكلفة الطلب: ${total_cost_with_profit:.3f}\n💰 رصيدك: ${balance:.2f}", reply_markup=back_button())
            del USER_STEPS[user_id]
            return

        markup = smm_confirm_keyboard(service_id, qty, total_cost_with_profit)
        bot.send_message(
            message.chat.id,
            f"📋 **تأكيد تفاصيل طلب الرشق:**\n\n"
            f"🔗 الرابط: `{link}`\n"
            f"📊 الكمية: {qty}\n"
            f"💵 التكلفة الإجمالية: `${total_cost_with_profit:.3f}`\n\n"
            f"اضغط على زر التأكيد أدناه للمتابعة:",
            parse_mode="Markdown",
            reply_markup=markup
        )

@bot.message_handler(func=lambda msg: not msg.text.startswith('/'), content_types=['text'])
def handle_ai_chat(message):
    user_id = message.from_user.id
    if is_user_banned(user_id): return
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT ai_balance FROM users WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    
    if res and res[0] > 0:
        cursor.execute("UPDATE users SET ai_balance = ai_balance - 1 WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()
        try:
            response = ai_model.generate_content(message.text)
            bot.reply_to(message, response.text)
        except:
            bot.reply_to(message, "⚠️ خطأ في الاتصال بالذكاء الاصطناعي.")
    else:
        conn.close()
        bot.reply_to(message, "❌ نفد رصيد أسئلة الذكاء الاصطناعي.")

set_bot_commands()
print("Bot is running smoothly with Full Menu Commands...")
bot.infinity_polling()
