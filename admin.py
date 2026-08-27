import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def register_admin_handlers(bot, ADMIN_ID, get_db):
    
    # أمر إضافة الرصيد
    @bot.message_handler(commands=['add_bal'])
    def add_balance_cmd(message):
        if str(message.from_user.id) != str(ADMIN_ID):
            return
        try:
            parts = message.text.split()
            target_id = int(parts[1])
            amount = float(parts[2])
            
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_id))
            conn.commit()
            conn.close()
            
            bot.reply_to(message, f"✅ تمت إضافة ${amount:.2f} بنجاح إلى حساب المعرف: {target_id}")
        except Exception:
            bot.reply_to(message, "❌ طريقة الاستخدام الخاطئة!\nارسل الأمر كالتالي:\n/add_bal USER_ID AMOUNT")

    # لوحة الإدارة عبر الـ Callback
    @bot.callback_query_handler(func=lambda call: call.data == "admin_panel")
    def admin_panel_callback(call):
        user_id = call.from_user.id
        if str(user_id) != str(ADMIN_ID):
            return
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        u_count = cursor.fetchone()[0]
        conn.close()
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_main"))
        
        text = f"⚙️ لوحة الإدارة الكبرى:\nإجمالي المستخدمين: {u_count}\n\nلشحن رصيد:\n`/add_bal ID AMOUNT`"
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        except Exception:
            bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=markup)
