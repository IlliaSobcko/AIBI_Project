"""
Простий скрипт для отримання вашого Telegram ID
Запустіть цей скрипт, він виведе ваш ID який потрібно додати в .env
"""

import os
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv()

async def get_my_id():
    api_id = int(os.getenv("TG_API_ID"))
    api_hash = os.getenv("TG_API_HASH")

    # Використовуємо існуючу сесію
    client = TelegramClient("aibi_session", api_id, api_hash)
    await client.connect()

    if not await client.is_user_authorized():
        print("Помилка: Потрібна авторизація. Запустіть main.py спочатку.")
        return

    me = await client.get_me()

    print("=" * 50)
    print("ВАШ TELEGRAM ID:")
    print(f"  ID: {me.id}")
    print(f"  Username: @{me.username}")
    print(f"  Ім'я: {me.first_name} {me.last_name or ''}")
    print("=" * 50)
    print(f"\nДодайте це значення в .env файл:")
    print(f"OWNER_TELEGRAM_ID={me.id}")
    print()

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(get_my_id())
