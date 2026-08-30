import telebot
from config import TOKEN

# استيراد دوال التسجيل لكل ملف مستقل
from handlers.ai_landing import register_ai_landing_handler
from handlers.buy_number import register_buy_number_handler
from handlers.fast_telegram import register_fast_telegram_handler
from handlers.fast_whatsapp import register_fast_whatsapp_handler
from handlers.best_selling import register_best_selling_handler
from handlers.most_available import register_most_available_handler
from handlers.smm_services import register_smm_services_handler
from handlers.admin_panel import register_admin_panel_handler
from handlers.general_features import register_general_features_handlers

# تهيئة البوت الأساسية
bot = telebot.TeleBot(TOKEN, parse_mode='Markdown')

# تسجيل جميع المعالجات من الملفات المستقلة
register_ai_landing_handler(bot)
register_buy_number_handler(bot)
register_fast_telegram_handler(bot)
register_fast_whatsapp_handler(bot)
register_best_selling_handler(bot)
register_most_available_handler(bot)
register_smm_services_handler(bot)
register_admin_panel_handler(bot)
register_general_features_handlers(bot)

if __name__ == '__main__':
    print("🚀 Bot is running successfully with fully separated button files...")
    bot.infinity_polling(skip_pending=True)
