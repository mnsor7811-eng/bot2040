from telebot import TeleBot
from keyboards import back_button

def register_most_available_handler(bot: TeleBot):
    @bot.callback_query_handler(func=lambda call: call.data == "most_available")
    def handle_most_available(call):
        text = (
            "🎲 **الخدمات والأرقام الأكثر توفراً:**\n\n"
            "قائمة الدول والخدمات التي تتوافر فيها المخزونات بشكل مستمر على مدار الساعة."
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=back_button(),
            parse_mode="Markdown"
        )
