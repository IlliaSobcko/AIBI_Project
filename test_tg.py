"""
Simple test script to verify Telegram message sending using telegram_service.py
Sends one "Hello" message to OWNER_TELEGRAM_ID
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
from telegram_service import TelegramService


async def main():
    """Test sending a simple message"""
    # Load environment variables
    load_dotenv()

    api_id = os.getenv("TG_API_ID")
    api_hash = os.getenv("TG_API_HASH")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    owner_id = os.getenv("OWNER_TELEGRAM_ID")

    # Validate configuration
    if not all([api_id, api_hash, bot_token, owner_id]):
        print("[ERROR] Missing required environment variables:")
        print(f"  TG_API_ID: {bool(api_id)}")
        print(f"  TG_API_HASH: {bool(api_hash)}")
        print(f"  TELEGRAM_BOT_TOKEN: {bool(bot_token)}")
        print(f"  OWNER_TELEGRAM_ID: {bool(owner_id)}")
        return False

    print("[OK] All environment variables loaded")
    print(f"[OK] Target user ID: {owner_id}")

    try:
        # Create and connect service
        service = TelegramService(
            api_id=int(api_id),
            api_hash=api_hash,
            bot_token=bot_token,
            session_name="test_tg_service"
        )

        print("\n[TEST] Connecting to Telegram...")
        if not await service.connect():
            print("[ERROR] Failed to connect")
            return False

        # Send simple test message
        print("\n[TEST] Sending 'Hello' message...")
        message_text = "Hello"
        success = await service.send_message(
            recipient_id=int(owner_id),
            text=message_text
        )

        if success:
            print("[OK] Test PASSED - Message sent successfully")
            return True
        else:
            print("[ERROR] Test FAILED - Message not sent")
            return False

    except Exception as e:
        print(f"[ERROR] Test error: {type(e).__name__}: {e}")
        import traceback
        print(traceback.format_exc())
        return False

    finally:
        # Cleanup
        if 'service' in locals():
            await service.disconnect()


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n[WARN] Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Unhandled error: {type(e).__name__}: {e}")
        import traceback
        print(traceback.format_exc())
        sys.exit(1)
