from telebot import TeleBot
from config import SERVERS
from keyboards import servers_keyboard

def register_buy_number_handler(bot: TeleBot):
    @bot.callback_query_handler(func=lambda call: call.data == "buy_number")
    def handle_buy_number(call):
        user_id = call.from_user.id
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🌐 **اختر سيرفر الأرقام المناسب لك:**",
            reply_markup=servers_keyboard(user_id),
            parse_mode="Markdown"
        )
