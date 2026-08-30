from telebot import TeleBot
from keyboards import back_button

def register_ai_landing_handler(bot: TeleBot):
    @bot.callback_query_handler(func=lambda call: call.data == "ai_landing")
    def handle_ai_landing(call):
        text = (
            "🤖 **قسم اشتراكات برامج الذكاء الاصطناعي (AI):**\n\n"
            "مرحباً بك في قسم الذكاء الاصطناعي. يمكنك تفعيل حساباتك والاشتراك في أقوى التطبيقات والخدمات الذكية."
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=back_button(),
            parse_mode="Markdown"
        )
