import os
import sys
import shutil
import time
import datetime
import sqlite3
import hmac
import hashlib
import html
import json
import re
import ssl
import urllib.request
from urllib.parse import urlencode
import threading

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand

from config import (
    TOKEN, ADMIN_ID, ADMIN_USERNAME, REWARD_PER_INVITE, MIN_TRANSFER_AMOUNT, 
    DEFAULT_PRICE, PAYMENT_DETAILS, SERVERS, SMM_SERVERS, READY_ACCOUNTS_PROVIDERS,
    USER_STEPS, BOT_SETTINGS, CHANNEL_OFFICIAL_NAME, CHANNEL_OFFICIAL_ID, CHANNEL_OFFICIAL_URL,
    CHANNEL_ORDERS_NAME, CHANNEL_ORDERS_ID, CHANNEL_ORDERS_URL,
    CHANNEL_TUTORIALS_NAME, CHANNEL_TUTORIALS_ID, CHANNEL_TUTORIALS_URL,
    CHANNEL_EXPLAINS_NAME, CHANNEL_EXPLAINS_ID, CHANNEL_EXPLAINS_URL,
    get_db, get_or_create_user, is_user_banned, fetch_server_prices, get_server_raw_price,
    grizzly_request, get_clean_country_info, clean_phone_number, fetch_ready_accounts_api,
    buy_ready_account_api, get_ready_account_code_api,
    http_get_json, http_post_form,
    get_setting, set_setting, is_section_enabled, toggle_section, get_profit_margin,
    record_user_purchase, add_user_balance, deduct_user_balance, set_user_ban_status, format_money,
    get_payment_methods_db, update_payment_method_db, toggle_payment_method_db,
    get_providers_db, update_provider_api_key_db, add_provider_db, delete_provider_db,
    get_agents_db, add_agent_db, remove_agent_db, get_user_agent_discount,
    POPULAR_SERVICES, DB_FILE, get_db_metrics, scan_and_recover_database,
    restore_database_from_uploaded_file, backup_db_safely,
    get_custom_smm_services, get_custom_smm_categories_counts, add_custom_smm_service, delete_custom_smm_service,
    export_custom_smm_services_json, import_custom_smm_services_json,
    ensure_user_columns, is_user_verified, set_user_verified
)

from keyboards import (
    main_keyboard, back_button, admin_back_button, admin_panel_keyboard,
    more_settings_keyboard, ready_accounts_keyboard, ready_aged_years_keyboard,
    ready_accounts_countries_keyboard, ready_account_detail_keyboard, ready_account_code_keyboard,
    tg_servers_keyboard, wa_servers_keyboard, recharge_keyboard,
    binance_amount_keyboard, binance_details_keyboard, binance_txid_input_keyboard, binance_txid_fail_keyboard,
    servers_keyboard, services_keyboard, countries_keyboard_fast, active_number_keyboard,
    no_numbers_keyboard, completed_number_keyboard,
    smm_main_keyboard, smm_servers_menu_keyboard, games_keyboard, boost_keyboard, dynamic_smm_keyboard,
    smm_detail_grid_keyboard, smm_cancel_link_keyboard, smm_confirm_keyboard,
    smm_order_status_keyboard, translate_text, get_store_keyboard, get_back_to_store_keyboard,
    admin_sections_keyboard, admin_profits_keyboard, admin_payments_keyboard,
    admin_payment_detail_keyboard, admin_providers_keyboard, admin_provider_detail_keyboard,
    admin_channels_keyboard, admin_agents_keyboard, admin_support_keyboard,
    admin_transfer_keyboard, admin_referrals_keyboard, admin_aged_stock_keyboard,
    admin_smm_custom_keyboard, admin_smm_select_app_keyboard, admin_smm_categories_view_keyboard,
    admin_smm_services_list_keyboard, admin_smm_guarantee_keyboard, admin_smm_speed_keyboard,
    user_support_keyboard, admin_captcha_keyboard, free_balance_keyboard,
    free_balance_team_keyboard, free_balance_earnings_keyboard,
    admin_users_pagination_keyboard
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

def get_binance_pay_id():
    try:
        methods = get_payment_methods_db()
        for m in methods:
            if m[0] == 'binance' and m[2]:
                val = str(m[2]).strip()
                if val: return val
    except Exception:
        pass
    return BINANCE_PAY_ID

def get_binance_signature(query_string, secret_key):
    return hmac.new(secret_key.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

def is_txid_already_used(txid):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id FROM used_txids WHERE txid = ?", (str(txid).strip(),))
        return cursor.fetchone() is not None
    except Exception:
        return False
    finally:
        conn.close()

def record_used_txid(txid, user_id, amount):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR REPLACE INTO used_txids (txid, user_id, amount) VALUES (?, ?, ?)", (str(txid).strip(), user_id, float(amount)))
        conn.commit()
    except Exception as e:
        print(f"Error recording txid: {e}")
    finally:
        conn.close()

def verify_binance_txid(txid, expected_amount):
    txid_clean = str(txid).strip()
    if not txid_clean:
        return False, "empty"
    
    if is_txid_already_used(txid_clean):
        return False, "used"

    url = "https://api.binance.com/sapi/v1/pay/transactions"
    timestamp = int(time.time() * 1000)
    params = {"timestamp": timestamp, "txId": txid_clean}
    query_string = urlencode(params)
    signature = get_binance_signature(query_string, SECRET_KEY)
    headers = {"X-MBX-APIKEY": API_KEY_BINANCE}
    try:
        data = http_get_json(f"{url}?{query_string}&signature={signature}", headers=headers, timeout=10)
        if data and "data" in data and len(data["data"]) > 0:
            tx_info = data["data"][0]
            tx_amount = float(tx_info.get("amount", 0))
            if tx_amount >= float(expected_amount) * 0.98:
                return True, "ok"
        return False, "not_found"
    except Exception as e:
        print(f"Error checking transaction: {e}")
        return False, "error"

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
        return http_post_form(srv['url'], payload, timeout=12)
    except Exception as e:
        print(f"SMM API Error ({server_id}): {e}")
        return None

def parse_safe_float(val, default=0.0):
    if val is None: return default
    s = str(val).strip()
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    for i, d in enumerate(arabic_digits):
        s = s.replace(d, str(i))
    s = re.sub(r'[^\d\.,\-]', '', s)
    s = s.replace(',', '.')
    try:
        return float(s)
    except:
        return default

def parse_safe_int(val, default=0):
    if val is None: return default
    s = str(val).strip()
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    for i, d in enumerate(arabic_digits):
        s = s.replace(d, str(i))
    s = re.sub(r'[^\d\-]', '', s)
    try:
        return int(s)
    except:
        return default

def get_cached_smm_services(server_id='2'):
    global SMM_SERVICES_CACHE, SMM_CACHE_TIME
    server_id = str(server_id)
    now = time.time()

    # السيرفر 2 (الأرخص): يعتمد 100% فقط وحصرياً على الخدمات اليدوية المضافة من الأدمن
    if server_id == 'tiger':
        return get_custom_smm_services(server_id='tiger')

    # جلب أي خدمات مخصصة مدخلة يدوياً
    custom_services = get_custom_smm_services(server_id=server_id)

    if server_id in SMM_SERVICES_CACHE and (now - SMM_CACHE_TIME.get(server_id, 0) < 300):
        api_services = SMM_SERVICES_CACHE[server_id]
    else:
        api_services = smm_request(server_id, 'services')
        if api_services and isinstance(api_services, list):
            SMM_SERVICES_CACHE[server_id] = api_services
            SMM_CACHE_TIME[server_id] = now
        else:
            api_services = []

    if custom_services:
        return custom_services + [s for s in api_services if not any(str(c['service']) == str(s.get('service')) for c in custom_services)]
    return api_services

CATEGORY_TITLES = {
    'telegram': 'رشق تيليجرام',
    'instagram': 'رشق إنستغرام',
    'youtube': 'رشق يوتيوب',
    'twitter': 'رشق تويتر (X)',
    'facebook': 'رشق فيسبوك',
    'tiktok': 'رشق تيك توك',
    'threads': 'رشق ثريدز',
    'whatsapp': 'رشق واتساب',
    'others': 'خدمات أخرى'
}

def filter_smm_services(target_type, server_id='2'):
    server_id = str(server_id)
    
    # للسيرفر 2: جلب الخدمات المخصصة لهذا التطبيق مباشرة بدون أي خلط أو ترجمة عشوائية
    if server_id == 'tiger':
        return get_custom_smm_services(server_id='tiger', category=target_type)

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
        if srv.get('is_custom'):
            cat = str(srv.get('category', '')).lower()
            if cat == target_type or (target_type == 'others' and cat not in arabic_keywords):
                filtered.append(srv)
                continue

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
def check_subscription(user_id):
    # الأدمن يتجاوز فحص الاشتراك دائماً
    if user_id == ADMIN_ID:
        return True

    # هل الاشتراك الإجباري مفعل من الإدارة؟
    if get_setting('force_sub_active', '1') != '1':
        return True

    # جلب معرفات القنوات الأربع من الإعدادات
    ch_official_id = get_setting('channel_official_id', CHANNEL_OFFICIAL_ID)
    ch_orders_id = get_setting('channel_orders_id', CHANNEL_ORDERS_ID)
    ch_tutorials_id = get_setting('channel_tutorials_id', CHANNEL_TUTORIALS_ID)
    ch_explains_id = get_setting('channel_explains_id', CHANNEL_EXPLAINS_ID)

    channels_to_check = []
    for c_id in [ch_official_id, ch_orders_id, ch_tutorials_id, ch_explains_id]:
        if c_id:
            c_str = str(c_id).strip()
            if c_str:
                try:
                    channels_to_check.append(int(c_str))
                except ValueError:
                    channels_to_check.append(c_str)

    if not channels_to_check:
        return True

    valid_statuses = ['member', 'creator', 'administrator']
    for ch in channels_to_check:
        try:
            member = bot.get_chat_member(ch, user_id)
            if member.status not in valid_statuses:
                return False
        except Exception as e:
            err_msg = str(e).lower()
            if "user not found" in err_msg or "user_not_participant" in err_msg:
                return False
            # في حال لم يكن البوت مشرفاً في القناة أو خطأ في المعرف، نتجاوز حتى لا يتعطل المستخدم
            print(f"Subscription check warning for channel {ch}: {e}")
            continue

    return True

def subscription_markup():
    ch_off_url = get_setting('channel_official_url', CHANNEL_OFFICIAL_URL)
    ch_ord_url = get_setting('channel_orders_url', CHANNEL_ORDERS_URL)
    ch_tut_url = get_setting('channel_tutorials_url', CHANNEL_TUTORIALS_URL)
    ch_exp_url = get_setting('channel_explains_url', CHANNEL_EXPLAINS_URL)
    
    ch_off_name = get_setting('channel_official_name', CHANNEL_OFFICIAL_NAME)
    ch_ord_name = get_setting('channel_orders_name', CHANNEL_ORDERS_NAME)
    ch_tut_name = get_setting('channel_tutorials_name', CHANNEL_TUTORIALS_NAME)
    ch_exp_name = get_setting('channel_explains_name', CHANNEL_EXPLAINS_NAME)

    markup = InlineKeyboardMarkup()
    # الصف الأول: القناة الرسمية وقناة التفعيلات
    row1 = []
    if ch_off_url:
        row1.append(InlineKeyboardButton(f"{ch_off_name} 📢", url=ch_off_url))
    if ch_ord_url:
        row1.append(InlineKeyboardButton(f"{ch_ord_name} 🛍️", url=ch_ord_url))
    if row1:
        markup.row(*row1)

    # الصف الثاني: قناة التعليمات وقناة الشروحات
    row2 = []
    if ch_tut_url:
        row2.append(InlineKeyboardButton(f"{ch_tut_name} 📚", url=ch_tut_url))
    if ch_exp_url:
        row2.append(InlineKeyboardButton(f"{ch_exp_name} 🎬", url=ch_exp_url))
    if row2:
        markup.row(*row2)

    markup.add(InlineKeyboardButton("تحقـق من الاشتـراك ✅", callback_data="check_sub"))
    return markup

# ==================== إشعارات الطلبات والتفعيلات التلقائية للقناة ====================
def mask_phone(phone):
    if not phone: return "••••••••"
    clean = str(phone).replace(" ", "").strip()
    has_plus = clean.startswith("+")
    raw = clean.replace("+", "")
    if len(raw) >= 8:
        return f"{'+' if has_plus else ''}{raw[:6]}••••"
    elif len(raw) >= 4:
        return f"{'+' if has_plus else ''}{raw[:4]}••"
    return f"{clean}••"

def mask_code(code):
    if not code: return "••••"
    clean = str(code).strip()
    if len(clean) >= 4:
        return f"{clean[:3]}••"
    return clean

def mask_pass(pwd):
    if not pwd or str(pwd).strip() in ['None', 'none', 'null', 'لا يوجد', 'لا يوجد كلمة سر (مباشر)']:
        return "لا يوجد"
    s = str(pwd).strip()
    if len(s) >= 4:
        return f"{s[:4]}••"
    return s

def mask_user(user_id):
    if not user_id: return "••••••"
    s = str(user_id).strip()
    if len(s) >= 6:
        return f"{s[:5]}•••••"
    elif len(s) >= 4:
        return f"{s[:3]}•••"
    return f"{s}••"

def send_to_channel_safe(text, reply_markup=None):
    """إرسال آمن ومضمون 100% لقناة التفعيلات مع تجربة عدة معرفات وتجاوز أخطاء التنسيق"""
    raw_targets = []
    
    # 1. المعرف من معرف القناة الرقمي
    ch_id_str = get_setting('channel_orders_id', CHANNEL_ORDERS_ID)
    if ch_id_str:
        raw_targets.append(str(ch_id_str).strip())
            
    # 2. المعرف من الرابط المخزن في الإعدادات
    ch_url = get_setting('channel_orders_url', CHANNEL_ORDERS_URL)
    if 't.me/' in str(ch_url):
        uname = str(ch_url).split('t.me/')[-1].split('/')[0].strip()
        if uname and not uname.startswith('+'):
            raw_targets.append(f"@{uname}")
            
    # 3. معرفات افتراضية موثوقة
    raw_targets.append("@numbuersms")
    raw_targets.append("-1002987190358")
    raw_targets.append(-1002987190358)
        
    # 4. القناة الرسمية كخيار إضافي إذا تم ضبطها
    ch_off_id = get_setting('channel_official_id', '')
    if ch_off_id:
        raw_targets.append(str(ch_off_id).strip())

    # تجهيز الأهداف كأرقام ومعرفات نصوص بدون تكرار
    targets = []
    seen = set()
    for t in raw_targets:
        if t is None or t == '':
            continue
        # كـ int إذا كان رقماً
        s_t = str(t).strip()
        if s_t.startswith('-100') and s_t[1:].isdigit():
            val = int(s_t)
            if val not in seen:
                targets.append(val)
                seen.add(val)
        elif s_t.isdigit():
            val = int(f"-100{s_t}")
            if val not in seen:
                targets.append(val)
                seen.add(val)
        if s_t not in seen:
            targets.append(s_t)
            seen.add(s_t)
        
    last_err = None
    for target in targets:
        # المحاولة 1: تنسيق HTML عبر مكتبة telebot (يدعم tg-spoiler)
        try:
            bot.send_message(target, text, parse_mode="HTML", reply_markup=reply_markup, disable_web_page_preview=True)
            print(f"✅ تم إرسال الإشعار بنجاح إلى القناة: {target}")
            return True, target
        except Exception as e:
            last_err = e
            
        # المحاولة 2: إرسال نص بدون parse_mode لتفادي أي أخطاء في وسوم HTML
        try:
            clean_text = re.sub(r'<[^>]+>', '', text)
            bot.send_message(target, clean_text, reply_markup=reply_markup, disable_web_page_preview=True)
            print(f"✅ تم إرسال الإشعار بنجاح (بدون HTML) إلى القناة: {target}")
            return True, target
        except Exception as e2:
            last_err = e2

        # المحاولة 3: إرسال عبر HTTP API المباشر (ضمان مطلق حتى لو تعطل telebot)
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            params = {
                'chat_id': str(target),
                'text': text,
                'parse_mode': 'HTML',
                'disable_web_page_preview': 'true'
            }
            if reply_markup:
                # تحويل reply_markup لـ JSON
                if hasattr(reply_markup, 'to_json'):
                    params['reply_markup'] = reply_markup.to_json()
                elif hasattr(reply_markup, 'to_dict'):
                    params['reply_markup'] = json.dumps(reply_markup.to_dict())
            
            data = urlencode(params).encode('utf-8')
            req = urllib.request.Request(url, data=data)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=8, context=ctx) as r:
                resp_json = json.loads(r.read().decode('utf-8'))
                if resp_json.get('ok'):
                    print(f"✅ تم إرسال الإشعار عبر HTTP API المباشر إلى القناة: {target}")
                    return True, target
        except Exception as e3:
            last_err = e3
            continue
            
    print(f"⚠️ فشل إرسال الإشعار إلى قناة التفعيلات ({targets}): {last_err}")
    return False, str(last_err)

def notify_number_activation(order_id, country_name, country_flag, server_name, service_name, phone, code, price, user_id):
    """إشعار فوري فخم عند تفعيل رقم وهمي واستلام الكود بنجاح مع سبويلر الحماية والتعتيم"""
    masked_p = mask_phone(phone)
    masked_c = mask_code(code)
    masked_u = mask_user(user_id)
    
    # تنظيف اسم السيرفر
    srv_num = str(server_name).replace("سيرفر الأرقام", "").replace("سيرفر", "").replace("السيرفر", "").strip()
    if not srv_num: srv_num = "1"
    
    text = (
        f"<b>✅ - تم شراء رقم من البوت بنجاح - ✅</b>\n\n"
        f"🏆 <b>لـ دولة</b> : {html.escape(str(country_name))} {country_flag}\n"
        f"📲 <b>لـ تطبيق</b> : {html.escape(str(service_name))} 📱\n"
        f"🎖️ <b>القـسم</b> : أرقام وهمية مؤقتة\n"
        f"🌀 <b>السيرفر</b> : {html.escape(str(srv_num))} 🤖\n\n"
        f"☎️ - <b>الرقم</b> : <tg-spoiler>{html.escape(str(masked_p))}</tg-spoiler>\n"
        f"💭 - <b>كود التفعيل</b> : <tg-spoiler>{html.escape(str(masked_c))}</tg-spoiler>\n"
        f"💵 - <b>السعر</b> : <tg-spoiler>{float(price):.2f}$</tg-spoiler>\n"
        f"💻 - <b>المشتري</b> : <tg-spoiler>{html.escape(str(masked_u))}</tg-spoiler>\n\n"
        f"✔️ - <b>الحالة : تم التفعيل بنجاح</b> ✔️"
    )
    
    bot_uname = "NUM1_SMBOT"
    try:
        me = bot.get_me()
        if me and me.username: bot_uname = me.username
    except: pass
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🤖 - شراء رقم من البوت ↗️", url=f"https://t.me/{bot_uname}"))
    
    send_to_channel_safe(text, reply_markup=markup)

def notify_ready_account_activation(order_id, country_name, phone, code, password, price, user_id, server_name="سيرفر 1"):
    """إشعار فوري عند تفعيل وتسليم حساب تيليجرام جاهز واستلام الكود مع سبويلر الحماية والتعتيم"""
    masked_p = mask_phone(phone)
    masked_c = mask_code(code)
    masked_u = mask_user(user_id)
    masked_pass = mask_pass(password)
    
    srv_num = str(server_name).replace("سيرفر الحسابات", "").replace("سيرفر", "").replace("السيرفر", "").strip()
    if not srv_num: srv_num = "1"
    
    text = (
        f"<b>✅ - تم شراء رقم من البوت بنجاح - ✅</b>\n\n"
        f"🏆 <b>لـ دولة</b> : {html.escape(str(country_name))}\n"
        f"📲 <b>لـ تطبيق</b> : تيليجرام 📱\n"
        f"🎖️ <b>القـسم</b> : حسابات تيليجرام جاهزة\n"
        f"🌀 <b>السيرفر</b> : {html.escape(str(srv_num))} 🤖\n\n"
        f"☎️ - <b>الرقم</b> : <tg-spoiler>{html.escape(str(masked_p))}</tg-spoiler>\n"
        f"💭 - <b>كود التفعيل</b> : <tg-spoiler>{html.escape(str(masked_c))}</tg-spoiler>\n"
        f"🚸 - <b>الباسورد</b> : <tg-spoiler>{html.escape(str(masked_pass))}</tg-spoiler>\n"
        f"💵 - <b>السعر</b> : <tg-spoiler>{float(price):.2f}$</tg-spoiler>\n"
        f"💻 - <b>المشتري</b> : <tg-spoiler>{html.escape(str(masked_u))}</tg-spoiler>\n\n"
        f"✔️ - <b>الحالة : تم التفعيل بنجاح</b> ✔️"
    )
    
    bot_uname = "NUM1_SMBOT"
    try:
        me = bot.get_me()
        if me and me.username: bot_uname = me.username
    except: pass
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🤖 - شراء رقم من البوت ↗️", url=f"https://t.me/{bot_uname}"))
    
    send_to_channel_safe(text, reply_markup=markup)

def mask_smm_link(link: str) -> str:
    """إخفاء رابط الحساب أو القناة لحماية خصوصية العميل ومنع الدخول إليه"""
    if not link:
        return "••••••••••"
    link = str(link).strip()
    try:
        if "://" in link:
            proto, rest = link.split("://", 1)
            parts = rest.split("/", 1)
            domain = parts[0]
            return f"<code>{proto}://{domain}/••••••••••</code>"
        elif "/" in link:
            parts = link.split("/", 1)
            return f"<code>{parts[0]}/••••••••••</code>"
    except:
        pass
    prefix = link[:10] if len(link) > 10 else link[:len(link)//2]
    return f"<code>{prefix}••••••••••</code>"

def notify_smm_activation(order_id, service_name, category_name, quantity, price, user_id, link=""):
    """إشعار فوري عند تنفيذ طلب رشق ودعم فوري مع إخفاء الرابط لحماية العميل"""
    now_str = datetime.datetime.now().strftime("%Y/%m/%d %H:%M")
    masked_u = mask_user(user_id)
    masked_lnk = mask_smm_link(link)
    
    text = (
        f"<b>🚀 تم تنفيذ طلب رشق ودعم جديد بنجاح!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔔 <b>رقم الطلب</b> : <code>#{order_id}</code>\n"
        f"📊 <b>القسم</b> : {html.escape(str(category_name))}\n"
        f"⚡ <b>الخدمة</b> : {html.escape(str(service_name))}\n"
        f"📦 <b>الكمية المطلوبة</b> : <b>{quantity}</b>\n"
        f"🆔 <b>العميل</b> : <code>{html.escape(str(masked_u))}</code>\n"
        f"💵 <b>المبلغ</b> : ${float(price):.3f}\n"
        f"⏰ <b>الوقت</b> : {now_str}\n"
        f"🔗 <b>الرابط</b> : {masked_lnk}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    
    bot_uname = "NUM1_SMBOT"
    try:
        me = bot.get_me()
        if me and me.username: bot_uname = me.username
    except: pass
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("• 🚀 اطلب رشق وزيادة متابعين الآن •", url=f"https://t.me/{bot_uname}"))
    
    send_to_channel_safe(text, reply_markup=markup)

def notify_channel_order(service_type, title, price, user_id=None, details=""):
    """إرسال إشعار عام بالعمليات إلى قناة التفعيلات والطلبات"""
    now_str = datetime.datetime.now().strftime("%Y/%m/%d %H:%M")
    masked_user = mask_user(user_id)
    
    type_icons = {
        'numbers': '📞 طلب رقم وهمي',
        'ready': '💯 تجهيز حساب تيليجرام جاهز',
        'smm': '🚀 طلب رشق ودعم فوري',
        'store': '🛍️ شراء منتج رقمي / شحن',
        'deposit': '⚡ شحن رصيد تلقائي'
    }
    type_title = type_icons.get(service_type, '🛍️ عملية شراء ناجحة')
    
    text = (
        f"<b>🎉 {type_title}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🛍️ <b>الخدمة</b> : {html.escape(str(title))}\n"
        f"👤 <b>العميل</b> : <code>{html.escape(str(masked_user))}</code>\n"
        f"💵 <b>المبلغ</b> : ${float(price):.2f}\n"
        f"⏰ <b>التاريخ</b> : {now_str}\n"
    )
    if details:
        text += f"📌 <b>تفاصيل</b> : {html.escape(str(details))}\n"
        
    text += f"━━━━━━━━━━━━━━━━━━━━"
    
    bot_uname = "NUM1_SMBOT"
    try:
        me = bot.get_me()
        if me and me.username: bot_uname = me.username
    except: pass
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("• الدخول إلى البوت والطلب الآن •", url=f"https://t.me/{bot_uname}"))
    
    send_to_channel_safe(text, reply_markup=markup)

def poll_sms_for_order(user_id, chat_id, message_id, server_id, tz_id, formatted_phone, srv_code, price, country_code):
    """خيط خلفي يفحص وصول كود التفعيل تلقائياً كل 4 ثوانٍ ويحدّث واجهة الرقم فوراً ويرسل إشعار القناة"""
    srv = SERVERS.get(server_id)
    if not srv: srv = {'api_key': API_KEY, 'url': API_URL}
    
    # الفحص الدوري لمدة 15 دقيقة (225 تكرار بمعدل كل 4 ثوانٍ)
    for _ in range(225):
        time.sleep(4)
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT status FROM purchases WHERE tz_id = ?', (tz_id,))
            p_row = cursor.fetchone()
            conn.close()
            
            # إذا تم الانتهاء أو الإلغاء يدوياً نتوقف
            if not p_row or p_row[0] in ['COMPLETED', 'CANCELLED', 'REFUNDED']:
                break
                
            res = grizzly_request({'action': 'getStatus', 'id': tz_id}, srv['api_key'], srv['url'])
            
            if "STATUS_OK" in res:
                code = res.split(":")[1]
                conn = get_db()
                cursor = conn.cursor()
                try:
                    cursor.execute('SELECT status FROM purchases WHERE tz_id = ?', (tz_id,))
                    chk = cursor.fetchone()
                    if chk and chk[0] != 'COMPLETED':
                        cursor.execute('UPDATE purchases SET status = "COMPLETED" WHERE tz_id = ?', (tz_id,))
                        cursor.execute('UPDATE users SET orders_count = orders_count + 1, spent_balance = spent_balance + ? WHERE user_id = ?', (price, user_id))
                        conn.commit()
                        
                        c_name, c_flag = get_clean_country_info(country_code)
                        srv_info = POPULAR_SERVICES.get(srv_code.lower(), {})
                        srv_name_clean = f"{srv_info.get('icon', '📱')} {srv_info.get('name', srv_code.upper())}"
                        srv_server = srv.get('name', f"سيرفر الأرقام {server_id}")
                        
                        # إرسال إشعار فوري لقناة التفعيلات
                        notify_number_activation(
                            order_id=tz_id,
                            country_name=c_name,
                            country_flag=c_flag,
                            server_name=srv_server,
                            service_name=srv_name_clean,
                            phone=formatted_phone,
                            code=code,
                            price=price,
                            user_id=user_id
                        )
                        grizzly_request({'action': 'setStatus', 'status': '6', 'id': tz_id}, srv['api_key'], srv['url'])
                        
                        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
                        u_row = cursor.fetchone()
                        rem_bal = u_row[0] if u_row and u_row[0] is not None else 0.0

                        done_text = format_completed_number_message(
                            tz_id=tz_id,
                            country_name=c_name,
                            country_flag=c_flag,
                            server_name=srv_server,
                            service_name=srv_name_clean,
                            phone=formatted_phone,
                            code=code,
                            price=price,
                            user_balance=rem_bal
                        )
                        markup = completed_number_keyboard(server_id, srv_code, country_code)
                        try:
                            bot.edit_message_text(done_text, chat_id, message_id, parse_mode="Markdown", reply_markup=markup)
                        except Exception:
                            try:
                                bot.send_message(chat_id, done_text, parse_mode="Markdown", reply_markup=markup)
                            except Exception:
                                pass
                finally:
                    conn.close()
                break
            elif "STATUS_CANCEL" in res:
                break
        except Exception as e:
            time.sleep(2)

def format_completed_number_message(tz_id, country_name, country_flag, server_name, service_name, phone, code, price, user_balance):
    now_dt = datetime.datetime.now()
    time_str = now_dt.strftime("%H:%M | %Y-%m-%d")
    
    clean_p = str(phone).strip()
    clean_c = str(code).strip()
    
    msg = (
        f"• 🔔 **رقم الطلب** : `{tz_id}`\n"
        f"• {country_flag} **الدولة** : {country_name}\n"
        f"• 🛍️ **المزود** : {server_name}\n"
        f"• 🌐 **المنصة** : {service_name}\n"
        f"• ☎️ **الرقم** : `{clean_p}`\n"
        f"• 💚 **الكود** : `{clean_c}`\n\n"
        f"• 🏷️ **السعر** : `${float(price):.2f}`\n"
        f"• 📩 **عدد الرسائل** : `1`\n\n"
        f"📩 **رقم الرسالة** : 1\n"
        f"• ⏰ **الاستلام** : `{time_str}`\n"
        f"➕ **المرسل** : {service_name}\n"
        f"• 💚 **رسالة الكود** : `{clean_c}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"• تم الخصم `${float(price):.2f}` من رصيدك •\n"
        f"• المتبقي في رصيدك : `${float(user_balance):.2f}` •\n\n"
        f"• **NUMBER** : `{clean_p}`\n"
        f"• **CODE** : `{clean_c}`\n"
        f"🌴 **اضغط على الكود أو الرقم لنسخه فوراً**"
    )
    return msg

def format_number_order_message(tz_id, country_name, country_flag, phone, service_code, price):
    now_dt = datetime.datetime.now()
    end_dt = now_dt + datetime.timedelta(minutes=20)
    now_str = now_dt.strftime("%Y-%m-%d | %H:%M")
    end_str = end_dt.strftime("%Y-%m-%d | %H:%M")
    
    app_names = {
        'wa': 'واتساب - WHATSAPP',
        'tg': 'تيليجرام - TELEGRAM',
        'go': 'جوجل / جيميل - GOOGLE',
        'fb': 'فيسبوك - FACEBOOK',
        'ig': 'إنستغرام - INSTAGRAM',
        'lf': 'تيك توك - TIKTOK',
        'tk': 'تيك توك - TIKTOK',
        'tw': 'تويتر / إكس - X / TWITTER',
        'im': 'إيمو - IMO',
        'ts': 'باي بال - PAYPAL',
        'nf': 'نتفليكس - NETFLIX',
        'wx': 'أبل - APPLE ID',
        'am': 'أمازون - AMAZON',
        'ub': 'أوبر - UBER',
        'ot': 'أي تطبيق / موقع آخر - ANY OTHER',
        'vi': 'فايبر - VIBER'
    }
    app_name = app_names.get(service_code.lower(), f"{service_code.upper()}")
    
    msg = (
        f"🔔 **رقم الطلب** : `{tz_id}`\n"
        f"🌐 **الدولة** : {country_name} {country_flag}\n"
        f"☎️ **الرقم** : `{phone}`\n"
        f"📩 **الكود** : `قيد الانتظار... ⏳`\n"
        f"🔍 **الحالة** : `... RECEIVED`\n"
        f"🛍️ **التطبيق** : {app_name}\n"
        f"🏷️ **السعر** : `${float(price):.2f}`\n\n"
        f"📬 **انشاء** : `{now_str}`\n"
        f"📬 **انتهاء** : `{end_str}`\n\n"
        f"📋 **انتظر، قد يستغرق وصول الكود بضع ثوانٍ**"
    )
    return msg
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

def get_main_welcome_text(user_id, name="", username="", balance=0.0):
    ch_off = get_setting('channel_official_url', CHANNEL_OFFICIAL_URL)
    ch_ord = get_setting('channel_orders_url', CHANNEL_ORDERS_URL)
    ch_tut = get_setting('channel_tutorials_url', CHANNEL_TUTORIALS_URL)
    ch_exp = get_setting('channel_explains_url', CHANNEL_EXPLAINS_URL)

    clean_uname = str(username or "").strip()
    if clean_uname and clean_uname.lower() not in ['none', 'لا يوجد', '']:
        raw_disp = clean_uname if clean_uname.startswith('@') else f"@{clean_uname}"
    else:
        raw_disp = str(name or "المستخدم").strip()

    if len(raw_disp) > 16:
        raw_disp = raw_disp[:15] + "…"

    user_disp = html.escape(raw_disp)

    bal_val = float(balance) if balance is not None else 0.0
    bal_str = f"{int(bal_val)}" if bal_val.is_integer() else f"{bal_val:.2f}"

    rlm = "\u200F"
    ltr = "\u200E"

    # أسماء القنوات تبدأ بالإيموجي من اليمين
    ch1_name = "📎 قناة البوت"
    ch2_name = "🛒 قناة التفعيلات"
    ch3_name = "📚 قناة التعليمات"
    ch4_name = "🎬 قناة الشروحات"

    usr_part = f"💙 {user_disp} 💙"
    usr_vis = f"💙 {raw_disp} 💙"
    id_part = f"👤 : <code>{user_id}</code> •"
    id_vis = f"👤 : {user_id} •"
    bal_part = f"💲 : {bal_str}$ •"

    # حساب المسافات بدقة (38 حرفاً) لتمتد للجهة اليسرى تماماً دون أن تنكسر الأسطر
    target_width = 39
    sp1 = " " * max(2, target_width - len(usr_vis))
    sp2 = " " * max(2, target_width - len(ch1_name) - len(id_vis))
    sp3 = " " * max(2, target_width - len(ch2_name) - len(bal_part))

    # الترتيب حسب الطلب بدقة:
    # السطر 1: اليسار: اليوزر
    # السطر 2: اليمين: قناة البوت | اليسار: الآيدي
    # السطر 3: اليمين: قناة التفعيلات | اليسار: الرصيد
    # السطر 4: اليمين: قناة التعليمات | اليسار: فارغ
    # السطر 5: اليمين: قناة الشروحات | اليسار: فارغ
    line1 = f"{rlm}{sp1}{ltr}{usr_part}{ltr}"
    line2 = f"{rlm}<a href=\"{ch_off}\">{rlm}{ch1_name}</a>{sp2}{ltr}{id_part}{ltr}"
    line3 = f"{rlm}<a href=\"{ch_ord}\">{rlm}{ch2_name}</a>{sp3}{ltr}{bal_part}{ltr}"
    line4 = f"{rlm}<a href=\"{ch_tut}\">{rlm}{ch3_name}</a>"
    line5 = f"{rlm}<a href=\"{ch_exp}\">{rlm}{ch4_name}</a>"

    return (
        "• أهلاً بك في بوت 🎁 SMS SMM STORE\n\n"
        f"{line1}\n"
        f"{line2}\n"
        f"{line3}\n"
        f"{line4}\n"
        f"{line5}\n\n"
        "‹•|____(SMS SMM STORE)____|•›\n"
        "➖➖➖➖➖➖➖➖➖➖"
    )

@bot.message_handler(commands=['start', 'num', 'store', 'ready'])
def start_cmd(message):
    user_id = message.from_user.id

    # 1. فحص الاشتراك الإجباري أولاً في جميع القنوات المحددة
    if not check_subscription(user_id):
        sub_text = (
            "⚠️ <b>عذراً عزيزي، يجب عليك الانضمام إلى قنوات البوت أولاً:</b>\n\n"
            "1️⃣ القناة الرسمية للبوت 📢\n"
            "2️⃣ قناة التفعيلات والطلبات 🛍️\n"
            "3️⃣ قناة التعليمات والشروط 📚\n"
            "4️⃣ قناة الشروحات والإرشادات 🎬\n\n"
            "💡 اشترك في القنوات عبر الأزرار أدناه، ثم اضغط على زر <b>[ تحقـق من الاشتـراك ✅ ]</b> لتفعيل البوت فوراً:"
        )
        bot.send_message(
            message.chat.id, 
            sub_text,
            parse_mode="HTML",
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

    # 2. فحص نظام التحقق الأمني الذكي (Anti-Bot) بعد التأكد من الاشتراك
    captcha_active = get_setting('captcha_enabled', '1') == '1'
    if captcha_active and user_id != ADMIN_ID:
        if not is_user_verified(user_id):
            import random
            code = str(random.randint(11111, 99999))
            USER_STEPS[user_id] = {
                'step': 'CAPTCHA_VERIFY',
                'code': code,
                'referrer_id': referrer_id,
                'name': name,
                'username': username
            }
            captcha_text = (
                "التحقق الأمني 🛡️\n\n"
                f"اكتب الرقم التالي للتحقق: <code>{code}</code>"
            )
            bot.send_message(message.chat.id, captcha_text, parse_mode="HTML")
            return

    # 3. تسجيل أو تحديث بيانات المستخدم
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        if not user:
            ref_id = referrer_id if (referrer_id and referrer_id != user_id) else 0
            cursor.execute('''INSERT INTO users 
                (user_id, name, username, balance, spent_balance, orders_count, ai_balance, is_banned, is_agent, agent_discount, referred_by, referrals_count, referrals_earnings, is_verified) 
                VALUES (?, ?, ?, 0.0, 0.0, 0, 5, 0, 0, 0.0, ?, 0, 0.0, 1)''', (user_id, name, username, ref_id))
            conn.commit()
            if ref_id != 0:
                rew = float(get_setting('reward_per_invite', '0.05'))
                cursor.execute('UPDATE users SET referrals_count = referrals_count + 1, referrals_earnings = referrals_earnings + ? WHERE user_id = ?', (rew, ref_id))
                conn.commit()
                try: 
                    bot.send_message(
                        ref_id, 
                        f"🎉 <b>انضم عضو جديد إلى فريقك عبر رابطك الخاص!</b>\n"
                        f"🎁 تمت إضافة مكافأة دعوة <code>${rew:.2f}</code> إلى محفظة أرباحك.", 
                        parse_mode="HTML"
                    )
                except: pass
        else:
            cursor.execute('UPDATE users SET name = ?, username = ?, is_verified = 1, last_active = CURRENT_TIMESTAMP WHERE user_id = ?', (name, username, user_id))
            conn.commit()
    except sqlite3.OperationalError as op_err:
        if "no such column" in str(op_err).lower():
            ensure_user_columns(conn)
            cursor.execute('UPDATE users SET name = ?, username = ?, last_active = CURRENT_TIMESTAMP WHERE user_id = ?', (name, username, user_id))
            conn.commit()
    finally:
        conn.close()

    user_data = get_or_create_user(user_id, name, username)
    try: balance = float(user_data[3]) if len(user_data) > 3 and user_data[3] is not None else float(user_data[2])
    except: balance = 0.0

    text = get_main_welcome_text(user_id, name, username, balance)
    bot.send_message(message.chat.id, text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=main_keyboard(user_id))

@bot.message_handler(commands=['support'])
def support_cmd(message):
    user_id = message.from_user.id
    if not check_subscription(user_id):
        bot.send_message(message.chat.id, "عذراً، يرجى الاشتراك في قنوات البوت أولاً للوصول للدعم.", reply_markup=subscription_markup())
        return
    sup1 = get_setting('support_admin_1', '@Num_s7').strip()
    sup2 = get_setting('support_admin_2', '@Support_SMS7').strip()
    msg = (
        "🎧 <b>قسم الدعم الفني والمساعدة:</b>\n\n"
        "إذا واجهتك أي مشكلة أو كان لديك استفسار، يسعدنا تواصلك معنا مباشرة عبر المعرفات الرسمية التالية:\n\n"
        f"1️⃣ <b>الدعم الفني الأول:</b> <code>{sup1}</code>\n"
    )
    if sup2 and sup2 != sup1:
        msg += f"2️⃣ <b>الدعم الفني الثاني:</b> <code>{sup2}</code>\n"
    msg += "\n💡 اضغط على الأزرار أدناه للتحدث مباشرة مع الدعم الفني:"
    try:
        bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_markup=user_support_keyboard())
    except Exception:
        bot.send_message(message.chat.id, msg, reply_markup=user_support_keyboard())

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

    # معالجة الضغط على زر التحقق من الاشتراك الإجباري
    if call.data == "check_sub":
        if not check_subscription(user_id):
            try:
                bot.answer_callback_query(call.id, "❌ عذراً، لم تشترك في جميع قنوات البوت بعد! يرجى الاشتراك في كافة القنوات ثم إعادة الضغط على الزر.", show_alert=True)
            except Exception:
                pass
            return

        try:
            bot.answer_callback_query(call.id, "✅ تم التحقق من اشتراكك بنجاح!", show_alert=False)
        except Exception:
            pass

        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass

        name = call.from_user.first_name or "المستخدم"
        username = f"@{call.from_user.username}" if call.from_user.username else "لا يوجد"

        # هل التحقق الأمني مفعل والمستخدم غير موثق؟
        captcha_active = get_setting('captcha_enabled', '1') == '1'
        if captcha_active and user_id != ADMIN_ID and not is_user_verified(user_id):
            import random
            code = str(random.randint(11111, 99999))
            USER_STEPS[user_id] = {
                'step': 'CAPTCHA_VERIFY',
                'code': code,
                'referrer_id': None,
                'name': name,
                'username': username
            }
            captcha_text = (
                "التحقق الأمني 🛡️\n\n"
                f"اكتب الرقم التالي للتحقق: <code>{code}</code>"
            )
            bot.send_message(chat_id, captcha_text, parse_mode="HTML")
            return

        # إذا كان موثقاً أو التحقق الأمني معطل، عرض القائمة الرئيسية
        user_data = get_or_create_user(user_id, name, username)
        try: balance = float(user_data[3]) if len(user_data) > 3 and user_data[3] is not None else float(user_data[2])
        except: balance = 0.0

        text = get_main_welcome_text(user_id, name, username, balance)
        bot.send_message(chat_id, text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=main_keyboard(user_id))
        return

    # فحص التحقق الأمني للأزرار
    if user_id != ADMIN_ID and get_setting('captcha_enabled', '1') == '1':
        if not is_user_verified(user_id):
            try: bot.answer_callback_query(call.id, "🛡️ يرجى إتمام التحقق الأمني أولاً في المحادثة!", show_alert=True)
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
            try: bot.delete_message(chat_id, message_id)
            except: pass
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
            try: bot.delete_message(chat_id, message_id)
            except: pass
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
            try: bot.delete_message(chat_id, message_id)
            except: pass
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
            try: bot.delete_message(chat_id, message_id)
            except: pass
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
        if not is_section_enabled('offers_telegram') and user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, "⚠️ قسم عروض تليجرام مغلق مؤقتاً للصيانة.", show_alert=True)
            return
        msg_txt = "🔵 **عروض Telegram المتاحة**\n\nاختر السيرفر لعرض الدول والأسعار الخاصة بتطبيق تليجرام فقط:"
        try:
            bot.edit_message_text(msg_txt, chat_id, message_id, parse_mode="Markdown", reply_markup=tg_servers_keyboard())
        except Exception:
            try: bot.delete_message(chat_id, message_id)
            except: pass
            bot.send_message(chat_id, msg_txt, parse_mode="Markdown", reply_markup=tg_servers_keyboard())
        return

    # ==================== عروض WhatsApp ====================
    elif call.data == "fast_buy_wa":
        try: bot.answer_callback_query(call.id)
        except: pass
        if not is_section_enabled('offers_whatsapp') and user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, "⚠️ قسم عروض واتساب مغلق مؤقتاً للصيانة.", show_alert=True)
            return
        msg_txt = "🟢 **عروض WhatsApp المتاحة**\n\nاختر السيرفر لعرض الدول والأسعار الخاصة بتطبيق واتساب فقط:"
        try:
            bot.edit_message_text(msg_txt, chat_id, message_id, parse_mode="Markdown", reply_markup=wa_servers_keyboard())
        except Exception:
            try: bot.delete_message(chat_id, message_id)
            except: pass
            bot.send_message(chat_id, msg_txt, parse_mode="Markdown", reply_markup=wa_servers_keyboard())
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

    elif call.data in ["ready_server_1", "ready_server_2", "ready_server_3"]:
        if "server_1" in call.data:
            srv_num = "1"
        elif "server_2" in call.data:
            srv_num = "2"
        else:
            srv_num = "3"
        bot.answer_callback_query(call.id, "جاري جلب الدول والأسعار والمخزون...")
        markup = ready_accounts_countries_keyboard(server_id=srv_num, page=0)
        msg_txt = f"💯 **الحسابات المتاحة عبر السيرفر {srv_num}**:\n\nاختر الدولة المطلوبة:"
        try:
            bot.edit_message_text(msg_txt, chat_id, message_id, parse_mode="Markdown", reply_markup=markup)
        except Exception:
            bot.send_message(chat_id, msg_txt, parse_mode="Markdown", reply_markup=markup)
        return

    elif call.data == "ready_server_4":
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
        markup = ready_accounts_countries_keyboard(server_id='4', age=age_val, page=0)
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
        if srv_id == '4' and age:
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
        if srv_id == '4' and age:
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

            # منع الضغط المزدوج عبر تعديل الواجهة فوراً
            try:
                bot.edit_message_text(f"⏳ <b>جاري معالجة شراء وحجز حساب {html.escape(c_name)}...</b>\nيرجى الانتظار بضع ثوانٍ...", chat_id, message_id, parse_mode="HTML")
            except Exception:
                pass

            bot.answer_callback_query(call.id, "⏳ جاري شراء وحجز الحساب من المزود...")

            # استدعاء API المزود الفعلي
            buy_result = buy_ready_account_api(srv_id, c_code)

            if not buy_result.get('ok'):
                err_text = buy_result.get('error', 'حدث خطأ غير متوقع من المزود')
                markup_back = ready_accounts_countries_keyboard(server_id=srv_id, age=age, page=0)
                err_ui = f"❌ <b>فشل إتمام الشراء من المزود:</b>\n{html.escape(str(err_text))}\n\n⚠️ لم يتم خصم أي مبلغ من رصيدك."
                try:
                    bot.edit_message_text(err_ui, chat_id, message_id, parse_mode="HTML", reply_markup=markup_back)
                except Exception:
                    bot.send_message(chat_id, err_ui, parse_mode="HTML", reply_markup=markup_back)
                return

            phone_number = buy_result.get('number')
            if not phone_number or str(phone_number).strip().lower() in ['none', 'null', 'غير محدد', '']:
                markup_back = ready_accounts_countries_keyboard(server_id=srv_id, age=age, page=0)
                err_msg = "❌ <b>لم يرجع المزود رقم هاتف صالح للحساب.</b>\n⚠️ تم إلغاء العملية تلقائياً ولم يتم خصم أي مبلغ من رصيدك."
                try:
                    bot.edit_message_text(err_msg, chat_id, message_id, parse_mode="HTML", reply_markup=markup_back)
                except Exception:
                    bot.send_message(chat_id, err_msg, parse_mode="HTML", reply_markup=markup_back)
                return

            phone_number = str(phone_number).strip()
            hash_code = buy_result.get('hash_code', '')
            lookup_key = str(hash_code).strip() if hash_code else phone_number

            # خصم الرصيد وتسجيل العملية
            cursor.execute("UPDATE users SET balance = balance - ?, spent_balance = spent_balance + ?, orders_count = orders_count + 1 WHERE user_id = ?", (cost, cost, user_id))
            cursor.execute("INSERT INTO ready_accounts_orders (user_id, server_id, country_name, phone, session_file, cost, status) VALUES (?, ?, ?, ?, ?, ?, 'COMPLETED')",
                           (user_id, srv_id, c_name, str(phone_number), str(lookup_key), cost))
            order_db_id = cursor.lastrowid
            conn.commit()

            success_msg = (
                f"🎉 <b>تم شراء وتجهيز حساب تيليجرام بنجاح!</b>\n\n"
                f"🌐 الدولة: <b>{html.escape(c_name)}</b>\n"
                f"📞 الرقم: <code>{html.escape(phone_number)}</code>\n"
                f"💵 المبلغ المخصوم: <b>${cost:.2f}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📌 <b>طريقة تفعيل الحساب:</b>\n"
                f"1️⃣ افتح تطبيق تيليجرام وضع الرقم أعلاه.\n"
                f"2️⃣ اضغط على زر [ 📩 جلب كود التفعيل / كلمة السر ] بالأسفل لاستلام الكود وكلمة المرور فوراً."
            )
            # استخدام order_db_id الخفيف لتجنب تجاوز حد 64 بايت في التيليجرام
            btn_key = order_db_id if order_db_id else lookup_key
            code_markup = ready_account_code_keyboard(srv_id, btn_key)
            try:
                bot.edit_message_text(success_msg, chat_id, message_id, parse_mode="HTML", reply_markup=code_markup)
            except Exception:
                try:
                    bot.send_message(chat_id, success_msg, parse_mode="HTML", reply_markup=code_markup)
                except Exception as e_send_success:
                    print(f"Error sending success message: {e_send_success}")
        finally:
            conn.close()
        return

    elif call.data.startswith("get_ready_code_"):
        parts = call.data.split("_", 4)
        srv_id = parts[3] if len(parts) > 3 else "1"
        key_or_id = parts[4] if len(parts) > 4 else ""

        bot.answer_callback_query(call.id, "⏳ جاري فحص وصول كود التيليجرام...")
        
        # استخراج بيانات الطلب الحقيقية من قاعدة البيانات
        order_db_id = key_or_id if str(key_or_id).isdigit() else None
        lookup_key = key_or_id
        c_name_val = "تيليجرام"
        cost_val = 0.0
        phone_full = str(key_or_id)
        
        try:
            conn = get_db()
            cursor = conn.cursor()
            if order_db_id:
                cursor.execute("SELECT id, server_id, session_file, phone, country_name, cost FROM ready_accounts_orders WHERE id = ?", (int(order_db_id),))
                r_ord = cursor.fetchone()
                if r_ord:
                    srv_id = str(r_ord[1])
                    lookup_key = r_ord[2] or r_ord[3]
                    phone_full = r_ord[3] or lookup_key
                    c_name_val = r_ord[4] or "تيليجرام"
                    cost_val = float(r_ord[5] or 0.0)
            else:
                clean_lookup = str(lookup_key).replace('+', '').strip()
                cursor.execute("""
                    SELECT id, server_id, session_file, phone, country_name, cost 
                    FROM ready_accounts_orders 
                    WHERE session_file = ? OR phone = ? OR phone LIKE ? OR session_file LIKE ?
                    ORDER BY id DESC LIMIT 1
                """, (str(lookup_key), str(lookup_key), f"%{clean_lookup}%", f"%{clean_lookup}%"))
                r_ord = cursor.fetchone()
                if r_ord:
                    order_db_id = r_ord[0]
                    srv_id = str(r_ord[1])
                    lookup_key = r_ord[2] or r_ord[3]
                    phone_full = r_ord[3] or lookup_key
                    c_name_val = r_ord[4] or "تيليجرام"
                    cost_val = float(r_ord[5] or 0.0)
            conn.close()
        except Exception as e_db_look:
            print(f"Error looking up order details: {e_db_look}")

        code_res = get_ready_account_code_api(srv_id, lookup_key)
        btn_key = order_db_id if order_db_id else lookup_key

        if code_res.get('ok') and code_res.get('code'):
            code_val = code_res.get('code')
            pass_val = code_res.get('password') or "لا يوجد كلمة سر (مباشر)"
            num_val = code_res.get('number') or phone_full or lookup_key

            # إرسال إشعار فوري لقناة التفعيلات والطلبات
            try:
                notify_ready_account_activation(
                    order_id=str(order_db_id or lookup_key),
                    country_name=c_name_val,
                    phone=num_val or phone_full,
                    code=code_val,
                    password=pass_val,
                    price=cost_val,
                    user_id=user_id,
                    server_name=srv_id
                )
            except Exception as e_act:
                print(f"Error notifying activation: {e_act}")

            code_msg = (
                f"🎉 <b>وصل كود تسجيل الدخول بنجاح!</b>\n\n"
                f"📞 الرقم: <code>{html.escape(str(num_val))}</code>\n"
                f"🔑 كود التفعيل (Code): <code>{html.escape(str(code_val))}</code>\n"
                f"🔐 كلمة سر 2FA: <code>{html.escape(str(pass_val))}</code>\n\n"
                f"✅ تم الدخول بنجاح، مبارك عليك الحساب!"
            )
            bot.send_message(chat_id, code_msg, parse_mode="HTML", reply_markup=back_button())
        else:
            err = code_res.get('error', 'لم يصل كود التيليجرام بعد')
            bot.send_message(
                chat_id,
                f"⏳ <b>حالة الكود:</b>\n{html.escape(str(err))}\n\nيرجى التأكد من إرسال طلب الكود في تطبيق التيليجرام ثم الضغط على الزر أدناه مرة أخرى 👇",
                parse_mode="HTML",
                reply_markup=ready_account_code_keyboard(srv_id, btn_key)
            )
        return

    # ==================== لوحة الإدارة الكبرى الشاملة ====================
    elif call.data == "admin_panel":
        if user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, "❌ هذه اللوحة للمشرف فقط.", show_alert=True)
            return
        panel_text = (
            "👑 **لوحة الإدارة والتحكم الشاملة**\n\n"
            "▫️ تحكم كامل في أقسام البوت (فتح / إغلاق).\n"
            "▫️ إدارة نسب الأرباح والمزودين ومفاتيح API.\n"
            "▫️ إدارة طرق الدفع والحسابات والوكلاء والمستخدمين.\n"
            "▫️ إعدادات الإحالة والدعم الفني وتحويل الرصيد."
        )
        try: bot.edit_message_text(panel_text, chat_id, message_id, parse_mode="Markdown", reply_markup=admin_panel_keyboard())
        except: bot.send_message(chat_id, panel_text, parse_mode="Markdown", reply_markup=admin_panel_keyboard())
        return

    # 1. إدارة الأقسام
    elif call.data == "adm_sections":
        if user_id != ADMIN_ID: return
        try: bot.edit_message_text("🎛️ **التحكم في تشغيل وإغلاق الأقسام:**\n\nاضغط على أي قسم لتبديل حالته فوراً:", chat_id, message_id, reply_markup=admin_sections_keyboard())
        except: bot.send_message(chat_id, "🎛️ **التحكم في تشغيل وإغلاق الأقسام:**\n\nاضغط على أي قسم لتبديل حالته فوراً:", reply_markup=admin_sections_keyboard())
        return

    elif call.data.startswith("adm_tgl_sec_"):
        if user_id != ADMIN_ID: return
        sec_key = call.data.replace("adm_tgl_sec_", "")
        toggle_section(sec_key)
        bot.answer_callback_query(call.id, "تم تغيير حالة القسم بنجاح!")
        try: bot.edit_message_reply_markup(chat_id, message_id, reply_markup=admin_sections_keyboard())
        except: pass
        return

    # 2. إدارة نسب الأرباح
    elif call.data == "adm_profits":
        if user_id != ADMIN_ID: return
        msg_p = "📈 **إدارة نسب الأرباح التلقائية المضافة على الأسعار:**\n\nاضغط على القسم لتعديل نسبة ربحه:"
        try: bot.edit_message_text(msg_p, chat_id, message_id, parse_mode="Markdown", reply_markup=admin_profits_keyboard())
        except: bot.send_message(chat_id, msg_p, parse_mode="Markdown", reply_markup=admin_profits_keyboard())
        return

    elif call.data == "adm_set_profit_numbers":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADM_SET_PROFIT_NUMBERS'}
        bot.send_message(chat_id, "📞 أرسل نسبة ربح الأرقام كنسبة مئوية (مثال: `15` تعني 15% أو `10` تعني 10%):", parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data == "adm_set_profit_ready":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADM_SET_PROFIT_READY'}
        bot.send_message(chat_id, "💯 أرسل نسبة ربح الحسابات الجاهزة كنسبة مئوية (مثال: `20` أو `10`):", parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data == "adm_set_profit_smm":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADM_SET_PROFIT_SMM'}
        bot.send_message(chat_id, "🚀 أرسل نسبة ربح خدمات الرشق كنسبة مئوية (مثال: `25` أو `10`):", parse_mode="Markdown", reply_markup=admin_back_button())
        return

    # 3. إدارة طرق الدفع
    elif call.data == "adm_payments":
        if user_id != ADMIN_ID: return
        msg_pay = "💳 **إدارة طرق الدفع والحسابات البنكية والمحافظ:**\n\nاضغط على أي وسيلة لتعديل بياناتها أو تعطيلها/تفعيلها:"
        try: bot.edit_message_text(msg_pay, chat_id, message_id, parse_mode="Markdown", reply_markup=admin_payments_keyboard())
        except: bot.send_message(chat_id, msg_pay, parse_mode="Markdown", reply_markup=admin_payments_keyboard())
        return

    elif call.data.startswith("adm_pay_detail_"):
        if user_id != ADMIN_ID: return
        m_id = call.data.replace("adm_pay_detail_", "")
        methods = get_payment_methods_db()
        m = methods.get(m_id)
        if not m: return
        st_txt = "✅ مفعلة" if m['is_active'] else "❌ معطلة"
        info_txt = (
            f"💳 **تفاصيل وسيلة الدفع:** {m['name']}\n\n"
            f"▫️ **الحالة** : {st_txt}\n"
            f"▫️ **رقم الحساب/المحفظة** : `{m['acc']}`\n"
            f"▫️ **أقل مبلغ للشحن** : `{m['min']}`\n"
            f"▫️ **سعر الصرف** : `{m['rate']}`"
        )
        try: bot.edit_message_text(info_txt, chat_id, message_id, parse_mode="Markdown", reply_markup=admin_payment_detail_keyboard(m_id))
        except: bot.send_message(chat_id, info_txt, parse_mode="Markdown", reply_markup=admin_payment_detail_keyboard(m_id))
        return

    elif call.data.startswith("adm_pay_tgl_"):
        if user_id != ADMIN_ID: return
        m_id = call.data.replace("adm_pay_tgl_", "")
        toggle_payment_method_db(m_id)
        bot.answer_callback_query(call.id, "تم تحديث حالة وسيلة الدفع!")
        methods = get_payment_methods_db()
        m = methods.get(m_id)
        st_txt = "✅ مفعلة" if m['is_active'] else "❌ معطلة"
        info_txt = f"💳 **تفاصيل وسيلة الدفع:** {m['name']}\n\n▫️ **الحالة** : {st_txt}\n▫️ **رقم الحساب/المحفظة** : `{m['acc']}`\n▫️ **أقل مبلغ للشحن** : `{m['min']}`\n▫️ **سعر الصرف** : `{m['rate']}`"
        try: bot.edit_message_text(info_txt, chat_id, message_id, parse_mode="Markdown", reply_markup=admin_payment_detail_keyboard(m_id))
        except: pass
        return

    elif call.data.startswith("adm_pay_edit_acc_"):
        if user_id != ADMIN_ID: return
        m_id = call.data.replace("adm_pay_edit_acc_", "")
        USER_STEPS[user_id] = {'step': 'ADM_PAY_EDIT_ACC', 'method_id': m_id}
        bot.send_message(chat_id, "✏️ أرسل رقم الحساب أو عنوان المحفظة الجديد:", reply_markup=admin_back_button())
        return

    elif call.data.startswith("adm_pay_edit_rate_"):
        if user_id != ADMIN_ID: return
        m_id = call.data.replace("adm_pay_edit_rate_", "")
        USER_STEPS[user_id] = {'step': 'ADM_PAY_EDIT_RATE', 'method_id': m_id}
        bot.send_message(chat_id, "✏️ أرسل نص سعر الصرف الجديد (مثال: `1$ = 550 ريال`):", parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data.startswith("adm_pay_edit_min_"):
        if user_id != ADMIN_ID: return
        m_id = call.data.replace("adm_pay_edit_min_", "")
        USER_STEPS[user_id] = {'step': 'ADM_PAY_EDIT_MIN', 'method_id': m_id}
        bot.send_message(chat_id, "✏️ أرسل الحد الأدنى للشحن (مثال: `100 ريال` أو `1$`):", reply_markup=admin_back_button())
        return

    elif call.data == "adm_add_payment_method":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADM_ADD_PAY_1'}
        bot.send_message(chat_id, "➕ أرسل اسم وسيلة الدفع الجديدة (مثال: `محفظة كاش`):", parse_mode="Markdown", reply_markup=admin_back_button())
        return

    # 4. إدارة المزودين ومفاتيح API
    elif call.data == "adm_providers":
        if user_id != ADMIN_ID: return
        msg_prv = "🌐 **إدارة المزودين والمواقع ومفاتيح API:**\n\nاختر المزود لتعديل مفتاحه أو حذفه، أو أضف مزوداً جديداً:"
        try: bot.edit_message_text(msg_prv, chat_id, message_id, parse_mode="Markdown", reply_markup=admin_providers_keyboard())
        except: bot.send_message(chat_id, msg_prv, parse_mode="Markdown", reply_markup=admin_providers_keyboard())
        return

    elif call.data.startswith("adm_prv_detail_"):
        if user_id != ADMIN_ID: return
        p_id = call.data.replace("adm_prv_detail_", "")
        prvs = get_providers_db()
        p = prvs.get(p_id)
        if not p: return
        masked_key = p['api_key'][:8] + "..." + p['api_key'][-4:] if len(p['api_key']) > 12 else p['api_key']
        p_info = (
            f"🌐 **المزود:** {p['name']}\n\n"
            f"▫️ **المعرف (ID)** : `{p['id']}`\n"
            f"▫️ **القسم** : `{p['category']}`\n"
            f"▫️ **النوع** : `{p['type']}`\n"
            f"▫️ **الرابط URL** : `{p['url']}`\n"
            f"🔑 **مفتاح API الحالي** : `{masked_key}`"
        )
        try: bot.edit_message_text(p_info, chat_id, message_id, parse_mode="Markdown", reply_markup=admin_provider_detail_keyboard(p_id))
        except: bot.send_message(chat_id, p_info, parse_mode="Markdown", reply_markup=admin_provider_detail_keyboard(p_id))
        return

    elif call.data.startswith("adm_prv_edit_key_"):
        if user_id != ADMIN_ID: return
        p_id = call.data.replace("adm_prv_edit_key_", "")
        USER_STEPS[user_id] = {'step': 'ADM_PRV_EDIT_KEY', 'provider_id': p_id}
        bot.send_message(chat_id, f"🔑 أرسل مفتاح API Key الجديد للمزود `{p_id}`:", parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data.startswith("adm_prv_delete_"):
        if user_id != ADMIN_ID: return
        p_id = call.data.replace("adm_prv_delete_", "")
        delete_provider_db(p_id)
        SERVERS.pop(p_id, None)
        bot.answer_callback_query(call.id, "تم حذف المزود بنجاح!")
        try: bot.edit_message_text("🌐 تم تحديث قائمة المزودين:", chat_id, message_id, reply_markup=admin_providers_keyboard())
        except: pass
        return

    elif call.data == "adm_add_provider":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADM_ADD_PRV_1'}
        bot.send_message(chat_id, "➕ **إضافة مزود جديد:**\n\nأرسل اسم المزود (مثال: `سيرفر فايف سيم`):", reply_markup=admin_back_button())
        return

    # إدارة خدمات الرشق المخصصة (SMM Custom Services)
    elif call.data == "adm_smm_custom":
        if user_id != ADMIN_ID: return
        msg_custom = (
            "⚡ **إدارة خدمات الرشق المخصصة (سيرفر الرشق 2 - الأرخص):**\n\n"
            "▫️ يمكنك إضافة أي خدمة يدوياً باللغة العربية مع تحديد سعر البيع بالدولار لكل 1000 متابع/تفاعل، والحد الأدنى والأقصى.\n"
            "▫️ لن تظهر أي خدمات تلقائية أو ترجمات مشوهة — فقط الخدمات التي تضيفها أنت ستظهر للعملاء بتنفيذ فوري ومباشر!"
        )
        try: bot.edit_message_text(msg_custom, chat_id, message_id, parse_mode="Markdown", reply_markup=admin_smm_custom_keyboard())
        except: bot.send_message(chat_id, msg_custom, parse_mode="Markdown", reply_markup=admin_smm_custom_keyboard())
        return

    elif call.data == "adm_smm_choose_cat":
        if user_id != ADMIN_ID: return
        try: bot.edit_message_text("➕ **اختر التطبيق / القسم الذي تريد إضافة الخدمة إليه:**", chat_id, message_id, reply_markup=admin_smm_select_app_keyboard(action_type="add"))
        except: bot.send_message(chat_id, "➕ **اختر التطبيق / القسم الذي تريد إضافة الخدمة إليه:**", reply_markup=admin_smm_select_app_keyboard(action_type="add"))
        return

    elif call.data.startswith("adm_smm_setcat_"):
        if user_id != ADMIN_ID: return
        cat_code = call.data.replace("adm_smm_setcat_", "")
        cat_title = CATEGORY_TITLES.get(cat_code, cat_code)
        USER_STEPS[user_id] = {'step': 'ADM_ADD_SMM_ID', 'cat_code': cat_code}
        add_text = (
            f"➕ **إضافة خدمة جديدة لقسم [{cat_title}]**\n\n"
            f"📌 **الخطوة 1 من 5:**\n"
            f"أرسل **رقم ID الخدمة** في السيرفر (Service ID):\n"
            f"(مثال: `2934` أو `145`)"
        )
        try: bot.edit_message_text(add_text, chat_id, message_id, parse_mode="Markdown", reply_markup=admin_back_button())
        except: bot.send_message(chat_id, add_text, parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data == "adm_smm_cats_menu":
        if user_id != ADMIN_ID: return
        msg_cats = "📂 **اختر التطبيق لعرض وإدارة وحذف الخدمات المضافة فيه:**"
        try: bot.edit_message_text(msg_cats, chat_id, message_id, parse_mode="Markdown", reply_markup=admin_smm_categories_view_keyboard())
        except: bot.send_message(chat_id, msg_cats, parse_mode="Markdown", reply_markup=admin_smm_categories_view_keyboard())
        return

    elif call.data.startswith("adm_smm_list_"):
        if user_id != ADMIN_ID: return
        parts = call.data.split("_")
        # adm_smm_list_<cat>_<page>
        cat = parts[3] if len(parts) > 3 else "all"
        page = int(parts[4]) if len(parts) > 4 else 0
        cat_name = CATEGORY_TITLES.get(cat, "جميع الأقسام") if cat != "all" else "جميع الأقسام"
        try: bot.edit_message_text(f"📋 **قائمة خدمات [{cat_name}]:**", chat_id, message_id, parse_mode="Markdown", reply_markup=admin_smm_services_list_keyboard(category=cat, page=page))
        except: bot.send_message(chat_id, f"📋 **قائمة خدمات [{cat_name}]:**", parse_mode="Markdown", reply_markup=admin_smm_services_list_keyboard(category=cat, page=page))
        return

    elif call.data.startswith("adm_smm_del_"):
        if user_id != ADMIN_ID: return
        parts = call.data.split("_")
        db_id = int(parts[3])
        cat = parts[4] if len(parts) > 4 else "all"
        page = int(parts[5]) if len(parts) > 5 else 0
        delete_custom_smm_service(db_id)
        bot.answer_callback_query(call.id, "✅ تم حذف الخدمة بنجاح!", show_alert=True)
        try: bot.edit_message_text(f"📋 تم التحديث - قائمة الخدمات:", chat_id, message_id, reply_markup=admin_smm_services_list_keyboard(category=cat, page=page))
        except: pass
        return

    elif call.data.startswith("adm_smm_view_"):
        if user_id != ADMIN_ID: return
        db_id = int(call.data.split("_")[3])
        services = get_custom_smm_services(server_id='tiger')
        srv = next((s for s in services if s.get('db_id') == db_id), None)
        if not srv: return
        cat_title = CATEGORY_TITLES.get(srv.get('category'), srv.get('category'))
        view_text = (
            f"⚡ **تفاصيل الخدمة المخصصة:**\n\n"
            f"▫️ **الاسم بالعربي** : {srv.get('name_ar')}\n"
            f"▫️ **المعرف في السيرفر (ID)** : `{srv.get('service')}`\n"
            f"▫️ **التطبيق / القسم** : {cat_title}\n"
            f"▫️ **السعر لكل 1000** : `${srv.get('rate')}`\n"
            f"▫️ **الحد الأدنى** : `{srv.get('min')}`\n"
            f"▫️ **الحد الأقصى** : `{srv.get('max')}`\n"
            f"▫️ **السرعة / وقت البدء** : {srv.get('speed', 'فورية ⚡')}\n"
            f"▫️ **الضمان / الوصف** : {srv.get('description', 'بدون ضمان ⚠️')}"
        )
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🗑️ حذف هذه الخدمة", callback_data=f"adm_smm_del_{db_id}_{srv.get('category')}_0"))
        markup.row(InlineKeyboardButton("🔙 رجوع للقائمة", callback_data=f"adm_smm_list_{srv.get('category')}_0"))
        try: bot.edit_message_text(view_text, chat_id, message_id, parse_mode="Markdown", reply_markup=markup)
        except: bot.send_message(chat_id, view_text, parse_mode="Markdown", reply_markup=markup)
        return

    elif call.data == "adm_smm_export_json":
        if user_id != ADMIN_ID: return
        services = get_custom_smm_services()
        if not services:
            bot.answer_callback_query(call.id, "⚠️ لا توجد أي خدمات مضافة حالياً لتصديرها.", show_alert=True)
            return
        json_data = export_custom_smm_services_json()
        temp_file = os.path.join(os.path.dirname(DB_FILE), "custom_smm_services_backup.json")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(json_data)
            with open(temp_file, "rb") as f:
                bot.send_document(
                    chat_id,
                    f,
                    caption=(
                        f"💾 <b>نسخة احتياطية لخدمات الرشق المخصصة (JSON)</b>\n\n"
                        f"▫️ <b>عدد الخدمات المحفوظة</b> : {len(services)} خدمة\n"
                        f"▫️ <b>تاريخ الحفظ</b> : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                        f"🔒 احتفظ بهذا الملف! عند تحديث البوت أو رفع كود جديد يمكنك استرجاع كافة الخدمات بضغطة زر عبر (استيراد خدمات الرشق)."
                    ),
                    parse_mode="HTML"
                )
            bot.answer_callback_query(call.id, "✅ تم تصدير الخدمات وإرسال الملف بنجاح!")
        except Exception as e:
            bot.send_message(chat_id, f"❌ حدث خطأ أثناء التصدير: {e}")
        finally:
            if os.path.exists(temp_file):
                try: os.remove(temp_file)
                except: pass
        return

    elif call.data == "adm_smm_import_json":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADM_IMPORT_SMM_JSON'}
        import_prompt = (
            "📥 <b>استيراد واسترجاع خدمات الرشق المخصصة:</b>\n\n"
            "▫️ قم بإرسال ملف الـ JSON الذي قمت بتصديره سابقاً كملف.\n"
            "▫️ أو قم بنسخ ولصق نص الـ JSON كاملاً في هذه المحادثة مباشرة.\n\n"
            "سيقوم البوت فوراً بقراءة الخدمات وتفعيلها في قاعدة البيانات بدون أي تعب!"
        )
        try: bot.edit_message_text(import_prompt, chat_id, message_id, parse_mode="HTML", reply_markup=admin_back_button())
        except: bot.send_message(chat_id, import_prompt, parse_mode="HTML", reply_markup=admin_back_button())
        return

    elif call.data.startswith("adm_smm_setspd_"):
        if user_id != ADMIN_ID: return
        spd_code = call.data.replace("adm_smm_setspd_", "")
        step_data = USER_STEPS.get(user_id, {})
        if spd_code == "custom":
            step_data['step'] = 'ADM_ADD_SMM_CUSTOM_SPEED'
            USER_STEPS[user_id] = step_data
            prompt = (
                "✍️ <b>كتابة وقت وسرعة مخصصة للخدمة:</b>\n\n"
                "أرسل الآن وقت وسرعة تنفيذ الخدمة كتابةً في الشات:\n"
                "(مثال: <code>دقيقة واحدة ⏱️</code> أو <code>نصف ساعة ⏱️</code> أو <code>1 - 2 ساعة ⏳</code> أو <code>فوري بعد الدفع ⚡</code>):"
            )
            try: bot.edit_message_text(prompt, chat_id, message_id, parse_mode="HTML", reply_markup=admin_back_button())
            except: bot.send_message(chat_id, prompt, parse_mode="HTML", reply_markup=admin_back_button())
            return

        spd_map = {
            'instant': 'فورية ⚡',
            '5m': '1 - 5 دقائق ⏱️',
            '30m': '15 - 30 دقيقة ⏱️',
            '3h': '1 - 3 ساعات ⏳',
            '12h': '6 - 12 ساعة ⏳',
            '24h': '24 - 48 ساعة 📆'
        }
        speed_text = spd_map.get(spd_code, 'فورية ⚡')
        step_data['speed'] = speed_text
        step_data['step'] = 'ADM_ADD_SMM_GUARANTEE'
        USER_STEPS[user_id] = step_data

        srv_api_id = step_data.get('srv_api_id')
        cat_code = step_data.get('cat_code', 'others')
        cat_title = CATEGORY_TITLES.get(cat_code, cat_code)
        name_ar = step_data.get('name_ar')
        rate = step_data.get('rate', 1.0)
        min_q = step_data.get('min_q', 10)
        max_q = step_data.get('max_q', 100000)

        confirm_prompt = (
            f"🛡️ <b>اختر نوع الضمان لإتمام إضافة الخدمة:</b>\n\n"
            f"▫️ <b>القسم</b> : {cat_title}\n"
            f"▫️ <b>الاسم</b> : {name_ar}\n"
            f"▫️ <b>معرف السيرفر (ID)</b> : <code>{srv_api_id}</code>\n"
            f"▫️ <b>السعر</b> : ${rate:.3f} لكل 1K\n"
            f"▫️ <b>الكمية</b> : من {min_q} إلى {max_q}\n"
            f"▫️ <b>السرعة المحددة</b> : {speed_text}\n\n"
            f"اضغط على نوع الضمان بالأسفل لحفظ الخدمة وتفعيلها فوراً:"
        )
        try: bot.edit_message_text(confirm_prompt, chat_id, message_id, parse_mode="HTML", reply_markup=admin_smm_guarantee_keyboard())
        except: bot.send_message(chat_id, confirm_prompt, parse_mode="HTML", reply_markup=admin_smm_guarantee_keyboard())
        return

    elif call.data.startswith("adm_smm_setg_"):
        if user_id != ADMIN_ID: return
        g_type = call.data.replace("adm_smm_setg_", "")
        g_map = {
            'none': 'بدون ضمان ⚠️',
            '30d': 'ضمان 30 يوم ♻️',
            '60d': 'ضمان 60 يوم ♻️',
            '90d': 'ضمان 90 يوم ♻️',
            '365d': 'ضمان 365 يوم ♻️',
            'lifetime': 'ضمان مدى الحياة ♾️',
            'skip': 'بدون ضمان ⚠️'
        }
        guarantee_text = g_map.get(g_type, 'بدون ضمان ⚠️')
        step_data = USER_STEPS.get(user_id, {})
        
        srv_api_id = step_data.get('srv_api_id', '0')
        cat_code = step_data.get('cat_code', 'others')
        name_ar = step_data.get('name_ar', 'خدمة رشق')
        rate = step_data.get('rate', 1.0)
        min_q = step_data.get('min_q', 10)
        max_q = step_data.get('max_q', 100000)
        speed_text = step_data.get('speed', 'فورية ⚡')

        add_custom_smm_service(
            server_id='tiger',
            service_id=srv_api_id,
            category=cat_code,
            name_ar=name_ar,
            price_per_1k=rate,
            min_q=min_q,
            max_q=max_q,
            description=guarantee_text,
            speed=speed_text
        )
        USER_STEPS.pop(user_id, None)
        cat_title = CATEGORY_TITLES.get(cat_code, cat_code)
        success_text = (
            f"🎉 تمت إضافة وتفعيل خدمة الرشق بنجاح!\n\n"
            f"▫️ التطبيق / القسم : {cat_title}\n"
            f"▫️ الاسم بالعربي : {name_ar}\n"
            f"▫️ معرف السيرفر (ID) : {srv_api_id}\n"
            f"▫️ سعر البيع لكل 1K : ${rate:.3f}\n"
            f"▫️ الحد الأدنى : {min_q} | الحد الأقصى : {max_q}\n"
            f"▫️ السرعة : {speed_text}\n"
            f"▫️ الضمان : {guarantee_text}\n\n"
            f"✅ أصبحت الخدمة متاحة ومباشرة للعملاء في سيرفر الرشق 2 (الأرخص)!"
        )
        try:
            bot.edit_message_text(success_text, chat_id, message_id, reply_markup=admin_smm_custom_keyboard())
        except Exception:
            try:
                bot.send_message(chat_id, success_text, reply_markup=admin_smm_custom_keyboard())
            except Exception as e:
                print(f"Error sending smm add success msg: {e}")
        return

    # 5. إدارة القنوات
    elif call.data == "adm_channels":
        if user_id != ADMIN_ID: return
        ch_off = get_setting('channel_official_url', 'https://t.me/SM_SMS7')
        ch_ord = get_setting('channel_orders_url', 'https://t.me/numbuersms')
        ch_tut = get_setting('channel_tutorials_url', 'https://t.me/SMS_SMM1')
        ch_exp = get_setting('channel_explains_url', 'https://t.me/SMS_SMMHUB')
        sub_st = "✅ مفعل" if get_setting('force_sub_active', '1') == '1' else "❌ معطل"
        msg_ch = (
            f"📢 **إدارة القنوات والاشتراك الإجباري:**\n\n"
            f"▫️ **حالة الاشتراك الإجباري** : {sub_st}\n"
            f"▫️ **القناة الرسمية** : {ch_off}\n"
            f"▫️ **قناة التفعيلات والطلبات** : {ch_ord}\n"
            f"▫️ **قناة التعليمات** : {ch_tut}\n"
            f"▫️ **قناة الشروحات** : {ch_exp}"
        )
        try: bot.edit_message_text(msg_ch, chat_id, message_id, reply_markup=admin_channels_keyboard())
        except: bot.send_message(chat_id, msg_ch, reply_markup=admin_channels_keyboard())
        return

    elif call.data == "adm_tgl_force_sub":
        if user_id != ADMIN_ID: return
        curr = get_setting('force_sub_active', '1')
        new_val = '0' if curr == '1' else '1'
        set_setting('force_sub_active', new_val)
        bot.answer_callback_query(call.id, "تم تغيير حالة الاشتراك الإجباري!")
        try: bot.edit_message_reply_markup(chat_id, message_id, reply_markup=admin_channels_keyboard())
        except: pass
        return

    elif call.data == "adm_edit_ch_official":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADM_EDIT_CH_OFFICIAL'}
        bot.send_message(chat_id, "📢 أرسل رابط القناة الرسمية الجديد (أو معرّفها):", reply_markup=admin_back_button())
        return

    elif call.data == "adm_edit_ch_orders":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADM_EDIT_CH_ORDERS'}
        bot.send_message(chat_id, "🛍️ أرسل رابط قناة التفعيلات والطلبات الجديد (أو معرّفها مثل @numbuersms):", reply_markup=admin_back_button())
        return

    elif call.data == "adm_edit_ch_tutorials":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADM_EDIT_CH_TUTORIALS'}
        bot.send_message(chat_id, "📚 أرسل رابط قناة التعليمات الجديد (أو معرّفها مثل @SMS_SMM1):", reply_markup=admin_back_button())
        return

    elif call.data == "adm_edit_ch_explains":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADM_EDIT_CH_EXPLAINS'}
        bot.send_message(chat_id, "🎬 أرسل رابط قناة الشروحات الجديد (أو معرّفها مثل @SMS_SMMHUB):", reply_markup=admin_back_button())
        return

    elif call.data == "adm_test_channel":
        if user_id != ADMIN_ID: return
        bot.answer_callback_query(call.id, "⏳ جاري إرسال رسالة تجريبية لقناة التفعيلات والطلبات...")
        test_text = (
            "<b>🌟 Number-sms sales | تجربة ربط قناة التفعيلات والطلبات الناجحة</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✅ تم الربط بنجاح بين البوت وقناة التفعيلات والطلبات!\n"
            "▫️ جميع عمليات شراء وتفعيل الأرقام وحسابات التيليجرام الجاهزة ستُنشر هنا فوراً وبشكل آلي مع تمويه الأرقام والأكواد.\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        ok, target_or_err = send_to_channel_safe(test_text)
        if ok:
            bot.send_message(chat_id, f"✅ **نجح إرسال التجربة!**\nتم نشر الرسالة التجريبية في القناة بنجاح (`{target_or_err}`).\n\nتفضل بفتح القناة والتأكد من وصول الرسالة.", reply_markup=admin_back_button(), parse_mode="Markdown")
        else:
            bot_u = "NUM1_SMBOT"
            try:
                me = bot.get_me()
                if me and me.username: bot_u = me.username
            except: pass
            bot.send_message(
                chat_id,
                f"❌ **تعذر إرسال الرسالة إلى القناة:**\n`{target_or_err}`\n\n"
                f"💡 **لحل هذه المشكلة في خطوتين بسيطتين:**\n"
                f"1️⃣ افتح قناتك في تيليجرام واضغط على اسم القناة ثم **المشرفون (Administrators)**.\n"
                f"2️⃣ اضغط **إضافة مشرف** وابحث عن يوزر البوت `@{bot_u}` وقم بإضافته مع تفعيل صلاحية **نشر الرسائل (Post Messages)**.\n"
                f"3️⃣ اضغط زر التجربة هنا مرة أخرى للتأكد من نجاح الإرسال.",
                reply_markup=admin_back_button(),
                parse_mode="Markdown"
            )
        return

    elif call.data == "adm_backup_db":
        if user_id != ADMIN_ID: return
        bot.answer_callback_query(call.id, "⏳ جاري استخراج وتجهيز نسخة احتياطية من قاعدة البيانات...")
        try:
            backup_db_safely()
            if os.path.exists(DB_FILE) and os.path.getsize(DB_FILE) > 0:
                metrics = get_db_metrics(DB_FILE) or {'users': 0, 'balance': 0.0, 'orders': 0}
                with open(DB_FILE, 'rb') as f:
                    now_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
                    caption = (
                        f"💾 <b>نسخة احتياطية كاملة لقاعدة بيانات البوت</b>\n"
                        f"📅 التاريخ: <code>{now_str}</code>\n"
                        f"👥 عدد المستخدمين: <b>{metrics['users']}</b>\n"
                        f"💵 إجمالي الأرصدة: <b>${metrics['balance']:.2f}</b>\n"
                        f"📦 إجمالي الطلبات: <b>{metrics['orders']}</b>\n\n"
                        f"🔒 احتفظ بهذا الملف! يمكنك في أي وقت إرساله للبوت كملف أو الضغط على زر (رفع واستعادة نسخة احتياطية) لاسترجاع كل شيء فوراً."
                    )
                    bot.send_document(chat_id, f, visible_file_name=f"bot_database_{now_str}.db", caption=caption, parse_mode="HTML")
            else:
                bot.send_message(chat_id, "❌ لم يتم العثور على ملف قاعدة البيانات محلياً.", reply_markup=admin_back_button())
        except Exception as e:
            bot.send_message(chat_id, f"❌ خطأ أثناء استخراج قاعدة البيانات: {e}", reply_markup=admin_back_button())
        return

    elif call.data == "adm_recover_db":
        if user_id != ADMIN_ID: return
        bot.answer_callback_query(call.id, "🔍 جاري فحص ملفات السيرفر واسترجاع البيانات...")
        success, res_msg = scan_and_recover_database()
        bot.send_message(chat_id, res_msg, parse_mode="HTML", reply_markup=admin_back_button())
        return

    elif call.data == "adm_upload_db":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'WAITING_DB_RESTORE_FILE'}
        msg_up = (
            "📥 <b>استعادة قاعدة البيانات عبر رفع ملف:</b>\n\n"
            "قم الآن بإرسال ملف قاعدة البيانات (مثل <code>bot_database.db</code>) مباشرة في هذه المحادثة كملف (Document).\n\n"
            "⚡ سيقوم البوت فوراً بالتحقق من الملف واستبدال قاعدة البيانات الحالية واسترجاع المستخدمين والأرصدة والطلبات بنجاح وبأمان تام."
        )
        bot.send_message(chat_id, msg_up, parse_mode="HTML", reply_markup=admin_back_button())
        return

    # 6. إدارة الوكلاء والموزعين
    elif call.data == "adm_agents":
        if user_id != ADMIN_ID: return
        msg_ag = "🤝 **إدارة الوكلاء والموزعين المعتمدين:**\n\nيمكنك إضافة وكيل مع تحديد نسبة خصمه المباشر، أو حذف وكيل حالي:"
        try: bot.edit_message_text(msg_ag, chat_id, message_id, reply_markup=admin_agents_keyboard())
        except: bot.send_message(chat_id, msg_ag, reply_markup=admin_agents_keyboard())
        return

    elif call.data.startswith("adm_del_agent_"):
        if user_id != ADMIN_ID: return
        ag_uid = int(call.data.replace("adm_del_agent_", ""))
        remove_agent_db(ag_uid)
        bot.answer_callback_query(call.id, "تم حذف الوكيل بنجاح!")
        try: bot.edit_message_reply_markup(chat_id, message_id, reply_markup=admin_agents_keyboard())
        except: pass
        return

    elif call.data == "adm_add_agent_input":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADM_ADD_AGENT_ID'}
        bot.send_message(chat_id, "➕ أرسل آيدي المستخدم واسمه ونسبة الخصم مفصولين بمسافة:\nمثال: `6113734300 وكيل_صنعاء 5`", parse_mode="Markdown", reply_markup=admin_back_button())
        return

    # 7. إدارة حسابات الدعم الفني
    elif call.data == "adm_support":
        if user_id != ADMIN_ID: return
        sup1 = get_setting('support_admin_1', '@Num_s7')
        sup2 = get_setting('support_admin_2', '@Support_SMS7')
        msg_sup = f"🎧 **إدارة معرفات الدعم الفني:**\n\n1️⃣ الدعم الأول: `{sup1}`\n2️⃣ الدعم الثاني: `{sup2}`"
        try: bot.edit_message_text(msg_sup, chat_id, message_id, parse_mode="Markdown", reply_markup=admin_support_keyboard())
        except: bot.send_message(chat_id, msg_sup, parse_mode="Markdown", reply_markup=admin_support_keyboard())
        return

    elif call.data == "adm_edit_sup_1":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADM_EDIT_SUP_1'}
        bot.send_message(chat_id, "🎧 أرسل معرف الدعم الفني الأول (مثال: `@Num_s7`):", parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data == "adm_edit_sup_2":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADM_EDIT_SUP_2'}
        bot.send_message(chat_id, "🎧 أرسل معرف الدعم الفني الثاني (مثال: `@Support_SMS7`):", parse_mode="Markdown", reply_markup=admin_back_button())
        return

    # 8. إدارة تحويل الرصيد
    elif call.data == "adm_transfer":
        if user_id != ADMIN_ID: return
        min_t = get_setting('min_transfer_amount', '1.0')
        fee_t = get_setting('transfer_fee_percent', '0.0')
        msg_tr = f"🔄 **إعدادات تحويل الرصيد بين المستخدمين:**\n\n▫️ **الحد الأدنى للتحويل** : `${min_t}`\n▫️ **عمولة التحويل** : `{fee_t}%`"
        try: bot.edit_message_text(msg_tr, chat_id, message_id, parse_mode="Markdown", reply_markup=admin_transfer_keyboard())
        except: bot.send_message(chat_id, msg_tr, parse_mode="Markdown", reply_markup=admin_transfer_keyboard())
        return

    elif call.data == "adm_edit_transfer_min":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADM_EDIT_TRANSFER_MIN'}
        bot.send_message(chat_id, "💵 أرسل الحد الأدنى الجديد للتحويل بالدولار (مثال: `1.0` أو `0.5`):", parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data == "adm_edit_transfer_fee":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADM_EDIT_TRANSFER_FEE'}
        bot.send_message(chat_id, "📊 أرسل نسبة عمولة التحويل (مثال: `2` تعني 2% أو `0` بدون عمولة):", parse_mode="Markdown", reply_markup=admin_back_button())
        return

    # 9. إدارة قسم اربح رصيد مجاناً (نظام الشراكة والأرباح)
    elif call.data == "adm_referrals":
        if user_id != ADMIN_ID: return
        rew = get_setting('reward_per_invite', '0.05')
        pct = get_setting('referral_purchase_percent', '5.0')
        min_w = get_setting('min_invite_withdraw', '0.5')
        sec_st = "✅ مفعل" if is_section_enabled('free') else "❌ معطل"
        msg_ref = (
            f"💎 **إعدادات قسم (اربح رصيد مجاناً):**\n\n"
            f"▫️ **مكافأة الدعوة الواحدة** : `${rew}`\n"
            f"▫️ **نسبة عمولة المشتريات** : `{pct}%` (مدى الحياة من كل تفعيل أو شراء)\n"
            f"▫️ **الحد الأدنى لتحويل الأرباح** : `${min_w}`\n"
            f"▫️ **حالة قسم الأرباح بالبوت** : {sec_st}"
        )
        try: bot.edit_message_text(msg_ref, chat_id, message_id, parse_mode="Markdown", reply_markup=admin_referrals_keyboard())
        except: bot.send_message(chat_id, msg_ref, parse_mode="Markdown", reply_markup=admin_referrals_keyboard())
        return

    elif call.data == "adm_edit_ref_reward":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADM_EDIT_REF_REWARD'}
        bot.send_message(chat_id, "🎁 أرسل قيمة مكافأة الدعوة الواحدة بالدولار (مثال: `0.05` أو `0.10`):", parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data == "adm_edit_ref_pct":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADM_EDIT_REF_PCT'}
        bot.send_message(chat_id, "📈 أرسل نسبة العمولة من مشتريات الفريق (مثال: `5` تعني 5%، `10` تعني 10%):", parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data == "adm_edit_ref_min":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADM_EDIT_REF_MIN'}
        bot.send_message(chat_id, "🏧 أرسل الحد الأدنى لتحويل الأرباح لرصيد البوت (مثال: `0.5` أو `1.0`):", parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data == "adm_tgl_free_sec":
        if user_id != ADMIN_ID: return
        curr = is_section_enabled('free')
        toggle_section('free', not curr)
        bot.answer_callback_query(call.id, f"تم تغيير حالة قسم الأرباح إلى: {'معطل ❌' if curr else 'مفعل ✅'}")
        try: bot.edit_message_reply_markup(chat_id, message_id, reply_markup=admin_referrals_keyboard())
        except: pass
        return

    # إعدادات التحقق الأمني (Anti-Bot)
    elif call.data == "adm_captcha_menu":
        if user_id != ADMIN_ID: return
        c_st = "✅ مفعل" if get_setting('captcha_enabled', '1') == '1' else "❌ معطل"
        msg_c = (
            "🛡️ <b>إعدادات التحقق الأمني الذكي (Anti-Bot):</b>\n\n"
            f"▫️ <b>الحالة الحالية:</b> {c_st}\n"
            "▫️ <b>طريقة العمل:</b> عند تشغيله، يطلب البوت من أي مستخدم جديد كتابة كود أمني رقمي للتحقق من أنه إنسان وليس روبوت، لحماية البوت من السبام وسحب البيانات، تماماً مثل كبرى البوتات.\n"
            "▫️ <b>ملاحظة:</b> يتم طلب الكود مرة واحدة فقط عند انضمام المستخدم، وبعدها يعمل البوت معه بشكل طبيعي."
        )
        try: bot.edit_message_text(msg_c, chat_id, message_id, parse_mode="HTML", reply_markup=admin_captcha_keyboard())
        except: bot.send_message(chat_id, msg_c, parse_mode="HTML", reply_markup=admin_captcha_keyboard())
        return

    elif call.data == "adm_tgl_captcha":
        if user_id != ADMIN_ID: return
        curr = get_setting('captcha_enabled', '1')
        new_val = '0' if curr == '1' else '1'
        set_setting('captcha_enabled', new_val)
        bot.answer_callback_query(call.id, f"تم تغيير حالة التحقق الأمني إلى: {'مفعل ✅' if new_val == '1' else 'معطل ❌'}")
        try: bot.edit_message_reply_markup(chat_id, message_id, reply_markup=admin_captcha_keyboard())
        except: pass
        return

    # 10. مخزون الحسابات القديمة (سيرفر 3)
    elif call.data == "adm_aged_stock":
        if user_id != ADMIN_ID: return
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM aged_stock WHERE is_sold = 0")
            stock_cnt = cursor.fetchone()[0]
        finally:
            conn.close()
        msg_stk = f"📦 **إدارة مخزون الحسابات القديمة (السيرفر 3):**\n\n▫️ الحسابات المتوفرة بالمخزون حالياً: `{stock_cnt}` حساب"
        try: bot.edit_message_text(msg_stk, chat_id, message_id, parse_mode="Markdown", reply_markup=admin_aged_stock_keyboard())
        except: bot.send_message(chat_id, msg_stk, parse_mode="Markdown", reply_markup=admin_aged_stock_keyboard())
        return

    elif call.data == "adm_add_aged_account":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADM_ADD_AGED_ACC_DATA'}
        bot.send_message(chat_id, "➕ أرسل بيانات الحساب القديم بالشكل التالي:\n`السنة الدولة الرقم كود_2FA السعر`\n\nمثال:\n`2018 اليمن +967770000000 password123 7.5`", parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data == "adm_view_aged_orders":
        if user_id != ADMIN_ID: return
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, user_id, country_name, phone, cost, created_at FROM ready_accounts_orders WHERE server_id = '3' ORDER BY id DESC LIMIT 10")
            orders = cursor.fetchall()
        finally:
            conn.close()
        if not orders:
            bot.send_message(chat_id, "📦 لا توجد طلبات حسابات قديمة مسجلة حتى الآن.", reply_markup=admin_back_button())
            return
        msg = "📋 **أحدث طلبات الحسابات القديمة:**\n\n"
        for o in orders:
            msg += f"🧾 الطلب #{o[0]} | المستخدم `{o[1]}`\n🌐 {o[2]} | 📞 `{o[3]}`\n💵 ${o[4]:.2f} | ⏰ {o[5]}\n\n"
        bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=admin_back_button())
        return

    elif call.data == "admin_self_charge_manual":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADMIN_SELF_CHARGE_INPUT'}
        bot.send_message(chat_id, "⚡ **شحن رصيد ذاتي لحسابك كأدمن**\n\nأرسل المبلغ المراد إضافته لرصيدك مباشرة (مثال: 50 أو 100):", reply_markup=admin_back_button())
        return

    elif call.data == "admin_all_users" or call.data.startswith("adm_users_pg_"):
        if user_id != ADMIN_ID: return
        try: bot.answer_callback_query(call.id)
        except: pass

        page = int(call.data.split("_")[-1]) if call.data.startswith("adm_users_pg_") else 0
        per_page = 5

        conn = get_db()
        cursor = conn.cursor()
        try:
            ensure_user_columns(conn)
            cursor.execute("SELECT COUNT(*) FROM users")
            total_count = cursor.fetchone()[0] or 0
            total_pages = max(1, (total_count + per_page - 1) // per_page)
            page = max(0, min(page, total_pages - 1))
            offset = page * per_page

            cursor.execute("SELECT user_id, name, username, balance, spent_balance, orders_count, is_banned, is_agent, agent_discount, referrals_count, referrals_earnings, last_active FROM users ORDER BY rowid DESC LIMIT ? OFFSET ?", (per_page, offset))
            users = cursor.fetchall()
        finally:
            conn.close()

        if not users:
            bot.send_message(chat_id, "❌ لا يوجد مستخدمين مسجلين بعد.", reply_markup=admin_back_button())
            return

        bot.send_message(chat_id, f"👥 <b>قائمة المستخدمين المسجلين (إجمالي: {total_count} مستخدم) - صفحة {page+1}/{total_pages}:</b>", parse_mode="HTML")
        for u in users:
            u_id, u_name, u_uname, u_bal, u_spent, u_orders, u_ban, u_ag, u_ag_disc, u_ref_cnt, u_ref_earn, u_last_active = u
            u_name_safe = html.escape(str(u_name or "بدون اسم"))
            u_uname_safe = html.escape(str(u_uname or "").strip())
            if u_uname_safe and u_uname_safe.lower() not in ['none', 'لا يوجد', '']:
                uname_disp = u_uname_safe if u_uname_safe.startswith('@') else f"@{u_uname_safe}"
            else:
                uname_disp = "بدون معرف"

            status = "🚫 محظور" if u_ban == 1 else "✅ نشط"
            agent_tag = f" [⭐️ وكيل - خصم {u_ag_disc or 0}%]" if u_ag == 1 else ""
            card_msg = (
                f"👤 <b>الاسم</b> : {u_name_safe} ({uname_disp}){agent_tag}\n"
                f"🆔 <b>الآيدي</b> : <code>{u_id}</code> (اضغط للنسخ)\n"
                f"💰 <b>الرصيد الحالي</b> : <code>${format_money(u_bal)}</code>\n"
                f"💸 <b>إجمالي الصرف</b> : <code>${format_money(u_spent)}</code>\n"
                f"📦 <b>الطلبات الناجحة</b> : <code>{u_orders or 0}</code> طلب\n"
                f"🎁 <b>أرباح الإحالات</b> : <code>${float(u_ref_earn or 0):.2f}</code> (👥 {u_ref_cnt or 0} أعضاء)\n"
                f"🕒 <b>آخر ظهور</b> : <code>{u_last_active or 'غير مسجل'}</code>\n"
                f"📌 <b>الحالة</b> : <b>{status}</b>"
            )
            mk = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("➕ شحن", callback_data=f"act_add_{u_id}"), InlineKeyboardButton("➖ خصم", callback_data=f"act_deduct_{u_id}"))
            mk.row(InlineKeyboardButton("🚫 حظر/فك", callback_data=f"act_ban_{u_id}"), InlineKeyboardButton("🔍 كشف العمليات بالتفصيل", callback_data=f"act_inspect_{u_id}"))
            try:
                bot.send_message(chat_id, card_msg, parse_mode="HTML", reply_markup=mk)
            except Exception as e_send:
                print(f"Error sending user card: {e_send}")

        nav_markup = admin_users_pagination_keyboard(page, total_pages)
        bot.send_message(chat_id, "📄 للتنقل بين صفحات المستخدمين:", reply_markup=nav_markup)
        return

    elif call.data.startswith("act_inspect_"):
        if user_id != ADMIN_ID: return
        target_uid = int(call.data.replace("act_inspect_", ""))
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT name, username, balance, spent_balance FROM users WHERE user_id = ?", (target_uid,))
            u_info = cursor.fetchone()
            u_name = html.escape(str(u_info[0])) if u_info else "مستخدم"
            u_uname = html.escape(str(u_info[1] or "")) if u_info else ""
            u_bal = float(u_info[2]) if u_info else 0.0
            u_spent = float(u_info[3]) if u_info else 0.0

            cursor.execute("SELECT tz_id, phone, service, cost, status, created_at FROM purchases WHERE user_id = ? ORDER BY id DESC LIMIT 10", (target_uid,))
            nums = cursor.fetchall()
            cursor.execute("SELECT order_id, service_name, quantity, cost, status, created_at FROM smm_orders WHERE user_id = ? ORDER BY id DESC LIMIT 10", (target_uid,))
            smms = cursor.fetchall()
            cursor.execute("SELECT server_id, country_name, phone, cost, status, created_at FROM ready_accounts_orders WHERE user_id = ? ORDER BY id DESC LIMIT 10", (target_uid,))
            readys = cursor.fetchall()
        finally:
            conn.close()

        msg = (
            f"🔍 <b>كشف وسجل عمليات المستخدم الكامل:</b>\n"
            f"👤 <b>الاسم</b> : {u_name} ({u_uname})\n"
            f"🆔 <b>الآيدي</b> : <code>{target_uid}</code>\n"
            f"💰 <b>الرصيد</b> : <code>${format_money(u_bal)}</code> | 💸 <b>الصرف</b> : <code>${format_money(u_spent)}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
        )
        if nums:
            msg += "📞 <b>طلبات الأرقام والتفعيلات المؤقتة:</b>\n"
            for n in nums:
                msg += f"• #{n[0]} | {html.escape(str(n[1]))} ({html.escape(str(n[2])).upper()}) - ${float(n[3]):.2f} [{n[4]}] ({n[5]})\n"
            msg += "\n"
        if smms:
            msg += "🚀 <b>طلبات خدمات الرشق والدعم:</b>\n"
            for s in smms:
                msg += f"• #{s[0]} | {html.escape(str(s[1]))} ({s[2]}) - ${float(s[3]):.3f} [{s[4]}] ({s[5]})\n"
            msg += "\n"
        if readys:
            msg += "💯 <b>طلبات الحسابات الجاهزة:</b>\n"
            for r in readys:
                msg += f"• سيرفر {r[0]} | {html.escape(str(r[1]))} ({html.escape(str(r[2]))}) - ${float(r[3]):.2f} [{r[4]}] ({r[5]})\n"
        if not nums and not smms and not readys:
            msg += "⚠️ لا توجد أي عمليات شراء أو طلبات مسجلة لهذا المستخدم حتى الآن."

        bot.send_message(chat_id, msg, parse_mode="HTML", reply_markup=admin_back_button())
        return

    elif call.data == "adm_view_top_refs":
        if user_id != ADMIN_ID: return
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*), SUM(referrals_earnings) FROM users WHERE referrals_count > 0 OR referrals_earnings > 0")
            row_tot = cursor.fetchone()
            tot_refs_users = row_tot[0] or 0
            tot_refs_earnings = row_tot[1] or 0.0

            cursor.execute("SELECT user_id, name, username, referrals_count, referrals_earnings, balance FROM users WHERE referrals_count > 0 ORDER BY referrals_earnings DESC, referrals_count DESC LIMIT 10")
            top_refs = cursor.fetchall()
        finally:
            conn.close()

        msg = (
            f"📊 <b>تقرير نظام الأرباح والإحالات الشامل:</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 <b>المستخدمين المشاركين بنظام الإحالة:</b> <code>{tot_refs_users}</code> مستخدم\n"
            f"💰 <b>إجمالي أرباح الإحالات المستحقة:</b> <code>${tot_refs_earnings:.2f}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 <b>أعلى المستخدمين إحالة وأرباحاً:</b>\n\n"
        )
        if top_refs:
            for idx, r in enumerate(top_refs, 1):
                r_uid, r_name, r_uname, r_cnt, r_earn, r_bal = r
                uname_str = f"@{r_uname}" if r_uname else (r_name or "بدون اسم")
                msg += f"<b>{idx}.</b> {html.escape(str(uname_str))} (<code>{r_uid}</code>)\n"
                msg += f"   👥 الفريق: <b>{r_cnt}</b> عضو | 💵 الأرباح: <b>${float(r_earn):.2f}</b> | 💳 الرصيد: <b>${format_money(r_bal)}</b>\n\n"
        else:
            msg += "⚠️ لا توجد بيانات إحالات مسجلة حتى الآن.\n"

        bot.send_message(chat_id, msg, parse_mode="HTML", reply_markup=admin_back_button())
        return

    elif call.data == "admin_stats":
        if user_id != ADMIN_ID: return
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*), SUM(balance), SUM(spent_balance) FROM users")
            u_data = cursor.fetchone()
            total_users = u_data[0] or 0
            total_user_balance = u_data[1] or 0.0
            total_spent = u_data[2] or 0.0

            cursor.execute("SELECT COUNT(*), SUM(cost) FROM purchases WHERE status = 'COMPLETED'")
            p_data = cursor.fetchone()
            num_purchases = p_data[0] or 0
            num_spent = p_data[1] or 0.0

            cursor.execute("SELECT COUNT(*), SUM(cost) FROM smm_orders WHERE status NOT IN ('Canceled', 'Cancelled')")
            s_data = cursor.fetchone()
            smm_count = s_data[0] or 0
            smm_spent = s_data[1] or 0.0

            cursor.execute("SELECT COUNT(*), SUM(cost) FROM ready_accounts_orders WHERE status = 'COMPLETED'")
            r_data = cursor.fetchone()
            ready_count = r_data[0] or 0
            ready_spent = r_data[1] or 0.0

            cursor.execute("SELECT COUNT(*) FROM purchases WHERE status = 'CANCELLED'")
            cancelled_nums = cursor.fetchone()[0] or 0
        finally:
            conn.close()

        profit_pct_num = float(get_setting('profit_margin_numbers', '0.10'))
        profit_pct_smm = float(get_setting('profit_margin_smm', '0.10'))
        profit_pct_ready = float(get_setting('profit_margin_ready', '0.10'))

        num_cost = num_spent / (1.0 + profit_pct_num) if num_spent > 0 else 0.0
        smm_cost = smm_spent / (1.0 + profit_pct_smm) if smm_spent > 0 else 0.0
        ready_cost = ready_spent / (1.0 + profit_pct_ready) if ready_spent > 0 else 0.0

        total_sales = num_spent + smm_spent + ready_spent
        total_cost = num_cost + smm_cost + ready_cost
        net_profit = max(0.0, total_sales - total_cost)
        total_orders = num_purchases + smm_count + ready_count

        msg = (
            f"📊 **إحصائيات البوت الدقيقة والمالية (المكتملة فقط):**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 **إجمالي المستخدمين المسجلين** : `{total_users}` مستخدم\n"
            f"💰 **إجمالي أرصدة المستخدمين الحالية** : `${format_money(total_user_balance)}`\n"
            f"💸 **إجمالي المصروفات الدائمة** : `${format_money(total_spent)}`\n\n"
            f"📈 **تفاصيل المبيعات المكتملة:**\n"
            f"📞 **الأرقام المفعلة بنجاح** : `{num_purchases}` طلب (${format_money(num_spent)})\n"
            f"🚀 **طلبات الرشق المنفذة** : `{smm_count}` طلب (${format_money(smm_spent)})\n"
            f"💯 **الحسابات الجاهزة المسلمة** : `{ready_count}` حساب (${format_money(ready_spent)})\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🧾 **إجمالي الطلبات المكتملة** : `{total_orders}` طلب\n"
            f"💵 **إجمالي المبيعات (Sales)** : `${format_money(total_sales)}`\n"
            f"📦 **إجمالي تكلفة المزودين (Cost)** : `${format_money(total_cost)}`\n"
            f"💎 **صافي الأرباح الفعلية (Net Profit)** : `${format_money(net_profit)}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ **الطلبات الملغاة والمسترجعة** : `{cancelled_nums}` طلب (تمت إعادة رصيدها بالكامل ولا تحتسب ضمن المبيعات)"
        )
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
                bot.send_message(chat_id, "🚫 تم تقييد/حظر العضو." if new_status == 1 else "🟢 تم فك تقييد العضو.", reply_markup=admin_back_button())
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

    elif call.data == "admin_ban_menu":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADMIN_BAN_USER'}
        bot.send_message(chat_id, "🚫 **تقييد أو فك تقييد عضو:**\n\nأرسل آيدي المستخدم المراد تقييده/فك تقييده:", reply_markup=admin_back_button())
        return

    elif call.data == "admin_broadcast":
        if user_id != ADMIN_ID: return
        USER_STEPS[user_id] = {'step': 'ADMIN_BROADCAST'}
        bot.send_message(chat_id, "📢 أرسل الرسالة التي ترغب في إذاعتها لجميع المستخدمين الآن:", reply_markup=admin_back_button())
        return

    elif call.data == "admin_toggle_maintenance":
        if user_id != ADMIN_ID: return
        curr_m = get_setting('maintenance_mode', '0')
        new_m = '0' if curr_m == '1' else '1'
        set_setting('maintenance_mode', new_m)
        status_txt = "🔴 تم تفعيل وضع الصيانة الشامل" if new_m == '1' else "🟢 تم إيقاف وضع الصيانة (البوت متاح للجميع)"
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

    # ==================== الدفع عبر Binance (تلقائي) ====================
    elif call.data == "pay_binance" or call.data == "deposit_binance":
        bot.answer_callback_query(call.id)
        USER_STEPS[user_id] = {"step": "waiting_binance_amount"}
        binance_intro = (
            "🟡 <b>شحن رصيد عبر Binance Pay (تلقائي)</b>\n\n"
            "⚠️‼️ <b>تنبيه مهم</b> ‼️⚠️\n"
            "• هذه بوابة دفع تلقائية عبر Binance Pay.\n"
            "• سيتم إضافة الرصيد تلقائياً بعد التحقق من المعاملة.\n"
            "• تأكد من إدخال نفس المبلغ الذي اخترته عند التحويل.\n"
            "• لا تشارك TXID مع أي شخص آخر.\n"
            "━━━━━━━━━━━━━━━━\n"
            "💰 <b>ارسل المبلغ الذي تريد شحنه (بالدولار USDT):</b>\n\n"
            "مثال: 10"
        )
        try: bot.edit_message_text(binance_intro, chat_id, message_id, reply_markup=binance_amount_keyboard(), parse_mode="HTML")
        except: bot.send_message(chat_id, binance_intro, reply_markup=binance_amount_keyboard(), parse_mode="HTML")
        return

    elif call.data in ["copy_binance_addr", "copy_id"]:
        binance_addr = get_binance_pay_id()
        bot.answer_callback_query(call.id, text=f"📍 عنوان المحفظة:\n{binance_addr}\n\nتم النسخ بنجاح!", show_alert=True)
        return

    elif call.data in ["binance_enter_txid", "enter_txid", "binance_retry_txid"]:
        bot.answer_callback_query(call.id)
        step_data = USER_STEPS.get(user_id, {})
        amount = step_data.get('amount', 0)
        amount_str = step_data.get('amount_str', str(amount))
        USER_STEPS[user_id] = {"step": "waiting_binance_txid", "amount": amount, "amount_str": amount_str}

        txid_prompt = (
            "🟡 <b>أدخل TXID (رقم المعاملة)</b>\n\n"
            "⚠️ <b>تأكد من:</b>\n"
            "• إدخال TXID الصحيح من محفظتك.\n"
            "• أن المبلغ المرسل يساوي المبلغ الذي اخترته.\n"
            "• انتظر دقيقة بعد التحويل قبل إدخال TXID.\n\n"
            "<b>أرسل TXID الآن:</b>"
        )
        try: bot.edit_message_text(txid_prompt, chat_id, message_id, reply_markup=binance_txid_input_keyboard(), parse_mode="HTML")
        except: bot.send_message(chat_id, txid_prompt, reply_markup=binance_txid_input_keyboard(), parse_mode="HTML")
        return

    elif call.data == "binance_back_to_details":
        bot.answer_callback_query(call.id)
        step_data = USER_STEPS.get(user_id, {})
        amount = step_data.get('amount')
        if not amount:
            USER_STEPS[user_id] = {"step": "waiting_binance_amount"}
            binance_intro = (
                "🟡 <b>شحن رصيد عبر Binance Pay (تلقائي)</b>\n\n"
                "⚠️‼️ <b>تنبيه مهم</b> ‼️⚠️\n"
                "• هذه بوابة دفع تلقائية عبر Binance Pay.\n"
                "• سيتم إضافة الرصيد تلقائياً بعد التحقق من المعاملة.\n"
                "• تأكد من إدخال نفس المبلغ الذي اخترته عند التحويل.\n"
                "• لا تشارك TXID مع أي شخص آخر.\n"
                "━━━━━━━━━━━━━━━━\n"
                "💰 <b>ارسل المبلغ الذي تريد شحنه (بالدولار USDT):</b>\n\n"
                "مثال: 10"
            )
            try: bot.edit_message_text(binance_intro, chat_id, message_id, reply_markup=binance_amount_keyboard(), parse_mode="HTML")
            except: bot.send_message(chat_id, binance_intro, reply_markup=binance_amount_keyboard(), parse_mode="HTML")
            return
        
        amount_str = step_data.get('amount_str', f"{int(amount)}" if float(amount).is_integer() else f"{float(amount):g}")
        binance_addr = get_binance_pay_id()
        USER_STEPS[user_id] = {"step": "binance_details", "amount": amount, "amount_str": amount_str}
        details_msg = (
            "🟡 <b>تفاصيل الدفع عبر Binance Pay</b>\n\n"
            f"💰 <b>المبلغ المطلوب:</b> {amount_str} USDT\n\n"
            "📍 <b>عنوان المحفظة:</b>\n"
            f"<code>{binance_addr}</code>\n\n"
            "📋 <b>الخطوات:</b>\n"
            "1️⃣ حول المبلغ المطلوب إلى العنوان أعلاه.\n"
            "2️⃣ تأكد من إرسال المبلغ نفسه الذي اخترته.\n"
            "3️⃣ بعد الانتهاء، انسخ TXID (رقم المعاملة) وأرسله هنا.\n\n"
            "⚠️ <b>ملاحظة:</b> سيتم التحقق من المعاملة تلقائياً عبر Binance API."
        )
        try: bot.edit_message_text(details_msg, chat_id, message_id, reply_markup=binance_details_keyboard(), parse_mode="HTML")
        except: bot.send_message(chat_id, details_msg, reply_markup=binance_details_keyboard(), parse_mode="HTML")
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
            admin_contact = get_setting('support_admin_1', ADMIN_USERNAME).strip()
            msg = (
                f"📌 <b>تفاصيل الدفع عبر {pay_info['name']}</b>\n\n"
                f"🏷️ <b>رقم الحساب:</b> <code>{pay_info['acc']}</code>\n"
                f"💵 <b>أقل مبلغ:</b> {pay_info['min']}\n"
                f"💱 <b>سعر الصرف:</b> {pay_info['rate']}\n\n"
                f"⚠️ حوّل المبلغ وأرسل صورة الإشعار مع الآيدي (<code>{user_id}</code>) للإدارة: {admin_contact}"
            )
            back_markup = InlineKeyboardMarkup()
            back_markup.add(InlineKeyboardButton("🔙 العودة لوسائل الدفع", callback_data="recharge_menu"))
            back_markup.add(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
            try:
                bot.edit_message_text(msg, chat_id, message_id, reply_markup=back_markup, parse_mode="HTML")
            except Exception:
                try:
                    bot.send_message(chat_id, msg, reply_markup=back_markup, parse_mode="HTML")
                    try: bot.delete_message(chat_id, message_id)
                    except: pass
                except Exception:
                    bot.send_message(chat_id, msg, reply_markup=back_markup)
        return

    # ==================== باقي معالجات الأزرار القياسية ====================
    elif call.data == "back_main":
        try: bot.answer_callback_query(call.id)
        except: pass
        if user_id in USER_STEPS: del USER_STEPS[user_id]
        user_data = get_or_create_user(user_id, call.from_user.first_name, call.from_user.username or "")
        try: balance = float(user_data[3]) if len(user_data) > 3 and user_data[3] is not None else float(user_data[2])
        except: balance = 0.0

        user_uname = call.from_user.username or ""
        text = get_main_welcome_text(user_id, call.from_user.first_name, user_uname, balance)
        try: bot.edit_message_text(text, chat_id, message_id, parse_mode="HTML", disable_web_page_preview=True, reply_markup=main_keyboard(user_id))
        except Exception:
            try: bot.delete_message(chat_id, message_id)
            except: pass
            bot.send_message(chat_id, text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=main_keyboard(user_id))
        return

    elif call.data == "transfer":
        USER_STEPS[user_id] = {'step': 'TRANSFER_TARGET'}
        text = ("🔄 قسم تحويل الرصيد بين الحسابات\n\n✨ الميزات: عمولة 0%\n💵 أقل مبلغ: $1.00\n\n📌 يرجى إرسال آيدي (User ID) الشخص المستلم الآن:")
        bot.edit_message_text(text, chat_id, message_id, reply_markup=back_button())

    elif call.data == "buy_number":
        bot.edit_message_text("📞 قسم شراء الأرقام الوهمية\n\nاختر السيرفر المناسب لك:", chat_id, message_id, reply_markup=servers_keyboard())

    elif call.data.startswith("select_server_"):
        server_id = call.data.split("_")[2]
        bot.edit_message_text(f"⚙️ تم اختيار السيرفر بنجاح\n\nاختر التطبيق المطلوب:", chat_id, message_id, reply_markup=services_keyboard(server_id))

    elif call.data.startswith("tg_srv_"):
        server_id = call.data.replace("tg_srv_", "")
        bot.answer_callback_query(call.id, "جاري جلب أسعار ودول تليجرام... ⏳")
        srv_name = SERVERS.get(server_id, {}).get('name', f"سيرفر {server_id}")
        markup = countries_keyboard_fast(server_id, "tg", page=0, origin="tg")
        msg_txt = f"🔵 **عروض تليجرام - {srv_name}**:\n\nاختر الدولة المطلوبة:"
        try: bot.edit_message_text(msg_txt, chat_id, message_id, parse_mode="Markdown", reply_markup=markup)
        except Exception:
            try: bot.delete_message(chat_id, message_id)
            except: pass
            bot.send_message(chat_id, msg_txt, parse_mode="Markdown", reply_markup=markup)
        return

    elif call.data.startswith("wa_srv_"):
        server_id = call.data.replace("wa_srv_", "")
        bot.answer_callback_query(call.id, "جاري جلب أسعار ودول واتساب... ⏳")
        srv_name = SERVERS.get(server_id, {}).get('name', f"سيرفر {server_id}")
        markup = countries_keyboard_fast(server_id, "wa", page=0, origin="wa")
        msg_txt = f"🟢 **عروض واتساب - {srv_name}**:\n\nاختر الدولة المطلوبة:"
        try: bot.edit_message_text(msg_txt, chat_id, message_id, parse_mode="Markdown", reply_markup=markup)
        except Exception:
            try: bot.delete_message(chat_id, message_id)
            except: pass
            bot.send_message(chat_id, msg_txt, parse_mode="Markdown", reply_markup=markup)
        return

    elif call.data.startswith("srv_app_"):
        bot.answer_callback_query(call.id, "جاري جلب الدول والأسعار الحية من الموقع... ⏳")
        _, _, server_id, srv_code = call.data.split("_")
        srv_info = POPULAR_SERVICES.get(srv_code, {})
        srv_display = f"{srv_info.get('icon', '📱')} {srv_info.get('name', srv_code.upper())}"
        markup = countries_keyboard_fast(server_id, srv_code, page=0)
        bot.edit_message_text(f"🌐 اختر الدولة المطلوبة لـ {srv_display}:", chat_id, message_id, reply_markup=markup)

    elif call.data.startswith("pg_"):
        parts = call.data.split("_")
        server_id = parts[1]
        srv_code = parts[2]
        page = int(parts[3])
        origin = parts[4] if len(parts) > 4 else None

        srv_info = POPULAR_SERVICES.get(srv_code, {})
        srv_display = f"{srv_info.get('icon', '📱')} {srv_info.get('name', srv_code.upper())}"
        markup = countries_keyboard_fast(server_id, srv_code, page=page, origin=origin)

        if origin == "tg":
            title = f"🔵 **عروض تليجرام (صفحة {page + 1}):**\n\nاختر الدولة المطلوبة:"
        elif origin == "wa":
            title = f"🟢 **عروض واتساب (صفحة {page + 1}):**\n\nاختر الدولة المطلوبة:"
        else:
            title = f"🌐 اختر الدولة المطلوبة لـ {srv_display}:"

        try: bot.edit_message_text(title, chat_id, message_id, parse_mode="Markdown", reply_markup=markup)
        except Exception:
            try: bot.delete_message(chat_id, message_id)
            except: pass
            bot.send_message(chat_id, title, parse_mode="Markdown", reply_markup=markup)
        return

    elif call.data.startswith("b_"):
        bot.answer_callback_query(call.id, "جاري طلب الرقم، يرجى الانتظار...")
        _, server_id, srv_code, country_code = call.data.split("_")
        prices = fetch_server_prices(server_id, srv_code)
        price = prices.get(str(country_code), DEFAULT_PRICE)

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            balance = row[0] if row and row[0] is not None else 0.0

            if balance < price:
                try: bot.edit_message_text(f"❌ **رصيدك غير كافٍ!**\n\nسعر الرقم: ${price:.2f}\nرصيدك الحالي: ${balance:.2f}", chat_id, message_id, parse_mode="Markdown", reply_markup=back_button())
                except: bot.send_message(chat_id, f"❌ **رصيدك غير كافٍ!**\n\nسعر الرقم: ${price:.2f}\nرصيدك الحالي: ${balance:.2f}", parse_mode="Markdown", reply_markup=back_button())
                return

            srv = SERVERS.get(server_id)
            if not srv:
                srv = {'api_key': API_KEY, 'url': API_URL}
            
            get_params = {'action': 'getNumber', 'service': srv_code, 'country': country_code}
            raw_cost = get_server_raw_price(server_id, srv_code, country_code)
            if server_id == 'smsbower' and raw_cost:
                get_params['maxPrice'] = str(raw_cost)
            
            res = grizzly_request(get_params, srv['api_key'], srv['url'])

            if "ACCESS_NUMBER" in res:
                parts = res.split(":")
                tz_id, raw_phone = parts[1], parts[2]
                formatted_phone = clean_phone_number(raw_phone, country_code)
                c_name, c_flag = get_clean_country_info(country_code)

                cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (price, user_id))
                cursor.execute('INSERT INTO purchases (user_id, tz_id, phone, service, cost, country_code, status) VALUES (?, ?, ?, ?, ?, ?, "PENDING")',
                               (user_id, tz_id, formatted_phone, srv_code, price, country_code))
                conn.commit()

                msg = format_number_order_message(tz_id, c_name, c_flag, formatted_phone, srv_code, price)
                try: bot.edit_message_text(msg, chat_id, message_id, parse_mode="Markdown", reply_markup=active_number_keyboard(tz_id, server_id, srv_code, formatted_phone))
                except: bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=active_number_keyboard(tz_id, server_id, srv_code, formatted_phone))

                # بدء خيط خلفي ذكي لفحص وصول الكود وتحديث الواجهة تلقائياً دون الحاجة للضغط يدوياً
                threading.Thread(
                    target=poll_sms_for_order,
                    args=(user_id, chat_id, message_id, server_id, tz_id, formatted_phone, srv_code, price, country_code),
                    daemon=True
                ).start()
            else:
                if "NO_NUMBERS" in res:
                    err_msg = "لا توجد أرقام متاحة حالياً في هذا السيرفر... 🐶\nقم بتجربة سيرفر اخر 💙"
                elif "NO_BALANCE" in res:
                    err_msg = "عذراً، رصيد السيرفر غير كافٍ حالياً."
                else:
                    err_msg = f"❌ **لم يكتمل الطلب:**\n{res}"

                markup = no_numbers_keyboard(server_id, srv_code, country_code)
                try: bot.edit_message_text(err_msg, chat_id, message_id, parse_mode="Markdown", reply_markup=markup)
                except: bot.send_message(chat_id, err_msg, parse_mode="Markdown", reply_markup=markup)
        finally:
            conn.close()

    elif call.data.startswith("check_sms_"):
        parts = call.data.split("_")
        server_id, tz_id = parts[2], parts[3]
        srv = SERVERS.get(server_id)
        if not srv: srv = {'api_key': API_KEY, 'url': API_URL}
        
        bot.answer_callback_query(call.id, "⏳ جاري فحص وصول كود التفعيل...")
        res = grizzly_request({'action': 'getStatus', 'id': tz_id}, srv['api_key'], srv['url'])
        
        if "STATUS_OK" in res:
            code = res.split(":")[1]
            conn = get_db()
            cursor = conn.cursor()
            try:
                cursor.execute('SELECT phone, service, cost, country_code, status FROM purchases WHERE tz_id = ?', (tz_id,))
                p_row = cursor.fetchone()
                if p_row:
                    phone_val, srv_c, cost_val, c_code, curr_st = p_row
                    if curr_st != 'COMPLETED':
                        cursor.execute('UPDATE purchases SET status = "COMPLETED" WHERE tz_id = ?', (tz_id,))
                        cursor.execute('UPDATE users SET orders_count = orders_count + 1, spent_balance = spent_balance + ? WHERE user_id = ?', (cost_val, user_id))
                        conn.commit()
                        
                        c_name, c_flag = get_clean_country_info(c_code)
                        srv_info = POPULAR_SERVICES.get(srv_c.lower(), {})
                        srv_name_clean = f"{srv_info.get('icon', '📱')} {srv_info.get('name', srv_c.upper())}"
                        srv_server = srv.get('name', f"سيرفر الأرقام {server_id}")
                        
                        notify_number_activation(
                            order_id=tz_id,
                            country_name=c_name,
                            country_flag=c_flag,
                            server_name=srv_server,
                            service_name=srv_name_clean,
                            phone=phone_val,
                            code=code,
                            price=cost_val,
                            user_id=user_id
                        )
                        grizzly_request({'action': 'setStatus', 'status': '6', 'id': tz_id}, srv['api_key'], srv['url'])
                    else:
                        c_name, c_flag = get_clean_country_info(c_code)
                        srv_info = POPULAR_SERVICES.get(srv_c.lower(), {})
                        srv_name_clean = f"{srv_info.get('icon', '📱')} {srv_info.get('name', srv_c.upper())}"
                        srv_server = srv.get('name', f"سيرفر الأرقام {server_id}")
                else:
                    phone_val = "الرقم المطلوب"
                    srv_c = 'wa'
                    cost_val = 0.0
                    c_code = '6'
                    c_name, c_flag = get_clean_country_info(c_code)
                    srv_info = POPULAR_SERVICES.get(srv_c.lower(), {})
                    srv_name_clean = f"{srv_info.get('icon', '📱')} {srv_info.get('name', srv_c.upper())}"
                    srv_server = srv.get('name', f"سيرفر الأرقام {server_id}")

                cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
                u_row = cursor.fetchone()
                rem_bal = u_row[0] if u_row and u_row[0] is not None else 0.0
            finally:
                conn.close()
                
            done_text = format_completed_number_message(
                tz_id=tz_id,
                country_name=c_name,
                country_flag=c_flag,
                server_name=srv_server,
                service_name=srv_name_clean,
                phone=phone_val,
                code=code,
                price=cost_val,
                user_balance=rem_bal
            )
            markup = completed_number_keyboard(server_id, srv_c, c_code)
            try:
                bot.edit_message_text(done_text, chat_id, message_id, parse_mode="Markdown", reply_markup=markup)
            except Exception:
                try:
                    bot.delete_message(chat_id, message_id)
                except Exception:
                    pass
                bot.send_message(chat_id, done_text, parse_mode="Markdown", reply_markup=markup)
        elif "STATUS_WAIT_CODE" in res or "STATUS_WAIT_RESEND" in res or "ACCESS_READY" in res:
            bot.answer_callback_query(call.id, "⏳ لم يصل الكود بعد! يرجى طلب إرسال الكود من داخل تطبيق واتساب/تيليجرام والانتظار قليلاً.", show_alert=True)
        elif "STATUS_CANCEL" in res:
            bot.answer_callback_query(call.id, "❌ تم إلغاء هذا الرقم من المزود.", show_alert=True)
        else:
            bot.answer_callback_query(call.id, f"حالة الطلب: {res}", show_alert=True)

    elif call.data.startswith("change_num_"):
        parts = call.data.split("_")
        server_id, tz_id = parts[2], parts[3]
        srv = SERVERS.get(server_id)
        if not srv: srv = {'api_key': API_KEY, 'url': API_URL}

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT service, country_code, cost, status, phone FROM purchases WHERE tz_id = ?', (tz_id,))
            p_row = cursor.fetchone()
            if not p_row or p_row[3] not in ['PENDING']:
                bot.answer_callback_query(call.id, "❌ لا يمكن استبدال هذا الرقم (تم إنهاؤه مسبقاً).", show_alert=True)
                return
                
            srv_code, country_code, cost, _, old_phone = p_row

            # إشعار فوري للمستخدم
            bot.answer_callback_query(call.id, "⚡ جاري استخراج رقم جديد لك فوراً بدون انتظار...")

            # 1. طلب رقم جديد فـوراً ومباشرة من المزود لنفس الدولة والتطبيق دون انتظار انتهاء عداد الرقم القديم
            get_params = {'action': 'getNumber', 'service': srv_code, 'country': country_code}
            raw_cost = get_server_raw_price(server_id, srv_code, country_code)
            if server_id == 'smsbower' and raw_cost:
                get_params['maxPrice'] = str(raw_cost)
                
            res = grizzly_request(get_params, srv['api_key'], srv['url'])
            if "ACCESS_NUMBER" in res:
                p_parts = res.split(":")
                new_tz_id, new_raw_phone = p_parts[1], p_parts[2]
                new_phone = clean_phone_number(new_raw_phone, country_code)
                c_name, c_flag = get_clean_country_info(country_code)

                # تحديث حالة الرقم القديم إلى مستبدل
                cursor.execute('UPDATE purchases SET status = "REPLACED" WHERE tz_id = ?', (tz_id,))
                # إدراج الرقم الجديد كطلب قيد الانتظار
                cursor.execute('INSERT INTO purchases (user_id, tz_id, phone, service, cost, country_code, status) VALUES (?, ?, ?, ?, ?, ?, "PENDING")',
                               (user_id, new_tz_id, new_phone, srv_code, cost, country_code))
                conn.commit()

                # عرض بيانات الرقم الجديد فوراً للمستخدم
                msg = format_number_order_message(new_tz_id, c_name, c_flag, new_phone, srv_code, cost)
                try: bot.edit_message_text(msg, chat_id, message_id, parse_mode="Markdown", reply_markup=active_number_keyboard(new_tz_id, server_id, srv_code, new_phone))
                except: bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=active_number_keyboard(new_tz_id, server_id, srv_code, new_phone))

                # 2. محاولة إلغاء الرقم القديم في المزود الآن
                res_cancel = grizzly_request({'action': 'setStatus', 'status': '8', 'id': tz_id}, srv['api_key'], srv['url'])
                if "ACCESS_CANCEL" in res_cancel or "STATUS_CANCEL" in res_cancel or "NO_ACTIVATION" in res_cancel:
                    # تم إلغاؤه فوراً بنجاح في المزود
                    cursor.execute('DELETE FROM pending_cancellations WHERE tz_id = ?', (tz_id,))
                    conn.commit()
                else:
                    # في فترة الانتظار (العداد متاح خلال): نضعه في طابور الإلغاء التلقائي ليلغيه خيط الخلفية فور انتهاء العداد وتسترجع رصيدك في المزود
                    cursor.execute('INSERT OR REPLACE INTO pending_cancellations (tz_id, server_id, user_id, chat_id, cost, phone, refund_user) VALUES (?, ?, ?, ?, ?, ?, 0)',
                                   (tz_id, server_id, user_id, chat_id, cost, old_phone, 0))
                    conn.commit()
            else:
                # إذا لم تتوفر أرقام جديدة في المزود حالياً
                cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (cost, user_id))
                cursor.execute('UPDATE purchases SET status = "CANCELLED" WHERE tz_id = ?', (tz_id,))
                conn.commit()
                err_msg = "الأرقام غير متوفرة حالياً لهذه الدولة في المزود" if "NO_NUMBERS" in res else res
                try: bot.edit_message_text(f"⚠️ **تعذر جلب رقم بديل:** {err_msg}\n\n✅ تم إلغاء الطلب واسترجاع المبلغ (${cost:.2f}) إلى رصيدك كاملاً.", chat_id, message_id, parse_mode="Markdown", reply_markup=back_button())
                except: bot.send_message(chat_id, f"⚠️ **تعذر جلب رقم بديل:** {err_msg}\n\n✅ تم إلغاء الطلب واسترجاع المبلغ (${cost:.2f}) إلى رصيدك كاملاً.", parse_mode="Markdown", reply_markup=back_button())

                # إلغاء الرقم القديم من المزود في الخلفية
                res_cancel = grizzly_request({'action': 'setStatus', 'status': '8', 'id': tz_id}, srv['api_key'], srv['url'])
                if not ("ACCESS_CANCEL" in res_cancel or "STATUS_CANCEL" in res_cancel or "NO_ACTIVATION" in res_cancel):
                    cursor.execute('INSERT OR REPLACE INTO pending_cancellations (tz_id, server_id, user_id, chat_id, cost, phone, refund_user) VALUES (?, ?, ?, ?, ?, ?, 0)',
                                   (tz_id, server_id, user_id, chat_id, cost, old_phone, 0))
                    conn.commit()
        finally:
            conn.close()

    elif call.data.startswith("cancel_num_"):
        bot.answer_callback_query(call.id, "جاري إلغاء الطلب واسترجاع الرصيد فوراً...")
        parts = call.data.split("_")
        server_id, tz_id = parts[2], parts[3]
        srv = SERVERS.get(server_id)
        if not srv: srv = {'api_key': API_KEY, 'url': API_URL}

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT cost, phone, status FROM purchases WHERE tz_id = ?', (tz_id,))
            purchase = cursor.fetchone()
            if not purchase or purchase[2] != 'PENDING':
                bot.answer_callback_query(call.id, "العملية ملغاة أو مكتملة مسبقاً.", show_alert=True)
                return

            cost, phone = purchase[0], purchase[1]

            # إعادة الرصيد للمستخدم فوراً وإلغاء الطلب محلياً دون أي تأخير أو انتظار
            cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (cost, user_id))
            cursor.execute('UPDATE purchases SET status = "CANCELLED" WHERE tz_id = ?', (tz_id,))
            conn.commit()

            try:
                bot.edit_message_text(
                    f"❌ **تم إلغاء الطلب بنجاح!**\n\n📱 الرقم: `{phone}`\n💰 تمت إعادة المبلغ (${cost:.2f}) إلى رصيدك بالكامل.",
                    chat_id, message_id, parse_mode="Markdown", reply_markup=back_button()
                )
            except Exception:
                try: bot.delete_message(chat_id, message_id)
                except: pass
                bot.send_message(
                    chat_id,
                    f"❌ **تم إلغاء الطلب بنجاح!**\n\n📱 الرقم: `{phone}`\n💰 تمت إعادة المبلغ (${cost:.2f}) إلى رصيدك بالكامل.",
                    parse_mode="Markdown", reply_markup=back_button()
                )

            # طلب الإلغاء من المزود
            res_cancel = grizzly_request({'action': 'setStatus', 'status': '8', 'id': tz_id}, srv['api_key'], srv['url'])
            if "ACCESS_CANCEL" in res_cancel or "STATUS_CANCEL" in res_cancel or "NO_ACTIVATION" in res_cancel:
                cursor.execute('DELETE FROM pending_cancellations WHERE tz_id = ?', (tz_id,))
                conn.commit()
            else:
                # في حال كان في فترة عداد الدقيقتين (EARLY_CANCEL_DENIED أو BAD_STATUS):
                # يوضع في طابور pending_cancellations ليلغيه الخيط التلقائي فور انتهاء العداد لاستعادة رصيدك في المزود
                cursor.execute('INSERT OR REPLACE INTO pending_cancellations (tz_id, server_id, user_id, chat_id, cost, phone, refund_user) VALUES (?, ?, ?, ?, ?, ?, 0)',
                               (tz_id, server_id, user_id, chat_id, cost, phone, 0))
                conn.commit()
        finally:
            conn.close()

    # ==================== أقسام الرشق (SMM) ====================
    elif call.data == "smm_main":
        text = ("🚀 الرشق وشحن الألعاب والبرامج 🔭\n▫️ زيادة متابعين وتفاعلات\n▫️ شحن الألعاب المختلفة")
        try: bot.edit_message_text(text, chat_id, message_id, reply_markup=smm_main_keyboard())
        except Exception: bot.send_message(chat_id, text, reply_markup=smm_main_keyboard())

    elif call.data == "smm_servers_menu":
        text_srv = "❤️ **قسم الرشق وزيادة المتابعين**\n\nيرجى اختيار سيرفر الرشق المطلوب لتصفح الخدمات:"
        try: bot.edit_message_text(text_srv, chat_id, message_id, parse_mode="Markdown", reply_markup=smm_servers_menu_keyboard())
        except: bot.send_message(chat_id, text_srv, parse_mode="Markdown", reply_markup=smm_servers_menu_keyboard())

    elif call.data.startswith("smm_srv_"):
        server_id = call.data.replace("smm_srv_", "")
        server_name = "سيرفر الرشق 2 (الأرخص)" if server_id == "tiger" else "سيرفر الرشق 1"
        text_boost = f"توفر خدمات متابعين وإعجابات ومشاهدات بأسعار مناسبة\n🏢 **{server_name}**\n\n🧛♂️ الرجاء إختيار التطبيق / الخدمة:"
        try: bot.edit_message_text(text_boost, chat_id, message_id, parse_mode="Markdown", reply_markup=boost_keyboard(server_id))
        except: bot.send_message(chat_id, text_boost, parse_mode="Markdown", reply_markup=boost_keyboard(server_id))

    elif call.data == "games_menu":
        try: bot.edit_message_text("🎮 شحن الألعاب وبرامج بلاس 🕹️", chat_id, message_id, reply_markup=games_keyboard())
        except: bot.send_message(chat_id, "🎮 شحن الألعاب وبرامج بلاس 🕹️", reply_markup=games_keyboard())

    elif call.data.startswith("smmc_"):
        bot.answer_callback_query(call.id, "جاري جلب الخدمات...")
        parts = call.data.split("_")
        server_id, category_code = parts[1], parts[2]
        filtered_services = filter_smm_services(category_code, server_id)

        if not filtered_services:
            bot.send_message(chat_id, "❌ عذراً، لا توجد خدمات مضافة لهذا القسم حالياً في هذا السيرفر.", reply_markup=back_button())
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

        raw_name = str(selected_srv.get('name_ar') or selected_srv.get('name', 'خدمة غير محددة'))
        name = translate_text(raw_name) if not selected_srv.get('is_custom') else raw_name
        category_display = CATEGORY_TITLES.get(category_code, selected_srv.get('category', 'عام'))
        min_q = selected_srv.get('min', '10')
        max_q = selected_srv.get('max', '1000000')
        rate = float(selected_srv.get('rate', 0))

        if selected_srv.get('is_custom'):
            price_profit = rate
        else:
            profit_margin = float(get_setting('profit_margin_smm', '0.10'))
            price_profit = round(rate * (1.0 + profit_margin), 4)

        if selected_srv.get('speed'):
            speed = str(selected_srv.get('speed')).strip()
        elif "سريع" in name or "fast" in name.lower() or "فوري" in name or "instant" in name.lower():
            speed = "فورية ⚡"
        elif "بطيء" in name or "slow" in name.lower():
            speed = "هادئة ⏱️"
        else:
            speed = "سريعة 🚀"

        if "ممتاز" in name or "super" in name.lower() or "vip" in name.lower() or "حقيقي" in name:
            quality = "ممتازة ⭐️"
        elif "عالي" in name or "hq" in name.lower() or "جودة" in name or "high" in name.lower():
            quality = "عالية ✅"
        elif "انخفاض" in name or "drop" in name.lower():
            quality = "جيدة 🌟"
        else:
            quality = "ممتازة ⭐️"

        # تحديد الضمان بدقة: إذا كانت الخدمة مخصصة أو لها وصف مسجل نأخذه مباشرة
        if selected_srv.get('description'):
            guarantee = str(selected_srv.get('description')).strip()
        elif any(w in name for w in ["بدون ضمان", "لا يوجد ضمان", "بدون تعويض", "بدون اعادة", "no refill", "no guarantee"]):
            guarantee = "بدون ضمان ⚠️"
        elif any(w in name for w in ["365", "سنة", "1 year"]):
            guarantee = "ضمان 365 يوم ♻️"
        elif "90" in name:
            guarantee = "ضمان 90 يوم ♻️"
        elif "60" in name:
            guarantee = "ضمان 60 يوم ♻️"
        elif any(w in name for w in ["30", "شهر", "30d"]):
            guarantee = "ضمان 30 يوم ♻️"
        elif any(w in name for w in ["مدى الحياة", "lifetime"]):
            guarantee = "ضمان مدى الحياة ♾️"
        elif any(w in name.lower() for w in ["refill", "تعبئة", "تعويض", "ضمان"]):
            guarantee = "ضمان تعويض ♻️"
        else:
            guarantee = "بدون ضمان ⚠️"

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

        raw_name = str(selected_srv.get('name_ar') or selected_srv.get('name', 'خدمة'))
        name = translate_text(raw_name) if not selected_srv.get('is_custom') else raw_name
        category_display = CATEGORY_TITLES.get(category_code, 'عام')
        min_q = int(selected_srv.get('min', 10))
        max_q = int(selected_srv.get('max', 1000000))
        rate = float(selected_srv.get('rate', 0))

        if selected_srv.get('is_custom'):
            price_1k = rate
        else:
            profit_margin = float(get_setting('profit_margin_smm', '0.10'))
            price_1k = round(rate * (1.0 + profit_margin), 4)

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
        try: bot.edit_message_text(msg_text, chat_id, message_id, reply_markup=smm_cancel_link_keyboard(service_id, category_code, server_id))
        except: bot.send_message(chat_id, msg_text, reply_markup=smm_cancel_link_keyboard(service_id, category_code, server_id))

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
            row = cursor.fetchone()
            balance = row[0] if row else 0.0

            if balance < total_cost:
                bot.answer_callback_query(call.id, "❌ رصيدك غير كافٍ لإتمام الطلب!", show_alert=True)
                return

            # خصم الرصيد فوراً وتحديث المصروفات وعدد الطلبات
            cursor.execute('''
                UPDATE users 
                SET balance = MAX(0.0, balance - ?), 
                    spent_balance = spent_balance + ?, 
                    orders_count = orders_count + 1,
                    last_active = CURRENT_TIMESTAMP 
                WHERE user_id = ?
            ''', (total_cost, total_cost, user_id))
            conn.commit()

            order_response = smm_request(server_id, 'add', service=service_id, link=link, quantity=qty)
            if order_response and 'order' in order_response:
                order_id = str(order_response['order'])
                cursor.execute('''
                    INSERT INTO smm_orders (order_id, user_id, service_id, service_name, category_name, link, quantity, cost, status, server_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?)
                ''', (order_id, user_id, service_id, service_name, category_name, link, qty, total_cost, str(server_id)))
                conn.commit()

                # جلب الرصيد المتبقي بدقة متناهية
                cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
                bal_row = cursor.fetchone()
                rem_bal = bal_row[0] if bal_row else 0.0

                # إشعار قناة التفعيلات والطلبات بالرابط المحمي المشفر
                notify_smm_activation(order_id, service_name, category_name, qty, total_cost, user_id, link=link)

                success_msg = (
                    f"✅ - تم تنفيذ الطلب بنجاح !\n\n"
                    f"♻️ : الخدمة: {service_name}\n"
                    f"📦 : الكمية: {qty}\n"
                    f"💰 : السعر الكلي: ${total_cost:.5f}\n"
                    f"💳 : رصيدك المتبقي: ${rem_bal:.4f}\n"
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
                # إذا حدث خطأ من المزود نعيد الرصيد فوراً لحساب العميل
                cursor.execute('''
                    UPDATE users 
                    SET balance = balance + ?, 
                        spent_balance = MAX(0.0, spent_balance - ?), 
                        orders_count = MAX(0, orders_count - 1) 
                    WHERE user_id = ?
                ''', (total_cost, total_cost, user_id))
                conn.commit()
                err = order_response.get('error', 'فشل الإرسال') if order_response else 'خطأ اتصال بالمزود'
                bot.edit_message_text(f"❌ خطأ من المزود: {err}\nلم يتم خصم أي رصيد من حسابك.", chat_id, message_id, reply_markup=back_button())
        finally:
            conn.close()
            if user_id in USER_STEPS: del USER_STEPS[user_id]

    elif call.data.startswith("smm_stat_"):
        order_id = call.data.split("_")[2]
        bot.answer_callback_query(call.id, "جاري فحص وتحديث حالة الطلب...")
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT service_name, category_name, link, quantity, cost, status, server_id FROM smm_orders WHERE order_id = ?', (order_id,))
            order_data = cursor.fetchone()
        finally:
            conn.close()

        if not order_data:
            bot.answer_callback_query(call.id, "❌ لم يتم العثور على الطلب.", show_alert=True)
            return

        srv_name, cat_name, link, qty, cost, db_status, order_srv = order_data
        target_server = str(order_srv) if order_srv else 'tiger'
        
        # فحص الحالة من السيرفر المسجل
        status_res = smm_request(target_server, 'status', order=order_id)
        if not status_res or 'error' in status_res:
            # تجربة السيرفر البديل إذا كان هناك خطأ في معرف السيرفر
            alt_srv = '2' if target_server == 'tiger' else 'tiger'
            alt_res = smm_request(alt_srv, 'status', order=order_id)
            if alt_res and 'error' not in alt_res:
                status_res = alt_res
                target_server = alt_srv
                conn = get_db()
                conn.execute('UPDATE smm_orders SET server_id = ? WHERE order_id = ?', (alt_srv, order_id))
                conn.commit()
                conn.close()

        api_status = status_res.get('status', db_status) if status_res else db_status
        remains = status_res.get('remains', '0') if status_res else '0'
        try: remains_num = int(remains)
        except: remains_num = 0

        completed_num = max(0, qty - remains_num)
        status_str = str(api_status).strip()
        is_completed = (status_str.lower() in ['completed', 'مكتمل']) or (remains_num == 0 and status_str.lower() not in ['canceled', 'cancelled', 'partial', 'fail'])

        date_str = get_arabic_datetime()
        if is_completed:
            completed_num = qty
            remains_num = 0
            conn = get_db()
            conn.execute('UPDATE smm_orders SET status = "Completed" WHERE order_id = ?', (order_id,))
            conn.commit()
            conn.close()

            done_msg = (
                f"✅ : تم اكتمال طلبك بنجاح 💙\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📦 : رقم الطلب : #{order_id}\n"
                f"📁 : القسم : {cat_name}\n"
                f"🛒 : الخدمة : {srv_name}\n"
                f"🔗 : الرابط : [{link}]\n"
                f"🔢 : الكمية : {qty}\n"
                f"📊 : تم التنفيذ : {qty}\n"
                f"⏳ : المتبقي : 0\n"
                f"📌 : الحالة : مكتمل ✅\n"
                f"⏰ : الوقت : {date_str}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🎉 : تم تنفيذ طلبك بالكامل بنجاح\n"
                f"💙 : شكراً لاستخدامك خدماتنا"
            )
            try:
                bot.edit_message_text(done_msg, chat_id, message_id, reply_markup=back_button())
                bot.answer_callback_query(call.id, "🎉 مبروك! تم اكتمال تنفيذ طلبك بنجاح!")
            except Exception as e:
                if "message is not modified" in str(e).lower():
                    bot.answer_callback_query(call.id, "✅ تم الفحص: طلبك مكتمل بالفعل!")
        else:
            status_display = "في الانتظار / قيد التنفيذ 🔄"
            if status_str.lower() in ['canceled', 'cancelled', 'ملغي']:
                status_display = "ملغي من المزود ❌"
            elif status_str.lower() in ['partial', 'جزئي']:
                status_display = "مكتمل جزئياً ⚠️"

            update_msg = (
                f"📊 - تفاصيل حالة الطلب الحالية -\n\n"
                f"🧾 : رقم الطلب: #{order_id}\n"
                f"🛒 : الخدمة: {srv_name}\n"
                f"🔗 : الرابط: [{link}]\n"
                f"🏷️ : العدد المطلوب: {qty}\n"
                f"📊 : العدد المكتمل: {completed_num}\n"
                f"🅿️ : العدد المتبقي: {remains_num}\n"
                f"🔘 : الحاله: {status_display}\n"
                f"⏰ : آخر فحص: {date_str}"
            )
            markup = smm_order_status_keyboard(order_id, "", qty, cost, link, cat_name, srv_name)
            try:
                bot.edit_message_text(update_msg, chat_id, message_id, reply_markup=markup)
                bot.answer_callback_query(call.id, "🔄 تم فحص وتحديث حالة الطلب!")
            except Exception as e:
                if "message is not modified" in str(e).lower():
                    bot.answer_callback_query(call.id, "ℹ️ تم الفحص: لا يوجد تغيير جديد في حالة الطلب بعد.")

    elif call.data == "free_ruble":
        try: bot.answer_callback_query(call.id)
        except: pass

        if not is_section_enabled('free'):
            bot.answer_callback_query(call.id, "⚠️ قسم الأرباح معطل حالياً من قبل الإدارة.", show_alert=True)
            return
        
        bot_uname = "NUM_SMBOT"
        try:
            me = bot.get_me()
            if me and me.username: bot_uname = me.username
        except: pass

        ref_link = f"https://t.me/{bot_uname}?start={user_id}"
        rew = float(get_setting('reward_per_invite', '0.05'))
        pct = float(get_setting('referral_purchase_percent', '5.0'))
        
        ref_msg = (
            "اربح رصيد مجانا 🎁\n\n"
            "يمكنك كسب رصيد مجاني عن طريق مشاركة رابط الدعوة الخاص بك مع اصدقائك في المجموعات و القنوات\n\n"
            f"- لكل شخص يقوم بالدخول الى البوت ستحصل على ( {rew:g}$ )\n"
            f"- ستحصل على نسبة ( {pct:g}% ) من كل عملية شحن أو شراء يقوم بها اصدقائك مدى الحياة\n\n"
            f"🔗 رابط الدعوة الخاص بك:\n<code>{ref_link}</code>"
        )
        try: bot.edit_message_text(ref_msg, chat_id, message_id, parse_mode="HTML", reply_markup=free_balance_keyboard(user_id, bot_uname))
        except: bot.send_message(chat_id, ref_msg, parse_mode="HTML", reply_markup=free_balance_keyboard(user_id, bot_uname))
        return

    elif call.data == "ref_team_stats":
        try: bot.answer_callback_query(call.id)
        except: pass

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT referrals_count, referrals_earnings FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            ref_cnt = row[0] if row and row[0] is not None else 0
            ref_earn = row[1] if row and row[1] is not None else 0.0

            cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by = ? AND spent_balance > 0", (user_id,))
            buyers_row = cursor.fetchone()
            buyers_cnt = buyers_row[0] if buyers_row and buyers_row[0] is not None else 0
        finally:
            conn.close()

        stats_msg = (
            "📊 إحصائيات فريقك:\n\n"
            f"👥 عدد الاعضاء في فريقك: {ref_cnt}\n"
            f"🛒 عدد المشتريين في فريقك: {buyers_cnt}\n"
            f"💰 اجمالي ارباحك من الفريق: ${ref_earn:.2f}"
        )
        try: bot.edit_message_text(stats_msg, chat_id, message_id, parse_mode="HTML", reply_markup=free_balance_team_keyboard())
        except: bot.send_message(chat_id, stats_msg, parse_mode="HTML", reply_markup=free_balance_team_keyboard())
        return

    elif call.data == "ref_my_earnings":
        try: bot.answer_callback_query(call.id)
        except: pass

        min_w = float(get_setting('min_invite_withdraw', '0.5'))
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT referrals_earnings FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            ref_earn = row[0] if row and row[0] is not None else 0.0
        finally:
            conn.close()

        can_w = ref_earn >= min_w and ref_earn > 0
        earnings_msg = (
            "💸 <b>أرباحك وسحب الرصيد:</b>\n\n"
            f"💰 <b>أرباحك الحالية المتاحة:</b> <code>${ref_earn:.2f}</code>\n"
            f"🏧 <b>الحد الأدنى للتحويل إلى رصيد البوت:</b> <code>${min_w:.2f}</code>\n\n"
            "💡 عند وصول أرباحك للحد الأدنى، يمكنك تحويلها بضغطة زر واحدة إلى رصيدك الأساسي واستخدامها في شراء الأرقام والخدمات فوراً!"
        )
        try: bot.edit_message_text(earnings_msg, chat_id, message_id, parse_mode="HTML", reply_markup=free_balance_earnings_keyboard(can_w, ref_earn))
        except: bot.send_message(chat_id, earnings_msg, parse_mode="HTML", reply_markup=free_balance_earnings_keyboard(can_w, ref_earn))
        return

    elif call.data == "withdraw_ref_earnings":
        min_w = float(get_setting('min_invite_withdraw', '0.5'))
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT referrals_earnings FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            ref_earn = row[0] if row and row[0] is not None else 0.0

            if ref_earn < min_w or ref_earn <= 0:
                bot.answer_callback_query(call.id, f"❌ الحد الأدنى لتحويل الأرباح لرصيدك هو ${min_w:.2f} (أرباحك الحالية ${ref_earn:.2f})", show_alert=True)
                return

            cursor.execute("UPDATE users SET balance = balance + ?, referrals_earnings = 0.0 WHERE user_id = ?", (ref_earn, user_id))
            conn.commit()
            bot.answer_callback_query(call.id, f"✅ تم تحويل ${ref_earn:.2f} إلى رصيدك الأساسي بنجاح!", show_alert=True)
            bot.send_message(chat_id, f"🎉 <b>تم تحويل أرباحك إلى رصيدك بنجاح!</b>\n\n💵 تم إضافة <code>${ref_earn:.2f}</code> إلى رصيدك الأساسي في البوت.\n💰 يمكنك الآن استخدامها لشراء الأرقام والحسابات والخدمات فوراً.", parse_mode="HTML", reply_markup=back_button())
        finally:
            conn.close()
        return

    elif call.data == "ai_landing":
        bot.edit_message_text("🤖 قسم خدمات الذكاء الاصطناعي\n\nاطرح سؤالك مباشرة في المحادثة وسيجيبك البوت.", chat_id, message_id, reply_markup=back_button())

    elif call.data == "best_selling":
        bot.edit_message_text("🔥 أكثر السيرفرات طلباً متوفرة في القائمة الرئيسية.", chat_id, message_id, reply_markup=back_button())

    elif call.data == "most_available":
        bot.edit_message_text("🎲 الأرقام الأكثر توفراً: روسيا، نيجيريا، أمريكا، وأوكرانيا.", chat_id, message_id, reply_markup=back_button())

    elif call.data == "support":
        sup1 = get_setting('support_admin_1', '@Num_s7').strip()
        sup2 = get_setting('support_admin_2', '@Support_SMS7').strip()
        msg = (
            "🎧 <b>قسم الدعم الفني والمساعدة:</b>\n\n"
            "إذا واجهتك أي مشكلة أو كان لديك استفسار، يسعدنا تواصلك معنا مباشرة عبر المعرفات الرسمية التالية:\n\n"
            f"1️⃣ <b>الدعم الفني الأول:</b> <code>{sup1}</code>\n"
        )
        if sup2 and sup2 != sup1:
            msg += f"2️⃣ <b>الدعم الفني الثاني:</b> <code>{sup2}</code>\n"
        msg += "\n💡 اضغط على الأزرار أدناه للتحدث مباشرة مع الدعم الفني:"
        try:
            bot.edit_message_text(msg, chat_id, message_id, parse_mode="HTML", reply_markup=user_support_keyboard())
        except Exception:
            try:
                bot.send_message(chat_id, msg, parse_mode="HTML", reply_markup=user_support_keyboard())
                try: bot.delete_message(chat_id, message_id)
                except: pass
            except:
                bot.send_message(chat_id, msg, reply_markup=user_support_keyboard())

    elif call.data == "purchase_stats":
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM purchases")
            p_cnt = cursor.fetchone()[0] or 0
            cursor.execute("SELECT COUNT(*) FROM smm_orders")
            s_cnt = cursor.fetchone()[0] or 0
            cursor.execute("SELECT COUNT(*) FROM aged_stock WHERE is_sold = 1")
            a_cnt = cursor.fetchone()[0] or 0
            cursor.execute("SELECT COUNT(*) FROM users")
            u_cnt = cursor.fetchone()[0] or 0
        finally:
            conn.close()

        total_orders = p_cnt + s_cnt + a_cnt
        ch_ord = get_setting('channel_orders_url', CHANNEL_ORDERS_URL)
        update_time = get_arabic_datetime()

        stats_text = (
            "📊 <b>إحصائيات التفعيلات والعمليات الناجحة في البوت:</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ <b>إجمالي العمليات المنفذة:</b> <code>{total_orders}</code> عملية\n"
            f"📱 <b>أرقام وتفعيلات مكتملة:</b> <code>{p_cnt}</code> رقم\n"
            f"🚀 <b>طلبات رشق نفذت:</b> <code>{s_cnt}</code> طلب\n"
            f"📦 <b>حسابات جاهزة تم تسليمها:</b> <code>{a_cnt}</code> حساب\n"
            f"👥 <b>إجمالي مستخدمي البوت:</b> <code>{u_cnt}</code> مستخدم\n"
            f"🕒 <b>آخر تحديث مباشر:</b> <code>{update_time}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💡 يتم نشر وتوثيق كافة التفعيلات والطلبات أولاً بأول في قناة التفعيلات والطلبات الرسمية."
        )
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🛍️ زيارة قناة التفعيلات والطلبات", url=ch_ord))
        markup.row(InlineKeyboardButton("🔄 تحديث الإحصائيات", callback_data="purchase_stats"))
        markup.row(InlineKeyboardButton("🔙 رجوع", callback_data="back_main"))
        try:
            bot.edit_message_text(stats_text, chat_id, message_id, parse_mode="HTML", reply_markup=markup)
            try: bot.answer_callback_query(call.id, "✅ تم تحديث الإحصائيات فورياً!")
            except: pass
        except Exception:
            try: bot.answer_callback_query(call.id, "✅ الإحصائيات محدثة بالفعل بأحدث الأرقام الحية!")
            except: pass
        return

    elif call.data == "my_account":
        user_data = get_or_create_user(user_id, call.from_user.first_name)
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT balance, spent_balance, orders_count FROM users WHERE user_id = ?', (user_id,))
            urow = cursor.fetchone()
            balance = urow[0] if urow and urow[0] is not None else 0.0
            spent = urow[1] if urow and urow[1] is not None else 0.0
            orders_c = urow[2] if urow and urow[2] is not None else 0
        finally:
            conn.close()

        msg = (
            f"👤 <b>معلومات حسابك ورصيدك:</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 <b>الرقم التعريفي (ID)</b> : <code>{user_id}</code>\n"
            f"💰 <b>الرصيد المتاح</b> : <b>${balance:.4f}</b>\n"
            f"💸 <b>إجمالي المصروفات</b> : <b>${spent:.4f}</b>\n"
            f"📦 <b>عدد الطلبات</b> : <b>{orders_c}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        try: bot.edit_message_text(msg, chat_id, message_id, parse_mode="HTML", reply_markup=back_button())
        except: bot.send_message(chat_id, msg, parse_mode="HTML", reply_markup=back_button())

# ==================== معالجة رفع واستعادة قاعدة البيانات عبر التلغرام ====================
@bot.message_handler(content_types=['document'])
def handle_admin_db_document(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        return
    doc = message.document
    if not doc:
        return
    file_name = (doc.file_name or "").lower()

    if file_name.endswith('.json') or USER_STEPS.get(user_id, {}).get('step') == 'ADM_IMPORT_SMM_JSON':
        wait_msg = bot.send_message(message.chat.id, "⏳ جاري قراءة ملف خدمات الرشق واسترجاعها...")
        try:
            file_info = bot.get_file(doc.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            content = downloaded_file.decode('utf-8')
            count = import_custom_smm_services_json(content)
            USER_STEPS.pop(user_id, None)
            try: bot.delete_message(message.chat.id, wait_msg.message_id)
            except: pass
            if count > 0:
                bot.send_message(
                    message.chat.id,
                    f"🎉 <b>تم بنجاح استرجاع خدمات الرشق!</b>\n\n▫️ <b>عدد الخدمات المسترجعة</b> : <code>{count}</code> خدمة\n✅ تم تفعيلها فوراً في البوت وهي جاهزة للعملاء الآن!",
                    parse_mode="HTML",
                    reply_markup=admin_smm_custom_keyboard()
                )
            else:
                bot.send_message(
                    message.chat.id,
                    "❌ تعذر استيراد الخدمات. تأكد من أن الملف هو ملف JSON صالح تم تصديره من البوت.",
                    reply_markup=admin_smm_custom_keyboard()
                )
        except Exception as e:
            try: bot.delete_message(message.chat.id, wait_msg.message_id)
            except: pass
            bot.send_message(message.chat.id, f"❌ حدث خطأ أثناء معالجة ملف الخدمات: {e}", reply_markup=admin_smm_custom_keyboard())
        return

    if not (file_name.endswith('.db') or file_name.endswith('.sqlite') or file_name.endswith('.sqlite3')):
        if USER_STEPS.get(user_id, {}).get('step') == 'WAITING_DB_RESTORE_FILE':
            bot.send_message(message.chat.id, "❌ الملف المرسل ليس ملف قاعدة بيانات (.db). يرجى إرسال ملف قاعدة البيانات.", reply_markup=admin_back_button())
        return

    wait_msg = bot.send_message(message.chat.id, "⏳ جاري تنزيل وفحص قاعدة البيانات واسترجاع البيانات...")
    try:
        file_info = bot.get_file(doc.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        temp_path = os.path.join(os.path.dirname(DB_FILE), f"temp_upload_{int(time.time())}.db")
        with open(temp_path, 'wb') as f:
            f.write(downloaded_file)

        success, res_msg = restore_database_from_uploaded_file(temp_path)
        if os.path.exists(temp_path):
            try: os.remove(temp_path)
            except: pass

        USER_STEPS.pop(user_id, None)
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        bot.send_message(message.chat.id, res_msg, parse_mode="HTML", reply_markup=admin_back_button())
    except Exception as e:
        try: bot.delete_message(message.chat.id, wait_msg.message_id)
        except: pass
        bot.send_message(message.chat.id, f"❌ حدث خطأ أثناء معالجة الملف: {e}", reply_markup=admin_back_button())

# ==================== معالجة الرسائل والخطوات ====================
@bot.message_handler(func=lambda msg: msg.from_user.id in USER_STEPS)
def handle_user_steps(message):
    user_id = message.from_user.id
    step_data = USER_STEPS.get(user_id, {})
    step = step_data.get('step')

    if step == "CAPTCHA_VERIFY":
        expected = step_data.get('code', '')
        ref_id = step_data.get('referrer_id')
        name = step_data.get('name', message.from_user.first_name or "المستخدم")
        username = step_data.get('username', f"@{message.from_user.username}" if message.from_user.username else "لا يوجد")
        
        if message.text.strip() == str(expected).strip():
            del USER_STEPS[user_id]
            set_user_verified(user_id, 1)
            conn = get_db()
            cursor = conn.cursor()
            try:
                cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
                user = cursor.fetchone()
                if not user:
                    r_id = ref_id if (ref_id and ref_id != user_id) else 0
                    cursor.execute('''INSERT INTO users 
                        (user_id, name, username, balance, spent_balance, orders_count, ai_balance, is_banned, is_agent, agent_discount, referred_by, referrals_count, referrals_earnings, is_verified) 
                        VALUES (?, ?, ?, 0.0, 0.0, 0, 5, 0, 0, 0.0, ?, 0, 0.0, 1)''', (user_id, name, username, r_id))
                    conn.commit()
                    if r_id != 0:
                        rew = float(get_setting('reward_per_invite', '0.05'))
                        cursor.execute('UPDATE users SET referrals_count = referrals_count + 1, referrals_earnings = referrals_earnings + ? WHERE user_id = ?', (rew, r_id))
                        conn.commit()
                        try:
                            bot.send_message(
                                r_id, 
                                f"🎉 <b>انضم عضو جديد إلى فريقك عبر رابطك الخاص!</b>\n"
                                f"🎁 تمت إضافة مكافأة دعوة <code>${rew:.2f}</code> إلى محفظة أرباحك.", 
                                parse_mode="HTML"
                            )
                        except: pass
                else:
                    cursor.execute('UPDATE users SET name = ?, username = ?, is_verified = 1, last_active = CURRENT_TIMESTAMP WHERE user_id = ?', (name, username, user_id))
                    conn.commit()
            except sqlite3.OperationalError as op_err:
                if "no such column" in str(op_err).lower():
                    ensure_user_columns(conn)
                    cursor.execute('UPDATE users SET name = ?, username = ?, last_active = CURRENT_TIMESTAMP WHERE user_id = ?', (name, username, user_id))
                    conn.commit()
            finally:
                conn.close()

            bot.send_message(message.chat.id, "✅ <b>تم التحقق الأمني بنجاح!</b> أهلاً بك في البوت.", parse_mode="HTML")
            user_data = get_or_create_user(user_id, name, username)
            try: balance = float(user_data[3]) if len(user_data) > 3 and user_data[3] is not None else float(user_data[2])
            except: balance = 0.0

            text = get_main_welcome_text(user_id, name, username, balance)
            bot.send_message(message.chat.id, text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=main_keyboard(user_id))
            return
        else:
            import random
            new_code = str(random.randint(11111, 99999))
            USER_STEPS[user_id]['code'] = new_code
            bot.send_message(message.chat.id, f"❌ <b>الرقم غير صحيح!</b>\n\nاكتب الرقم التالي للتحقق: <code>{new_code}</code>", parse_mode="HTML")
            return

    elif step == "waiting_binance_amount":
        try:
            amount = float(message.text.strip())
            if amount <= 0: raise ValueError()
            amount_str = f"{int(amount)}" if amount.is_integer() else f"{amount:g}"
            binance_addr = get_binance_pay_id()
            USER_STEPS[user_id] = {"step": "binance_details", "amount": amount, "amount_str": amount_str}

            binance_details = (
                "🟡 <b>تفاصيل الدفع عبر Binance Pay</b>\n\n"
                f"💰 <b>المبلغ المطلوب:</b> {amount_str} USDT\n\n"
                "📍 <b>عنوان المحفظة:</b>\n"
                f"<code>{binance_addr}</code>\n\n"
                "📋 <b>الخطوات:</b>\n"
                "1️⃣ حول المبلغ المطلوب إلى العنوان أعلاه.\n"
                "2️⃣ تأكد من إرسال المبلغ نفسه الذي اخترته.\n"
                "3️⃣ بعد الانتهاء، انسخ TXID (رقم المعاملة) وأرسله هنا.\n\n"
                "⚠️ <b>ملاحظة:</b> سيتم التحقق من المعاملة تلقائياً عبر Binance API."
            )
            bot.send_message(message.chat.id, binance_details, reply_markup=binance_details_keyboard(), parse_mode="HTML")
        except:
            bot.send_message(message.chat.id, "❌ يرجى إرسال رقم صحيح للمبلغ (مثال: 10 أو 4):")
        return

    elif step == "waiting_binance_txid":
        txid = message.text.strip()
        expected_amount = float(step_data.get("amount", 0))
        amount_str = step_data.get("amount_str", f"{int(expected_amount)}" if expected_amount.is_integer() else f"{expected_amount:g}")
        wait_msg = bot.send_message(message.chat.id, "🔄 جاري التحقق من المعاملة...\nيرجى الانتظار لحظة.")
        is_valid, reason = verify_binance_txid(txid, expected_amount)
        try:
            bot.delete_message(message.chat.id, wait_msg.message_id)
        except Exception:
            pass

        if is_valid:
            record_used_txid(txid, user_id, expected_amount)
            conn = get_db()
            cursor = conn.cursor()
            new_balance = expected_amount
            try:
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (expected_amount, user_id))
                cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                if row:
                    new_balance = float(row[0])
                conn.commit()
            finally:
                conn.close()
            USER_STEPS.pop(user_id, None)

            success_text = (
                "✅ <b>تم تأكيد الدفع بنجاح!</b>\n\n"
                f"💰 <b>المبلغ المضاف:</b> {amount_str} USDT\n"
                f"💵 <b>رصيدك الحالي:</b> ${new_balance:.2f}\n"
                f"🔖 <b>رقم المعاملة:</b> <code>{txid}</code>\n\n"
                "شكراً لاستخدامك خدماتنا!"
            )
            markup_main = InlineKeyboardMarkup()
            markup_main.add(InlineKeyboardButton("🏡 القائمة الرئيسية", callback_data="back_main"))
            bot.send_message(message.chat.id, success_text, reply_markup=markup_main, parse_mode="HTML")

            # إرسال إشعار فوري لقناة التفعيلات والطلبات
            try:
                txid_masked = f"{txid[:4]}••••{txid[-4:]}" if len(txid) >= 8 else "••••"
                ch_msg = (
                    "⚡ <b>عملية شحن رصيد ناجحة (Binance Pay)</b>\n\n"
                    f"👤 <b>العميل:</b> <code>{mask_user(user_id)}</code>\n"
                    f"💰 <b>المبلغ:</b> <b>${expected_amount:.2f} USDT</b>\n"
                    f"🔖 <b>المعاملة:</b> <code>{txid_masked}</code>\n"
                    f"⏰ <b>الوقت:</b> <code>{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}</code>\n"
                    "✅ <b>الحالة:</b> مكتملة وتلقائية"
                )
                send_to_channel_safe(ch_msg)
            except Exception as e:
                print(f"Error channel notify binance: {e}")
            return
        else:
            if reason == "used":
                fail_text = (
                    "❌ <b>فشل التحقق من المعاملة</b>\n\n"
                    "⚠️ رقم المعاملة هذا (TXID) تم استخدامه مسبقاً في البوت ولا يمكن استخدامه مرة أخرى.\n\n"
                    "<b>يرجى التأكد من:</b>\n"
                    "• صحة TXID الخاص بالعملية الجديدة\n"
                    "• عدم تكرار نفس رقم المعاملة\n"
                    "• انتظار دقيقة ثم المحاولة مرة أخرى"
                )
            else:
                fail_text = (
                    "❌ <b>فشل التحقق من المعاملة</b>\n\n"
                    "لم يتم العثور على المعاملة، تأكد من صحة TXID وانتظر دقيقة ثم حاول مرة أخرى\n\n"
                    "<b>يرجى التأكد من:</b>\n"
                    "• صحة TXID\n"
                    "• أن المبلغ المرسل مطابق للمبلغ المطلوب\n"
                    "• انتظار دقيقة ثم المحاولة مرة أخرى"
                )
            bot.send_message(message.chat.id, fail_text, reply_markup=binance_txid_fail_keyboard(), parse_mode="HTML")
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
                    bot.send_message(message.chat.id, f"❌ رصيدك غير كافٍ!\nرصيدك: ${format_money(sender_bal)}")
                    return
                cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_id))
                conn.commit()
            finally:
                conn.close()
            del USER_STEPS[user_id]
            bot.send_message(message.chat.id, f"✅ تم تحويل ${format_money(amount)} بنجاح إلى `{target_id}`.", parse_mode="Markdown", reply_markup=back_button())
            try: bot.send_message(target_id, f"🎉 وصلك تحويل رصيد بقيمة ${format_money(amount)}!")
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
                bot.send_message(message.chat.id, f"✅ تم شحن ${format_money(amt)} لحسابك كأدمن بنجاح!\n💰 رصيدك الحالي: ${format_money(new_bal)}", reply_markup=admin_back_button())
            except:
                bot.send_message(message.chat.id, "❌ يرجى كتابة مبلغ صحيح بالأرقام.", reply_markup=admin_back_button())
            return

        # 1. ضبط نسب الأرباح
        elif step == 'ADM_SET_PROFIT_NUMBERS':
            del USER_STEPS[user_id]
            try:
                val = float(message.text.strip())
                set_setting('profit_numbers', str(val))
                bot.send_message(message.chat.id, f"✅ تم تحديث نسبة ربح الأرقام إلى `{val}%` بنجاح!", parse_mode="Markdown", reply_markup=admin_back_button())
            except:
                bot.send_message(message.chat.id, "❌ يرجى إرسال رقم صحيح للنسبة المئوية.", reply_markup=admin_back_button())
            return

        elif step == 'ADM_SET_PROFIT_READY':
            del USER_STEPS[user_id]
            try:
                val = float(message.text.strip())
                set_setting('profit_ready_accounts', str(val))
                bot.send_message(message.chat.id, f"✅ تم تحديث نسبة ربح الحسابات الجاهزة إلى `{val}%` بنجاح!", parse_mode="Markdown", reply_markup=admin_back_button())
            except:
                bot.send_message(message.chat.id, "❌ يرجى إرسال رقم صحيح للنسبة المئوية.", reply_markup=admin_back_button())
            return

        elif step == 'ADM_SET_PROFIT_SMM':
            del USER_STEPS[user_id]
            try:
                val = float(message.text.strip())
                set_setting('profit_smm', str(val))
                bot.send_message(message.chat.id, f"✅ تم تحديث نسبة ربح خدمات الرشق إلى `{val}%` بنجاح!", parse_mode="Markdown", reply_markup=admin_back_button())
            except:
                bot.send_message(message.chat.id, "❌ يرجى إرسال رقم صحيح للنسبة المئوية.", reply_markup=admin_back_button())
            return

        # 2. تعديل وسائل الدفع
        elif step == 'ADM_PAY_EDIT_ACC':
            m_id = step_data.get('method_id')
            del USER_STEPS[user_id]
            val = message.text.strip()
            update_payment_method_db(m_id, acc=val)
            bot.send_message(message.chat.id, f"✅ تم تحديث رقم الحساب / المحفظة بنجاح إلى:\n`{val}`", parse_mode="Markdown", reply_markup=admin_back_button())
            return

        elif step == 'ADM_PAY_EDIT_RATE':
            m_id = step_data.get('method_id')
            del USER_STEPS[user_id]
            val = message.text.strip()
            update_payment_method_db(m_id, rate=val)
            bot.send_message(message.chat.id, f"✅ تم تحديث سعر الصرف بنجاح إلى: `{val}`", parse_mode="Markdown", reply_markup=admin_back_button())
            return

        elif step == 'ADM_PAY_EDIT_MIN':
            m_id = step_data.get('method_id')
            del USER_STEPS[user_id]
            val = message.text.strip()
            update_payment_method_db(m_id, min_val=val)
            bot.send_message(message.chat.id, f"✅ تم تحديث الحد الأدنى للشحن بنجاح إلى: `{val}`", parse_mode="Markdown", reply_markup=admin_back_button())
            return

        elif step == 'ADM_ADD_PAY_1':
            name = message.text.strip()
            USER_STEPS[user_id] = {'step': 'ADM_ADD_PAY_2', 'name': name}
            bot.send_message(message.chat.id, f"➕ الآن أرسل تفاصيل وسيلة ({name}) بالشكل التالي:\n`رقم_الحساب | سعر_الصرف | الحد_الأدنى`\n\nمثال:\n`777000000 | 1$ = 540 ريال | 1000 ريال`", parse_mode="Markdown", reply_markup=admin_back_button())
            return

        elif step == 'ADM_ADD_PAY_2':
            name = step_data.get('name')
            del USER_STEPS[user_id]
            parts = [p.strip() for p in message.text.split("|")]
            if len(parts) >= 3:
                acc, rate, min_v = parts[0], parts[1], parts[2]
                m_id = f"custom_{int(time.time())}"
                update_payment_method_db(m_id, name=name, acc=acc, rate=rate, min_val=min_v)
                bot.send_message(message.chat.id, f"✅ تم إضافة وسيلة الدفع الجديدة ({name}) بنجاح!", reply_markup=admin_back_button())
            else:
                bot.send_message(message.chat.id, "❌ صيغة غير صحيحة، يرجى الفصل بعلامة `|`", reply_markup=admin_back_button())
            return

        # 3. إدارة المزودين
        elif step == 'ADM_PRV_EDIT_KEY':
            p_id = step_data.get('provider_id')
            del USER_STEPS[user_id]
            key_val = message.text.strip()
            update_provider_api_key_db(p_id, key_val)
            if p_id in SERVERS:
                SERVERS[p_id]['api_key'] = key_val
            bot.send_message(message.chat.id, f"✅ تم تحديث مفتاح API للمزود `{p_id}` بنجاح!", parse_mode="Markdown", reply_markup=admin_back_button())
            return

        elif step == 'ADM_ADD_PRV_1':
            name = message.text.strip()
            USER_STEPS[user_id] = {'step': 'ADM_ADD_PRV_2', 'name': name}
            bot.send_message(message.chat.id, "🌐 أرسل تفاصيل المزود بالشكل التالي:\n`المعرف القسم النوع الرابط المفتاح`\n\nالقسم: `numbers` أو `ready_accounts` أو `smm`\nالنوع: `grizzly` أو `sim5` أو `tg_leon` أو `smm`\n\nمثال:\n`myserver numbers grizzly https://api.myserver.com/stubs/handler_api.php MY_KEY_123`", parse_mode="Markdown", reply_markup=admin_back_button())
            return

        elif step == 'ADM_ADD_PRV_2':
            name = step_data.get('name')
            del USER_STEPS[user_id]
            parts = message.text.strip().split()
            if len(parts) >= 5:
                p_id, cat, p_type, url, key = parts[0], parts[1], parts[2], parts[3], parts[4]
                add_provider_db(p_id, name, cat, p_type, api_key=key, url=url)
                if cat == 'numbers':
                    SERVERS[p_id] = {'name': name, 'api_key': key, 'url': url}
                bot.send_message(message.chat.id, f"✅ تم إضافة المزود الجديد `{name}` بنجاح!", parse_mode="Markdown", reply_markup=admin_back_button())
            else:
                bot.send_message(message.chat.id, "❌ بيانات غير مكتملة، يرجى كتابة المعرف، القسم، النوع، الرابط، والمفتاح.", reply_markup=admin_back_button())
            return

        # 4. تعديل القنوات
        elif step == 'ADM_EDIT_CH_OFFICIAL':
            del USER_STEPS[user_id]
            val = message.text.strip()
            set_setting('channel_official_url', val)
            if 't.me/' in val:
                u = val.split('t.me/')[-1].split('/')[0].strip()
                if u and not u.startswith('+'):
                    set_setting('channel_official_id', f"@{u}")
            elif val.startswith('@') or val.startswith('-100') or val.isdigit():
                set_setting('channel_official_id', val)
            bot.send_message(message.chat.id, f"✅ تم تحديث رابط ومعرف القناة الرسمية إلى:\n{val}", reply_markup=admin_back_button())
            return

        elif step == 'ADM_EDIT_CH_ORDERS':
            del USER_STEPS[user_id]
            val = message.text.strip()
            set_setting('channel_orders_url', val)
            if 't.me/' in val:
                u = val.split('t.me/')[-1].split('/')[0].strip()
                if u and not u.startswith('+'):
                    set_setting('channel_orders_id', f"@{u}")
            elif val.startswith('@') or val.startswith('-100') or val.isdigit():
                set_setting('channel_orders_id', val)
            bot.send_message(message.chat.id, f"✅ تم تحديث رابط ومعرف قناة التفعيلات إلى:\n{val}\n\n💡 يمكنك فحص وصول الرسائل بالضغط على زر (فحص وتجربة قناة التفعيلات).", reply_markup=admin_back_button())
            return

        elif step == 'ADM_EDIT_CH_TUTORIALS':
            del USER_STEPS[user_id]
            val = message.text.strip()
            set_setting('channel_tutorials_url', val)
            if 't.me/' in val:
                u = val.split('t.me/')[-1].split('/')[0].strip()
                if u and not u.startswith('+'):
                    set_setting('channel_tutorials_id', f"@{u}")
            elif val.startswith('@') or val.startswith('-100') or val.isdigit():
                set_setting('channel_tutorials_id', val)
            bot.send_message(message.chat.id, f"✅ تم تحديث رابط ومعرف قناة التعليمات إلى:\n{val}", reply_markup=admin_back_button())
            return

        elif step == 'ADM_EDIT_CH_EXPLAINS':
            del USER_STEPS[user_id]
            val = message.text.strip()
            set_setting('channel_explains_url', val)
            if 't.me/' in val:
                u = val.split('t.me/')[-1].split('/')[0].strip()
                if u and not u.startswith('+'):
                    set_setting('channel_explains_id', f"@{u}")
            elif val.startswith('@') or val.startswith('-100') or val.isdigit():
                set_setting('channel_explains_id', val)
            bot.send_message(message.chat.id, f"✅ تم تحديث رابط ومعرف قناة الشروحات إلى:\n{val}", reply_markup=admin_back_button())
            return

        # 5. إضافة وكيل
        elif step == 'ADM_ADD_AGENT_ID':
            del USER_STEPS[user_id]
            try:
                parts = message.text.strip().split()
                ag_id = int(parts[0])
                ag_name = parts[1] if len(parts) > 1 else "وكيل معتمد"
                ag_disc = float(parts[2]) if len(parts) > 2 else 5.0
                add_agent_db(ag_id, ag_name, ag_disc)
                bot.send_message(message.chat.id, f"✅ تم تعيين المستخدم `{ag_id}` كوكيل معتمد ({ag_name}) بنسبة خصم `{ag_disc}%`!", parse_mode="Markdown", reply_markup=admin_back_button())
                try: bot.send_message(ag_id, f"🎉 تهانينا! تمت ترقيتك إلى وكيل معتمد بنسبة خصم خاصة `{ag_disc}%` على كافة الخدمات!")
                except: pass
            except:
                bot.send_message(message.chat.id, "❌ صيغة غير صحيحة! اكتب: `ID الاسم الخصم`\nمثال: `6113734300 وكيل_صنعاء 5`", parse_mode="Markdown", reply_markup=admin_back_button())
            return

        # 6. تعديل الدعم الفني
        elif step == 'ADM_EDIT_SUP_1':
            del USER_STEPS[user_id]
            val = message.text.strip()
            set_setting('support_admin_1', val)
            bot.send_message(message.chat.id, f"✅ تم تحديث معرف الدعم الأول إلى: `{val}`", parse_mode="Markdown", reply_markup=admin_back_button())
            return

        elif step == 'ADM_EDIT_SUP_2':
            del USER_STEPS[user_id]
            val = message.text.strip()
            set_setting('support_admin_2', val)
            bot.send_message(message.chat.id, f"✅ تم تحديث معرف الدعم الثاني إلى: `{val}`", parse_mode="Markdown", reply_markup=admin_back_button())
            return

        # 7. تعديل تحويل الرصيد
        elif step == 'ADM_EDIT_TRANSFER_MIN':
            del USER_STEPS[user_id]
            try:
                val = float(message.text.strip())
                set_setting('min_transfer_amount', str(val))
                bot.send_message(message.chat.id, f"✅ تم تحديث الحد الأدنى للتحويل إلى `${val:.2f}`!", reply_markup=admin_back_button())
            except:
                bot.send_message(message.chat.id, "❌ أرسل رقماً صحيحاً.", reply_markup=admin_back_button())
            return

        elif step == 'ADM_EDIT_TRANSFER_FEE':
            del USER_STEPS[user_id]
            try:
                val = float(message.text.strip())
                set_setting('transfer_fee_percent', str(val))
                bot.send_message(message.chat.id, f"✅ تم تحديث عمولة التحويل إلى `{val}%`!", reply_markup=admin_back_button())
            except:
                bot.send_message(message.chat.id, "❌ أرسل رقماً صحيحاً.", reply_markup=admin_back_button())
            return

        # 8. تعديل الإحالات
        elif step == 'ADM_EDIT_REF_REWARD':
            del USER_STEPS[user_id]
            try:
                val = float(message.text.strip())
                set_setting('reward_per_invite', str(val))
                bot.send_message(message.chat.id, f"✅ تم تحديث مكافأة الدعوة إلى `${val:.3f}`!", reply_markup=admin_back_button())
            except:
                bot.send_message(message.chat.id, "❌ أرسل رقماً صحيحاً.", reply_markup=admin_back_button())
            return

        elif step == 'ADM_EDIT_REF_PCT':
            del USER_STEPS[user_id]
            try:
                val = float(message.text.strip())
                set_setting('referral_purchase_percent', str(val))
                bot.send_message(message.chat.id, f"✅ تم تحديث نسبة عمولة المشتريات إلى `{val}%`!", parse_mode="Markdown", reply_markup=admin_back_button())
            except:
                bot.send_message(message.chat.id, "❌ أرسل رقماً صحيحاً (مثال: `5` تعني 5%).", reply_markup=admin_back_button())
            return

        elif step == 'ADM_EDIT_REF_MIN':
            del USER_STEPS[user_id]
            try:
                val = float(message.text.strip())
                set_setting('min_invite_withdraw', str(val))
                bot.send_message(message.chat.id, f"✅ تم تحديث الحد الأدنى لسحب الإحالات إلى `${val:.2f}`!", reply_markup=admin_back_button())
            except:
                bot.send_message(message.chat.id, "❌ أرسل رقماً صحيحاً.", reply_markup=admin_back_button())
            return

        # 9. إضافة حسابات قديمة إلى المخزون (سيرفر 3)
        elif step == 'ADM_ADD_AGED_ACC_DATA':
            del USER_STEPS[user_id]
            parts = message.text.strip().split()
            if len(parts) >= 5:
                year, country, phone, two_fa, cost = parts[0], parts[1], parts[2], parts[3], float(parts[4])
                conn = get_db()
                cursor = conn.cursor()
                try:
                    cursor.execute("INSERT INTO aged_stock (year, country, phone, two_fa, cost, is_sold) VALUES (?, ?, ?, ?, ?, 0)",
                                   (year, country, phone, two_fa, cost))
                    conn.commit()
                finally:
                    conn.close()
                bot.send_message(message.chat.id, f"✅ تم إضافة الحساب القديم للمخزون بنجاح!\n📅 السنة: {year}\n🌐 الدولة: {country}\n📞 الرقم: `{phone}`\n💵 السعر: ${cost:.2f}", parse_mode="Markdown", reply_markup=admin_back_button())
            else:
                bot.send_message(message.chat.id, "❌ صيغة غير صحيحة! يرجى إرسال:\n`السنة الدولة الرقم كود_2FA السعر`", parse_mode="Markdown", reply_markup=admin_back_button())
            return

        # خطوات إضافة خدمة رشق مخصصة جديدة للأدمن (SMM Custom Service)
        elif step == 'ADM_ADD_SMM_ID':
            srv_api_id = str(message.text.strip())
            step_data['srv_api_id'] = srv_api_id
            step_data['step'] = 'ADM_ADD_SMM_NAME'
            USER_STEPS[user_id] = step_data
            cat_code = step_data.get('cat_code', 'others')
            cat_title = CATEGORY_TITLES.get(cat_code, cat_code)
            msg_text = (
                f"✅ تم حفظ ID الخدمة: {srv_api_id}\n\n"
                f"📌 الخطوة 2 من 5:\n"
                f"أرسل اسم الخدمة باللغة العربية كاملاً لقسم [{cat_title}]:\n"
                f"(مثال: أعضاء قنوات تيليجرام حقيقيين ضمان 30 يوم)"
            )
            try:
                bot.send_message(message.chat.id, msg_text, reply_markup=admin_back_button())
            except Exception as e:
                print(f"Error sending ADM_ADD_SMM_ID msg: {e}")
            return

        elif step == 'ADM_ADD_SMM_NAME':
            name_ar = message.text.strip()
            step_data['name_ar'] = name_ar
            step_data['step'] = 'ADM_ADD_SMM_RATE'
            USER_STEPS[user_id] = step_data
            msg_text = (
                f"✅ تم حفظ الاسم:\n{name_ar}\n\n"
                f"📌 الخطوة 3 من 5:\n"
                f"أرسل سعر بيع الخدمة لكل 1000 بالدولار ($):\n"
                f"(مثال: 0.85 أو 0.10 أو 1.5):"
            )
            try:
                bot.send_message(message.chat.id, msg_text, reply_markup=admin_back_button())
            except Exception as e:
                print(f"Error sending ADM_ADD_SMM_NAME msg: {e}")
            return

        elif step == 'ADM_ADD_SMM_RATE':
            rate = parse_safe_float(message.text, default=0.0)
            if rate <= 0:
                try: bot.send_message(message.chat.id, "❌ يرجى إرسال رقم سعر صالح (مثال: 0.85 أو 0.10):", reply_markup=admin_back_button())
                except: pass
                return
            step_data['rate'] = rate
            step_data['step'] = 'ADM_ADD_SMM_MIN'
            USER_STEPS[user_id] = step_data
            msg_text = (
                f"✅ تم تحديد السعر: ${rate:.3f} لكل 1,000\n\n"
                f"📌 الخطوة 4 من 5:\n"
                f"أرسل الحد الأدنى للطلب (Min Quantity):\n"
                f"(مثال: 10 أو 50 أو 100):"
            )
            try:
                bot.send_message(message.chat.id, msg_text, reply_markup=admin_back_button())
            except Exception as e:
                print(f"Error sending ADM_ADD_SMM_RATE msg: {e}")
            return

        elif step == 'ADM_ADD_SMM_MIN':
            min_q = parse_safe_int(message.text, default=10)
            if min_q <= 0: min_q = 10
            step_data['min_q'] = min_q
            step_data['step'] = 'ADM_ADD_SMM_MAX'
            USER_STEPS[user_id] = step_data
            msg_text = (
                f"✅ الحد الأدنى: {min_q}\n\n"
                f"📌 الخطوة 5 من 5:\n"
                f"أرسل الحد الأقصى للطلب (Max Quantity):\n"
                f"(مثال: 10000 أو 50000 أو 100000):"
            )
            try:
                bot.send_message(message.chat.id, msg_text, reply_markup=admin_back_button())
            except Exception as e:
                print(f"Error sending ADM_ADD_SMM_MIN msg: {e}")
            return

        elif step == 'ADM_ADD_SMM_MAX':
            max_q = parse_safe_int(message.text, default=100000)
            if max_q <= 0: max_q = 100000
            step_data['max_q'] = max_q
            step_data['step'] = 'ADM_ADD_SMM_SPEED'
            USER_STEPS[user_id] = step_data
            
            srv_api_id = step_data.get('srv_api_id')
            cat_code = step_data.get('cat_code', 'others')
            cat_title = CATEGORY_TITLES.get(cat_code, cat_code)
            name_ar = step_data.get('name_ar')
            rate = step_data.get('rate', 1.0)
            min_q = step_data.get('min_q', 10)

            speed_prompt = (
                f"⚡ <b>حدد وقت وسرعة تنفيذ الخدمة:</b>\n\n"
                f"▫️ <b>القسم</b> : {cat_title}\n"
                f"▫️ <b>الاسم</b> : {name_ar}\n"
                f"▫️ <b>معرف السيرفر (ID)</b> : <code>{srv_api_id}</code>\n"
                f"▫️ <b>السعر</b> : ${rate:.3f} لكل 1K\n"
                f"▫️ <b>الكمية</b> : من {min_q} إلى {max_q}\n\n"
                f"اختر سرعة الخدمة من الأزرار أو اضغط (✍️ كتابة وقت مخصص):"
            )
            try:
                bot.send_message(message.chat.id, speed_prompt, parse_mode="HTML", reply_markup=admin_smm_speed_keyboard())
            except Exception as e:
                print(f"Error sending ADM_ADD_SMM_MAX msg: {e}")
            return

        elif step == 'ADM_ADD_SMM_CUSTOM_SPEED':
            speed_text = message.text.strip()
            if not speed_text: speed_text = 'فورية ⚡'
            step_data['speed'] = speed_text
            step_data['step'] = 'ADM_ADD_SMM_GUARANTEE'
            USER_STEPS[user_id] = step_data

            srv_api_id = step_data.get('srv_api_id')
            cat_code = step_data.get('cat_code', 'others')
            cat_title = CATEGORY_TITLES.get(cat_code, cat_code)
            name_ar = step_data.get('name_ar')
            rate = step_data.get('rate', 1.0)
            min_q = step_data.get('min_q', 10)
            max_q = step_data.get('max_q', 100000)

            confirm_prompt = (
                f"🛡️ <b>الخطوة الأخيرة: اختر نوع الضمان لإتمام إضافة الخدمة:</b>\n\n"
                f"▫️ <b>القسم</b> : {cat_title}\n"
                f"▫️ <b>الاسم</b> : {name_ar}\n"
                f"▫️ <b>معرف السيرفر (ID)</b> : <code>{srv_api_id}</code>\n"
                f"▫️ <b>السعر</b> : ${rate:.3f} لكل 1K\n"
                f"▫️ <b>الكمية</b> : من {min_q} إلى {max_q}\n"
                f"▫️ <b>السرعة</b> : {speed_text}\n\n"
                f"اضغط على نوع الضمان بالأسفل لحفظ الخدمة وتفعيلها فوراً:"
            )
            try:
                bot.send_message(message.chat.id, confirm_prompt, parse_mode="HTML", reply_markup=admin_smm_guarantee_keyboard())
            except Exception as e:
                print(f"Error sending custom speed guarantee prompt: {e}")
            return

        elif step == 'ADM_IMPORT_SMM_JSON':
            raw_text = message.text.strip()
            count = import_custom_smm_services_json(raw_text)
            USER_STEPS.pop(user_id, None)
            if count > 0:
                bot.send_message(
                    message.chat.id,
                    f"🎉 <b>تم بنجاح!</b>\n\nتم استيراد واسترجاع <b>{count}</b> خدمة رشق بنجاح وتفعيلها في البوت!",
                    parse_mode="HTML",
                    reply_markup=admin_smm_custom_keyboard()
                )
            else:
                bot.send_message(
                    message.chat.id,
                    "❌ تعذر استيراد الخدمات. تأكد من إرسال نص JSON صالح أو إرسال ملف JSON الذي قمت بتصديره سابقاً.",
                    reply_markup=admin_smm_custom_keyboard()
                )
            return

        # 10. تقييد / فك تقييد مستخدم
        elif step == 'ADMIN_BAN_USER':
            del USER_STEPS[user_id]
            try:
                t_id = int(message.text.strip())
                if t_id == ADMIN_ID:
                    bot.send_message(message.chat.id, "❌ لا يمكن تقييد حساب المدير.", reply_markup=admin_back_button())
                    return
                conn = get_db()
                cursor = conn.cursor()
                try:
                    cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (t_id,))
                    row = cursor.fetchone()
                    if not row:
                        cursor.execute("INSERT INTO users (user_id, name, is_banned) VALUES (?, 'مستخدم', 1)", (t_id,))
                        new_st = 1
                    else:
                        new_st = 0 if row[0] == 1 else 1
                        cursor.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (new_st, t_id))
                    conn.commit()
                finally:
                    conn.close()
                msg_txt = f"🚫 تم تقييد/حظر المستخدم `{t_id}` بنجاح." if new_st == 1 else f"🟢 تم فك تقييد المستخدم `{t_id}` بنجاح."
                bot.send_message(message.chat.id, msg_txt, parse_mode="Markdown", reply_markup=admin_back_button())
            except:
                bot.send_message(message.chat.id, "❌ يرجى إرسال آيدي رقمي صحيح.", reply_markup=admin_back_button())
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
                bot.send_message(message.chat.id, f"✅ تم خصم ${format_money(amt)} من الحساب `{t_id}` بنجاح!\n💰 رصيده الحالي: ${format_money(new_bal)}", parse_mode="Markdown", reply_markup=admin_back_button())
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
                bot.send_message(message.chat.id, f"✅ تمت العملية بنجاح للحساب `{t_id}`!\n💰 رصيده الآن: ${format_money(new_bal)}", parse_mode="Markdown", reply_markup=admin_back_button())
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
                res = f"👤 {u[1]} ({u[2]})\n🆔 `{u[0]}` | 💰 ${format_money(u[3])} | 📌 {st}"
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

def process_pending_cancellations():
    """فحص دوري في الخلفية كل 10 ثوان لإلغاء الأرقام فور انتهاء عداد الانتظار في المزود"""
    while True:
        try:
            time.sleep(10)
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT tz_id, server_id, user_id, chat_id, cost, phone, refund_user, (julianday('now') - julianday(COALESCE(created_at, 'now'))) * 1440 FROM pending_cancellations")
            pending_list = cursor.fetchall()
            for row in pending_list:
                tz_id, server_id, user_id, chat_id, cost, phone, refund_user, age_minutes = row
                srv = SERVERS.get(server_id)
                if not srv:
                    srv = {'api_key': API_KEY, 'url': API_URL}

                # إذا مر أكثر من 22 دقيقة، يكون المزود قد أنهى التفعيل تلقائياً
                if age_minutes is not None and age_minutes > 22:
                    cursor.execute("DELETE FROM pending_cancellations WHERE tz_id = ?", (tz_id,))
                    conn.commit()
                    continue

                res = grizzly_request({'action': 'setStatus', 'status': '8', 'id': tz_id}, srv['api_key'], srv['url'])
                
                # فقط عند تأكيد الإلغاء الفعلي من المزود أو انتهاء التفعيل
                if "ACCESS_CANCEL" in res or "STATUS_CANCEL" in res or "NO_ACTIVATION" in res:
                    if refund_user == 1:
                        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (cost, user_id))
                        cursor.execute("UPDATE purchases SET status = 'CANCELLED' WHERE tz_id = ?", (tz_id,))
                        try:
                            bot.send_message(
                                chat_id,
                                f"✅ **تم اكتمال إلغاء الرقم بنجاح من المزود!**\n\n"
                                f"📱 الرقم: `{phone}`\n"
                                f"💰 تمت إعادة المبلغ (${cost:.2f}) إلى محفظتك بالكامل.",
                                parse_mode="Markdown"
                            )
                        except Exception as e:
                            print(f"Failed to notify user about auto cancellation: {e}")
                    else:
                        cursor.execute("UPDATE purchases SET status = 'REPLACED_CANCELLED' WHERE tz_id = ?", (tz_id,))
                    
                    cursor.execute("DELETE FROM pending_cancellations WHERE tz_id = ?", (tz_id,))
                    conn.commit()
                # إذا كانت النتيجة BAD_STATUS أو EARLY_CANCEL_DENIED:
                # العداد في المزود لم ينتهِ بعد، نبقيه في الجدول ليعيد المحاولة كل 10 ثوانٍ حتى ينتهي العداد ويلتغي فوراً!
            conn.close()
        except Exception as e:
            print(f"Pending cancellations worker error: {e}")

# تشغيل خيط معالجة الإلغاءات المؤجلة تلقائياً
threading.Thread(target=process_pending_cancellations, daemon=True).start()

def monitor_smm_orders_worker():
    """خيط خلفي ذكي يفحص طلبات الرشق المعلقة دورياً كل 30 ثانية وعند اكتمال الطلب يرسل إشعاراً فورياً للعميل بنمط بوت بلاس"""
    while True:
        try:
            time.sleep(30)
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT order_id, user_id, service_name, category_name, link, quantity, cost, server_id, status 
                FROM smm_orders 
                WHERE status IN ('Pending', 'Processing', 'In progress', 'In_progress', '') 
                ORDER BY id DESC LIMIT 25
            """)
            pending_orders = cursor.fetchall()
            conn.close()

            for ord_row in pending_orders:
                order_id, user_id, srv_name, cat_name, link, qty, cost, srv_id, db_st = ord_row
                target_srv = str(srv_id) if srv_id else 'tiger'
                status_res = smm_request(target_srv, 'status', order=order_id)
                if not status_res or 'error' in status_res:
                    alt_srv = '2' if target_srv == 'tiger' else 'tiger'
                    alt_res = smm_request(alt_srv, 'status', order=order_id)
                    if alt_res and 'error' not in alt_res:
                        status_res = alt_res
                        target_srv = alt_srv
                        conn = get_db()
                        conn.execute('UPDATE smm_orders SET server_id = ? WHERE order_id = ?', (alt_srv, order_id))
                        conn.commit()
                        conn.close()

                if not status_res:
                    continue

                api_status = status_res.get('status', db_st)
                remains = status_res.get('remains', '1')
                try: remains_num = int(remains)
                except: remains_num = 1

                st_lower = str(api_status).strip().lower()
                is_completed = (st_lower in ['completed', 'مكتمل']) or (remains_num == 0 and st_lower not in ['canceled', 'cancelled', 'partial', 'fail', 'error'])

                if is_completed:
                    conn = get_db()
                    conn.execute('UPDATE smm_orders SET status = "Completed" WHERE order_id = ?', (order_id,))
                    conn.commit()
                    conn.close()

                    date_str = get_arabic_datetime()
                    done_msg = (
                        f"✅ : تم اكتمال طلبك بنجاح 💙\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"📦 : رقم الطلب : #{order_id}\n"
                        f"📁 : القسم : {cat_name}\n"
                        f"🛒 : الخدمة : {srv_name}\n"
                        f"🔗 : الرابط : [{link}]\n"
                        f"🔢 : الكمية : {qty}\n"
                        f"📊 : تم التنفيذ : {qty}\n"
                        f"⏳ : المتبقي : 0\n"
                        f"📌 : الحالة : مكتمل ✅\n"
                        f"⏰ : الوقت : {date_str}\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"🎉 : تم تنفيذ طلبك بالكامل بنجاح\n"
                        f"💙 : شكراً لاستخدامك خدماتنا"
                    )
                    try:
                        bot.send_message(user_id, done_msg, reply_markup=back_button())
                    except Exception as err:
                        print(f"Failed to send smm completion notification to {user_id}: {err}")

                elif st_lower in ['canceled', 'cancelled']:
                    conn = get_db()
                    conn.execute('UPDATE smm_orders SET status = "Canceled" WHERE order_id = ?', (order_id,))
                    conn.execute('UPDATE users SET balance = balance + ?, spent_balance = MAX(0.0, spent_balance - ?) WHERE user_id = ?', (cost, cost, user_id))
                    conn.commit()
                    conn.close()
                    try:
                        cancel_msg = (
                            f"⚠️ <b>تنبيه: تم إلغاء طلب الرشق من السيرفر</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"📦 <b>رقم الطلب</b> : <code>#{order_id}</code>\n"
                            f"🛒 <b>الخدمة</b> : {srv_name}\n"
                            f"💰 <b>تمت إعادة الرصيد إلى محفظتك بالكامل</b> : <b>${cost:.4f}</b>"
                        )
                        bot.send_message(user_id, cancel_msg, parse_mode="HTML", reply_markup=back_button())
                    except Exception as err:
                        print(f"Failed to notify cancelled smm to {user_id}: {err}")
        except Exception as e:
            print(f"SMM orders monitor worker error: {e}")

# تشغيل خيط مراقبة وإشعار اكتمال طلبات الرشق تلقائياً
threading.Thread(target=monitor_smm_orders_worker, daemon=True).start()

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
