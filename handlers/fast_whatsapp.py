from telebot import TeleBot
from keyboards import back_button

def register_fast_whatsapp_handler(bot: TeleBot):
    @bot.callback_query_handler(func=lambda call: call.data == "fast_buy_wa")
    def handle_fast_whatsapp(call):
        text = (
            "🟢 **عروض أرقام وحسابات واتساب:**\n\n"
            "تصفح أقوى عروض حسابات وأرقام الواتساب الجاهزة والموثقة."
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=back_button(),
            parse_mode="Markdown"
        )
