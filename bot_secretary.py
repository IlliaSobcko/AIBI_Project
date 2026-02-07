import os
from telethon import TelegramClient, events
from voice_handler import process_voice_message
from dotenv import load_dotenv

load_dotenv()

# Налаштування бота
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
api_id = int(os.getenv("TG_API_ID"))
api_hash = os.getenv("TG_API_HASH")

bot = TelegramClient('bot_session', api_id, api_hash).start(bot_token=bot_token)

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond("🛡️ Вітаю! Я твій секретар AIBI. Надсилай мені голосові інструкції або чекай на звіти.")

@bot.on(events.NewMessage(incoming=True))
async def handle_message(event):
    # Якщо прийшло голосове повідомлення
    if event.voice:
        path = await event.download_media(file="voice_command.ogg")
        await event.respond("🎤 Обробляю твій голос...")
        
        text = process_voice_message(path)
        
        if text:
            await event.respond(f"✅ Додано нове правило:\n\"{text}\"")
        else:
            await event.respond("❌ Не вдалося розпізнати голос.")
        
        if os.path.exists(path): os.remove(path)

async def send_notification(message):
    """Функція для відправки звіту тобі в чат"""
    # Тобі треба дізнатися свій ID. Напиши боту будь-що, і він його виведе в консоль.
    # Для тесту відправимо повідомлення в перший знайдений діалог
    await bot.send_message("me", message) 

if __name__ == "__main__":
    print("Бот запущений...")
    bot.run_until_disconnected()