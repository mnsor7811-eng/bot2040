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
    DEFAULT_PRICE, PAYMENT_DETAILS, SERVERS, SMM_SERVERS, READY_ACCOUNTS_PROVIDERS,
    USER_STEPS, BOT_SETTINGS, CHANNEL_OFFICIAL_URL, CHANNEL_ORDERS_URL,
    get_db, get_or_create_user, is_user_banned, fetch_server_prices, 
    grizzly_request, get_clean_country_info, fetch_ready_accounts_api,
    buy_ready_account_api, get_ready_account_code_api
)

from keyboards import (
    main_keyboard, back_button, admin_back_button, admin_panel_keyboard,
    more_settings_keyboard, ready_accounts_keyboard, ready_aged_years_keyboard,
    ready_accounts_countries_keyboard, ready_account_detail_keyboard, ready_account_code_keyboard,
    tg_servers_keyboard, recharge_keyboard,
    servers_keyboard, services_keyboard, countries_keyboard_fast, active_number_keyboard,
    smm_main_keyboard, games_keyboard, boost_keyboard, dynamic_smm_keyboard,
    smm_detail_grid_keyboard, smm_cancel_link_keyboard, smm_confirm_keyboard,
    smm_order_status_keyboard, translate_text, get_store_keyboard, get_back_to_store_keyboard
)

from foxreload_api import (
    search_products_by_category, 
    get_account_balance, 
    create_and_pay_order, 
    fetch_categories
)

bot = telebot.TeleBot(TOKEN)

# ==================== إزالة الويب هوك القديم ====================
try:
    bot.remove_webhook()
    print("تم حذف الويب هوك القديم بنجاح.")
except Exception as e:
    print(f"حدث خطأ أثناء حذف الويب هوك: {e}")

# ==================== إعدادات بايننس باي (Binance Pay) ====================
BINANCE_PAY_ID = "979808293"
API_KEY_BINANCE = "Q2BSm09k0oVAaSwlWK415h9EfMHKnwwDYZEr9wSGXhnSJN2amXgJBYMa0COSM7QN"
SECRET_KEY = "Ld01qxgadxLjYKosPjFOANXTD7x6CM1GHWX3RpbC32kqqmlzvlApGMiR5ILBteCQ"

def get_binance_signature(query_string, secret_key):
    return hmac.new(secret_key.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

def verify_binance_txid(txid, expected_amount):
    url = "https://api.binance.com/sapi/v1/pay/transactions"
    timestamp = int(time.time() * 1000)
    params = {"timestamp": timestamp, "txId": txid}
    query_string = urlencode(params)
    signature = get_binance_signature(query_string, SECRET_KEY)
    headers = {"X-MBX-APIKEY": API_KEY_BINANCE}
    try:
        response = requests.get(f"{url}?{query_string}&signature={signature}", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                tx_info = data["data"][0]
                if float(tx_info.get("amount", 0)) >= float(expected_amount):
                    return True
        return False
    except Exception as e:
        print(f"Error checking transaction: {e}")
        return False

# ==================== تعيين قائمة الأوامر (Menu Commands) ====================
def set_bot_commands():
    commands = [
        BotCommand("start", "🏡 القائمة الرئيسية"),
        BotCommand("num", "📞 شراء أرقام وهمية"),
        BotCommand("ready", "💯 حسابات جاهزة"),
        BotCommand("recharge", "🎳 شحن الرصيد"),
        BotCommand("smm", "🚀 الرشق والخدمات"),
        BotCommand("store", "🛍️ المتجر والخدمات الرقمية"),
        BotCommand("free", "💎 اربح رصيد مجاناً"),
        BotCommand("transfer", "🔄 تحويل الرصيد"),
        BotCommand("support", "🎧 الدعم الفني"),
        BotCommand("account", "👤 حسابي"),
        BotCommand("more", "⚙️ الإعدادات والمزيد"),
        BotCommand("admin", "👑 لوحة الإدارة الكبرى")
    ]
    try: bot.set_my_commands(commands)
    except: pass

# ==================== دوال SMM API ====================
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
        combined_text = f"{str(srv.get('name', '')).lower()} {str(srv.get('category', '')).lower()}"
        if target_type == 'others':
            all_main_keys = [k for sublist in arabic_keywords.values() for k in sublist]
            if not any(k in combined_text for k in all_main_keys):
                filtered.append(srv)
        else:
            if any(k in combined_text for k in keys):
                filtered.append(srv)
    return filtered

def get_arabic_datetime():
    days_ar = {'Monday': 'الاثنين', 'Tuesday': 'الثلاثاء', 'Wednesday': 'الأربعاء', 'Thursday': 'الخميس', 'Friday': 'الجمعة', 'Saturday': 'السبت', 'Sunday': 'الأحد'}
    months_ar = {1: 'يناير', 2: 'فبراير', 3: 'مارس', 4: 'أبريل', 5: 'مايو', 6: 'يونيو', 7: 'يوليو', 8: 'أغسطس', 9: 'سبتمبر', 10: 'أكتوبر', 11: 'نوفمبر', 12: 'ديسمبر'}
    now = datetime.datetime.now()
    day_name = days_ar.get(now.strftime('%A'), now.strftime('%A'))
    month_name = months_ar.get(now.month, str(now.month))
    hour_12 = now.strftime('%I:%M').lstrip('0')
    period = 'م' if now.strftime('%p') == 'PM' else 'ص'
    return f"{day_name}، {now.day} {month_name} {hour_12} {period}"

# ==================== أوامر البدء ====================
# ================= كود التحقق من الاشتراك الإجباري =================
CHANNEL_1 = -1002987190358  
CHANNEL_2 = -1003004681072  

def check_subscription(user_id):
    try:
        member_1 = bot.get_chat_member(CHANNEL_1, user_id)
        member_2 = bot.get_chat_member(CHANNEL_2, user_id)
        valid_statuses = ['member', 'creator', 'administrator']
        return member_1.status in valid_statuses and member_2.status in valid_statuses
    except Exception as e:
        print(f"خطأ أثناء التحقق من الاشتراك: {e}")
        return False

def subscription_markup():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("قناة التفعيلات والطلبات 📢", url="https://t.me/numbuersms"))
    markup.add(InlineKeyboardButton("قناة البوت الرسمية 🤖", url="https://t.me/SM_SMS7"))
    markup.add(InlineKeyboardButton("تحقـق من الاشتـراك ✅", callback_data="check_sub"))
    return markup
# =================================================================

# دالة مساعدة لإنشاء لوحة مفاتيح منتجات المتجر مع نظام الصفحات
def build_store_products_keyboard(category_key, page=0, per_page=10):
    products = search_products_by_category(category_key)
    keyboard = InlineKeyboardMarkup(row_width=1)

    total = len(products)
    total_pages = max(1, (total + per_page - 1) // per_page)
    current_page = max(0, min(page, total_pages - 1))

    start_idx = current_page * per_page
    end_idx = start_idx + per_page
    page_items = products[start_idx:end_idx]

    icon_map = {"gift": "🎁", "game": "🎮", "service": "🌐"}
    icon = icon_map.get(category_key, "🛍️")

    if page_items:
        for p in page_items:
            p_name = p.get('display_name') or p.get('name', 'منتج رقمي')
            p_price = p.get('price', 0)
            p_id = p.get('id') or p.get('slug')
            keyboard.add(InlineKeyboardButton(f"{icon} {p_name} - ${p_price}", callback_data=f"buyprod_{p_id}"))
    else:
        keyboard.add(InlineKeyboardButton("❌ لا توجد منتجات متوفرة حالياً بهذا القسم", callback_data="ignore"))

    # أزرار التنقل بين الصفحات
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"storepg_{category_key}_{current_page - 1}"))

    nav_buttons.append(InlineKeyboardButton(f"📄 {current_page + 1} / {total_pages}", callback_data="ignore"))

    if current_page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"storepg_{category_key}_{current_page + 1}"))

    if len(nav_buttons) > 1:
        keyboard.row(*nav_buttons)

    keyboard.add(InlineKeyboardButton("🔙 عودة للمتجر", callback_data="store_menu"))
    return keyboard, total, current_page, total_pages

@bot.message_handler(commands=['start', 'num', 'store', 'ready'])
def start_cmd(message):
    user_id = message.from_user.id

    # فحص الاشتراك الإجباري أولاً
    if not check_subscription(user_id):
        bot.send_message(
            message.chat.id, 
            "عذراً، لا يمكنك استخدام البوت إلا بعد الاشتراك في قناتي البوت:\n\n1️⃣ قناة التفعيلات والطلبات\n2️⃣ القناة الرسمية\n\nاشترك فيهما ثم اضغط على زر التحقق أدناه 👇",
            reply_markup=subscription_markup()
        )
        return

    name = message.from_user.first_name or "المستخدم"
    username = f"@{message.from_user.username}" if message.from_user.username else "لا يوجد"

    if is_user_banned(user_id):
        bot.send_message(
            message.chat.id,
            "عذراً، لقد تم حظرك من استخدام 🚫\n(.) هذا البوت بواسطة الإدارة"
        )
        return

    if BOT_SETTINGS.get('maintenance', False) and user_id != ADMIN_ID:
        bot.send_message(message.chat.id, "🛠️ البوت في وضع الصيانة والتحديث حالياً، يرجى المحاولة لاحقاً.")
        return

    # إذا كان الأمر هو /ready
    if message.text.strip().startswith('/ready'):
        ready_text = (
            "💯 **قسم حسابات تيليجرام الجاهزة**\n\n"
            "▫️ حسابات مفعلة تسليم فوري وتلقائي.\n"
            "▫️ استلام كود الدخول وكلمة سر التحقق بخطوتين (2FA) فوراً.\n"
            "▫️ الربح 10% مضاف تلقائياً لجميع الأسعار.\n\n"
            "اختر السيرفر المطلوب:"
        )
        bot.send_message(message.chat.id, ready_text, parse_mode="Markdown", reply_markup=ready_accounts_keyboard())
        return

    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None

    conn = get_db()
    cursor = conn.cursor()
    try:
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
                try: bot.send_message(ref_id, f"🎉 انضم مستخدم جديد عبر رابطك!\n🎁 تم إضافة ${REWARD_PER_INVITE:.2f} إلى رصيدك.")
                except: pass
        else:
            cursor.execute('UPDATE users SET name = ?, username = ? WHERE user_id = ?', (name, username, user_id))
            conn.commit()
    finally:
        conn.close()

    user_data = get_or_create_user(user_id, name)
    try: balance = float(user_data[3]) if len(user_data) > 3 and user_data[3] is not None else float(user_data[2])
    except: balance = 0.0
    try: ai_bal = int(user_data[4]) if len(user_data) > 4 and user_data[4] is not None else 5
    except: ai_bal = 5

    text = (f"💠 أهلاً بك عزيزي في البوت الشامل 💠\n\n"
            f"👤 حسابك: {ADMIN_USERNAME}\n"
            f"💰 رصيدك الحالي: ${balance:.2f}\n"
            f"🤖 رصيد أسئلة الذكاء: {ai_bal} سؤال\n\n"
            f"📌 استخدم الأزرار بالأسفل لتنفيذ طلباتك:")
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard(user_id))

@bot.message_handler(commands=['admin'])
def admin_cmd(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(message.chat.id, f"❌ عذراً، هذه اللوحة للمشرف فقط. آيديك: `{user_id}`", parse_mode="Markdown")
        return
    bot.send_message(message.chat.id, "👑 **أهلاً بك في لوحة الإدارة الكبرى**\n\nتحكم كامل بكل ميزات وإعدادات ومستخدمي البوت:", parse_mode="Markdown", reply_markup=admin_panel_keyboard())

# ==================== معالجة أزرار الكول باك ====================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if call.data == "ignore":
        try: bot.answer_callback_query(call.id)
        except: pass
        return

    # ==================== قسم المتجر الرقمي والتلقائي (FoxReload API) ====================
    if call.data == "store_menu":
        try: bot.answer_callback_query(call.id)
        except: pass
        try:
            bot.edit_message_text(
                "🛍️ **الـمتجر والخدمات الرقمية والتلقائية**\nاختر القسم المطلوب:", 
                chat_id, 
                message_id, 
                reply_markup=get_store_keyboard(), 
                parse_mode="Markdown"
            )
        except Exception:
            bot.send_message(chat_id, "🛍️ **الـمتجر والخدمات الرقمية والتلقائية**\nاختر القسم المطلوب:", reply_markup=get_store_keyboard(), parse_mode="Markdown")
        return

    elif call.data == "cat_giftcards":
        try: bot.answer_callback_query(call.id)
        except: pass
        keyboard, total, cur_page, total_pages = build_store_products_keyboard("gift", page=0)
        msg_text = f"🎁 **قائمة بطاقات الهدايا المتوفرة ({total} منتج):**\n📄 الصفحة ({cur_page + 1}/{total_pages})\nاختر المنتج الذي تود شراءه:"
        try:
            bot.edit_message_text(msg_text, chat_id, message_id, reply_markup=keyboard, parse_mode="Markdown")
        except:
            bot.send_message(chat_id, msg_text, reply_markup=keyboard, parse_mode="Markdown")
        return

    elif call.data == "cat_gaming":
        try: bot.answer_callback_query(call.id)
        except: pass
        keyboard, total, cur_page, total_pages = build_store_products_keyboard("game", page=0)
        msg_text = f"🎮 **قائمة شحن الألعاب المتوفرة ({total} منتج):**\n📄 الصفحة ({cur_page + 1}/{total_pages})\nاختر المنتج الذي تود شراءه:"
        try:
            bot.edit_message_text(msg_text, chat_id, message_id, reply_markup=keyboard, parse_mode="Markdown")
        except:
            bot.send_message(chat_id, msg_text, reply_markup=keyboard, parse_mode="Markdown")
        return

    elif call.data == "cat_services":
        try: bot.answer_callback_query(call.id)
        except: pass
        keyboard, total, cur_page, total_pages = build_store_products_keyboard("service", page=0)
        msg_text = f"🌐 **خدمات الإنترنت والبرمجيات المتوفرة ({total} منتج):**\n📄 الصفحة ({cur_page + 1}/{total_pages})\nاختر المنتج الذي تود شراءه:"
        try:
            bot.edit_message_text(msg_text, chat_id, message_id, reply_markup=keyboard, parse_mode="Markdown")
        except:
            bot.send_message(chat_id, msg_text, reply_markup=keyboard, parse_mode="Markdown")
        return

    elif call.data.startswith("storepg_"):
        parts = call.data.split("_")
        category_key = parts[1]
        target_page = int(parts[2])
        keyboard, total, cur_page, total_pages = build_store_products_keyboard(category_key, page=target_page)

        cat_titles = {"gift": "بطاقات الهدايا", "game": "شحن الألعاب", "service": "خدمات الإنترنت والبرمجيات"}
        c_title = cat_titles.get(category_key, "المنتجات")
        msg_text = f"🛍️ **قائمة {c_title} المتوفرة ({total} منتج):**\n📄 الصفحة ({cur_page + 1}/{total_pages})\nاختر المنتج الذي تود شراءه:"
        try:
            bot.edit_message_text(msg_text, chat_id, message_id, reply_markup=keyboard, parse_mode="Markdown")
        except:
            pass
        return

    elif call.data.startswith("buyprod_"):
        product_id = call.data.replace("buyprod_", "")
        bot.answer_callback_query(call.id, "⏳ جاري فحص الرصيد وتنفيذ الطلب تلقائياً...")

        # البحث عن سعر المنتج من الكاش
        found_product = None
        for cat in ["gift", "game", "service"]:
            for p in search_products_by_category(cat):
                if str(p.get("id")) == str(product_id) or str(p.get("slug")) == str(product_id):
                    found_product = p
                    break
            if found_product: break

        prod_price = float(found_product.get('price', 0)) if found_product else 0.0
        prod_title = found_product.get('display_name') or (found_product.get('name') if found_product else f"منتج #{product_id}")

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            user_bal_row = cursor.fetchone()
            current_balance = user_bal_row[0] if user_bal_row else 0.0

            if prod_price > 0 and current_balance < prod_price:
                bot.send_message(
                    chat_id, 
                    f"❌ **عذراً، رصيدك غير كافٍ لإتمام الشراء!**\n\n🛍️ المنتج: {prod_title}\n💵 السعر: ${prod_price:.2f}\n💰 رصيدك الحالي: ${current_balance:.2f}\n\nيرجى شحن حسابك ثم المحاولة مجدداً.", 
                    parse_mode="Markdown", 
                    reply_markup=get_back_to_store_keyboard()
                )
                return

            result = create_and_pay_order(product_id, quantity=1)

            if result.get("success"):
                if prod_price > 0:
                    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (prod_price, user_id))
                    conn.commit()
                order_details = result.get("data", {})
                bot.send_message(
                    chat_id, 
                    f"🎉 **تم شراء المنتج وتسليمه بنجاح!**\n\n🛍️ المنتج: {prod_title}\n💵 المبلغ المخصوم: ${prod_price:.2f}\n\n📦 تفاصيل الطلب:\n`{order_details}`", 
                    parse_mode="Markdown", 
                    reply_markup=get_back_to_store_keyboard()
                )
            else:
                err_msg = result.get("error", "حدث خطأ غير معروف أثناء الشراء.")
                bot.send_message(
                    chat_id, 
                    f"❌ **فشل اتمام الطلب التلقائي:**\n{err_msg}\n\n(لم يتم خصم أي رصيد من حسابك)", 
                    parse_mode="Markdown", 
                    reply_markup=get_back_to_store_keyboard()
                )
        finally:
            conn.close()
        return

    # ==================== قائمة الإعدادات والمزيد ====================
    elif call.data == "more_settings_menu":
        try: bot.answer_callback_query(call.id)
        except: pass
        msg_txt = "⚙️ **قائمة المزيد والإعدادات**\n\nاختر الخيار المناسب:"
        try:
            bot.edit_message_text(msg_txt, chat_id, message_id, parse_mode="Markdown", reply_markup=more_settings_keyboard())
        except Exception:
            bot.send_message(chat_id, msg_txt, parse_mode="Markdown", reply_markup=more_settings_keyboard())
        return

    # ==================== عروض Telegram ====================
    elif call.data == "fast_buy_tg_servers":
        try: bot.answer_callback_query(call.id)
        except: pass
        msg_txt = "🔵 **عروض Telegram المتاحة**\n\nاختر السيرفر لعرض الدول والأسعار الخاصة بتطبيق تيليجرام فقط:"
        try:
            bot.edit_message_text(msg_txt, chat_id, message_id, parse_mode="Markdown", reply_markup=tg_servers_keyboard())
        except Exception:
            bot.send_message(chat_id, msg_txt, parse_mode="Markdown", reply_markup=tg_servers_keyboard())
        return

    # ==================== حسابات تيليجرام جاهزة ====================
    elif call.data == "ready_accounts_menu":
        try: bot.answer_callback_query(call.id)
        except: pass
        ready_text = (
            "💯 **قسم حسابات تيليجرام الجاهزة**\n\n"
            "▫️ حسابات مفعلة تسليم فوري وتلقائي.\n"
            "▫️ استلام كود الدخول وكلمة سر التحقق بخطوتين (2FA) فوراً.\n\n"
            "اختر السيرفر المطلوب:"
        )
        try:
            bot.edit_message_text(ready_text, chat_id, message_id, parse_mode="Markdown", reply_markup=ready_accounts_keyboard())
        except Exception:
            bot.send_message(chat_id, ready_text, parse_mode="Markdown", reply_markup=ready_accounts_keyboard())
        return

    elif call.data in ["ready_server_1", "ready_server_2"]:
        srv_num = "1" if "server_1" in call.data else "2"
        bot.answer_callback_query(call.id, "جاري جلب الدول والأسعار والمخزون...")
        markup = ready_accounts_countries_keyboard(server_id=srv_num, page=0)
        msg_txt = f"💯 **الحسابات المتاحة عبر السيرفر {srv_num}**:\n\nاختر الدولة المطلوبة:"
        try:
            bot.edit_message_text(msg_txt, chat_id, message_id, parse_mode="Markdown", reply_markup=markup)
        except Exception:
            bot.send_message(chat_id, msg_txt, parse_mode="Markdown", reply_markup=markup)
        return

    elif call.data == "ready_server_3":
        try: bot.answer_callback_query(call.id)
        except: pass
        msg_txt = "⏳ **قسم الحسابات القديمة والمعتقة**:\n\nاختر عمر الحساب المطلوب:"
        try:
            bot.edit_message_text(msg_txt, chat_id, message_id, parse_mode="Markdown", reply_markup=ready_aged_years_keyboard())
        except:
            bot.send_message(chat_id, msg_txt, parse_mode="Markdown", reply_markup=ready_aged_years_keyboard())
        return

    elif call.data.startswith("aged_age_"):
        age_val = call.data.replace("aged_age_", "")
        bot.answer_callback_query(call.id, f"جاري جلب حسابات {age_val}...")
        markup = ready_accounts_countries_keyboard(server_id='3', age=age_val, page=0)
        msg_txt = f"⏳ **الحسابات المتوفرة لسنة/عمر: {age_val}**\n\nاختر الدولة المطلوبة:"
        try:
            bot.edit_message_text(msg_txt, chat_id, message_id, parse_mode="Markdown", reply_markup=markup)
        except:
            bot.send_message(chat_id, msg_txt, parse_mode="Markdown", reply_markup=markup)
        return

    elif call.data.startswith("readyref_"):
        parts = call.data.split("_")
        srv_id = parts[1]
        age = parts[2] if len(parts) > 2 and parts[2] != 'none' else None
        bot.answer_callback_query(call.id, "🔄 جاري تحديث المخزون مباشرة من المزود...")
        fetch_ready_accounts_api(srv_id, age=age, force_refresh=True)
        markup = ready_accounts_countries_keyboard(server_id=srv_id, age=age, page=0)
        if srv_id == '3' and age:
            msg_txt = f"⏳ **الحسابات المتوفرة لسنة/عمر: {age}**\n\nاختر الدولة المطلوبة:"
        else:
            msg_txt = f"💯 **الحسابات المتاحة عبر السيرفر {srv_id}**:\n\nاختر الدولة المطلوبة:"
        try:
            bot.edit_message_text(msg_txt, chat_id, message_id, parse_mode="Markdown", reply_markup=markup)
        except Exception:
            try: bot.edit_message_reply_markup(chat_id, message_id, reply_markup=markup)
            except: pass
        return

    elif call.data.startswith("readypg_"):
        parts = call.data.split("_")
        srv_id = parts[1]
        age = parts[2] if len(parts) > 2 and parts[2] != 'none' else None
        page = int(parts[3]) if len(parts) > 3 else 0
        markup = ready_accounts_countries_keyboard(server_id=srv_id, age=age, page=page)
        if srv_id == '3' and age:
            msg_txt = f"⏳ **الحسابات المتوفرة لسنة/عمر: {age}**\n\nاختر الدولة المطلوبة:"
        else:
            msg_txt = f"💯 **الحسابات المتاحة عبر السيرفر {srv_id}**:\n\nاختر الدولة المطلوبة:"
        try:
            bot.edit_message_text(msg_txt, chat_id, message_id, parse_mode="Markdown", reply_markup=markup)
        except Exception:
            try: bot.edit_message_reply_markup(chat_id, message_id, reply_markup=markup)
            except: pass
        return

    elif call.data.startswith("view_ready_"):
        parts = call.data.split("_")
        srv_id = parts[2]
        c_code = parts[3]
        age = parts[4] if len(parts) > 4 and parts[4] != 'none' else None

        # جلب تفاصيل الدولة والسعر المحسوب
        countries = fetch_ready_accounts_api(srv_id, age=age)
        target = next((c for c in countries if str(c['code']).upper() == str(c_code).upper()), None)
        if not target:
            bot.answer_callback_query(call.id, "❌ عذراً، لم يعد هذا الحساب متوفراً حالياً.", show_alert=True)
            return

        c_name = target['name']
        price = target['price']
        count = target['count']

        detail_msg = (
            f"💙 **حساب Telegram جاهز - استلام فوري 100%**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"▫️ **السيرفر** : السيرفر {srv_id}\n"
            f"▫️ **الدولة** : {c_name}\n"
            f"▫️ **السعر** : `${price:.2f}`\n"
            f"▫️ **الكمية المتوفرة** : {count} حساب\n\n"
            f"ملاحظة : هذة الخدمة تعطيك رقم تم تجهيزة مسبقا وكل ما عليك نقل الرقم فقط فلا يمكنك إلغاء الرقم بعد شرائة وصول الكود مضمون 100%"
        )
        markup = ready_account_detail_keyboard(srv_id, c_code, age=age)
        try:
            bot.edit_message_text(detail_msg, chat_id, message_id, parse_mode="Markdown", reply_markup=markup)
        except Exception:
            bot.send_message(chat_id, detail_msg, parse_mode="Markdown", reply_markup=markup)
        return

    elif call.data.startswith("do_buy_ready_"):
        parts = call.data.split("_")
        srv_id = parts[3]
        c_code = parts[4]
        age = parts[5] if len(parts) > 5 and parts[5] != 'none' else None

        countries = fetch_ready_accounts_api(srv_id, age=age)
        target = next((c for c in countries if str(c['code']).upper() == str(c_code).upper()), None)
        if not target:
            bot.answer_callback_query(call.id, "❌ الحساب غير متوفر حالياً!", show_alert=True)
            return

        cost = target['price']
        c_name = target['name']

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            bal = row[0] if row else 0.0

            if bal < cost:
                bot.answer_callback_query(call.id, f"❌ رصيدك غير كافٍ!\nسعر الحساب: ${cost:.2f}\nرصيدك: ${bal:.2f}", show_alert=True)
                return

            bot.answer_callback_query(call.id, "⏳ جاري شراء وحجز الحساب من المزود...")

            # استدعاء API المزود الفعلي
            buy_result = buy_ready_account_api(srv_id, c_code)

            if not buy_result.get('ok'):
                err_text = buy_result.get('error', 'حدث خطأ غير متوقع من المزود')
                bot.send_message(chat_id, f"❌ **فشل إتمام الشراء من المزود:**\n{err_text}\n\n⚠️ لم يتم خصم أي مبلغ من رصيدك.", parse_mode="Markdown")
                return

            phone_number = buy_result.get('number', 'غير محدد')
            hash_code = buy_result.get('hash_code', '')
            lookup_key = hash_code if hash_code else phone_number

            # خصم الرصيد وتسجيل العملية
            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (cost, user_id))
            cursor.execute("INSERT INTO ready_accounts_orders (user_id, server_id, country_name, phone, session_file, cost, status) VALUES (?, ?, ?, ?, ?, ?, 'COMPLETED')",
                           (user_id, srv_id, c_name, str(phone_number), str(lookup_key), cost))
            conn.commit()

            success_msg = (
                f"🎉 **تم شراء وتجهيز حساب تيليجرام بنجاح!**\n\n"
                f"🌐 الدولة: {c_name}\n"
                f"📞 الرقم: `{phone_number}`\n"
                f"💵 المبلغ المخصوم: `${cost:.2f}`\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📌 **طريقة تفعيل الحساب:**\n"
                f"1️⃣ افتح تطبيق تيليجرام وضع الرقم أعلاه.\n"
                f"2️⃣ اضغط على زر [ 📩 جلب كود التفعيل / كلمة السر ] بالأسفل لاستلام الكود وكلمة المرور فوراً."
            )
            code_markup = ready_account_code_keyboard(srv_id, lookup_key)
            bot.send_message(chat_id, success_msg, parse_mode="Markdown", reply_markup=code_markup)
        finally:
            conn.close()
        return

    elif call.data.startswith("get_ready_code_"):
        parts = call.data.split("_")
        srv_id = parts[3]
        lookup_key = parts[4]

        bot.answer_callback_query(call.id, "⏳ جاري فحص وصول كود التيليجرام...")
        code_res = get_ready_account_code_api(srv_id, lookup_key)

        if code_res.get('ok') and code_res.get('code'):
            code_val = code_res.get('code')
            pass_val = code_res.get('password') or "لا يوجد كلمة سر (مباشر)"
            num_val = code_res.get('number') or lookup_key

            code_msg = (
                f"🎉 **وصل كود تسجيل الدخول بنجاح!**\n\n"
                f"📞 الرقم: `{num_val}`\n"
                f"🔑 كود التفعيل (Code): `{code_val}`\n"
                f"🔐 كلمة سر 2FA: `{pass_val}`\n\n"
                f"✅ تم الدخول بنجاح، مبارك عليك الحساب!"
            )
            bot.send_message(chat_id, code_msg, parse_mode="Markdown", reply_markup=back_button())
        else:
            err = code_res.get('error', 'لم يصل كود التيليجرام بعد')
            bot.send_message(
                chat_id,
                f"⏳ **حالة الكود:**\n{err}\n\nيرجى التأكد من إرسال طلب الكود في تطبيق التيليجرام ثم الضغط على الزر أدناه مرة أخرى 👇",
                reply_markup=ready_account_code_keyboard(srv_id, lookup_key)
            )
        return

    # ==================== لوحة الإدارة الكبرى ====================
    elif call.data == "admin_panel":
        if user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, f"❌ هذه اللوحة للمشرف فقط.", show_alert=True)
            return
        try: bot.edit_message_text("👑 **أهلاً بك في لوحة الإدارة الكبرى**\n\nتحكم كامل بكل ميزات وإعدادات ومستخدمي البوت:", chat_id, message_id, parse_mode="Markdown", reply_markup=admin_panel_keyboard())
        except: bot.send_message(chat_id, "👑 **أهلاً بك في لوحة الإدارة الكبرى**\n\nتحكم كامل بكل ميزات وإعدادات ومستخدمي البوت:", parse_mode="Markdown", reply_markup=admin_panel_keyboard())
        return

    elif call.data == "admin_self_charge_manual":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADMIN_SELF_CHARGE_INPUT'}
        bot.send_message(chat_id, "⚡ **شحن رصيد ذاتي لحسابك كأدمن**\n\nأرسل المبلغ المراد إضافته لرصيدك مباشرة (مثال: 50 أو 100):", reply_markup=admin_back_button())
        return

    elif call.data == "admin_all_users":
        if user_id != ADMIN_ID: return
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT user_id, name, username, balance, is_banned FROM users ORDER BY rowid DESC")
            all_users = cursor.fetchall()
        finally:
            conn.close()

        if not all_users:
            bot.send_message(chat_id, "❌ لا يوجد مستخدمين مسجلين بعد.", reply_markup=admin_back_button())
            return

        bot.send_message(chat_id, f"👥 **إجمالي المستخدمين المسجلين ({len(all_users)} مستخدم):**")
        for u in all_users[:25]:
            u_id, u_name, u_uname, u_bal, u_ban = u
            status = "محظور 🚫" if u_ban == 1 else "نشط ✅"
            card_msg = f"👤 {u_name} ({u_uname})\n🆔 `{u_id}` | 💰 ${u_bal:.2f} | 📌 {status}"
            mk = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("➕ شحن", callback_data=f"act_add_{u_id}"), InlineKeyboardButton("➖ خصم", callback_data=f"act_deduct_{u_id}"), InlineKeyboardButton("🚫 حظر/فك", callback_data=f"act_ban_{u_id}"))
            bot.send_message(chat_id, card_msg, parse_mode="Markdown", reply_markup=mk)
        return

    elif call.data == "admin_stats":
        if user_id != ADMIN_ID: return
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*), SUM(balance) FROM users")
            u_data = cursor.fetchone()
            total_users = u_data[0] or 0
            total_user_balance = u_data[1] or 0.0

            cursor.execute("SELECT COUNT(*), SUM(cost) FROM purchases")
            p_data = cursor.fetchone()
            num_purchases = p_data[0] or 0
            num_spent = p_data[1] or 0.0

            cursor.execute("SELECT COUNT(*), SUM(cost) FROM smm_orders")
            s_data = cursor.fetchone()
            smm_count = s_data[0] or 0
            smm_spent = s_data[1] or 0.0
        finally:
            conn.close()

        msg = (f"📊 **إحصائيات البوت الشاملة والأرصدة:**\n\n"
               f"👥 إجمالي المستخدمين: `{total_users}`\n"
               f"💰 إجمالي أرصدة المستخدمين: `${total_user_balance:.2f}`\n\n"
               f"📞 عمليات شراء الأرقام: `{num_purchases}` (مجموع: `${num_spent:.2f}`)\n"
               f"🚀 عمليات طلبات الرشق: `{smm_count}` (مجموع: `${smm_spent:.2f}`)\n"
               f"💵 إجمالي المبيعات الكلي: `${(num_spent + smm_spent):.2f}`")
        try: bot.edit_message_text(msg, chat_id, message_id, parse_mode="Markdown", reply_markup=admin_back_button())
        except: bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data == "admin_search_user":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADMIN_SEARCH_USER'}
        bot.send_message(chat_id, "🔍 أرسل آيدي أو يوزر أو اسم المستخدم للبحث عنه:", reply_markup=admin_back_button())
        return

    elif call.data.startswith("act_add_"):
        target_id = call.data.replace("act_add_", "")
        USER_STEPS[user_id] = {'step': 'ADMIN_ADD_BALANCE_DIRECT', 'target_id': target_id}
        bot.send_message(chat_id, f"💰 أرسل المبلغ المراد إضافته للحساب (`{target_id}`):", parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data.startswith("act_deduct_"):
        target_id = call.data.replace("act_deduct_", "")
        USER_STEPS[user_id] = {'step': 'ADMIN_DEDUCT_BALANCE_DIRECT', 'target_id': target_id}
        bot.send_message(chat_id, f"➖ أرسل المبلغ المراد خصمه من الحساب (`{target_id}`):", parse_mode="Markdown", reply_markup=admin_back_button())
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

    elif call.data == "admin_add_balance":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADMIN_ADD_BALANCE_INPUT'}
        bot.send_message(chat_id, "💰 **إضافة رصيد لمستخدم**\n\nأرسل آيدي المستخدم والمبلغ مفصولين بمسافة:\nمثال: `6113734300 25`", parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data == "admin_deduct_balance":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADMIN_DEDUCT_BALANCE_INPUT'}
        bot.send_message(chat_id, "➖ **خصم رصيد من مستخدم**\n\nأرسل آيدي المستخدم والمبلغ مفصولين بمسافة:\nمثال: `6113734300 10`", parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data == "admin_add_ai":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADMIN_ADD_AI'}
        bot.send_message(chat_id, "🤖 أرسل الآيدي وعدد أسئلة الذكاء:\n`ID العدد`", parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data == "admin_ban_menu":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADMIN_BAN_USER'}
        bot.send_message(chat_id, "🚫 أرسل آيدي المستخدم المراد حظره أو فك حظره:", reply_markup=admin_back_button())
        return

    elif call.data == "admin_broadcast":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADMIN_BROADCAST'}
        bot.send_message(chat_id, "📢 أرسل الرسالة التي ترغب في إذاعتها لجميع المستخدمين الآن:", reply_markup=admin_back_button())
        return

    elif call.data == "admin_recent_smm":
        if user_id != ADMIN_ID: return
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT order_id, user_id, service_name, quantity, cost, status, created_at FROM smm_orders ORDER BY id DESC LIMIT 5")
            orders = cursor.fetchall()
        finally:
            conn.close()
        if not orders:
            bot.send_message(chat_id, "📦 لا توجد طلبات رشق مسجلة بعد.", reply_markup=admin_back_button())
            return
        msg = "📦 **أحدث 5 طلبات رشق:**\n\n"
        for o in orders:
            msg += f"🧾 #{o[0]} | 👤 `{o[1]}`\n🛒 {o[2]}\n📊 الكمية: {o[3]} | 💵 ${o[4]:.3f} | 📌 {o[5]}\n⏰ {o[6]}\n\n"
        bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data == "admin_recent_numbers":
        if user_id != ADMIN_ID: return
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT tz_id, user_id, phone, service, cost, status, created_at FROM purchases ORDER BY id DESC LIMIT 5")
            purchases = cursor.fetchall()
        finally:
            conn.close()
        if not purchases:
            bot.send_message(chat_id, "📞 لا توجد طلبات أرقام مسجلة بعد.", reply_markup=admin_back_button())
            return
        msg = "📞 **أحدث 5 طلبات أرقام:**\n\n"
        for p in purchases:
            msg += f"🆔 #{p[0]} | 👤 `{p[1]}`\n📞 {p[2]} ({p[3].upper()})\n💵 ${p[4]:.2f} | 📌 {p[5]}\n⏰ {p[6]}\n\n"
        bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data == "admin_toggle_maintenance":
        if user_id != ADMIN_ID: return
        BOT_SETTINGS['maintenance'] = not BOT_SETTINGS.get('maintenance', False)
        status_txt = "🔴 تم تفعيل وضع الصيانة" if BOT_SETTINGS['maintenance'] else "🟢 تم إيقاف وضع الصيانة (البوت متاح للجميع)"
        bot.answer_callback_query(call.id, status_txt, show_alert=True)
        return

    # ==================== خيارات الإعدادات والمزيد ====================
    elif call.data == "my_orders_menu":
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT order_id, service_name, quantity, cost, status FROM smm_orders WHERE user_id = ? ORDER BY id DESC LIMIT 5", (user_id,))
            user_smm = cursor.fetchall()
            cursor.execute("SELECT tz_id, phone, service, cost, status FROM purchases WHERE user_id = ? ORDER BY id DESC LIMIT 5", (user_id,))
            user_nums = cursor.fetchall()
        finally:
            conn.close()

        msg = "📦 **قائمة آخر طلباتك:**\n\n"
        if user_smm:
            msg += "🚀 **طلبات الرشق:**\n"
            for s in user_smm:
                msg += f"• #{s[0]} | {s[1]} ({s[2]}) - ${s[3]:.3f} [{s[4]}]\n"
            msg += "\n"
        if user_nums:
            msg += "📞 **طلبات الأرقام:**\n"
            for n in user_nums:
                msg += f"• #{n[0]} | {n[1]} ({n[2].upper()}) - ${n[3]:.2f} [{n[4]}]\n"
        if not user_smm and not user_nums:
            msg += "لا توجد أي طلبات سابقة في حسابك حتى الآن."

        try: bot.edit_message_text(msg, chat_id, message_id, parse_mode="Markdown", reply_markup=more_settings_keyboard())
        except: bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=more_settings_keyboard())
        return

    elif call.data == "request_refill_all":
        bot.answer_callback_query(call.id, "🔄 تم إرسال طلب فحص التعويض التلقائي لجميع طلباتك المؤهلة!", show_alert=True)
        return

    elif call.data == "terms_and_rules":
        terms_text = (
            "📜 **الشروط والتعليمات لاستخدام الخدمات:**\n\n"
            "1️⃣ يرجى التأكد من وضع الحساب عام (Public) وليس خاص عند طلب الرشق.\n"
            "2️⃣ لا تقم بتغيير يوزر الحساب أو الرابط أثناء سريان تنفيذ الطلب.\n"
            "3️⃣ في حال واجهت أي استفسار يمكنك التواصل مع الدعم الفني مباشرة.\n"
            "4️⃣ يتم تسليم أكواد الأرقام تلقائياً فور وصول الرسالة من المزود."
        )
        try: bot.edit_message_text(terms_text, chat_id, message_id, parse_mode="Markdown", reply_markup=more_settings_keyboard())
        except: bot.send_message(chat_id, terms_text, parse_mode="Markdown", reply_markup=more_settings_keyboard())
        return

    elif call.data in ["check_single_order", "cancel_single_order"]:
        USER_STEPS[user_id] = {'step': 'CHECK_ORDER_ID'}
        bot.send_message(chat_id, "🔍 يرجى إرسال رقم الطلب (ID) للبحث ومتابعة حالته الآن:", reply_markup=more_settings_keyboard())
        return

    # ==================== الدفع عبر Binance ====================
    elif call.data == "pay_binance" or call.data == "deposit_binance":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="recharge_menu"))

        binance_intro = (
            "🟡 **شحن رصيد عبر Binance (تلقائي)**\n\n"
            "💵 ارسل المبلغ الذي تريد شحنه (بالدولار USDT):"
        )
        bot.send_message(chat_id, binance_intro, reply_markup=markup, parse_mode="Markdown")
        USER_STEPS[user_id] = {"step": "waiting_binance_amount"}
        return

    elif call.data == "enter_txid":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="recharge_menu"))
        bot.send_message(chat_id, "🟡 **أدخل رقم المعاملة (TXID):**", reply_markup=markup, parse_mode="Markdown")
        if user_id in USER_STEPS:
            USER_STEPS[user_id]["step"] = "waiting_binance_txid"
        else:
            USER_STEPS[user_id] = {"step": "waiting_binance_txid"}
        return

    elif call.data == "copy_id":
        bot.answer_callback_query(call.id, text=f"Pay ID: {BINANCE_PAY_ID} (تم النسخ)")
        return

    elif call.data == "recharge_menu":
        bot.answer_callback_query(call.id)
        if user_id in USER_STEPS: USER_STEPS.pop(user_id, None)
        try: bot.edit_message_text("🎳 شحن الرصيد / الاشتراكات\n\nاختر وسيلة الدفع التي تناسبك:", chat_id, message_id, reply_markup=recharge_keyboard())
        except: bot.send_message(chat_id, "🎳 شحن الرصيد / الاشتراكات\n\nاختر وسيلة الدفع التي تناسبك:", reply_markup=recharge_keyboard())
        return

    elif call.data.startswith("pay_"):
        pay_key = call.data.replace("pay_", "")
        pay_info = PAYMENT_DETAILS.get(pay_key)
        if pay_info:
            msg = (f"📌 تفاصيل الدفع عبر {pay_info['name']}\n\n🏷️ رقم الحساب: {pay_info['acc']}\n💵 أقل مبلغ: {pay_info['min']}\n💱 سعر الصرف: {pay_info['rate']}\n\n⚠️ حوّل المبلغ وأرسل صورة الإشعار مع الآيدي ({user_id}) للإدارة: {ADMIN_USERNAME}")
            back_markup = InlineKeyboardMarkup()
            back_markup.add(InlineKeyboardButton("🔙 العودة لوسائل الدفع", callback_data="recharge_menu"))
            try: bot.send_message(chat_id, msg, reply_markup=back_markup)
            except: pass
        return

    # ==================== باقي معالجات الأزرار القياسية ====================
    elif call.data == "back_main":
        if user_id in USER_STEPS: del USER_STEPS[user_id]
        user_data = get_or_create_user(user_id, call.from_user.first_name)
        try: balance = float(user_data[3]) if len(user_data) > 3 and user_data[3] is not None else float(user_data[2])
        except: balance = 0.0
        try: ai_bal = int(user_data[4]) if len(user_data) > 4 and user_data[4] is not None else 5
        except: ai_bal = 5

        text = (f"💠 أهلاً بك عزيزي في البوت الشامل 💠\n\n👤 حسابك: {ADMIN_USERNAME}\n💰 رصيدك الحالي: ${balance:.2f}\n🤖 رصيد أسئلة الذكاء: {ai_bal} سؤال\n\n📌 استخدم الأزرار بالأسفل لتنفيذ طلباتك:")
        try: bot.edit_message_text(text, chat_id, message_id, reply_markup=main_keyboard(user_id))
        except Exception:
            try: bot.delete_message(chat_id, message_id)
            except: pass
            bot.send_message(chat_id, text, reply_markup=main_keyboard(user_id))

    elif call.data == "transfer":
        USER_STEPS[user_id] = {'step': 'TRANSFER_TARGET'}
        text = ("🔄 قسم تحويل الرصيد بين الحسابات\n\n✨ الميزات: عمولة 0%\n💵 أقل مبلغ: $1.00\n\n📌 يرجى إرسال آيدي (User ID) الشخص المستلم الآن:")
        bot.edit_message_text(text, chat_id, message_id, reply_markup=back_button())

    elif call.data == "buy_number":
        bot.edit_message_text("📞 قسم شراء الأرقام الوهمية\n\nاختر السيرفر المناسب لك:", chat_id, message_id, reply_markup=servers_keyboard())

    elif call.data.startswith("select_server_"):
        server_id = call.data.split("_")[2]
        bot.edit_message_text(f"⚙️ تم اختيار السيرفر بنجاح\n\nاختر التطبيق المطلوب:", chat_id, message_id, reply_markup=services_keyboard(server_id))

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
            balance = cursor.fetchone()[0] or 0.0

            if balance < price:
                bot.send_message(chat_id, f"❌ رصيدك غير كافٍ!\nسعر الرقم: ${price:.2f}\nرصيدك الحالي: ${balance:.2f}")
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
                bot.send_message(chat_id, f"❌ لم يكتمل الطلب: {res}")
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
            cursor.execute('SELECT cost, status FROM purchases WHERE tz_id = ?', (tz_id,))
            purchase = cursor.fetchone()
            if purchase and purchase[1] == 'PENDING':
                cost = purchase[0]
                cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (cost, user_id))
                cursor.execute('UPDATE purchases SET status = "CANCELLED" WHERE tz_id = ?', (tz_id,))
                conn.commit()
                bot.edit_message_text(f"❌ تم إلغاء الرقم وإعادة (${cost:.2f}) إلى رصيدك.", chat_id, message_id, reply_markup=back_button())
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
        try: bot.edit_message_text("توفر خدمات متابعين وإعجابات ومشاهدات بأسعار مناسبة\n\n🧛♂️ الرجاء إختيار الخدمة:", chat_id, message_id, reply_markup=boost_keyboard("2"))
        except: bot.send_message(chat_id, "توفر خدمات متابعين وإعجابات ومشاهدات بأسعار مناسبة\n\n🧛♂️ الرجاء إختيار الخدمة:", reply_markup=boost_keyboard("2"))

    elif call.data == "games_menu":
        try: bot.edit_message_text("🎮 شحن الألعاب وبرامج بلاس 🕹️", chat_id, message_id, reply_markup=games_keyboard())
        except: bot.send_message(chat_id, "🎮 شحن الألعاب وبرامج بلاس 🕹️", reply_markup=games_keyboard())

    elif call.data.startswith("smmc_"):
        bot.answer_callback_query(call.id, "جاري جلب الخدمات...")
        parts = call.data.split("_")
        server_id, category_code = parts[1], parts[2]
        filtered_services = filter_smm_services(category_code, server_id)

        if not filtered_services:
            bot.send_message(chat_id, "❌ عذراً، لا توجد خدمات متاحة لهذا القسم حالياً.", reply_markup=back_button())
            return

        markup = dynamic_smm_keyboard(filtered_services, category_code, page=0, smm_server_id=server_id)
        msg_text = "✅ : جميع الخدمات المتوفرة في هذا القسم 👇\n☑️ : يرجى اختيار الخدمة المناسبة لك 👇"
        try: bot.edit_message_text(msg_text, chat_id, message_id, reply_markup=markup)
        except: bot.send_message(chat_id, msg_text, reply_markup=markup)

    elif call.data.startswith("smmp_"):
        parts = call.data.split("_")
        server_id, category_code, page = parts[1], parts[2], int(parts[3])
        filtered_services = filter_smm_services(category_code, server_id)
        markup = dynamic_smm_keyboard(filtered_services, category_code, page=page, smm_server_id=server_id)
        try: bot.edit_message_text("✅ : جميع الخدمات المتوفرة في هذا القسم 👇\n☑️ : يرجى اختيار الخدمة المناسبة لك 👇", chat_id, message_id, reply_markup=markup)
        except: pass

    elif call.data.startswith("smmbuy_"):
        parts = call.data.split("_")
        server_id, service_id = parts[1], parts[2]
        category_code = parts[3] if len(parts) > 3 else "others"

        services = get_cached_smm_services(server_id)
        selected_srv = next((s for s in services if str(s.get('service')) == str(service_id)), None)
        if not selected_srv:
            bot.answer_callback_query(call.id, "❌ خطأ في جلب بيانات الخدمة.", show_alert=True)
            return

        name = translate_text(str(selected_srv.get('name', 'خدمة غير محددة')))
        category_display = CATEGORY_TITLES.get(category_code, selected_srv.get('category', 'عام'))
        min_q = selected_srv.get('min', '10')
        max_q = selected_srv.get('max', '1000000')
        rate = float(selected_srv.get('rate', 0))
        price_profit = round(rate * 1.10, 4)

        speed = "سريعة" if "fast" in name.lower() or "سريع" in name else "فورية ⚡"
        quality = "عالية ✅" if "hq" in name.lower() or "جودة" in name else "ممتازة ⭐️"
        guarantee = "30 يوم" if "30" in name else ("ضمان تعويض ♻️" if "refill" in name.lower() or "ضمان" in name else "بدون ضمان ⚠️")

        msg_text = (
            f"📁 : اسم القسم: - {category_display}\n"
            f"🛍️ : الخدمة: {name}\n\n"
            f"✳️ : المعلومات الأكثر تفاصيل تجدها اسفل👇\n"
            f"🏷️ : يمكنك طلب الخدمة عبر الضغط على زر ( طلب الخدمة ) 🆔 ID الخدمة: {service_id}"
        )
        grid_markup = smm_detail_grid_keyboard(service_id, price_profit, speed, quality, guarantee, min_q, max_q, category_code, server_id)
        try: bot.edit_message_text(msg_text, chat_id, message_id, reply_markup=grid_markup)
        except: bot.send_message(chat_id, msg_text, reply_markup=grid_markup)

    elif call.data.startswith("smm_order_"):
        parts = call.data.split("_")
        server_id, service_id = parts[2], parts[3]
        category_code = parts[4] if len(parts) > 4 else "others"

        services = get_cached_smm_services(server_id)
        selected_srv = next((s for s in services if str(s.get('service')) == str(service_id)), None)
        if not selected_srv: return

        name = translate_text(str(selected_srv.get('name', 'خدمة')))
        category_display = CATEGORY_TITLES.get(category_code, 'عام')
        min_q = int(selected_srv.get('min', 10))
        max_q = int(selected_srv.get('max', 1000000))
        rate = float(selected_srv.get('rate', 0))
        price_1k = round(rate * 1.10, 4)

        USER_STEPS[user_id] = {
            'step': 'WAITING_LINK', 'service_id': service_id, 'server_id': server_id,
            'category_code': category_code, 'category_display': category_display,
            'service_name': name, 'min_q': min_q, 'max_q': max_q, 'price_1k': price_1k
        }

        msg_text = (
            f"🚀 : انشاء طلب جديد\n\n"
            f"♻️ : اسم الخدمة: {name}\n"
            f"💰 : السعر لكل 1000: ${price_1k:.3f}\n"
            f"📊 : الحد الأدنى: {min_q} | 📉 : الحد الأقصى: {max_q}\n\n"
            f"🔗 : الآن من فضلك أرسل رابط الطلب:"
        )
        try: bot.edit_message_text(msg_text, chat_id, message_id, reply_markup=smm_cancel_link_keyboard(service_id, category_code))
        except: bot.send_message(chat_id, msg_text, reply_markup=smm_cancel_link_keyboard(service_id, category_code))

    elif call.data.startswith("smm_confirm_"):
        parts = call.data.split("_")
        server_id, service_id, qty, total_cost = parts[2], parts[3], int(parts[4]), float(parts[5])
        category_code = parts[6] if len(parts) > 6 else "others"

        step_info = USER_STEPS.get(user_id, {})
        link = step_info.get('link', '')
        service_name = step_info.get('service_name', f"خدمة #{service_id}")
        category_name = step_info.get('category_display', 'عام')

        if not link:
            bot.send_message(chat_id, "❌ انتهت الجلسة، يرجى إعادة إرسال الرابط مجدداً.", reply_markup=back_button())
            return

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
            balance = cursor.fetchone()[0] or 0.0

            if balance < total_cost:
                bot.answer_callback_query(call.id, "❌ رصيدك غير كافٍ لإتمام الطلب!", show_alert=True)
                return

            order_response = smm_request(server_id, 'add', service=service_id, link=link, quantity=qty)
            if order_response and 'order' in order_response:
                order_id = str(order_response['order'])
                cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (total_cost, user_id))
                cursor.execute('''
                    INSERT INTO smm_orders (order_id, user_id, service_id, service_name, category_name, link, quantity, cost, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
                ''', (order_id, user_id, service_id, service_name, category_name, link, qty, total_cost))
                conn.commit()

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
                except: bot.send_message(chat_id, success_msg, reply_markup=markup)
            else:
                err = order_response.get('error', 'فشل الإرسال') if order_response else 'خطأ اتصال'
                bot.edit_message_text(f"❌ خطأ من المزود: {err}\nلم يتم خصم أي رصيد.", chat_id, message_id, reply_markup=back_button())
        finally:
            conn.close()
            if user_id in USER_STEPS: del USER_STEPS[user_id]

    elif call.data.startswith("smm_stat_"):
        order_id = call.data.split("_")[2]
        bot.answer_callback_query(call.id, "جاري فحص حالة الطلب...")
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT service_name, category_name, link, quantity, cost, status FROM smm_orders WHERE order_id = ?', (order_id,))
            order_data = cursor.fetchone()
        finally:
            conn.close()

        if not order_data:
            bot.send_message(chat_id, "❌ لم يتم العثور على الطلب.")
            return

        srv_name, cat_name, link, qty, cost, db_status = order_data
        status_res = smm_request('2', 'status', order=order_id)
        api_status = status_res.get('status', db_status) if status_res else db_status
        remains = status_res.get('remains', '0') if status_res else '0'
        try: remains_num = int(remains)
        except: remains_num = 0

        date_str = get_arabic_datetime()
        if str(api_status).lower() in ['completed', 'مكتمل']:
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
            update_msg = (
                f"📊 - تفاصيل حالة الطلب الحالية -\n\n"
                f"🧾 : رقم الطلب: #{order_id}\n"
                f"🛒 : الخدمة: {srv_name}\n"
                f"🔗 : الرابط: [{link}]\n"
                f"🏷️ : العدد المطلوب: {qty}\n"
                f"🅿️ : العدد المتبقي: {remains_num}\n"
                f"🔘 : الحاله: في الانتظار / قيد التنفيذ 🔄\n"
                f"⏰ : آخر فحص: {date_str}"
            )
            markup = smm_order_status_keyboard(order_id, "", qty, cost, link, cat_name, srv_name)
            try: bot.edit_message_text(update_msg, chat_id, message_id, reply_markup=markup)
            except: bot.send_message(chat_id, update_msg, reply_markup=markup)

    elif call.data == "free_ruble":
        ref_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,))
            cnt = cursor.fetchone()[0]
        finally:
            conn.close()
        bot.edit_message_text(f"💎 نظام اربح رصيد مجاني 💎\n\nرابط إحالتك:\n`{ref_link}`\n👥 المدعوين: {cnt}\n💵 الأرباح: ${(cnt*REWARD_PER_INVITE):.2f}", chat_id, message_id, parse_mode="Markdown", reply_markup=back_button())

    elif call.data == "ai_landing":
        bot.edit_message_text("🤖 قسم خدمات الذكاء الاصطناعي\n\nاطرح سؤالك مباشرة في المحادثة وسيجيبك البوت.", chat_id, message_id, reply_markup=back_button())

    elif call.data == "fast_buy_wa":
        markup = countries_keyboard_fast("grizzly", "wa", page=0)
        bot.edit_message_text("🟢 عروض واتساب المتاحة:", chat_id, message_id, reply_markup=markup)

    elif call.data == "best_selling":
        bot.edit_message_text("🔥 أكثر السيرفرات طلباً متوفرة في القائمة الرئيسية.", chat_id, message_id, reply_markup=back_button())

    elif call.data == "most_available":
        bot.edit_message_text("🎲 الأرقام الأكثر توفراً: روسيا، نيجيريا، أمريكا، وأوكرانيا.", chat_id, message_id, reply_markup=back_button())

    elif call.data == "support":
        bot.edit_message_text(f"🎧 الدعم الفني: {ADMIN_USERNAME}", chat_id, message_id, reply_markup=back_button())

    elif call.data == "purchase_stats":
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM purchases")
            c1 = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM smm_orders")
            c2 = cursor.fetchone()[0]
        finally:
            conn.close()
        bot.edit_message_text(f"✔ إحصائيات العمليات الناجحة: تم تنفيذ أكثر من {c1 + c2 + 100} عملية بنجاح.", chat_id, message_id, reply_markup=back_button())

    elif call.data == "my_account":
        user_data = get_or_create_user(user_id, call.from_user.first_name)
        try: balance = float(user_data[3]) if len(user_data) > 3 and user_data[3] is not None else float(user_data[2])
        except: balance = 0.0
        try: ai_bal = int(user_data[4]) if len(user_data) > 4 and user_data[4] is not None else 5
        except: ai_bal = 5
        msg = f"👤 حسابك:\n🆔: `{user_data[0]}`\n💰 الرصيد: ${balance:.2f}\n🤖 رصيد AI: {ai_bal}"
        bot.edit_message_text(msg, chat_id, message_id, parse_mode="Markdown", reply_markup=back_button())

# ==================== معالجة الرسائل والخطوات ====================
@bot.message_handler(func=lambda msg: msg.from_user.id in USER_STEPS)
def handle_user_steps(message):
    user_id = message.from_user.id
    step_data = USER_STEPS.get(user_id, {})
    step = step_data.get('step')

    if step == "waiting_binance_amount":
        try:
            amount = float(message.text.strip())
            if amount <= 0: raise ValueError()
            USER_STEPS[user_id] = {"step": "waiting_binance_txid", "amount": amount}

            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("📋 نسخ العنوان", callback_data="copy_id"))
            markup.add(InlineKeyboardButton("✅ تم الدفع (أدخل TXID)", callback_data="enter_txid"))
            markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="recharge_menu"))

            binance_details = (
                f"🟡 **تفاصيل الدفع عبر Binance**\n\n"
                f"💵 المبلغ: {amount} USDT\n"
                f"📍 عنوان (Pay ID):\n`{BINANCE_PAY_ID}`"
            )
            bot.send_message(message.chat.id, binance_details, reply_markup=markup, parse_mode="Markdown")
        except:
            bot.send_message(message.chat.id, "❌ يرجى إرسال رقم صحيح للمبلغ (مثال: 10 أو 4):")
        return

    elif step == "waiting_binance_txid":
        txid = message.text.strip()
        expected_amount = step_data.get("amount", 0)
        wait_msg = bot.send_message(message.chat.id, "🔄 جاري التحقق من المعاملة...")
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
            bot.send_message(message.chat.id, f"✅ تم شحن {expected_amount} USDT إلى رصيدك بنجاح.")
            del USER_STEPS[user_id]
        else:
            bot.send_message(message.chat.id, "❌ فشل التحقق من المعاملة. تأكد من صحة TXID والمبلغ.")
        return

    elif step == 'TRANSFER_TARGET':
        target_id_str = message.text.strip()
        if not target_id_str.isdigit():
            bot.send_message(message.chat.id, "❌ أرسل الآيدي بالأرقام فقط.")
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
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود بالبوت.")
            return
        USER_STEPS[user_id] = {'step': 'TRANSFER_AMOUNT', 'target_id': target_id, 'target_name': target_user[0]}
        bot.send_message(message.chat.id, f"👤 المستلم: {target_user[0]} (`{target_id}`)\n💵 أدخل المبلغ المراد تحويله (أقل مبلغ ${MIN_TRANSFER_AMOUNT:.2f}):", parse_mode="Markdown")
        return

    elif step == 'TRANSFER_AMOUNT':
        try:
            amount = float(message.text.strip())
            if amount < MIN_TRANSFER_AMOUNT:
                bot.send_message(message.chat.id, f"❌ أقل مبلغ للتحويل ${MIN_TRANSFER_AMOUNT:.2f}.")
                return
            target_id = step_data['target_id']
            conn = get_db()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
                sender_bal = cursor.fetchone()[0] or 0.0
                if sender_bal < amount:
                    bot.send_message(message.chat.id, f"❌ رصيدك غير كافٍ!\nرصيدك: ${sender_bal:.2f}")
                    return
                cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_id))
                conn.commit()
            finally:
                conn.close()
            del USER_STEPS[user_id]
            bot.send_message(message.chat.id, f"✅ تم تحويل ${amount:.2f} بنجاح إلى `{target_id}`.", parse_mode="Markdown", reply_markup=back_button())
            try: bot.send_message(target_id, f"🎉 وصلك تحويل رصيد بقيمة ${amount:.2f}!")
            except: pass
        except:
            bot.send_message(message.chat.id, "❌ أدخل مبلغاً صحيحاً بالأرقام.")
        return

    if user_id == ADMIN_ID:
        if step == 'ADMIN_SELF_CHARGE_INPUT':
            del USER_STEPS[user_id]
            try:
                amt = float(message.text.strip())
                conn = get_db()
                cursor = conn.cursor()
                try:
                    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, ADMIN_ID))
                    conn.commit()
                    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (ADMIN_ID,))
                    new_bal = cursor.fetchone()[0]
                finally:
                    conn.close()
                bot.send_message(message.chat.id, f"✅ تم شحن ${amt:.2f} لحسابك كأدمن بنجاح!\n💰 رصيدك الحالي: ${new_bal:.2f}", reply_markup=admin_back_button())
            except:
                bot.send_message(message.chat.id, "❌ يرجى كتابة مبلغ صحيح بالأرقام.", reply_markup=admin_back_button())
            return

        elif step == 'ADMIN_ADD_BALANCE_INPUT':
            del USER_STEPS[user_id]
            try:
                parts = message.text.strip().split()
                t_id, amt = int(parts[0]), float(parts[1])
                conn = get_db()
                cursor = conn.cursor()
                try:
                    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (t_id,))
                    exists = cursor.fetchone()
                    if not exists:
                        cursor.execute("INSERT INTO users (user_id, name, balance) VALUES (?, 'مستخدم', ?)", (t_id, amt))
                    else:
                        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, t_id))
                    conn.commit()
                    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (t_id,))
                    new_bal = cursor.fetchone()[0]
                finally:
                    conn.close()
                bot.send_message(message.chat.id, f"✅ تم إضافة ${amt:.2f} للحساب `{t_id}` بنجاح!\n💰 رصيده الجديد: ${new_bal:.2f}", parse_mode="Markdown", reply_markup=admin_back_button())
                try: bot.send_message(t_id, f"🎁 تم شحن رصيدك بمبلغ ${amt:.2f} بواسطة الإدارة!")
                except: pass
            except:
                bot.send_message(message.chat.id, "❌ صيغة غير صحيحة! اكتب: `ID المبلغ`", parse_mode="Markdown", reply_markup=admin_back_button())
            return

        elif step == 'ADMIN_DEDUCT_BALANCE_INPUT':
            del USER_STEPS[user_id]
            try:
                parts = message.text.strip().split()
                t_id, amt = int(parts[0]), float(parts[1])
                conn = get_db()
                cursor = conn.cursor()
                try:
                    cursor.execute("UPDATE users SET balance = MAX(0.0, balance - ?) WHERE user_id = ?", (amt, t_id))
                    conn.commit()
                    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (t_id,))
                    new_bal = cursor.fetchone()[0]
                finally:
                    conn.close()
                bot.send_message(message.chat.id, f"✅ تم خصم ${amt:.2f} من الحساب `{t_id}` بنجاح!\n💰 رصيده الحالي: ${new_bal:.2f}", parse_mode="Markdown", reply_markup=admin_back_button())
            except:
                bot.send_message(message.chat.id, "❌ صيغة غير صحيحة! اكتب: `ID المبلغ`", parse_mode="Markdown", reply_markup=admin_back_button())
            return

        elif step in ['ADMIN_ADD_BALANCE_DIRECT', 'ADMIN_DEDUCT_BALANCE_DIRECT']:
            try:
                t_id = step_data['target_id']
                val = float(message.text.strip())
                conn = get_db()
                cursor = conn.cursor()
                try:
                    if step == 'ADMIN_ADD_BALANCE_DIRECT':
                        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (val, t_id))
                    else:
                        cursor.execute("UPDATE users SET balance = MAX(0.0, balance - ?) WHERE user_id = ?", (val, t_id))
                    conn.commit()
                    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (t_id,))
                    new_bal = cursor.fetchone()[0]
                finally:
                    conn.close()
                del USER_STEPS[user_id]
                bot.send_message(message.chat.id, f"✅ تمت العملية بنجاح للحساب `{t_id}`!\n💰 رصيده الآن: ${new_bal:.2f}", parse_mode="Markdown", reply_markup=admin_back_button())
            except:
                bot.send_message(message.chat.id, "❌ أدخل قيمة صحيحة.")
            return

        elif step == 'ADMIN_BROADCAST':
            del USER_STEPS[user_id]
            conn = get_db()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT user_id FROM users")
                all_u = cursor.fetchall()
            finally:
                conn.close()
            succ = fail = 0
            for (u_id,) in all_u:
                try:
                    bot.copy_message(u_id, message.chat.id, message.message_id)
                    succ += 1
                    time.sleep(0.04)
                except: fail += 1
            bot.send_message(message.chat.id, f"📢 تم الإرسال للجميع:\n✅ نجاح: `{succ}` | ❌ فشل: `{fail}`", parse_mode="Markdown", reply_markup=admin_back_button())
            return

        elif step == 'ADMIN_SEARCH_USER':
            del USER_STEPS[user_id]
            query = message.text.strip().replace("@", "")
            conn = get_db()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT user_id, name, username, balance, is_banned FROM users WHERE name LIKE ? OR username LIKE ? OR user_id = ?", ('%'+query+'%', '%'+query+'%', query))
                users = cursor.fetchall()
            finally:
                conn.close()
            if not users:
                bot.send_message(message.chat.id, "❌ لم يتم العثور على مستخدم.", reply_markup=admin_back_button())
                return
            for u in users:
                st = "محظور 🚫" if u[4] == 1 else "نشط ✅"
                res = f"👤 {u[1]} ({u[2]})\n🆔 `{u[0]}` | 💰 ${u[3]:.2f} | 📌 {st}"
                mk = InlineKeyboardMarkup()
                mk.row(InlineKeyboardButton("➕ رصيد", callback_data=f"act_add_{u[0]}"), InlineKeyboardButton("➖ خصم", callback_data=f"act_deduct_{u[0]}"), InlineKeyboardButton("🚫 حظر/فك", callback_data=f"act_ban_{u[0]}"))
                bot.send_message(message.chat.id, res, reply_markup=mk)
            return

    if step == 'WAITING_LINK':
        link = message.text.strip()
        step_data['link'] = link
        step_data['step'] = 'WAITING_QTY'
        price_1k = step_data.get('price_1k', 0.5)
        single_price = price_1k / 1000
        min_q, max_q = step_data.get('min_q', 10), step_data.get('max_q', 1000000)

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
            user_bal = cursor.fetchone()[0] or 0.0
        finally:
            conn.close()

        possible_qty = int(user_bal / single_price) if single_price > 0 else 0
        ask_qty_msg = (
            f"☑️ : يرجى إرسال عدد الأعضاء تذكر أقل عدد للطلب {min_q}، وأقصى عدد للطلب {max_q} 👤\n\n"
            f"💰 : سعر العضو الواحد: ${single_price:.6f}\n\n"
            f"🏆 : يمكنك رشق {possible_qty} عضو 👥"
        )
        bot.send_message(message.chat.id, ask_qty_msg)
        return

    elif step == 'WAITING_QTY':
        if not message.text.strip().isdigit():
            bot.send_message(message.chat.id, "❌ يرجى إرسال الكمية بالأرقام فقط.")
            return

        qty = int(message.text.strip())
        min_q, max_q = step_data.get('min_q', 10), step_data.get('max_q', 1000000)
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
            bot.send_message(message.chat.id, f"❌ رصيدك غير كافٍ!\n💵 تكلفة الطلب: ${total_cost:.5f}\n💰 رصيدك: ${balance:.2f}", reply_markup=back_button())
            del USER_STEPS[user_id]
            return

        confirm_text = (
            f"✅ - معلومات تأكيد الطلب .\n\n"
            f"🌀 - القسم: - {category_display}\n"
            f"🛍️ - الخدمة: {service_name}\n"
            f"💰 - السعر 1K: ${price_1k:.3f}\n"
            f"💸 - السعر الكلي: ${total_cost:.5f}\n"
            f"🔥 - الجودة: عالية جداً 🏆\n"
            f"🚀 - السرعة: سريعة وفورية 🚀\n"
            f"🧿 - الضمان: ضمان تعويض تلقائي 🔰\n\n"
            f"🔗 - الرابط: [{link}]\n\n"
            f"♻️ - هل تريد المتابعة وتأكيد الطلب؟"
        )
        markup = smm_confirm_keyboard(service_id, qty, total_cost, category_code=category_code, smm_server_id=server_id)
        bot.send_message(message.chat.id, confirm_text, reply_markup=markup)
        return

# معالج الضغط على زر التحقق
@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def callback_check(call):
    user_id = call.from_user.id
    if check_subscription(user_id):
        bot.answer_callback_query(call.id, "اشتركت بنجاح! 🎉", show_alert=True)
        bot.send_message(call.message.chat.id, "شكراً لاشتراكك! يمكنك استخدام البوت الآن.")
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
    else:
        bot.answer_callback_query(call.id, "عذراً، أنت لم تشترك في إحدى القناتين بعد! ❌", show_alert=True)

# ==================== بدء تشغيل البوت ====================
if __name__ == '__main__':
    print("🤖 تم بدء تشغيل البوت بنجاح وحفظ البيانات بشكل دائم في SQLite...")
    try:
        bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        print(f"Webhook reset warning: {e}")

    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=20, skip_pending=True)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)
