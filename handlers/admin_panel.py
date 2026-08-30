from telebot import TeleBot
from config import ADMIN_ID
from keyboards import admin_back_button

def register_admin_panel_handler(bot: TeleBot):
    @bot.callback_query_handler(func=lambda call: call.data == "admin_panel")
    def handle_admin_panel(call):
        user_id = call.from_user.id
        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "❌ عذراً، هذه اللوحة مخصصة للإدارة فقط!", show_alert=True)
            return

        text = (
            "⚙️ **لوحة الإدارة الكبرى:**\n\n"
            "مرحباً بك يا مدير البوت. يمكنك من هنا التحكم بالإعدادات، المستخدمين، الأرصدة، والإحصائيات."
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=admin_back_button(),
            parse_mode="Markdown"
        )
