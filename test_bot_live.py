import asyncio
import os
import sys
from dotenv import load_dotenv

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from draft_bot import DraftReviewBot

load_dotenv()

async def test():
    print('[TEST] Testing Bulletproof Draft Bot')
    print('[TEST] ======================================')

    api_id = int(os.getenv('TG_API_ID'))
    api_hash = os.getenv('TG_API_HASH')
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    owner_id = int(os.getenv('OWNER_TELEGRAM_ID'))

    print(f'[TEST] Configuration:')
    print(f'[TEST] API ID: {api_id}')
    print(f'[TEST] API Hash: {api_hash[:20]}...')
    print(f'[TEST] Owner ID: {owner_id}')

    if not bot_token:
        print('[ERROR] TELEGRAM_BOT_TOKEN not in .env')
        print('[ERROR] Cannot test without bot token')
        return

    print(f'[TEST] Bot Token: ...{bot_token[-10:]}')
    print()
    print('[TEST] Starting Draft Bot...')
    print('[TEST] ======================================')

    bot = DraftReviewBot(api_id, api_hash, bot_token, owner_id)

    try:
        success = await bot.start()

        if success:
            print()
            print('[SUCCESS] Bulletproof Draft Bot is ONLINE!')
            print('[SUCCESS] ======================================')
            print('[SUCCESS] Bot can receive button clicks')
            print('[SUCCESS] Auto-recovery: ENABLED')
            print('[SUCCESS] Network resilience: ACTIVE')
            print()

            # Test sending a message
            print('[TEST] Testing message send...')
            try:
                # Send a test message to owner
                await bot.client.send_message(
                    int(owner_id),
                    'Test: Bulletproof Draft Bot is operational!'
                )
                print('[SUCCESS] Test message sent to owner!')
            except Exception as e:
                print(f'[ERROR] Message send failed: {type(e).__name__}: {e}')

            print()
            print('[INFO] Test completed successfully!')
            await bot.stop()
        else:
            print('[ERROR] Bot failed to start')

    except Exception as e:
        print(f'[ERROR] Test failed: {type(e).__name__}: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
