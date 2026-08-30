from telebot import TeleBot
from config import get_or_create_user, PAYMENT_DETAILS, ADMIN_USERNAME
from keyboards import main_keyboard, recharge_keyboard, back_button

def register_general_features_handlers(bot: TeleBot):

    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        user_id = message.from_user.id
        name = message.from_user.first_name
        get_or_create_user(user_id, name)
        
        welcome_text = (
            f"مرحباً بك عزيزي {name} في البوت الشامل 🤖✨\n\n"
            "استخدم الأزرار بالأسفل لتنفيذ طلباتك:"
        )
        bot.send_message(message.chat.id, welcome_text, reply_markup=main_keyboard(user_id))

    @bot.callback_query_handler(func=lambda call: call.data == "back_main")
    def handle_back_main(call):
        user_id = call.from_user.id
        name = call.from_user.first_name
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🏠 **القائمة الرئيسية للبوت:**",
            reply_markup=main_keyboard(user_id),
            parse_mode="Markdown"
        )

    @bot.callback_query_handler(func=lambda call: call.data == "recharge_menu")
    def handle_recharge_menu(call):
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="💳 **اختر وسيلة الدفع المناسبة لشحن رصيدك:**",
            reply_markup=recharge_keyboard(),
            parse_mode="Markdown"
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
    def handle_payment_methods(call):
        method = call.data.replace("pay_", "")
        details = PAYMENT_DETAILS.get(method)
        if not details:
            return
            
        text = (
            f"📌 **طريقة الدفع عبر {details['name']}:**\n\n"
            f"🔹 **رقم الحساب / المحفظة:** `{details['acc']}`\n"
            f"🔹 **الحد الأدنى للشحن:** {details['min']}\n"
            f"🔹 **سعر الصرف:** {details['rate']}\n\n"
            f"💡 *بعد اتمام عملية التحويل، يرجى إرسال صورة الإيصال إلى الدعم الفني لتعبئة رصيدك فوراً.*"
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=back_button(),
            parse_mode="Markdown"
        )

    # 1. زر الدعم
    @bot.callback_query_handler(func=lambda call: call.data == "support")
    def handle_support(call):
        text = f"🎧 **الدعم الفني والخدمة:**\n\nللتواصل المباشر مع الإدارة وحل أي مشكلة تواجهك:\n👤 معرف الإدارة: {ADMIN_USERNAME}"
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=back_button(),
            parse_mode="Markdown"
        )

    # 2. زر تحويل الرصيد
    @bot.callback_query_handler(func=lambda call: call.data == "transfer")
    def handle_transfer(call):
        text = (
            "🔄 **قسم تحويل الرصيد:**\n\n"
            "يمكنك تحويل رصيد من حسابك إلى أي مستخدم آخر في البوت بسهولة وأمان."
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=back_button(),
            parse_mode="Markdown"
        )

    # 3. زر اربح رصيد مجانا
    @bot.callback_query_handler(func=lambda call: call.data == "free_ruble")
    def handle_free_ruble(call):
        user_id = call.from_user.id
        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        
        text = (
            f"💎 **اربح رصيد مجاني عبر دعوة الأصدقاء!**\n\n"
            f"شارك رابط الإحالة الخاص بك وكل شخص يسجل عبرك ستكسب مكافأة رصيد فورية.\n\n"
            f"🔗 **رابطك الخاص:**\n`{ref_link}`"
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=back_button(),
            parse_mode="Markdown"
        )

    # 4. زر إحصائيات الشراء الناجح
    @bot.callback_query_handler(func=lambda call: call.data == "purchase_stats")
    def handle_purchase_stats(call):
        text = (
            "✔ **إحصائيات الشراء الناجح:**\n\n"
            "هنا يمكنك متابعة إحصائيات العمليات الناجحة والطلبات المكتملة داخل البوت."
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=back_button(),
            parse_mode="Markdown"
        )

    # 5. زر حسابي
    @bot.callback_query_handler(func=lambda call: call.data == "my_account")
    def handle_my_account(call):
        user_id = call.from_user.id
        name = call.from_user.first_name
        user_info = get_or_create_user(user_id, name)
        
        balance = user_info[3]
        ai_bal = user_info[4]
        
        text = (
            f"👤 **معلومات حسابك الشخصي:**\n\n"
            f"🆔 **معرفك:** `{user_id}`\n"
            f"👤 **الاسم:** {name}\n"
            f"💰 **رصيدك الحالي:** `${balance:.2f}`\n"
            f"🤖 **رصيد الذكاء الاصطناعي:** `{ai_bal}` رسائل"
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=back_button(),
            parse_mode="Markdown"
        )

    # 6. زر خدمات وميزات أخرى
    @bot.callback_query_handler(func=lambda call: call.data == "other_services")
    def handle_other_services(call):
        text = (
            "🛸 **خدمات وميزات أخرى:**\n\n"
            "استكشف المزيد من الخدمات الإضافية والمميزات المتاحة لك في البوت."
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=back_button(),
            parse_mode="Markdown"
        )

    @bot.callback_query_handler(func=lambda call: call.data == "ignore")
    def handle_ignore(call):
        bot.answer_callback_query(call.id)
