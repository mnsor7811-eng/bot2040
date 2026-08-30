import telebot
from config import TOKEN
from handlers.general import register_general_handlers
from handlers.numbers import register_numbers_handlers
from handlers.smm import register_smm_handlers

# تهيئة البوت الأساسية
bot = telebot.TeleBot(TOKEN, parse_mode='Markdown')

# تسجيل جميع المعالجات (Handlers) من الملفات المستقلة
register_general_handlers(bot)
register_numbers_handlers(bot)
register_smm_handlers(bot)

if __name__ == '__main__':
    print("🚀 Bot is running successfully with modular file structure...")
    bot.infinity_polling(skip_pending=True)
