import os
import asyncio
from flask import Flask
from telethon import TelegramClient
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from telegram.ext import ConversationHandler
from threading import Thread

# Инициализация Flask
app = Flask(__name__)

# Ваши данные для подключения
api_id = 26071362  # Замените на свой api_id
api_hash = 'c3d12bc02851cde9de371fa1a919bd76'  # Замените на свой api_hash
bot_token = '7525592619:AAGJVfadSQFlR10qAxhVVtsm_xKxhJsmyFw'  # Токен вашего бота

# Инициализация клиента
client = TelegramClient('session_name', api_id, api_hash)

# Статусные переменные для пользователя
TYPING_MESSAGE, TYPING_INTERVAL, TYPING_CHAT_ID, TYPING_PHONE, TYPING_CODE = range(5)

# Flask route для проверки работы
@app.route('/')
def home():
    return "Telegram Bot is running!"

# Функция старта для бота
def start(update: Update, context: CallbackContext):
    update.message.reply_text('Привет! Я помогу тебе настроить автоматическую отправку сообщений. '
                              'Введите сообщение, которое хотите отправлять:')
    return TYPING_MESSAGE

# Обработка сообщения, которое будет отправлять бот
def message(update: Update, context: CallbackContext):
    context.user_data['message'] = update.message.text
    update.message.reply_text(f'Отлично! Я буду отправлять сообщение: "{update.message.text}". '
                              'Теперь укажи интервал (в секундах) между сообщениями:')
    return TYPING_INTERVAL

# Обработка интервала времени
def interval(update: Update, context: CallbackContext):
    try:
        interval = int(update.message.text)
        context.user_data['interval'] = interval
        update.message.reply_text(f'Интервал установлен на {interval} секунд. '
                                  'Теперь отправь мне ID чата, куда я должен отправлять сообщения:')
        return TYPING_CHAT_ID
    except ValueError:
        update.message.reply_text('Пожалуйста, введите число, которое будет интервалом в секундах.')
        return TYPING_INTERVAL

# Обработка ID чата
def chat_id(update: Update, context: CallbackContext):
    try:
        chat_id = int(update.message.text)
        context.user_data['chat_id'] = chat_id
        update.message.reply_text(f'Чат ID установлен: {chat_id}. Я буду отправлять сообщение "{context.user_data["message"]}" каждые {context.user_data["interval"]} секунд.')
        update.message.reply_text('Теперь отправь мне номер телефона для авторизации (формат +1234567890):')
        return TYPING_PHONE
    except ValueError:
        update.message.reply_text('Пожалуйста, введите действительный ID чата.')
        return TYPING_CHAT_ID

# Обработка номера телефона пользователя
def phone_number(update: Update, context: CallbackContext):
    context.user_data['phone'] = update.message.text
    update.message.reply_text('Спасибо! Я отправлю тебе код авторизации на твой телефон. Пожалуйста, введи его.')
    
    # Запуск авторизации через Telethon
    asyncio.create_task(start_telethon_auth(update, context.user_data))
    
    return TYPING_CODE

# Обработка кода, который пользователь введет из SMS
def code(update: Update, context: CallbackContext):
    context.user_data['code'] = update.message.text
    update.message.reply_text('Спасибо за ввод кода! Теперь я начну работать.')
    
    # После того как код получен, отправляем сообщение
    asyncio.create_task(send_message(context.user_data))

    return ConversationHandler.END

# Функция для авторизации через Telethon
async def start_telethon_auth(update, user_data):
    await client.start(phone=user_data['phone'])
    await client.send_code_request(user_data['phone'])
    update.message.reply_text("Я отправил код на ваш номер. Пожалуйста, введите его:")

# Функция для отправки сообщений через Telethon
async def send_message(user_data):
    await client.start(phone=user_data['phone'])
    chat_id = user_data['chat_id']
    message = user_data['message']
    interval = user_data['interval']
    
    while True:
        try:
            await client.send_message(chat_id, message)
            print(f"Сообщение отправлено в чат {chat_id}: {message}")
            await asyncio.sleep(interval)
        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")

# Основная функция для запуска бота
async def main():
    # Создание приложения
    application = Application.builder().token(bot_token).build()
    
    # Добавление обработчиков
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            TYPING_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, message)],
            TYPING_INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, interval)],
            TYPING_CHAT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, chat_id)],
            TYPING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone_number)],
            TYPING_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, code)],
        },
        fallbacks=[],
    )
    application.add_handler(conv_handler)
    
    # Запуск бота
    await application.run_polling()

# Запуск Flask в отдельном потоке
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    # Запуск Flask в фоновом режиме
    thread = Thread(target=run_flask)
    thread.daemon = True
    thread.start()

    # Запуск Telegram клиента
    asyncio.run(main())
