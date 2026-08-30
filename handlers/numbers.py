from telebot import TeleBot
from config import SERVERS, get_or_create_user, grizzly_request
from keyboards import servers_keyboard, services_keyboard, countries_keyboard_fast, active_number_keyboard, back_button

def register_numbers_handlers(bot: TeleBot):
    
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

    @bot.callback_query_handler(func=lambda call: call.data.startswith("select_server_"))
    def handle_select_server(call):
        server_id = call.data.replace("select_server_", "")
        if server_id not in SERVERS:
            bot.answer_callback_query(call.id, "❌ السيرفر غير متوفر حالياً!", show_alert=True)
            return
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"📱 **اختر التطبيق المطلوب من السيرفر:**",
            reply_markup=services_keyboard(server_id),
            parse_mode="Markdown"
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("srv_app_"))
    def handle_srv_app(call):
        parts = call.data.split("_")
        server_id = parts[2]
        app_type = parts[3]
        
        service_codes = {
            "wa": "wa",
            "tg": "tg",
            "ig": "ig",
            "tk": "tk"
        }
        service_code = service_codes.get(app_type, "wa")
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"🌍 **اختر الدولة المطلوبة:**",
            reply_markup=countries_keyboard_fast(server_id, service_code, page=0),
            parse_mode="Markdown"
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("pg_"))
    def handle_pagination(call):
        parts = call.data.split("_")
        server_id = parts[1]
        service_code = parts[2]
        page = int(parts[3])
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"🌍 **اختر الدولة المطلوبة (الصفحة {page+1}):**",
            reply_markup=countries_keyboard_fast(server_id, service_code, page=page),
            parse_mode="Markdown"
        )
