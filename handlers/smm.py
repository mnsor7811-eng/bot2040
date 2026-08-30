from telebot import TeleBot
import requests
from config import SMM_PROVIDERS, DEFAULT_SMM_PROVIDER
from keyboards import smm_main_keyboard, smm_servers_keyboard, boost_keyboard, games_keyboard, dynamic_smm_keyboard, smm_detail_grid_keyboard, smm_confirm_keyboard

def register_smm_handlers(bot: TeleBot):

    @bot.callback_query_handler(func=lambda call: call.data == "smm_main")
    def handle_smm_main(call):
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🚀 **مرحباً بك في قسم الرشق وشحن الألعاب والبرامج:**\nاختر القسم المناسب:",
            reply_markup=smm_main_keyboard(),
            parse_mode="Markdown"
        )

    @bot.callback_query_handler(func=lambda call: call.data == "smm_servers_menu")
    def handle_smm_servers_menu(call):
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🚀 **اختر سيرفر الرشق المناسب لك:**",
            reply_markup=smm_servers_keyboard(),
            parse_mode="Markdown"
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("select_smm_srv_"))
    def handle_select_smm_server(call):
        smm_server_id = call.data.replace("select_smm_srv_", "")
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="📱 **اختر منصة الرشق المطلوبة:**",
            reply_markup=boost_keyboard(smm_server_id),
            parse_mode="Markdown"
        )

    @bot.callback_query_handler(func=lambda call: call.data == "games_menu")
    def handle_games_menu(call):
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🎮 **اختر اللعبة أو البرنامج للشحن:**",
            reply_markup=games_keyboard(),
            parse_mode="Markdown"
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("smmc_"))
    def handle_smm_category(call):
        parts = call.data.split("_")
        smm_server_id = parts[1]
        category_code = parts[2]
        
        srv_info = SMM_PROVIDERS.get(smm_server_id, SMM_PROVIDERS[DEFAULT_SMM_PROVIDER])
        try:
            res = requests.post(srv_info['url'], data={
                'key': srv_info['key'],
                'action': 'services'
            }, timeout=10).json()
        except Exception:
            res = []

        filtered_services = []
        if isinstance(res, list):
            for s in res:
                name_lower = str(s.get('name', '')).lower()
                if category_code in name_lower or category_code == 'others':
                    filtered_services.append(s)
            if not filtered_services:
                filtered_services = res[:30] # عرض عينة في حال عدم التطابق الدقيق

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"📋 **الخدمات المتاحة في قسم ({category_code.upper()}):**",
            reply_markup=dynamic_smm_keyboard(filtered_services, category_code, page=0, smm_server_id=smm_server_id),
            parse_mode="Markdown"
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("smmbuy_"))
    def handle_smm_buy_item(call):
        parts = call.data.split("_")
        smm_server_id = parts[1]
        srv_id = parts[2]
        
        srv_info = SMM_PROVIDERS.get(smm_server_id, SMM_PROVIDERS[DEFAULT_SMM_PROVIDER])
        try:
            res = requests.post(srv_info['url'], data={
                'key': srv_info['key'],
                'action': 'services'
            }, timeout=10).json()
        except Exception:
            res = []
            
        service_data = next((s for s in res if str(s.get('service')) == str(srv_id)), {})
        price = float(service_data.get('rate', 0.5)) * 1.10
        speed = service_data.get('average_time', 'سريع')
        quality = "عالية الجودة"
        guarantee = "مضمون / تعويض" if service_data.get('refill') else "بدون ضمان"
        min_q = service_data.get('min', 10)
        max_q = service_data.get('max', 10000)

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"📄 **تفاصيل الخدمة (ID: {srv_id}):**\n{service_data.get('name', 'خدمة مميزة')}",
            reply_markup=smm_detail_grid_keyboard(srv_id, round(price, 3), speed, quality, guarantee, min_q, max_q, smm_server_id),
            parse_mode="Markdown"
        )
