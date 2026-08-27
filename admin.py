import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def register_admin_handlers(bot, ADMIN_ID, get_db_func):

    @bot.callback_query_handler(func=lambda call: call.data == "admin_panel")
    def admin_panel_handler(call):
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        message_id = call.message.message_id

        if str(user_id) != str(ADMIN_ID):
            bot.answer_callback_query(call.id, "❌ عذراً، هذه اللوحة خاصة بالمشرف فقط.", show_alert=True)
            return

        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("📊 إحصائيات البوت", callback_data="admin_stats"))
        markup.row(InlineKeyboardButton("📢 إرسال رسالة للجميع", callback_data="admin_broadcast"))
        markup.row(InlineKeyboardButton("💰 شحن رصيد لمستخدم", callback_data="admin_add_balance"))
        markup.row(InlineKeyboardButton("🚫 حظر / إلغاء حظر مستخدم", callback_data="admin_ban_menu"))
        markup.row(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))

        try:
            bot.edit_message_text("⚙️ **أهلاً بك في لوحة الإدارة الكبرى**\n\nاختر العملية التي تريد تنفيذها:", chat_id, message_id, parse_mode="Markdown", reply_markup=markup)
        except Exception:
            bot.send_message(chat_id, "⚙️ **أهلاً بك في لوحة الإدارة الكبرى**\n\nاختر العملية التي تريد تنفيذها:", parse_mode="Markdown", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
    def admin_stats_handler(call):
        user_id = call.from_user.id
        if str(user_id) != str(ADMIN_ID):
            return

        conn = get_db_func()
        cursor = conn.cursor()
        
        # إجمالي المستخدمين
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        # إجمالي عمليات الشراء
        cursor.execute("SELECT COUNT(*), SUM(cost) FROM purchases")
        purchases_data = cursor.fetchone()
        total_purchases = purchases_data[0] or 0
        total_spent = purchases_data[1] or 0.0
        
        conn.close()

        msg = (f"📊 **إحصائيات البوت الشاملة:**\n\n"
               f"👥 إجمالي المستخدمين: `{total_users}`\n"
               f"🛍️ إجمالي عمليات شراء الأرقام: `{total_purchases}`\n"
               f"💵 إجمالي مبالغ العمليات: `${total_spent:.2f}`")

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 رجوع لوحة الإدارة", callback_data="admin_panel"))
        
        try:
            bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        except Exception:
            bot.send_message(call.message.chat.id, msg, parse_mode="Markdown", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data in ["admin_broadcast", "admin_add_balance", "admin_ban_menu"])
    def admin_sub_menus(call):
        user_id = call.from_user.id
        if str(user_id) != str(ADMIN_ID):
            return

        chat_id = call.message.chat.id
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 رجوع لوحة الإدارة", callback_data="admin_panel"))

        if call.data == "admin_broadcast":
            bot.send_message(chat_id, "📢 أرسل النص أو الوسائط التي تريد إذاعتها لجميع المستخدمين الآن:", reply_markup=markup)
        elif call.data == "admin_add_balance":
            bot.send_message(chat_id, "💰 أرسل الآيدي والمبلغ بالشكل التالي:\n`ID المبلغ`\nمثال: `123456789 5.5`", parse_mode="Markdown", reply_markup=markup)
        elif call.data == "admin_ban_menu":
            bot.send_message(chat_id, "🚫 أرسل آيدي المستخدم المراد حظره أو إلغاء حظره:", reply_markup=markup)
