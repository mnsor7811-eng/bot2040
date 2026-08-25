import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# إعدادات التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# بيانات البوت والآدمن الخاصة بك
TOKEN = "8927305428:AAFok7iKK0S4D3px-kdgW1WvAIZjXr3dWH8"
ADMIN_ID = 6113734300
ADMIN_USERNAME = "@Num_s7"

# ==================== الواجهة الرئيسية ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    keyboard = [
        [InlineKeyboardButton("🛒 قائمة الخدمات والمزودين", callback_data="providers"), InlineKeyboardButton("💰 حسابي والرصيد", callback_data="my_account")],
        [InlineKeyboardButton("💳 شحن الحساب", callback_data="recharge"), InlineKeyboardButton("📥 طلباتي", callback_data="my_orders")],
        [InlineKeyboardButton("🛠️ الدعم الفني", callback_data="support")]
    ]
    
    # تظهر لوحة التحكم للإدارة فقط إذا كان الـ ID يطابق ID حسابك
    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("⚙️ لوحة تحكم الإدارة (الآدمن)", callback_data="admin_panel")])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_text = f"أهلاً بك **{update.effective_user.first_name}** في بوت الخدمات الشاملة! 🚀\n\nاختر من القائمة أدناه:"
    
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

# ==================== معالجة الأزرار ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if query.data == "providers":
        btn = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
        await query.edit_message_text("📊 **قائمة المزودين:**\nالخدمات والأسعار متاحة وجاهزة.", reply_markup=InlineKeyboardMarkup(btn), parse_mode="Markdown")
        
    elif query.data == "my_account":
        btn = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
        await query.edit_message_text(f"👤 **معلومات الحساب:**\n\n🆔 المعرف: `{user_id}`\n💵 الرصيد: **0.00 $**", reply_markup=InlineKeyboardMarkup(btn), parse_mode="Markdown")
        
    elif query.data == "recharge":
        btn = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
        await query.edit_message_text(f"💳 **طريقة الشحن:**\nيرجى التواصل مع الإدارة {ADMIN_USERNAME} لإضافة الرصيد.", reply_markup=InlineKeyboardMarkup(btn), parse_mode="Markdown")
        
    elif query.data == "my_orders":
        btn = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
        await query.edit_message_text("📥 **سجل الطلبات:**\nلا توجد طلبات سابقة.", reply_markup=InlineKeyboardMarkup(btn))
        
    elif query.data == "support":
        btn = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
        await query.edit_message_text(f"🛠️ **الدعم الفني:**\nتواصل مباشرة مع المطور والإدارة: {ADMIN_USERNAME}", reply_markup=InlineKeyboardMarkup(btn))
        
    elif query.data == "admin_panel":
        if user_id != ADMIN_ID:
            await query.edit_message_text("⚠️ هذه اللوحة مخصصة للآدمن فقط.")
            return
        btn = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
        await query.edit_message_text("⚙️ **أهلاً بك في لوحة تحكم الإدارة الكاملة.**", reply_markup=InlineKeyboardMarkup(btn))
        
    elif query.data == "main_menu":
        await start(update, context)

# ==================== التشغيل ====================
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("...تم تشغيل البوت بنجاح بالتوكن الجديد")
    app.run_polling()
