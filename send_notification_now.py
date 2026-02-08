import asyncio
import os
from telethon import TelegramClient
from telethon.tl.custom.button import Button
from dotenv import load_dotenv

print("[DIRECT NOTIFICATION] Starting...")

load_dotenv()
API_ID = int(os.getenv("TG_API_ID"))
API_HASH = os.getenv("TG_API_HASH")
OWNER_ID = int(os.getenv("OWNER_TELEGRAM_ID"))

async def send_notification():
    print("[DIRECT NOTIFICATION] Creating client with aibi_session...")
    client = TelegramClient('aibi_session', API_ID, API_HASH)

    try:
        print("[DIRECT NOTIFICATION] Connecting...")
        await client.connect()

        if not await client.is_user_authorized():
            print("[ERROR] Session not authorized")
            return

        print("[DIRECT NOTIFICATION] Connected! Preparing notification...")

        # Create notification for Ілля (87% confidence)
        notification = (
            f"NEW MESSAGE from Ілля (ID: 526791303)\n\n"
            f"MESSAGE:\n"
            f"Rr\n"
            f"Пришл список задач?\n"
            f"Записав так щоб не про них забут\n"
            f"Відправ мені\n\n"
            f"AI DRAFT:\n"
            f"Привіт! Звісно, зараз надішлю список задач. "
            f"Дуже добре, що хочеш все організувати!\n\n"
            f"Choose action:"
        )

        # Create interactive buttons
        buttons = [
            [
                Button.inline("[OK] Send Response", f"send_526791303"),
                Button.inline("[EDIT] Edit Draft", f"edit_526791303"),
            ],
            [
                Button.inline("[X] Ignore", f"skip_526791303"),
            ]
        ]

        print(f"[DIRECT NOTIFICATION] Sending to owner {OWNER_ID}...")
        await client.send_message(
            OWNER_ID,
            notification,
            buttons=buttons
        )

        print("[DIRECT NOTIFICATION] [SUCCESS] Notification sent!")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()
        print("[DIRECT NOTIFICATION] Disconnected")

if __name__ == "__main__":
    asyncio.run(send_notification())
