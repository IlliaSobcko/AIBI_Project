"""
Standalone Button Listener - Handles callback queries without bot service
Uses aibi_session (user account) to listen for button clicks
"""
import asyncio
import os
from telethon import TelegramClient, events
from telethon.sessions import MemorySession
from dotenv import load_dotenv

print("[BUTTON LISTENER] Starting standalone button listener...")

load_dotenv()
API_ID = int(os.getenv("TG_API_ID"))
API_HASH = os.getenv("TG_API_HASH")
OWNER_ID = int(os.getenv("OWNER_TELEGRAM_ID"))

async def main():
    print("[BUTTON LISTENER] Creating client with MemorySession...")
    # Use MemorySession to avoid database locks
    client = TelegramClient(MemorySession(), API_ID, API_HASH)

    # Load session from file
    print("[BUTTON LISTENER] Loading aibi_session credentials...")
    session_client = TelegramClient('aibi_session', API_ID, API_HASH)
    await session_client.connect()

    if not await session_client.is_user_authorized():
        print("[ERROR] aibi_session not authorized!")
        return

    print("[BUTTON LISTENER] Session authorized!")

    # Register callback handler
    @session_client.on(events.CallbackQuery())
    async def button_handler(event):
        # Only process if from owner
        if event.sender_id != OWNER_ID:
            await event.answer("Unauthorized", alert=True)
            return

        data = event.data.decode() if isinstance(event.data, bytes) else event.data
        print(f"[BUTTON CLICK] Received: {data}")

        try:
            action, chat_id_str = data.split("_", 1)
            chat_id = int(chat_id_str)

            message = event.message
            message_text = message.text or ""

            if action == "send":
                # Extract AI draft
                if "AI DRAFT:" in message_text:
                    draft_text = message_text.split("AI DRAFT:")[1].split("\n\nChoose action:")[0].strip()
                else:
                    await event.answer("Draft not found", alert=True)
                    return

                print(f"[SEND] Sending to chat {chat_id}...")
                await event.answer("Sending message...", alert=False)

                # Send using same client
                await session_client.send_message(chat_id, draft_text)

                await event.edit(
                    f"{message_text}\n\n[SUCCESS] Message sent to chat {chat_id}",
                    buttons=None
                )
                print(f"[SEND] [SUCCESS] Message delivered to {chat_id}")

            elif action == "edit":
                await event.answer("Reply with edited message", alert=False)
                await event.edit(
                    f"{message_text}\n\n[WAITING FOR YOUR EDIT...]",
                    buttons=None
                )
                print(f"[EDIT] Waiting for manual edit for chat {chat_id}")

            elif action == "skip":
                await event.answer("Draft deleted", alert=False)
                await event.edit(
                    f"{message_text}\n\n[SKIPPED BY USER]",
                    buttons=None
                )
                print(f"[SKIP] Draft skipped for chat {chat_id}")

        except Exception as e:
            print(f"[ERROR] {e}")
            import traceback
            traceback.print_exc()
            await event.answer(f"Error: {e}", alert=True)

    print("[BUTTON LISTENER] [OK] Listening for button clicks...")
    print("[BUTTON LISTENER] Press Ctrl+C to stop")

    # Run forever
    await session_client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
