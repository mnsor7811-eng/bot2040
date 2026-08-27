import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time
import requests

from config import (
    TOKEN, ADMIN_ID, ADMIN_USERNAME, REWARD_PER_INVITE, MIN_TRANSFER_AMOUNT, 
    DEFAULT_PRICE, PAYMENT_DETAILS, SERVERS, USER_STEPS, ai_model,
    get_db, get_or_create_user, is_user_banned, fetch_server_prices, 
    grizzly_request, get_clean_country_info
)

from keyboards import (
    main_keyboard, back_button, admin_back_button, recharge_keyboard,
    servers_keyboard, services_keyboard, countries_keyboard_fast,
    active_number_keyboard, smm_main_keyboard, games_keyboard, boost_keyboard
)

bot = telebot.TeleBot(TOKEN)

# ==================== إعدادات API موقع الرشق (SMM Stone) ====================
SMM_API_KEY = "Db5f57b29759abc91a56be0854b35e2e"
SMM_API_URL = "https://smmstone.com/api/v2"

def smm_request(action, **kwargs):
    payload = {'key': SMM_API_KEY, 'action': action}
    payload.update(kwargs)
    try:
        response = requests.post(SMM_API_URL, data=payload)
        return response.json()
    except Exception as e:
        print(f"SMM API Error: {e}")
        return None

# ==================== 1. أوامر البدء والرسائل ====================
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

# ==================== 2. معالجة الأزرار (Callbacks) ====================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    if call.data == "ignore":
        return

    if is_user_banned(user_id) and str(user_id) != str(ADMIN_ID):
        bot.send_message(chat_id, "أنت محظور من استخدام البوت.")
        return

    # ------------------ لوحة الإدارة الكبرى ------------------
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

        try:
            bot.edit_message_text("⚙️ **أهلاً بك في لوحة الإدارة الكبرى**\n\nاختر العملية التي تريد تنفيذها:", chat_id, message_id, parse_mode="Markdown", reply_markup=markup)
        except Exception:
            bot.send_message(chat_id, "⚙️ **أهلاً بك في لوحة الإدارة الكبرى**\n\nاختر العملية التي تريد تنفيذها:", parse_mode="Markdown", reply_markup=markup)
        return

    elif call.data == "admin_stats":
        if str(user_id) != str(ADMIN_ID):
            return

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

        try:
            bot.edit_message_text(msg, chat_id, message_id, parse_mode="Markdown", reply_markup=admin_back_button())
        except Exception:
            bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data == "admin_search_user":
        if str(user_id) != str(ADMIN_ID):
            return
        USER_STEPS[user_id] = {'step': 'ADMIN_SEARCH_USER'}
        bot.send_message(chat_id, "🔍 أرسل اسم المستخدم أو المعرف (@username) أو الآيدي الخاص به للبحث عنه:", reply_markup=admin_back_button())
        return

    elif call.data == "admin_recent_users":
        if str(user_id) != str(ADMIN_ID):
            return

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
            u_name = str(u_name) if u_name else "بدون اسم"
            u_uname = str(u_uname) if u_uname else "لا يوجد"
            u_bal = float(u_bal) if u_bal is not None else 0.0
            u_ai = int(u_ai) if u_ai is not None else 0
            status = "محظور 🚫" if u_ban == 1 else "نشط ✅"
            
            card_msg = (f"👤 الاسم: {u_name}\n"
                        f"🏷️ اليوزر: {u_uname}\n"
                        f"🆔 الآيدي: {u_id}\n"
                        f"💰 الرصيد: ${u_bal:.2f}\n"
                        f"🤖 أسئلة AI: {u_ai}\n"
                        f"📌 الحالة: {status}")
            
            mk = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("➕ شحن رصيد", callback_data=f"act_add_{u_id}"), InlineKeyboardButton("➖ خصم رصيد", callback_data=f"act_deduct_{u_id}"))
            mk.row(InlineKeyboardButton("🤖 شحن AI", callback_data=f"act_ai_{u_id}"), InlineKeyboardButton("🚫 حظر / فك", callback_data=f"act_ban_{u_id}"))
            
            try:
                bot.send_message(chat_id, card_msg, reply_markup=mk)
            except Exception as e:
                print(f"Error sending user card: {e}")
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
        if target_id == ADMIN_ID:
            bot.answer_callback_query(call.id, "❌ لا يمكنك حظر نفسك.", show_alert=True)
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (target_id,))
        res = cursor.fetchone()
        if res:
            new_status = 0 if res[0] == 1 else 1
            cursor.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (new_status, target_id))
            conn.commit()
            st_text = "🚫 تم حظر المستخدم بنجاح." if new_status == 1 else "🟢 تم إلغاء حظر المستخدم بنجاح."
            bot.send_message(chat_id, st_text, reply_markup=admin_back_button())
        conn.close()
        return

    elif call.data == "admin_deduct_balance":
        if str(user_id) != str(ADMIN_ID):
            return
        USER_STEPS[user_id] = {'step': 'ADMIN_DEDUCT_BALANCE'}
        bot.send_message(chat_id, "➖ أرسل الآيدي والمبلغ المراد خصمه بالشكل التالي:\n`ID المبلغ`\nمثال: `123456789 2.5`", parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data == "admin_add_ai":
        if str(user_id) != str(ADMIN_ID):
            return
        USER_STEPS[user_id] = {'step': 'ADMIN_ADD_AI'}
        bot.send_message(chat_id, "🤖 أرسل الآيدي وعدد الأسئلة المراد إضافتها بالشكل التالي:\n`ID العدد`\nمثال: `123456789 50`", parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data == "admin_broadcast":
        if str(user_id) != str(ADMIN_ID):
            return
        USER_STEPS[user_id] = {'step': 'ADMIN_BROADCAST'}
        bot.send_message(chat_id, "📢 أرسل النص أو الوسائط التي تريد إذاعتها لجميع المستخدمين الآن:", reply_markup=admin_back_button())
        return

    elif call.data == "admin_add_balance":
        if str(user_id) != str(ADMIN_ID):
            return
        USER_STEPS[user_id] = {'step': 'ADMIN_ADD_BALANCE'}
        bot.send_message(chat_id, "💰 أرسل الآيدي والمبلغ بالشكل التالي:\n`ID المبلغ`\nمثال: `123456789 5.5`", parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data == "admin_ban_menu":
        if str(user_id) != str(ADMIN_ID):
            return
        USER_STEPS[user_id] = {'step': 'ADMIN_BAN_USER'}
        bot.send_message(chat_id, "🚫 أرسل آيدي المستخدم المراد حظره أو إلغاء حظره:", reply_markup=admin_back_button())
        return

    if call.data == "back_main":
        if user_id in USER_STEPS:
            del USER_STEPS[user_id]
        user_data = get_or_create_user(user_id, call.from_user.first_name)
        text = (f"💠 أهلاً بك عزيزي في البوت الشامل 💠\n\n"
                f"👤 حسابك: {ADMIN_USERNAME}\n"
                f"💰 رصيدك الحالي: ${user_data[2]:.2f}\n"
                f"🤖 رصيد أسئلة الذكاء: {user_data[3]} سؤال\n\n"
                f"📌 استخدم الأزرار بالأسفل لتنفيذ طلباتك:")
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=main_keyboard(user_id))
        except Exception:
            bot.send_message(chat_id, text, reply_markup=main_keyboard(user_id))

    elif call.data.startswith("pay_"):
        pay_key = call.data.replace("pay_", "")
        pay_info = PAYMENT_DETAILS.get(pay_key)
        
        if pay_info:
            msg = (f"📌 تفاصيل الدفع عبر {pay_info['name']}\n\n"
                   f"🏷️ رقم الحساب / المعرف: {pay_info['acc']}\n"
                   f"💵 أقل مبلغ للتحويل: {pay_info['min']}\n"
                   f"💱 سعر الصرف: {pay_info['rate']}\n\n"
                   f"⚠️ خطوات الشحن:\n"
                   f"1. قم بالتحويل إلى رقم الحساب أعلاه.\n"
                   f"2. أرسل صورة إشعار التحويل مع الآيدي الخاص بك ({user_id}) إلى الإدارة:\n"
                   f"👤 الإدارة: {ADMIN_USERNAME}\n\n"
                   f"سيتم شحن رصيدك فوراً بعد التحقق!")
            
            back_markup = InlineKeyboardMarkup()
            back_markup.add(InlineKeyboardButton("🔙 العودة لوسائل الدفع", callback_data="recharge_menu"))
            
            try:
                bot.send_message(chat_id, msg, reply_markup=back_markup)
            except Exception as e:
                print(f"Error sending payment details: {e}")

    elif call.data == "transfer":
        USER_STEPS[user_id] = {'step': 'TRANSFER_TARGET'}
        text = (f"🔄 قسم تحويل الرصيد بين الحسابات\n\n"
                f"✨ الميزات: عمولة التحويل 0% (مجاناً)\n"
                f"💵 أقل مبلغ للتحويل: $1.00\n\n"
                f"📌 يرجى إرسال آيدي (User ID) الشخص المراد التحويل إليه الآن:")
        bot.edit_message_text(text, chat_id, message_id, reply_markup=back_button())

    elif call.data == "recharge_menu":
        text = "🎳 قسم شحن الرصيد / الاشتراكات\n\nاختر وسيلة الدفع التي تناسبك من القائمة أدناه:"
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=recharge_keyboard())
        except Exception:
            bot.send_message(chat_id, text, reply_markup=recharge_keyboard())

    elif call.data == "buy_number":
        text = "📞 قسم شراء الأرقام الافتراضية\n\nاختر السيرفر / الموقع الذي تريد الشراء منه:"
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=servers_keyboard())
        except Exception:
            bot.send_message(chat_id, text, reply_markup=servers_keyboard())

    elif call.data.startswith("select_server_"):
        server_id = call.data.split("_")[2]
        server_name = SERVERS[server_id]['name']
        text = f"⚙️ تم اختيار: {server_name}\n\nاختر التطبيق المراد تفعيله:"
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=services_keyboard(server_id))
        except Exception:
            bot.send_message(chat_id, text, reply_markup=services_keyboard(server_id))

    elif call.data.startswith("srv_app_"):
        _, _, server_id, srv_code = call.data.split("_")
        markup = countries_keyboard_fast(server_id, srv_code, page=0)
        text = f"🌐 اختر الدولة المطلوبة لـ ({srv_code.upper()}):"
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
        except Exception:
            bot.send_message(chat_id, text, reply_markup=markup)

    elif call.data.startswith("pg_"):
        _, server_id, srv_code, page = call.data.split("_")
        page = int(page)
        markup = countries_keyboard_fast(server_id, srv_code, page=page)
        text = f"🌐 اختر الدولة المطلوبة لـ ({srv_code.upper()}):"
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
        except Exception:
            pass

    elif call.data.startswith("b_"):
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
            
            msg = (f"🆔 **رقم الطلب** : `{tz_id}`\n"
                   f"🌐 **الدولة** : {c_name} {c_flag}\n"
                   f"📞 **الرقم** : `{formatted_phone}`\n"
                   f"📩 **الكود** : `قيد الانتظار... ⏳`\n"
                   f"🔍 **الحالة** : `WAITING_CODE`\n"
                   f"🛍️ **التطبيق** : `{srv_code.upper()}`\n"
                   f"💵 **السعر** : `${price:.2f}`\n\n"
                   f"📋 *اضغط على الرقم أو رقم الطلب لنسخه فوراً*")
            
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
            bot.send_message(chat_id, f"🎉 **تم استلام كود التفعيل بنجاح!**\n\n🔑 **الكود** : `{code}`\n\n(اضغط على الكود لنسخه)", parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "⏳ لم يتم استلام الكود بعد. يرجى الانتظار والمحاولة مجدداً.", show_alert=True)

    elif call.data.startswith("cancel_num_") or call.data.startswith("change_num_"):
        parts = call.data.split("_")
        action_type = parts[0]
        server_id, tz_id = parts[2], parts[3]
        srv = SERVERS.get(server_id)
        grizzly_request({'action': 'setStatus', 'status': '8', 'id': tz_id}, srv['api_key'], srv['url'])
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, cost, status, service, country_code FROM purchases WHERE tz_id = ?', (tz_id,))
        purchase = cursor.fetchone()
        
        if purchase and purchase[2] == 'PENDING':
            cost, srv_code, country_code = purchase[1], purchase[3], purchase[4]
            cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (cost, user_id))
            cursor.execute('UPDATE purchases SET status = "CANCELLED" WHERE tz_id = ?', (tz_id,))
            conn.commit()
            conn.close()
            
            if action_type == "change_num":
                bot.edit_message_text(f"🔄 تم إلغاء الرقم السابق وإعادة مبلغ (${cost:.2f}) لحسابك. جاري طلب رقم جديد...", chat_id, message_id)
                prices = fetch_server_prices(server_id, srv_code)
                price = prices.get(str(country_code), DEFAULT_PRICE)
                res = grizzly_request({'action': 'getNumber', 'service': srv_code, 'country': country_code}, srv['api_key'], srv['url'])
                if "ACCESS_NUMBER" in res:
                    parts = res.split(":")
                    new_tz_id, new_raw_phone = parts[1], parts[2]
                    formatted_phone = f"+{new_raw_phone}" if not new_raw_phone.startswith("+") else new_raw_phone
                    c_name, c_flag = get_clean_country_info(country_code)
                    
                    conn2 = get_db()
                    cursor2 = conn2.cursor()
                    cursor2.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (price, user_id))
                    cursor2.execute('INSERT INTO purchases (user_id, tz_id, phone, service, cost, country_code) VALUES (?, ?, ?, ?, ?, ?)',
                                   (user_id, new_tz_id, formatted_phone, srv_code, price, country_code))
                    conn2.commit()
                    conn2.close()
                    
                    msg = (f"🆔 **رقم الطلب الجديد** : `{new_tz_id}`\n"
                           f"🌐 **الدولة** : {c_name} {c_flag}\n"
                           f"📞 **الرقم** : `{formatted_phone}`\n"
                           f"📩 **الكود** : `قيد الانتظار... ⏳`\n"
                           f"🔍 **الحالة** : `WAITING_CODE`\n"
                           f"🛍️ **التطبيق** : `{srv_code.upper()}`\n"
                           f"💵 **السعر** : `${price:.2f}`\n\n"
                           f"📋 *اضغط على الرقم لنسخه فوراً*")
                    bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=active_number_keyboard(new_tz_id, server_id))
                else:
                    bot.send_message(chat_id, "❌ تعذر تلقي رقم جديد حالياً.")
            else:
                bot.edit_message_text(f"❌ تم إلغاء الرقم بنجاح وإعادة مبلغ (${cost:.2f}) إلى رصيدك.", chat_id, message_id, reply_markup=back_button())
        else:
            conn.close()
            bot.answer_callback_query(call.id, "العملية ملغاة أو منتهية مسبقاً.", show_alert=True)

    elif call.data == "smm_main":
        text = (f"🚀 الرشق وشحن الألعاب والبرامج 🔭\n"
                f"💣 -------------------------\n"
                f"▫️ زيادة متابعين وتفاعلات ومشاهدات\n"
                f"▫️ سيفرات متعدده وجودة واسعار ممتازة\n"
                f"▫️ شحن الألعاب المختلفة والبرامج\n"
                f"⬇️ -------------------------")
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=smm_main_keyboard())
        except Exception:
            bot.send_message(chat_id, text, reply_markup=smm_main_keyboard())

    elif call.data == "games_menu":
        text = (f"🎮 شحن الألعاب وبرامج بلاس 🕹️\n"
                f"اسحن الالعاب وبرامجك وطور من شخصياتك وحساباتك مع بوت بلاس 😎🌐\n\n"
                f"جميع الخدمات في الأسفل تعمل تلقائياً ✅")
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=games_keyboard())
        except Exception:
            bot.send_message(chat_id, text, reply_markup=games_keyboard())

    elif call.data == "boost_menu":
        text = (f"🐙 توفر خدمات متابعين وإعجابات ومشاهدات بأسعار مناسبة تتفاوت من حيث الجودة والسرعة\n\n"
                f"🧛‍♂️ الرجاء إختيار الخدمة المطلوبة من القائمة أدناه :")
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=boost_keyboard())
        except Exception:
            bot.send_message(chat_id, text, reply_markup=boost_keyboard())

    elif call.data.startswith("game_") or call.data.startswith("smm_"):
        service_id = call.data
        if call.data.startswith("smm_"):
            service_id = call.data.split("_")[1] # استخراج الـ ID الخاص بموقع SMM Stone
            
        USER_STEPS[user_id] = {'step': 'WAITING_LINK', 'service_id': service_id}
        bot.send_message(chat_id, "🔗 أرسل الرابط أو المعرف (ID) المطلوب للخدمة الآن:")

    elif call.data == "free_ruble":
        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,))
        invite_count = cursor.fetchone()[0]
        conn.close()
        earned_total = invite_count * REWARD_PER_INVITE
        msg = (f"💎 نظام اربح رصيد مجاني 💎\n\n"
               f"انسخ رابط الإحالة وشاركه مع أصدقائك:\n`{ref_link}`\n\n"
               f"👥 عدد المدعوين: {invite_count}\n"
               f"💵 إجمالي الأرباح: ${earned_total:.2f}")
        bot.edit_message_text(msg, chat_id, message_id, parse_mode="Markdown", reply_markup=back_button())

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

# ==================== 3. استقبال المخرجات والرسائل ====================
@bot.message_handler(func=lambda msg: msg.from_user.id in USER_STEPS)
def handle_user_steps(message):
    user_id = message.from_user.id
    step_data = USER_STEPS.get(user_id)
    step = step_data.get('step')

    # لوحة الإدارة (لم يتم المساس بها)
    if str(user_id) == str(ADMIN_ID):
        if step == 'ADMIN_BROADCAST':
            del USER_STEPS[user_id]
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users")
            all_users = cursor.fetchall()
            conn.close()
            success_count = 0
            fail_count = 0
            for (u_id,) in all_users:
                try:
                    bot.copy_message(u_id, message.chat.id, message.message_id)
                    success_count += 1
                    time.sleep(0.05)
                except Exception:
                    fail_count += 1
            bot.send_message(message.chat.id, f"📢 **تم إرسال الإذاعة بنجاح!**\n\n✅ تم الإرسال إلى: `{success_count}` مستخدم\n❌ فشل الإرسال إلى: `{fail_count}` مستخدم", parse_mode="Markdown", reply_markup=admin_back_button())
            return
        elif step == 'ADMIN_SEARCH_USER':
            del USER_STEPS[user_id]
            query = message.text.strip().replace("@", "")
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, name, username, balance, ai_balance, is_banned FROM users WHERE name LIKE ? OR username LIKE ? OR user_id = ?", ('%' + query + '%', '%' + query + '%', query))
            users = cursor.fetchall()
            conn.close()
            if not users:
                bot.send_message(message.chat.id, "❌ لم يتم العثور على أي مستخدم بهذا الاسم أو المعرف أو الآيدي.", reply_markup=admin_back_button())
                return
            bot.send_message(message.chat.id, f"🔍 تم العثور على ({len(users)}) نتيجة:")
            for u in users:
                u_id, u_name, u_uname, u_bal, u_ai, u_ban = u
                u_name = str(u_name) if u_name else "بدون اسم"
                u_uname = str(u_uname) if u_uname else "لا يوجد"
                u_bal = float(u_bal) if u_bal is not None else 0.0
                u_ai = int(u_ai) if u_ai is not None else 0
                status = "محظور 🚫" if u_ban == 1 else "نشط ✅"
                res = (f"👤 الاسم: {u_name}\n🏷️ اليوزر: {u_uname}\n🆔 الآيدي: {u_id}\n💰 الرصيد: ${u_bal:.2f}\n🤖 أسئلة AI: {u_ai}\n📌 الحالة: {status}")
                mk = InlineKeyboardMarkup()
                mk.row(InlineKeyboardButton("➕ شحن رصيد", callback_data=f"act_add_{u_id}"), InlineKeyboardButton("➖ خصم رصيد", callback_data=f"act_deduct_{u_id}"))
                mk.row(InlineKeyboardButton("🤖 شحن AI", callback_data=f"act_ai_{u_id}"), InlineKeyboardButton("🚫 حظر / فك", callback_data=f"act_ban_{u_id}"))
                bot.send_message(message.chat.id, res, reply_markup=mk)
            return
        elif step == 'ADMIN_ADD_BALANCE_DIRECT':
            del USER_STEPS[user_id]
            target_id = step_data['target_id']
            try:
                amount = float(message.text.strip())
            except ValueError:
                bot.send_message(message.chat.id, "❌ المبلغ غير صالح.", reply_markup=admin_back_button())
                return
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_id))
            conn.commit()
            conn.close()
            bot.send_message(message.chat.id, f"✅ تم إضافة `${amount:.2f}` إلى رصيد المستخدم (`{target_id}`) بنجاح.", parse_mode="Markdown", reply_markup=admin_back_button())
            return
        elif step == 'ADMIN_DEDUCT_BALANCE_DIRECT':
            del USER_STEPS[user_id]
            target_id = step_data['target_id']
            try:
                amount = float(message.text.strip())
            except ValueError:
                bot.send_message(message.chat.id, "❌ المبلغ غير صالح.", reply_markup=admin_back_button())
                return
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, target_id))
            conn.commit()
            conn.close()
            bot.send_message(message.chat.id, f"✅ تم خصم `${amount:.2f}` من رصيد المستخدم (`{target_id}`).", parse_mode="Markdown", reply_markup=admin_back_button())
            return
        elif step == 'ADMIN_ADD_AI_DIRECT':
            del USER_STEPS[user_id]
            target_id = step_data['target_id']
            if not message.text.strip().isdigit():
                bot.send_message(message.chat.id, "❌ يرجى إدخال عدد صحيح.", reply_markup=admin_back_button())
                return
            count = int(message.text.strip())
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET ai_balance = ai_balance + ? WHERE user_id = ?", (count, target_id))
            conn.commit()
            conn.close()
            bot.send_message(message.chat.id, f"✅ تم إضافة {count} سؤال ذكاء اصطناعي للمستخدم (`{target_id}`).", parse_mode="Markdown", reply_markup=admin_back_button())
            return
        elif step == 'ADMIN_ADD_BALANCE':
            del USER_STEPS[user_id]
            text = message.text.strip().split()
            if len(text) < 2 or not text[0].isdigit():
                bot.send_message(message.chat.id, "❌ الصيغة غير صحيحة.", reply_markup=admin_back_button())
                return
            target_id = int(text[0])
            try:
                amount = float(text[1])
            except ValueError:
                bot.send_message(message.chat.id, "❌ المبلغ غير صالح.", reply_markup=admin_back_button())
                return
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_id))
            conn.commit()
            conn.close()
            bot.send_message(message.chat.id, f"✅ تم إضافة `${amount:.2f}`.", reply_markup=admin_back_button())
            return
        elif step == 'ADMIN_DEDUCT_BALANCE':
            del USER_STEPS[user_id]
            text = message.text.strip().split()
            if len(text) < 2 or not text[0].isdigit():
                bot.send_message(message.chat.id, "❌ الصيغة غير صحيحة.", reply_markup=admin_back_button())
                return
            target_id = int(text[0])
            try:
                amount = float(text[1])
            except ValueError:
                bot.send_message(message.chat.id, "❌ المبلغ غير صالح.", reply_markup=admin_back_button())
                return
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, target_id))
            conn.commit()
            conn.close()
            bot.send_message(message.chat.id, f"✅ تم خصم `${amount:.2f}`.", reply_markup=admin_back_button())
            return
        elif step == 'ADMIN_ADD_AI':
            del USER_STEPS[user_id]
            text = message.text.strip().split()
            if len(text) < 2 or not text[0].isdigit() or not text[1].isdigit():
                bot.send_message(message.chat.id, "❌ الصيغة غير صحيحة.", reply_markup=admin_back_button())
                return
            target_id = int(text[0])
            count = int(text[1])
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET ai_balance = ai_balance + ? WHERE user_id = ?", (count, target_id))
            conn.commit()
            conn.close()
            bot.send_message(message.chat.id, f"✅ تم الإضافة بنجاح.", reply_markup=admin_back_button())
            return
        elif step == 'ADMIN_BAN_USER':
            del USER_STEPS[user_id]
            if not message.text.strip().isdigit():
                bot.send_message(message.chat.id, "❌ يرجى إرسال الآيدي بالأرقام فقط.", reply_markup=admin_back_button())
                return
            target_id = int(message.text.strip())
            if target_id == ADMIN_ID:
                bot.send_message(message.chat.id, "❌ لا يمكنك حظر نفسك.", reply_markup=admin_back_button())
                return
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (target_id,))
            res = cursor.fetchone()
            if not res:
                bot.send_message(message.chat.id, "❌ المستخدم غير مسجل في البوت.", reply_markup=admin_back_button())
                conn.close()
                return
            new_status = 0 if res[0] == 1 else 1
            cursor.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (new_status, target_id))
            conn.commit()
            conn.close()
            status_text = "🚫 تم حظر المستخدم بنجاح." if new_status == 1 else "🟢 تم إلغاء حظر المستخدم بنجاح."
            bot.send_message(message.chat.id, status_text, reply_markup=admin_back_button())
            return

    # باقي الخطوات للمستخدمين
    if step == 'TRANSFER_TARGET':
        if not message.text.strip().isdigit():
            bot.send_message(message.chat.id, "❌ يرجى إرسال الآيدي بالأرقام فقط.")
            return
        target_id = int(message.text.strip())
        if target_id == user_id:
            bot.send_message(message.chat.id, "❌ لا يمكنك التحويل لنفسك.")
            return
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM users WHERE user_id = ?', (target_id,))
        target_user = cursor.fetchone()
        conn.close()
        if not target_user:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود في البوت.")
            return
        step_data['target_id'] = target_id
        step_data['target_name'] = target_user[0]
        step_data['step'] = 'TRANSFER_AMOUNT'
        bot.send_message(message.chat.id, f"👤 المستلم: {target_user[0]}\n💵 أرسل المبلغ بالدولار (الحد الأدنى $1):")

    elif step == 'TRANSFER_AMOUNT':
        try:
            amount = float(message.text.strip())
        except ValueError:
            bot.send_message(message.chat.id, "❌ يرجى إرسال رقم صحيح.")
            return
        if amount < MIN_TRANSFER_AMOUNT:
            bot.send_message(message.chat.id, f"❌ الحد الأدنى ${MIN_TRANSFER_AMOUNT}")
            return
        target_id = step_data['target_id']
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        my_bal = cursor.fetchone()[0]
        if my_bal < amount:
            bot.send_message(message.chat.id, "❌ رصيدك غير كافٍ.")
            del USER_STEPS[user_id]
            conn.close()
            return
        cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (amount, user_id))
        cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, target_id))
        conn.commit()
        conn.close()
        del USER_STEPS[user_id]
        bot.send_message(message.chat.id, f"✅ تم تحويل ${amount:.2f} بنجاح.", reply_markup=back_button())
        try:
            bot.send_message(target_id, f"🎉 وصلك تحويل بقيمة ${amount:.2f}!")
        except Exception:
            pass

    elif step == 'WAITING_LINK':
        step_data['link'] = message.text
        step_data['step'] = 'WAITING_QTY'
        bot.send_message(message.chat.id, "🔢 أرسل الكمية المطلوبة أو الباقة المناسبة:")

    elif step == 'WAITING_QTY':
        if not message.text.isdigit():
            bot.send_message(message.chat.id, "❌ أرسل الكمية بالأرقام فقط.")
            return
            
        qty = int(message.text)
        service_id = step_data.get('service_id')
        link = step_data.get('link')
        
        # معالجة شحن الألعاب (بشكل وهمي حالياً لحين إرسال موقع الألعاب الخاص بك)
        if str(service_id).startswith("game_"):
            total_cost = round((1.00 / 1000) * qty, 2)
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
            balance = cursor.fetchone()[0]
            if balance < total_cost:
                bot.send_message(message.chat.id, "❌ رصيدك غير كافٍ لتنفيذ هذا الطلب.")
                del USER_STEPS[user_id]
                conn.close()
                return
            cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (total_cost, user_id))
            conn.commit()
            conn.close()
            del USER_STEPS[user_id]
            bot.send_message(message.chat.id, f"✅ تم تسجيل طلب اللعبة بنجاح بقيمة ${total_cost:.2f} وسيتم التنفيذ تلقائياً.", reply_markup=back_button())
            return
            
        # معالجة خدمات السوشيال ميديا وربطها بـ SMM Stone
        services_data = smm_request('services')
        service_rate = 0.0
        
        if services_data and isinstance(services_data, list):
            for srv in services_data:
                if str(srv.get('service')) == str(service_id):
                    service_rate = float(srv.get('rate', 0))
                    break
                    
        if service_rate == 0.0:
            bot.send_message(message.chat.id, "❌ عذراً، الخدمة غير متاحة حالياً أو هناك خطأ في جلب السعر من السيرفر. تواصل مع الإدارة لمعرفة ID الخدمة الصحيح.")
            del USER_STEPS[user_id]
            return

        # حساب التكلفة وإضافة نسبة ربح 10%
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
            
        # إرسال الطلب فعلياً למوقع SMM Stone
        order_response = smm_request('add', service=service_id, link=link, quantity=qty)
        
        if order_response and 'order' in order_response:
            order_id = order_response['order']
            cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (total_cost_with_profit, user_id))
            conn.commit()
            bot.send_message(message.chat.id, f"✅ تم تنفيذ طلبك بنجاح!\n\n🆔 رقم الطلب: `{order_id}`\n💵 التكلفة المخصومة: `${total_cost_with_profit:.3f}`\n\n(تمت إضافة 10% كرسوم خدمة)", parse_mode="Markdown", reply_markup=back_button())
        else:
            bot.send_message(message.chat.id, "❌ حدث خطأ أثناء إرسال الطلب للسيرفر، لم يتم خصم أي رصيد. حاول مجدداً.")
            
        conn.close()
        del USER_STEPS[user_id]

@bot.message_handler(func=lambda msg: not msg.text.startswith('/'), content_types=['text'])
def handle_ai_chat(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        return

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
        except Exception:
            bot.reply_to(message, "⚠️ خطأ في الاتصال بالذكاء الاصطناعي.")
    else:
        conn.close()
        bot.reply_to(message, "❌ نفد رصيد أسئلة الذكاء الاصطناعي الخاصة بك.")

print("Bot is running smoothly...")
bot.infinity_polling()
