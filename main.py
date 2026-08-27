import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time
import requests
import sqlite3

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
    dynamic_smm_keyboard
)

bot = telebot.TeleBot(TOKEN)

# ==================== إعدادات قاعدة البيانات والتأكد من الجداول ====================
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

# ==================== إعدادات API موقع الرشق (SMM Stone) ====================
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
            if ('telegram' in name_cat or 'تيليجرام' in name_cat or 'تليجرام' in name_cat) and ('member' in name_cat or 'sub' in name_cat or 'متابع' in name_cat or 'عضو' in name_cat): match = True
        elif target_type == 'tg_view':
            if ('telegram' in name_cat or 'تيليجرام' in name_cat or 'تليجرام' in name_cat) and ('view' in name_cat or 'post' in name_cat or 'مشاهد' in name_cat): match = True
        elif target_type == 'ig_fol':
            if ('instagram' in name_cat or 'انستجرام' in name_cat or 'انستا' in name_cat) and ('follow' in name_cat or 'متابع' in name_cat): match = True
        elif target_type == 'ig_like':
            if ('instagram' in name_cat or 'انستجرام' in name_cat or 'انستا' in name_cat) and ('like' in name_cat or 'لايك' in name_cat or 'اعجاب' in name_cat): match = True
        elif target_type == 'tk_view':
            if ('tiktok' in name_cat or 'تيك توك' in name_cat) and ('view' in name_cat or 'مشاهد' in name_cat): match = True
        elif target_type == 'tk_fol':
            if ('tiktok' in name_cat or 'تيك توك' in name_cat) and ('follow' in name_cat or 'متابع' in name_cat): match = True
        elif target_type == 'fb_fol':
            if ('facebook' in name_cat or 'فيسبوك' in name_cat or 'فيس' in name_cat) and ('follow' in name_cat or 'like' in name_cat or 'متابع' in name_cat or 'اعجاب' in name_cat): match = True
        elif target_type == 'yt_view':
            if ('youtube' in name_cat or 'يوتيوب' in name_cat) and ('view' in name_cat or 'مشاهد' in name_cat): match = True
        
        if match:
            filtered.append(srv)
            
    if not filtered and services:
        return services[:15]
        
    return filtered

# ==================== أوامر البدء والرسائل ====================
@bot.message_handler(commands=['start'])
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

    # التنقل العام
    if call.data == "back_main":
        if user_id in USER_STEPS:
            del USER_STEPS[user_id]
        user_data = get_or_create_user(user_id, call.from_user.first_name)
        text = (f"💠 أهلاً بك عزيزي في البوت الشامل 💠\n\n👤 حسابك: {ADMIN_USERNAME}\n💰 رصيدك الحالي: ${user_data[2]:.2f}\n🤖 رصيد أسئلة الذكاء: {user_data[3]} سؤال\n\n📌 استخدم الأزرار بالأسفل لتنفيذ طلباتك:")
        try: bot.edit_message_text(text, chat_id, message_id, reply_markup=main_keyboard(user_id))
        except: bot.send_message(chat_id, text, reply_markup=main_keyboard(user_id))

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

    elif call.data == "recharge_menu":
        bot.edit_message_text("🎳 قسم شحن الرصيد / الاشتراكات\n\nاختر وسيلة الدفع التي تناسبك:", chat_id, message_id, reply_markup=recharge_keyboard())

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

    # أقسام الرشق المتقدمة (SMM Stone)
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
            
            msg = (f"✅ **الخدمة المختارة:** {name}\n"
                   f"💰 **السعر (لكل 1000):** `${price_profit}`\n"
                   f"📉 **الحد الأدنى:** {min_q}\n"
                   f"📈 **الحد الأقصى:** {max_q}\n\n"
                   f"🔗 **أرسل الرابط أو المعرف (ID) المطلوب للخدمة الآن:**")
        else:
            msg = "🔗 أرسل الرابط أو المعرف (ID) المطلوب للخدمة الآن:"

        USER_STEPS[user_id] = {'step': 'WAITING_LINK', 'service_id': service_id}
        bot.send_message(chat_id, msg, parse_mode="Markdown")

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
        bot.edit_message_text(msg, chat_id, message_id, parse_mode="Markdown", reply_markup=back_button())

    elif call.data == "other_services":
        bot.edit_message_text("🛸 خدمات وميزات أخرى قادمة قريبأً.", chat_id, message_id, reply_markup=back_button())

# ==================== استقبال الرسائل والخطوات ====================
@bot.message_handler(func=lambda msg: msg.from_user.id in USER_STEPS)
def handle_user_steps(message):
    user_id = message.from_user.id
    step_data = USER_STEPS.get(user_id)
    step = step_data.get('step')

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
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
            balance = cursor.fetchone()[0]
            if balance < total_cost:
                bot.send_message(message.chat.id, "❌ رصيدك غير كافٍ.")
                del USER_STEPS[user_id]
                return
            cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (total_cost, user_id))
            conn.commit()
            conn.close()
            del USER_STEPS[user_id]
            bot.send_message(message.chat.id, f"✅ تم تسجيل طلب اللعبة بقيمة ${total_cost:.2f}.", reply_markup=back_button())
            return
            
        services_data = get_cached_smm_services()
        service_rate = 0.0
        
        for srv in services_data:
            if str(srv.get('service')) == str(service_id):
                service_rate = float(srv.get('rate', 0))
                break
                    
        if service_rate == 0.0:
            bot.send_message(message.chat.id, "❌ حدث خطأ في النظام، الخدمة غير متاحة.")
            del USER_STEPS[user_id]
            return

        original_cost = (qty / 1000) * service_rate
        total_cost_with_profit = round(original_cost * 1.10, 3) 

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        balance = cursor.fetchone()[0]
        
        if balance < total_cost_with_profit:
            bot.send_message(message.chat.id, f"❌ رصيدك غير كافٍ.\n💵 تكلفة الطلب: ${total_cost_with_profit:.3f}\n💰 رصيدك: ${balance:.2f}")
            del USER_STEPS[user_id]
            conn.close()
            return
            
        order_response = smm_request('add', service=service_id, link=link, quantity=qty)
        
        if order_response and 'order' in order_response:
            order_id = order_response['order']
            cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (total_cost_with_profit, user_id))
            conn.commit()
            bot.send_message(message.chat.id, f"✅ تم تنفيذ طلبك بنجاح!\n\n🆔 رقم الطلب: `{order_id}`\n💵 التكلفة المخصومة: `${total_cost_with_profit:.3f}`", parse_mode="Markdown", reply_markup=back_button())
        else:
            err_msg = order_response.get('error', 'خطأ غير معروف') if order_response else 'فشل الاتصال'
            bot.send_message(message.chat.id, f"❌ حدث خطأ من سيرفر الرشق: {err_msg}\n(لم يتم خصم الرصيد).")
            
        conn.close()
        del USER_STEPS[user_id]

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

print("Bot is running smoothly...")
bot.infinity_polling()
