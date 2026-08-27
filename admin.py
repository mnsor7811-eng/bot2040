from telebot import types

def register_admin_handlers(bot, ADMIN_ID, get_db):
    
    # دالة التحقق من أن المستخدم هو الأدمن
    def is_admin(user_id):
        return str(user_id) == str(ADMIN_ID)

    # 1. زر أو أمر لوحة الإدارة الكبرى
    @bot.message_handler(func=lambda message: message.text == "⚙️ لوحة الإدارة الكبرى")
    def admin_panel(message):
        if not is_admin(message.from_user.id):
            return
        
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            users_count = cursor.fetchone()[0]
            conn.close()
        except Exception:
            users_count = 0

        # إنشاء الأزرار التفاعلية للوحة الإدارة
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn_broadcast = types.InlineKeyboardButton("📢 إذاعة رسالة", callback_data="admin_broadcast")
        btn_stats = types.InlineKeyboardButton("📊 إحصائيات تفصيلية", callback_data="admin_stats")
        markup.add(btn_broadcast, btn_stats)
        
        text = (
            f"⚙️ **لوحة الإدارة الكبرى:**\n"
            f"👥 إجمالي المستخدمين: {users_count}\n\n"
            f"🔹 لشحن رصيد لمستخدم عبر الأمر المباشر:\n"
            f"`/add_bal ID AMOUNT`\n\n"
            f"اختر أحد الإجراءات أدناه:"
        )
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

    # 2. أمر شحن الرصيد المباشر
    @bot.message_handler(commands=['add_bal'])
    def add_balance(message):
        if not is_admin(message.from_user.id):
            return
        
        args = message.text.split()
        if len(args) < 3:
            bot.reply_to(message, "⚠️ خطأ! استخدم الأمر هكذا:\n`/add_bal ID AMOUNT`", parse_mode="Markdown")
            return
        
        try:
            target_id = int(args[1])
            amount = float(args[2])
        except ValueError:
            bot.reply_to(message, "⚠️ الآيدي أو المبلغ غير صحيح. تأكد من إرسال أرقام صحيحة.")
            return

        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_id))
            conn.commit()
            conn.close()
            bot.reply_to(message, f"✅ تم شحن مبلغ `${amount:.2f}` للمستخدم `{target_id}` بنجاح.", parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"❌ حدث خطأ أثناء التحديث في قاعدة البيانات: {e}")

    # 3. التعامل مع ضغط الأزرار الشفافة داخل لوحة الإدارة
    @bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
    def admin_callbacks(call):
        if not is_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ ليس لديك صلاحية للقيام بذلك.", show_alert=True)
            return

        if call.data == "admin_broadcast":
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, "📢 أرسل الآن الرسالة التي تريد إذاعتها لجميع المستخدمين:")
        
        elif call.data == "admin_stats":
            try:
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users")
                users_count = cursor.fetchone()[0]
                conn.close()
            except Exception:
                users_count = 0

            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, f"📊 **إحصائيات البوت:**\n- إجمالي الأعضاء: {users_count}\n- حالة السيرفر: يعمل بكفاءة 🚀", parse_mode="Markdown")
