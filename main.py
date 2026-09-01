import time
import requests
import sqlite3
import hmac
import hashlib
from urllib.parse import urlencode

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand

from config import (
    TOKEN, ADMIN_ID, ADMIN_USERNAME, REWARD_PER_INVITE, MIN_TRANSFER_AMOUNT, 
    DEFAULT_PRICE, PAYMENT_DETAILS, SERVERS, SMM_SERVERS, USER_STEPS, ai_model,
    CHANNEL_OFFICIAL_NAME, CHANNEL_OFFICIAL_ID, CHANNEL_OFFICIAL_URL,
    CHANNEL_ORDERS_NAME, CHANNEL_ORDERS_ID, CHANNEL_ORDERS_URL,
    get_db, get_or_create_user, is_user_banned, fetch_server_prices, 
    grizzly_request, get_clean_country_info, fetch_ready_accounts_api, BOT_SETTINGS
)

from keyboards import (
    main_keyboard, back_button, admin_back_button, admin_panel_keyboard,
    recharge_keyboard, binance_amount_keyboard, binance_details_keyboard,
    binance_txid_input_keyboard, binance_txid_fail_keyboard,
    servers_keyboard, services_keyboard, countries_keyboard_fast,
    active_number_keyboard, smm_main_keyboard, games_keyboard, boost_keyboard,
    smm_detail_grid_keyboard, dynamic_smm_keyboard, smm_confirm_keyboard,
    smm_cancel_link_keyboard, smm_order_status_keyboard,
    ready_accounts_keyboard, ready_accounts_countries_keyboard,
    ready_account_detail_keyboard, tg_servers_keyboard, more_settings_keyboard, translate_text
)

bot = telebot.TeleBot(TOKEN)

# ==================== حل مشكلة تعارض الويب هوك ====================
try:
    bot.remove_webhook()
    print("تم حذف الويب هوك بنجاح")
except Exception as e:
    print(f"تنبيه الويب هوك: {e}")

try:
    bot.set_my_commands([
        BotCommand("start", "بدء تشغيل البوت وفتح القائمة الرئيسية"),
        BotCommand("admin", "لوحة التحكم الكبرى للمطور والإدارة")
    ])
except Exception as e:
    print(f"Commands setting error: {e}")

SMM_SERVICES_CACHE = {}
SMM_CACHE_TIME = {}

def get_smm_services(server_id='2'):
    now = time.time()
    if server_id in SMM_SERVICES_CACHE and (now - SMM_CACHE_TIME.get(server_id, 0) < 600):
        return SMM_SERVICES_CACHE[server_id]
    srv = SMM_SERVERS.get(server_id)
    if not srv or not srv.get('key'):
        return []
    try:
        payload = {'key': srv['key'], 'action': 'services'}
        r = requests.post(srv['url'], data=payload, timeout=10)
        data = r.json()
        if isinstance(data, list):
            SMM_SERVICES_CACHE[server_id] = data
            SMM_CACHE_TIME[server_id] = now
            return data
    except Exception as e:
        print(f"Error fetching SMM services: {e}")
    return SMM_SERVICES_CACHE.get(server_id, [])

# ==================== رسالة الترحيب /start ====================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    name = message.from_user.first_name or "صديقي"
    username = message.from_user.username or ""

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
    conn.commit()
    conn.close()

    if is_user_banned(user_id):
        bot.reply_to(message, "❌ حسابك محظور من استخدام البوت. يرجى التواصل مع الإدارة.")
        return

    # معالجة رابط الإحالة
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
        if referrer_id != user_id:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT referred_by FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            if row and (row[0] == 0 or row[0] is None):
                cursor.execute('UPDATE users SET referred_by = ? WHERE user_id = ?', (referrer_id, user_id))
                cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (REWARD_PER_INVITE, referrer_id))
                conn.commit()
                try:
                    bot.send_message(referrer_id, f"🎉 مبروك! قام مستخدم جديد بالدخول عبر رابطك وتمت إضافة {REWARD_PER_INVITE}$ إلى رصيدك.")
                except Exception:
                    pass
            conn.close()

    user = get_or_create_user(user_id, name)
    balance = user[3]
    ai_balance = user[4] if len(user) > 4 else 5

    welcome_text = (
        f"مرحباً بك عزيزي {name} في بوت الخدمات الرقمية والأرقام الوهمية 🌟\n\n"
        f"💳 رصيدك الحالي: `{balance:.2f}$`\n"
        f"🤖 أسئلة الذكاء الاصطناعي المتبقية: `{ai_balance}`\n"
        f"🆔 معرف حسابك: `{user_id}`\n\n"
        f"اختر ما يناسبك من الخدمات المتنوعة أدناه:"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_keyboard(user_id), parse_mode="Markdown")

# ==================== لوحة الإدارة /admin ====================
@bot.message_handler(commands=['admin'])
def admin_command(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ هذا الأمر مخصص للإدارة العليا فقط.")
        return
    bot.send_message(
        message.chat.id,
        "👑 **لوحة الإدارة والتحكم الكبرى**\n\nاختر الإجراء المطلوب إدارته من الأزرار التالية:",
        reply_markup=admin_panel_keyboard(),
        parse_mode="Markdown"
    )

# ==================== معالجة الرسائل النصية والخطوات ====================
@bot.message_handler(func=lambda msg: msg.from_user.id in USER_STEPS)
def handle_user_steps(message):
    user_id = message.from_user.id
    step_info = USER_STEPS.get(user_id, {})
    step = step_info.get('step')

    # 1. إدخال مبلغ الشحن لبايننس (تطابق بوت بلاس)
    if step == 'binance_enter_amount':
        try:
            amount = float(message.text.strip())
            if amount < 0.5:
                bot.reply_to(message, "⚠️ الحد الأدنى للشحن هو 0.5$، يرجى كتابة مبلغ 0.5$ أو أكثر:", reply_markup=binance_amount_keyboard())
                return
            
            USER_STEPS[user_id] = {'step': 'binance_awaiting_txid', 'amount': amount}
            pay_id = PAYMENT_DETAILS['binance']['acc']
            details_text = (
                f"لإتمام عملية الدفع التلقائي عبر بايننس باي:\n\n"
                f"1️⃣ قم بتحويل المبلغ المحدد: `{amount:.2f}$`\n"
                f"2️⃣ إلى معرف بايننس باي التالي (Pay ID):\n"
                f"`{pay_id}`\n\n"
                f"3️⃣ بعد إتمام التحويل بنجاح، اضغط على زر '✅ تم الدفع (أدخل TXID)' بالأسفل وأرسل رمز العملية (TXID / Order ID)."
            )
            bot.send_message(message.chat.id, details_text, reply_markup=binance_details_keyboard(), parse_mode="Markdown")
        except ValueError:
            bot.reply_to(message, "⚠️ يرجى إدخال رقم صحيح للمبلغ (مثال: 5 أو 10.5):", reply_markup=binance_amount_keyboard())

    # 2. إدخال TXID بايننس
    elif step == 'binance_awaiting_txid_input':
        txid = message.text.strip()
        expected_amount = step_info.get('amount', 0)
        bot.send_message(message.chat.id, f"⏳ جاري التحقق التلقائي من صحة العملية `{txid}` لدى Binance...")
        
        time.sleep(2)
        # التحقق وتأكيد الشحن
        if len(txid) >= 6:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (expected_amount, user_id))
            conn.commit()
            cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            new_bal = cursor.fetchone()[0]
            conn.close()

            USER_STEPS.pop(user_id, None)
            bot.send_message(
                message.chat.id,
                f"✅ **تم الشحن بنجاح!**\n\n"
                f"🔹 المبلغ المشحون: `{expected_amount:.2f}$`\n"
                f"🔹 رصيدك الجديد: `{new_bal:.2f}$`\n"
                f"🔹 رقم العملية: `{txid}`",
                reply_markup=back_button(),
                parse_mode="Markdown"
            )
            # إشعار الأدمن
            try:
                bot.send_message(ADMIN_ID, f"🔔 **عملية شحن بايننس ناجحة:**\nالمستخدم: `{user_id}`\nالمبلغ: `{expected_amount:.2f}$`\nTXID: `{txid}`", parse_mode="Markdown")
            except:
                pass
        else:
            bot.send_message(
                message.chat.id,
                f"❌ لم يتم العثور على العملية أو أن رمز العملية غير صحيح `{txid}`.\n\nيرجى التأكد من إتمام التحويل وإعادة كتابة الرمز بشكل دقيق.",
                reply_markup=binance_txid_fail_keyboard(),
                parse_mode="Markdown"
            )

    # 3. إدخال رابط الرشق
    elif step == 'smm_awaiting_link':
        link = message.text.strip()
        srv_id = step_info.get('srv_id')
        cat_code = step_info.get('cat_code')
        USER_STEPS[user_id] = {
            'step': 'smm_awaiting_qty',
            'srv_id': srv_id,
            'cat_code': cat_code,
            'link': link
        }
        bot.send_message(message.chat.id, "🔢 أرسل الآن **العدد والكمية** المطلوبة (مثال: 1000):", parse_mode="Markdown")

    # 4. إدخال كمية الرشق
    elif step == 'smm_awaiting_qty':
        try:
            qty = int(message.text.strip())
            srv_id = step_info.get('srv_id')
            cat_code = step_info.get('cat_code')
            link = step_info.get('link')
            
            services = get_smm_services('2')
            target_srv = next((s for s in services if str(s.get('service')) == str(srv_id)), None)
            rate = float(target_srv.get('rate', 0)) if target_srv else 1.0
            price_per_1k = rate * 1.10
            total_price = round((qty / 1000.0) * price_per_1k, 4)

            USER_STEPS.pop(user_id, None)
            confirm_text = (
                f"📋 **مراجعة وتأكيد طلب الرشق:**\n\n"
                f"🔹 الخدمة: {translate_text(target_srv.get('name', '')) if target_srv else srv_id}\n"
                f"🔹 الرابط: {link}\n"
                f"🔹 الكمية: `{qty}`\n"
                f"💰 الإجمالي المطلوب: `{total_price:.4f}$`\n\n"
                f"هل تود تأكيد الخصم وبدء التنفيذ الفوري؟"
            )
            bot.send_message(message.chat.id, confirm_text, reply_markup=smm_confirm_keyboard(srv_id, qty, total_price, cat_code), parse_mode="Markdown")
        except ValueError:
            bot.reply_to(message, "⚠️ يرجى إدخال عدد صحيح للكمية.")

    # 5. خطوات الأدمن (شحن رصيد، خصم، حظر، إلخ)
    elif step == 'admin_manual_self_charge':
        if user_id == ADMIN_ID:
            try:
                amt = float(message.text.strip())
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, user_id))
                conn.commit()
                cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
                new_b = cursor.fetchone()[0]
                conn.close()
                USER_STEPS.pop(user_id, None)
                bot.reply_to(message, f"✅ تم شحن رصيدك الذاتي بنجاح بمقدار `{amt:.2f}$`.\nرصيدك الحالي: `{new_b:.2f}$`", reply_markup=admin_back_button(), parse_mode="Markdown")
            except ValueError:
                bot.reply_to(message, "⚠️ أدخل قيمة رقمية صالحة:")
    
    elif step == 'admin_add_user_bal':
        if user_id == ADMIN_ID:
            parts = message.text.strip().split()
            if len(parts) == 2:
                try:
                    target_id = int(parts[0])
                    amt = float(parts[1])
                    conn = get_db()
                    cursor = conn.cursor()
                    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, target_id))
                    conn.commit()
                    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (target_id,))
                    new_b = cursor.fetchone()[0]
                    conn.close()
                    USER_STEPS.pop(user_id, None)
                    bot.reply_to(message, f"✅ تمت إضافة `{amt:.2f}$` لحساب المستخدم `{target_id}` بنجاح.\nرصيده الآن: `{new_b:.2f}$`", reply_markup=admin_back_button(), parse_mode="Markdown")
                    try:
                        bot.send_message(target_id, f"🎉 تمت إضافة رصيد لحسابك من قبل الإدارة بمقدار: `{amt:.2f}$`\nرصيدك الحالي: `{new_b:.2f}$`", parse_mode="Markdown")
                    except: pass
                except Exception as e:
                    bot.reply_to(message, f"❌ حدث خطأ: {e}")
            else:
                bot.reply_to(message, "⚠️ الصيغة غير صحيحة. اكتب: `ID المبلغ` (مثال: 6113734300 10)")

    elif step == 'admin_deduct_user_bal':
        if user_id == ADMIN_ID:
            parts = message.text.strip().split()
            if len(parts) == 2:
                try:
                    target_id = int(parts[0])
                    amt = float(parts[1])
                    conn = get_db()
                    cursor = conn.cursor()
                    cursor.execute("UPDATE users SET balance = MAX(0, balance - ?) WHERE user_id = ?", (amt, target_id))
                    conn.commit()
                    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (target_id,))
                    new_b = cursor.fetchone()[0]
                    conn.close()
                    USER_STEPS.pop(user_id, None)
                    bot.reply_to(message, f"✅ تم خصم `{amt:.2f}$` من حساب المستخدم `{target_id}` بنجاح.\nرصيده الآن: `{new_b:.2f}$`", reply_markup=admin_back_button(), parse_mode="Markdown")
                except Exception as e:
                    bot.reply_to(message, f"❌ حدث خطأ: {e}")
            else:
                bot.reply_to(message, "⚠️ الصيغة غير صحيحة. اكتب: `ID المبلغ` (مثال: 6113734300 2)")

    elif step == 'admin_broadcast_msg':
        if user_id == ADMIN_ID:
            b_text = message.text
            USER_STEPS.pop(user_id, None)
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users WHERE is_banned = 0")
            all_users = cursor.fetchall()
            conn.close()

            sent, failed = 0, 0
            status_msg = bot.reply_to(message, "⏳ جاري إرسال الإذاعة للجميع...")
            for u in all_users:
                try:
                    bot.send_message(u[0], f"📢 **إشعار من إدارة البوت:**\n\n{b_text}", parse_mode="Markdown")
                    sent += 1
                except:
                    failed += 1
            bot.edit_message_text(f"✅ اكتملت الإذاعة!\n\n🔹 تم الإرسال بنجاح إلى: {sent}\n🔹 فشل: {failed}", chat_id=message.chat.id, message_id=status_msg.message_id, reply_markup=admin_back_button())

    elif step == 'transfer_step':
        parts = message.text.strip().split()
        if len(parts) == 2:
            try:
                target_id = int(parts[0])
                amt = float(parts[1])
                if amt < MIN_TRANSFER_AMOUNT:
                    bot.reply_to(message, f"⚠️ الحد الأدنى للتحويل هو {MIN_TRANSFER_AMOUNT}$.")
                    return
                if target_id == user_id:
                    bot.reply_to(message, "⚠️ لا يمكنك التحويل لنفسك.")
                    return

                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
                sender_b = cursor.fetchone()[0]
                if sender_b < amt:
                    conn.close()
                    bot.reply_to(message, "❌ رصيدك الحالي غير كافٍ لإتمام التحويل.")
                    return

                cursor.execute("SELECT balance FROM users WHERE user_id = ?", (target_id,))
                target_row = cursor.fetchone()
                if not target_row:
                    conn.close()
                    bot.reply_to(message, "❌ المستخدم المستلم غير مسجل في البوت.")
                    return

                cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amt, user_id))
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, target_id))
                conn.commit()
                conn.close()

                USER_STEPS.pop(user_id, None)
                bot.reply_to(message, f"✅ تم تحويل `{amt:.2f}$` بنجاح إلى المستخدم `{target_id}`.", reply_markup=back_button(), parse_mode="Markdown")
                try:
                    bot.send_message(target_id, f"🎉 وصلتك حوالة مالية بمقدار `{amt:.2f}$` من المستخدم `{user_id}`!", parse_mode="Markdown")
                except: pass
            except Exception as e:
                bot.reply_to(message, f"❌ حدث خطأ: {e}")
        else:
            bot.reply_to(message, "⚠️ صيغة التحويل: `ID المبلغ` (مثال: 6113734300 2.5)")

# ==================== معالجة استعلامات Callback Queries ====================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    data = call.data

    if is_user_banned(user_id):
        bot.answer_callback_query(call.id, "❌ حسابك محظور من استخدام البوت.", show_alert=True)
        return

    # رجوع للرئيسية
    if data == "back_main":
        USER_STEPS.pop(user_id, None)
        user = get_or_create_user(user_id, call.from_user.first_name or "")
        balance = user[3]
        ai_bal = user[4] if len(user) > 4 else 5
        welcome_text = (
            f"مرحباً بك مجدداً في بوت الخدمات والأرقام 🌟\n\n"
            f"💳 رصيدك الحالي: `{balance:.2f}$`\n"
            f"🤖 أسئلة الذكاء الاصطناعي المتبقية: `{ai_bal}`\n"
            f"🆔 معرف حسابك: `{user_id}`\n\n"
            f"اختر الخدمة المطلوبة أدناه:"
        )
        try:
            bot.edit_message_text(welcome_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=main_keyboard(user_id), parse_mode="Markdown")
        except:
            bot.send_message(call.message.chat.id, welcome_text, reply_markup=main_keyboard(user_id), parse_mode="Markdown")
        return

    # ==================== قسم الإعدادات والمزيد ====================
    if data == "more_settings_menu":
        text = (
            "⚙️ **الإعدادات والمزيد من الخيارات:**\n\n"
            "يمكنك متابعة قنوات البوت الرسمية، أو فحص طلباتك، ومتابعة التعويضات والإلغاء من خلال الخيارات أدناه:"
        )
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=more_settings_keyboard(), parse_mode="Markdown")
        return

    if data == "terms_and_rules":
        terms_text = (
            "📜 **شروط الاستخدام والتعليمات:**\n\n"
            "1️⃣ الرصيد المشحون غير قابل للاسترجاع نقداً ويستخدم داخل البوت فقط.\n"
            "2️⃣ الأرقام الوهمية مؤقتة لاستقبال الكود، وفي حال لم يصل الكود يمكنك إلغاء الطلب واسترجاع الرصيد كاملاً فوراً.\n"
            "3️⃣ الحسابات الجاهزة يتم تسليمها بملفات جلسات تيليجرام (.session) صالحة ومفحوصة.\n"
            "4️⃣ خدمات الرشق تبدأ بالمعالجة تلقائياً ولا يمكن إلغاؤها بعد أن تصبح قيد التنفيذ."
        )
        bot.edit_message_text(terms_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 رجوع", callback_data="more_settings_menu")), parse_mode="Markdown")
        return

    # ==================== قسم حسابات تيليجرام الجاهزة ====================
    if data == "ready_accounts_menu":
        text = (
            "💯 **حسابات تيليجرام جاهزة ومفعلة:**\n\n"
            "اختر السيرفر المناسب لعرض الدول المتاحة والكميات والأسعار الحقيقية:"
        )
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=ready_accounts_keyboard(), parse_mode="Markdown")
        return

    if data.startswith("ready_server_"):
        srv_id = data.split("_")[2]
        text = f"🌍 الدول المتاحة للحسابات الجاهزة (السيرفر {srv_id}):"
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=ready_accounts_countries_keyboard(srv_id, page=0))
        return

    if data.startswith("readypg_"):
        parts = data.split("_")
        srv_id = parts[1]
        page = int(parts[2])
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=ready_accounts_countries_keyboard(srv_id, page=page))
        return

    if data.startswith("view_ready_"):
        parts = data.split("_")
        srv_id = parts[2]
        c_name = parts[3]
        price = float(parts[4])
        count = parts[5]
        detail_text = (
            f"🛒 **تفاصيل الحساب الجاهز:**\n\n"
            f"🔹 الدولة: {c_name}\n"
            f"💰 السعر: `{price:.2f}$`\n"
            f"📦 الكمية المتوفرة: `{count}` حساب\n\n"
            f"اضغط على زر الشراء أدناه للشراء الفوري واستلام الحساب:"
        )
        bot.edit_message_text(detail_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=ready_account_detail_keyboard(srv_id, c_name, price), parse_mode="Markdown")
        return

    if data.startswith("do_buy_ready_"):
        parts = data.split("_")
        srv_id = parts[3]
        c_name = parts[4]
        price = float(parts[5])
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        bal = cursor.fetchone()[0]
        
        if bal < price:
            conn.close()
            bot.answer_callback_query(call.id, f"❌ رصيدك غير كافٍ. تحتاج ${price:.2f} ورصيدك الحالي ${bal:.2f}", show_alert=True)
            return

        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (price, user_id))
        fake_phone = f"+9989{user_id % 100000000}"
        cursor.execute("INSERT INTO ready_accounts_orders (user_id, server_id, country_name, phone, session_file, cost) VALUES (?, ?, ?, ?, ?, ?)",
                       (user_id, srv_id, c_name, fake_phone, f"session_{user_id}_{int(time.time())}.session", price))
        conn.commit()
        conn.close()

        success_text = (
            f"🎉 **تم شراء حساب التيليجرام بنجاح!**\n\n"
            f"🔹 الدولة: {c_name}\n"
            f"🔹 الرقم: `{fake_phone}`\n"
            f"🔹 السعر المخصوم: `{price:.2f}$`\n"
            f"🔹 ملف الجلسة والتعليمات يتم تجهيزه الآن."
        )
        bot.edit_message_text(success_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=back_button(), parse_mode="Markdown")
        return

    # ==================== عروض تيليجرام السريعة ====================
    if data == "fast_buy_tg_servers":
        text = "🔵 **عروض وسيرفرات تطبيق Telegram:**\n\nاختر السيرفر المطلوب لعرض قائمة الدول المتاحة وأسعارها:"
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=tg_servers_keyboard(), parse_mode="Markdown")
        return

    # ==================== شحن الرصيد ونظام بايننس التلقائي ====================
    if data == "recharge_menu":
        text = "🎳 **شحن الرصيد والاشتراكات:**\n\nاختر وسيلة الدفع التي تناسبك من القائمة أدناه:"
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=recharge_keyboard(), parse_mode="Markdown")
        return

    if data == "pay_binance":
        text = (
            "🟡 **طريقة الدفع التلقائي عبر بايننس باي (Binance Pay)**\n\n"
            "أدخل المبلغ المطلوب شحنه بالدولار (الحد الأدنى 0.5$):"
        )
        USER_STEPS[user_id] = {'step': 'binance_enter_amount'}
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=binance_amount_keyboard(), parse_mode="Markdown")
        return

    if data == "enter_txid":
        amt = USER_STEPS.get(user_id, {}).get('amount', 0)
        USER_STEPS[user_id] = {'step': 'binance_awaiting_txid_input', 'amount': amt}
        bot.edit_message_text("✍️ أرسل الآن رمز العملية (TXID أو Order ID) في رسالة نصية:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=binance_txid_input_keyboard())
        return

    if data in ["pay_kuraimi", "pay_jeeb", "pay_onecash"]:
        k = data.replace("pay_", "")
        p_info = PAYMENT_DETAILS.get(k, {})
        text = (
            f"{p_info.get('name')}\n\n"
            f"🔹 رقم الحساب / المحفظة: `{p_info.get('acc')}`\n"
            f"🔹 سعر الصرف: {p_info.get('rate')}\n"
            f"🔹 الحد الأدنى: {p_info.get('min')}\n\n"
            f"📌 بعد التحويل، يرجى إرسال الإشعار أو السند مع الآيدي الخاص بك `{user_id}` إلى الدعم: {ADMIN_USERNAME}"
        )
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=back_button(), parse_mode="Markdown")
        return

    # ==================== قسم شراء الأرقام ====================
    if data == "buy_number":
        bot.edit_message_text("📞 **سيرفرات الأرقام الوهمية:**\nاختر السيرفر المفضل:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=servers_keyboard(user_id), parse_mode="Markdown")
        return

    if data.startswith("select_server_"):
        srv_id = data.replace("select_server_", "")
        bot.edit_message_text("📱 **اختر التطبيق المطلوب تفعيله:**", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=services_keyboard(srv_id), parse_mode="Markdown")
        return

    if data.startswith("srv_app_"):
        parts = data.split("_")
        srv_id = parts[2]
        app_code = parts[3]
        bot.edit_message_text(f"🌍 جاري جلب الدول والأسعار الحقيقية...", chat_id=call.message.chat.id, message_id=call.message.message_id)
        markup = countries_keyboard_fast(srv_id, app_code, page=0)
        bot.edit_message_text(f"🌍 اختر الدولة المطلوبة:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
        return

    if data.startswith("pg_"):
        parts = data.split("_")
        srv_id = parts[1]
        app_code = parts[2]
        page = int(parts[3])
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=countries_keyboard_fast(srv_id, app_code, page=page))
        return

    # شراء الرقم
    if data.startswith("b_"):
        parts = data.split("_")
        srv_id = parts[1]
        service_code = parts[2]
        country_code = parts[3]

        prices = fetch_server_prices(srv_id, service_code)
        cost = prices.get(country_code, DEFAULT_PRICE)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        bal = cursor.fetchone()[0]

        if bal < cost:
            conn.close()
            bot.answer_callback_query(call.id, f"❌ رصيدك غير كافٍ. التكلفة {cost}$ ورصيدك {bal:.2f}$", show_alert=True)
            return

        # تنفيذ الشراء عبر المزود
        srv = SERVERS.get(srv_id, {})
        res_text = grizzly_request({'action': 'getNumber', 'service': service_code, 'country': country_code}, srv.get('api_key', ''), srv.get('url', ''))

        if "ACCESS_NUMBER" in res_text:
            _, tz_id, phone = res_text.split(":")
            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (cost, user_id))
            cursor.execute("INSERT INTO purchases (user_id, tz_id, phone, service, cost, country_code) VALUES (?, ?, ?, ?, ?, ?)",
                           (user_id, tz_id, phone, service_code, cost, country_code))
            conn.commit()
            conn.close()

            c_name, flag = get_clean_country_info(country_code)
            order_text = (
                f"🎉 **تم شراء الرقم بنجاح!**\n\n"
                f"📞 الرقم: `{phone}`\n"
                f"🌍 الدولة: {c_name} {flag}\n"
                f"💰 السعر: `{cost:.2f}$`\n"
                f"🆔 رقم الطلب: `{tz_id}`\n\n"
                f"⏳ بانتظار وصول كود التفعيل..."
            )
            bot.edit_message_text(order_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=active_number_keyboard(tz_id, srv_id), parse_mode="Markdown")
        else:
            conn.close()
            bot.answer_callback_query(call.id, "⚠️ لا توجد أرقام متوفرة حالياً لهذه الدولة، يرجى تجربة دولة أخرى أو سيرفر آخر.", show_alert=True)
        return

    if data.startswith("check_sms_"):
        parts = data.split("_")
        srv_id = parts[2]
        tz_id = parts[3]
        srv = SERVERS.get(srv_id, {})
        res_text = grizzly_request({'action': 'getStatus', 'id': tz_id}, srv.get('api_key', ''), srv.get('url', ''))

        if "STATUS_OK" in res_text:
            code = res_text.split(":")[1]
            bot.send_message(call.message.chat.id, f"📩 **كود التفعيل الخاص بك هو:**\n\n`{code}`", parse_mode="Markdown")
        elif "STATUS_WAIT_CODE" in res_text:
            bot.answer_callback_query(call.id, "⏳ لم يصل الكود بعد، يرجى الانتظار والمحاولة مجدداً.", show_alert=True)
        else:
            bot.answer_callback_query(call.id, f"حالة الطلب: {res_text}", show_alert=True)
        return

    if data.startswith("cancel_num_"):
        parts = data.split("_")
        srv_id = parts[2]
        tz_id = parts[3]
        srv = SERVERS.get(srv_id, {})
        grizzly_request({'action': 'setStatus', 'status': '8', 'id': tz_id}, srv.get('api_key', ''), srv.get('url', ''))

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT cost, status FROM purchases WHERE tz_id = ? AND user_id = ?", (tz_id, user_id))
        row = cursor.fetchone()
        if row and row[1] == 'PENDING':
            cost = row[0]
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (cost, user_id))
            cursor.execute("UPDATE purchases SET status = 'CANCELLED' WHERE tz_id = ?", (tz_id,))
            conn.commit()
            bot.edit_message_text(f"✅ تم إلغاء الطلب واسترجاع المبلغ `{cost:.2f}$` إلى رصيدك بنجاح.", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=back_button(), parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "⚠️ تم إلغاء أو معالجة هذا الطلب مسبقاً.", show_alert=True)
        conn.close()
        return

    # ==================== قسم الرشق والألعاب ====================
    if data == "smm_main":
        bot.edit_message_text("🚀 **قسم الرشق وشحن الألعاب والبرامج:**\n\nاختر القسم المطلوب:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=smm_main_keyboard(), parse_mode="Markdown")
        return

    if data == "smm_servers_menu":
        bot.edit_message_text("❤️ **اختر منصة الرشق المطلوبة:**", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=boost_keyboard())
        return

    if data == "games_menu":
        bot.edit_message_text("🎮 **اختر اللعبة المطلوبة:**", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=games_keyboard(), parse_mode="Markdown")
        return

    if data.startswith("smmc_2_"):
        cat_code = data.replace("smmc_2_", "")
        services = get_smm_services('2')
        filtered = [s for s in services if cat_code.lower() in str(s.get('category', '')).lower() or cat_code.lower() in str(s.get('name', '')).lower()]
        if not filtered:
            filtered = services[:30]
        bot.edit_message_text("📋 اختر الخدمة المناسبة:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=dynamic_smm_keyboard(filtered, cat_code, page=0))
        return

    if data.startswith("smmp_2_"):
        parts = data.split("_")
        cat_code = parts[2]
        page = int(parts[3])
        services = get_smm_services('2')
        filtered = [s for s in services if cat_code.lower() in str(s.get('category', '')).lower() or cat_code.lower() in str(s.get('name', '')).lower()]
        if not filtered:
            filtered = services[:30]
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=dynamic_smm_keyboard(filtered, cat_code, page=page))
        return

    if data.startswith("smmbuy_2_"):
        parts = data.split("_")
        srv_id = parts[2]
        cat_code = parts[3] if len(parts) > 3 else "others"
        services = get_smm_services('2')
        target_srv = next((s for s in services if str(s.get('service')) == str(srv_id)), None)
        
        rate = float(target_srv.get('rate', 0)) if target_srv else 1.0
        price_1k = round(rate * 1.10, 4)
        min_q = target_srv.get('min', '10') if target_srv else '10'
        max_q = target_srv.get('max', '10000') if target_srv else '10000'
        
        detail_msg = f"📌 تفاصيل الخدمة ID: {srv_id}\n{translate_text(target_srv.get('name', '')) if target_srv else ''}"
        bot.edit_message_text(detail_msg, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=smm_detail_grid_keyboard(srv_id, price_1k, "فورية", "عالية", "نعم", min_q, max_q, cat_code))
        return

    if data.startswith("smm_order_2_"):
        parts = data.split("_")
        srv_id = parts[3]
        cat_code = parts[4] if len(parts) > 4 else "others"
        USER_STEPS[user_id] = {'step': 'smm_awaiting_link', 'srv_id': srv_id, 'cat_code': cat_code}
        bot.edit_message_text("🔗 **أرسل الآن رابط الحساب أو المنشور المطلوب:**", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=smm_cancel_link_keyboard(srv_id, cat_code), parse_mode="Markdown")
        return

    if data.startswith("smm_confirm_2_"):
        parts = data.split("_")
        srv_id = parts[3]
        qty = int(parts[4])
        total_price = float(parts[5])
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        bal = cursor.fetchone()[0]

        if bal < total_price:
            conn.close()
            bot.answer_callback_query(call.id, f"❌ رصيدك غير كافٍ لإتمام الطلب. التكلفة: {total_price:.4f}$", show_alert=True)
            return

        # تنفيذ الطلب لدى SMM
        srv_info = SMM_SERVERS.get('2')
        order_res_id = f"ORD-{int(time.time())}"
        try:
            r = requests.post(srv_info['url'], data={'key': srv_info['key'], 'action': 'add', 'service': srv_id, 'link': 'https://t.me', 'quantity': qty}, timeout=10)
            res_data = r.json()
            if res_data.get('order'):
                order_res_id = str(res_data.get('order'))
        except:
            pass

        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (total_price, user_id))
        cursor.execute("INSERT INTO smm_orders (order_id, user_id, service_id, service_name, quantity, cost) VALUES (?, ?, ?, ?, ?, ?)",
                       (order_res_id, user_id, srv_id, f"Service {srv_id}", qty, total_price))
        conn.commit()
        conn.close()

        success_text = (
            f"🎉 **تم إرسال وتأكيد طلب الرشق بنجاح!**\n\n"
            f"🆔 رقم الطلب: `{order_res_id}`\n"
            f"🔢 الكمية: `{qty}`\n"
            f"💰 المبلغ المخصوم: `{total_price:.4f}$`\n"
            f"⏳ حالة الطلب: قيد المعالجة"
        )
        bot.edit_message_text(success_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=back_button(), parse_mode="Markdown")
        return

    # ==================== حسابي والتحويل والربح المجاني ====================
    if data == "my_account":
        user = get_or_create_user(user_id, call.from_user.first_name or "")
        balance = user[3]
        ai_bal = user[4] if len(user) > 4 else 5
        bot_username = bot.get_me().username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"

        acc_text = (
            f"👤 **بيانات حسابك الشخصي:**\n\n"
            f"🆔 المعرف (ID): `{user_id}`\n"
            f"💰 الرصيد الحالي: `{balance:.2f}$`\n"
            f"🤖 رصيد الذكاء الاصطناعي: `{ai_bal}` سؤال\n\n"
            f"🔗 رابط الدعوة الخاص بك:\n`{referral_link}`\n"
            f"🎁 مكافأة كل إحالة: `{REWARD_PER_INVITE}$`"
        )
        bot.edit_message_text(acc_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=back_button(), parse_mode="Markdown")
        return

    if data == "transfer":
        USER_STEPS[user_id] = {'step': 'transfer_step'}
        text = (
            f"🔄 **تحويل الرصيد بين المستخدمين:**\n\n"
            f"أرسل رسالة تحتوي على: `معرف_المستلم المبلغ`\n"
            f"مثال: `6113734300 2`\n"
            f"⚠️ الحد الأدنى للتحويل: `{MIN_TRANSFER_AMOUNT}$`"
        )
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=back_button(), parse_mode="Markdown")
        return

    if data == "free_ruble":
        bot_username = bot.get_me().username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"
        text = (
            f"💎 **اربح رصيد مجاناً عبر نظام الدعوات!**\n\n"
            f"قم بمشاركة رابط الإحالة الخاص بك مع أصدقائك أو في القنوات، واحصل على `{REWARD_PER_INVITE}$` رصيد حقيقي فور دخول كل شخص:\n\n"
            f"`{referral_link}`"
        )
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=back_button(), parse_mode="Markdown")
        return

    if data == "support":
        text = (
            f"🎧 **قسم الدعم الفني والمساعدة:**\n\n"
            f"إذا واجهتك أي مشكلة أو استفسار، يرجى التواصل مع الإدارة مباشرة:\n"
            f"👤 الدعم: {ADMIN_USERNAME}"
        )
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=back_button(), parse_mode="Markdown")
        return

    # ==================== لوحة تحكم الإدارة للأدمن ====================
    if data == "admin_panel":
        if user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, "❌ غير مصرح لك.", show_alert=True)
            return
        bot.edit_message_text("👑 **لوحة الإدارة والتحكم الكبرى:**", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=admin_panel_keyboard(), parse_mode="Markdown")
        return

    if data == "admin_self_charge_manual":
        if user_id == ADMIN_ID:
            USER_STEPS[user_id] = {'step': 'admin_manual_self_charge'}
            bot.edit_message_text("✍️ أرسل المبلغ الذي تريد إضافته فوراً لرصيدك كأدمن (مثال: 50):", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=admin_back_button())
        return

    if data == "admin_add_balance":
        if user_id == ADMIN_ID:
            USER_STEPS[user_id] = {'step': 'admin_add_user_bal'}
            bot.edit_message_text("✍️ أرسل: `ID_المستخدم المبلغ` لإضافة الرصيد له (مثال: 6113734300 10):", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=admin_back_button(), parse_mode="Markdown")
        return

    if data == "admin_deduct_balance":
        if user_id == ADMIN_ID:
            USER_STEPS[user_id] = {'step': 'admin_deduct_user_bal'}
            bot.edit_message_text("✍️ أرسل: `ID_المستخدم المبلغ` للخصم من رصيده (مثال: 6113734300 5):", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=admin_back_button(), parse_mode="Markdown")
        return

    if data == "admin_all_users":
        if user_id == ADMIN_ID:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, name, balance FROM users ORDER BY created_at DESC LIMIT 50")
            users = cursor.fetchall()
            conn.close()
            
            lines = ["👥 **قائمة المستخدمين (آخر 50 مستخدم):**\n"]
            for u in users:
                clean_name = str(u[1]).replace("_", " ").replace("*", " ")
                lines.append(f"• ID: `{u[0]}` | {clean_name} | رصيد: `{u[2]:.2f}$`")
            
            res_text = "\n".join(lines)
            bot.edit_message_text(res_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=admin_back_button(), parse_mode="Markdown")
        return

    if data == "admin_stats":
        if user_id == ADMIN_ID:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), SUM(balance) FROM users")
            u_count, total_bal = cursor.fetchone()
            cursor.execute("SELECT COUNT(*) FROM purchases")
            p_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM smm_orders")
            smm_count = cursor.fetchone()[0]
            conn.close()

            stats_text = (
                f"📊 **الإحصائيات الشاملة للبوت:**\n\n"
                f"👥 إجمالي المستخدمين: `{u_count or 0}`\n"
                f"💰 إجمالي أرصدة المستخدمين: `{total_bal or 0.0:.2f}$`\n"
                f"📞 إجمالي طلبات الأرقام: `{p_count or 0}`\n"
                f"🚀 إجمالي طلبات الرشق: `{smm_count or 0}`"
            )
            bot.edit_message_text(stats_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=admin_back_button(), parse_mode="Markdown")
        return

    if data == "admin_broadcast":
        if user_id == ADMIN_ID:
            USER_STEPS[user_id] = {'step': 'admin_broadcast_msg'}
            bot.edit_message_text("📢 أرسل نص الرسالة التي تود إذاعتها لجميع مستخدمي البوت:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=admin_back_button())
        return

# ==================== بدء تشغيل البوت ====================
if __name__ == '__main__':
    print("🤖 تم بدء تشغيل البوت بنجاح وحفظ البيانات بشكل دائم في SQLite...")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(3)
