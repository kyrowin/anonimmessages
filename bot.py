from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters
import sqlite3

BOT_TOKEN = "YOUR BOT TOKEN"
admin_id = "YOUR CHAT ID"

conn = sqlite3.connect("anonymous_bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT
);
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER,
    receiver_id INTEGER,
    message TEXT
);
""")
conn.commit()

async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    username = update.effective_user.username or "NoUsername"

    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()

    ref_link = f"https://t.me/{context.bot.username}?start={user_id}"

    message = (
        "Добро пожаловать!\n"
        f"Ваша реферальная ссылка: {ref_link}\n\n"
        "Отправьте её кому угодно, чтобы получать анонимные сообщения."
    )
    await update.message.reply_text(message)

async def handle_start_with_ref(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    ref_id = int(context.args[0]) if context.args else None

    if ref_id and ref_id != user_id:
        context.user_data['ref_id'] = ref_id
        await update.message.reply_text(
            "Вы можете отправить анонимное сообщение. Напишите его сюда."
        )
    else:
        await start(update, context)

async def handle_message(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    ref_id = context.user_data.get('ref_id')

    if ref_id:
        cursor.execute(
            "INSERT INTO messages (sender_id, receiver_id, message) VALUES (?, ?, ?)",
            (user_id, ref_id, update.message.text)
        )
        conn.commit()

        await update.message.reply_text(
            "Ваше сообщение отправлено анонимно!\n"
            f"Вот ваша реферальная ссылка: https://t.me/{context.bot.username}?start={user_id}"
        )

        try:
            await context.bot.send_message(
                chat_id=ref_id,
                text=f"Вам пришло анонимное сообщение:\n\n{update.message.text}"
            )
        except Exception:
            pass
    else:
        await update.message.reply_text("Неизвестная команда. Используйте /start.")

async def broadcast(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id != admin_id:
        return

    message = " ".join(context.args)
    if not message:
        await update.message.reply_text("Напишите сообщение для рассылки.")
        return

    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    for user in users:
        try:
            await context.bot.send_message(chat_id=user[0], text=message)
        except Exception:
            pass

    await update.message.reply_text("Сообщение успешно разослано.")

app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", handle_start_with_ref, filters=filters.TEXT))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CommandHandler("broadcast", broadcast))

app.run_polling()
