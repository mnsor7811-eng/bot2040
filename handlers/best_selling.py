from telebot import TeleBot
from keyboards import back_button

def register_best_selling_handler(bot: TeleBot):
    @bot.callback_query_handler(func=lambda call: call.data == "best_selling")
    def handle_best_selling(call):
        text = (
            "🔥 **السيرفرات والخدمات الأكثر مبيعاً:**\n\n"
            "الخدمات الأكثر إقبالاً وطلباً من قبل المستخدمين لجودتها العالية وسرعتها."
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=back_button(),
            parse_mode="Markdown"
        )
