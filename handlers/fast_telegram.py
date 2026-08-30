from telebot import TeleBot
from keyboards import back_button

def register_fast_telegram_handler(bot: TeleBot):
    @bot.callback_query_handler(func=lambda call: call.data == "fast_buy_tg")
    def handle_fast_telegram(call):
        text = (
            "🔵 **قسم حسابات تليجرام الجاهزة:**\n\n"
            "هنا يمكنك شراء حسابات تليجرام جاهزة ومفعلة وجاهزة للاستخدام الفوري وبأفضل الأسعار."
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=back_button(),
            parse_mode="Markdown"
        )
