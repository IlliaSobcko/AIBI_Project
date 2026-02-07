import asyncio
import os
import sys
from dotenv import load_dotenv
from draft_bot import DraftReviewBot

# Set UTF-8 encoding for console output on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()

async def test_draft_bot():
    """Test the draft bot sending functionality"""

    api_id = int(os.getenv("TG_API_ID", "0"))
    api_hash = os.getenv("TG_API_HASH", "")
    owner_id = int(os.getenv("OWNER_TELEGRAM_ID", "0"))

    if api_id == 0 or not api_hash or owner_id == 0:
        print("[ERROR] Missing environment variables: TG_API_ID, TG_API_HASH, or OWNER_TELEGRAM_ID")
        return

    print("[TEST] Starting draft bot test...")
    print(f"[TEST] Owner ID: {owner_id}")
    print(f"[TEST] API ID: {api_id}")

    bot = DraftReviewBot(api_id, api_hash, session_name="test_draft_bot")

    try:
        # Connect and start
        if not await bot.start():
            print("[ERROR] Failed to authenticate with Telegram")
            return

        print("[OK] Bot connected and authenticated")

        # Test sending a draft
        test_chat_id = 123456789
        test_chat_title = "Test Chat"
        test_draft = "This is a test draft message for review."
        test_confidence = 65

        print(f"\n[TEST] Sending test draft to owner ({owner_id})...")
        await bot.send_draft_for_review(test_chat_id, test_chat_title, test_draft, test_confidence)

        print("[OK] Test completed! Check your Telegram for the draft message.")
        print("[INFO] If you received the message without 'key is not registered' error, the fix works!")

    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(test_draft_bot())
