import asyncio
import os
from telethon import TelegramClient
from dotenv import load_dotenv

print("[START] Скрипт завантажується...")

load_dotenv()
API_ID = int(os.getenv("TG_API_ID"))
API_HASH = os.getenv("TG_API_HASH")

async def test():
    print("[STEP 1] Спроба ініціалізації клієнта...")
    client = TelegramClient('aibi_session', API_ID, API_HASH)
    
    try:
        print("[STEP 2] Підключення до Telegram API...")
        await client.connect()
        
        if not await client.is_user_authorized():
            print("[!!!] ПОМИЛКА: Сесія не авторизована. Потрібен вхід.")
            return

        print("[STEP 3] Отримання даних акаунта...")
        me = await client.get_me()
        print(f"[SUCCESS] Увійшов як: {me.first_name} | ID: {me.id} | Phone: {me.phone}")

        print("[STEP 4] Надсилаю повідомлення клієнту...")
# STEP 4: Надсилаю повідомлення клієнту
        # Заміни 'username_тут' на реальний нікнейм (наприклад, '@illia_name')
        # Або встав числовий ID, якщо ти його знаєш
        target = '@IlliaSxs' 
        
        print(f"[STEP 4] Надсилаю повідомлення для {target}...")
        try:
            await client.send_message(target, 'Привіт! Це фінальний тест зв’язку через Python. Система майже готова до роботи!')
            print(f"[FINISH] Повідомлення для {target} відправлено успішно!")
        except Exception as e:
            print(f"[ERR] Не вдалося відправити клієнту: {e}")
            print("Порада: Можливо, клієнт ще не писав боту першим?")
    except Exception as e:
        print(f"[CRITICAL ERROR] Щось пішло не так: {e}")
    finally:
        await client.disconnect()
        print("[END] З'єднання розірвано.")

if __name__ == "__main__":
    asyncio.run(test())