import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ============================================
# البيانات الصحيحة والمعتمدة الخاصة بك
# ============================================
API_TOKEN = "8927305428:AAFok7iKK0S4D3px-kdgW1WvAIZjXr3dWH8"
ADMIN_ID = 6113734300  # آيدي الأدمن والمالك
ADMIN_USERNAME = "Num_s7"  # يوزر حسابك الشخصي للدعم
BOT_USERNAME = "NUM1_SMBOT"  # يوزر البوت

bot = telebot.TeleBot(API_TOKEN)

# ============================================
# أمر /start - القائمة الرئيسية (مطابقة للواجهة تماماً)
# ============================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username or "لا يوجد"
    
    # نص الرسالة مطابق للصورة للتصميم المطلوب
    welcome_text = (
        "💎 𝨭•|━━━━( **NUMBER SMS** )━━━━|•𝨭\n"
        f"• **@{username}** : **0$** •\n\n"
        "🔪 **قناة البوت الرسمية**\n"
        "🛒 **قناة التستيلآت**\n"
        "🐨 **قناة شرح الاستخدام**\n"
        "🎈 **قناة التوفر المتقطع** 🇸🇦 🇲🇦 🇨🇦\n\n"
        "𝨭•|━━━━( **NUMBER SMS** )━━━━|•𝨭\n"
        "━━━━━━━━━━━━━━"
    )
    
    markup = InlineKeyboardMarkup()
    
    # الصف 1
    markup.add(InlineKeyboardButton("☎️ شراء رقم افتراضي", callback_data="buy_virtual_number"))
    
    # الصف 2
    markup.row(
        InlineKeyboardButton("عروض WhatsApp 🟩", callback_data="whatsapp_offers"),
        InlineKeyboardButton("جاهز Telegram 🟦", callback_data="telegram_ready")
    )
    
    # الصف 3
    markup.add(InlineKeyboardButton("📈 السيرفرات الأكثر مبيعاً", callback_data="top_servers"))
    
    # الصف 4
    markup.row(
        InlineKeyboardButton("• شحن الرصيد 🎳 •", callback_data="refill_balance"),
        InlineKeyboardButton("• الأكثر توفراً 🎲 •", callback_data="most_available")
    )
    
    # الصف 5
    markup.add(InlineKeyboardButton("• الرش%ق وشحن الألعاب والبرامج 🔭 •", callback_data="smm_games_charge"))
    
    # الصف 6
    markup.add(InlineKeyboardButton("• اربح روبـل مجاناً 💎 •", callback_data="earn_free_ruble"))
    
    # الصف 7 (زر الدعم يوجه لحسابك مباشرة)
    markup.row(
        InlineKeyboardButton("• تحويل الرصيد 🔄 •", callback_data="transfer_balance"),
        InlineKeyboardButton("🕒 الدعم", url=f"https://t.me/{ADMIN_USERNAME}")
    )
    
    # الصف 8
    markup.add(InlineKeyboardButton("• إحص%ائيات الشراء الناجح ✔️ •", callback_data="purchase_stats"))
    
    # الصف 9
    markup.add(InlineKeyboardButton("𓃠 حسابي 📇", callback_data="my_account"))
    
    # الصف 10
    markup.add(InlineKeyboardButton("• خدمات وميزات أخرى 🛸 •", callback_data="other_services"))
    
    bot.send_message(
        message.chat.id, 
        welcome_text, 
        parse_mode="Markdown", 
        disable_web_page_preview=True, 
        reply_markup=markup
    )

# ============================================
# أمر /admin - لوحة تحكم الأدمن
# ============================================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id == ADMIN_ID:
        admin_text = (
            "⚙️ **لوحة تحكم مالك البوت**\n\n"
            f"مرحباً بك يا @{ADMIN_USERNAME}، لديك كامل الصلاحيات لإدارة البوت:"
        )
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🎛 إدارة الأقسام (فتح/قفل)", callback_data="admin_opclo"))
        markup.row(
            InlineKeyboardButton("📱 تفعيل التطبيقات", callback_data="admin_app_settings"),
            InlineKeyboardButton("🌐 إضافة دولة/مورد", callback_data="admin_add_number")
        )
        markup.add(InlineKeyboardButton("🔄 نظام البوت (تلقائي/يدوي)", callback_data="admin_system_direct"))
        markup.add(InlineKeyboardButton("📊 إحصائيات البوت", callback_data="admin_stats"))
        
        bot.send_message(message.chat.id, admin_text, parse_mode="Markdown", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "❌ عذراً، هذا الأمر مخصص لمالك البوت فقط.")

# ============================================
# معالج الاستجابة للأزرار
# ============================================
@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    if call.data == "buy_virtual_number":
        bot.answer_callback_query(call.id, "جاري فتح قسم شراء الأرقام...")
    elif call.data == "my_account":
        bot.answer_callback_query(call.id, "جاري عرض تفاصيل حسابك...")
    elif call.data == "refill_balance":
        bot.answer_callback_query(call.id, "جاري فتح قسم شحن الرصيد...")
    else:
        bot.answer_callback_query(call.id, "تم الاستجابة للطلب.")

if __name__ == "__main__":
    print(f"🤖 تم تشغيل البوت @{BOT_USERNAME} بنجاح...")
    bot.infinity_polling()
