"""
MANUAL PHONE AUTHENTICATION SCRIPT

This script allows you to authenticate your Telegram account interactively
via console input. Use this if the Web UI keeps timing out.

IMPORTANT: This will wait INDEFINITELY for your phone code input.
NO AUTO-RESTART, NO TIMEOUT.

Usage:
    python manual_phone_auth.py
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from telethon import TelegramClient

# Load environment variables
load_dotenv()

# Get credentials from .env
API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
SESSION_NAME = "aibi_session"

print("=" * 80)
print("MANUAL TELEGRAM PHONE AUTHENTICATION")
print("=" * 80)
print()
print(f"API ID: {API_ID}")
print(f"API Hash: {'*' * 10}...{API_HASH[-4:]}")
print(f"Session file: {SESSION_NAME}.session")
print()

# Check if session already exists
session_file = Path(f"{SESSION_NAME}.session")
if session_file.exists():
    print(f"⚠️  WARNING: Session file already exists: {session_file}")
    response = input("Delete existing session and start fresh? (yes/no): ").strip().lower()
    if response == 'yes':
        try:
            session_file.unlink()
            print(f"✅ Deleted {session_file}")
        except Exception as e:
            print(f"❌ Failed to delete session: {e}")
            print("Please delete it manually and try again")
            exit(1)
    else:
        print("Keeping existing session. Attempting to use it...")


async def authenticate():
    """Authenticate user account with INFINITE WAIT for code entry"""

    print()
    print("=" * 80)
    print("STEP 1: ENTER YOUR PHONE NUMBER")
    print("=" * 80)
    print()
    print("Format: +1234567890 (with country code)")
    print()

    phone = input("Phone number: ").strip()

    if not phone:
        print("❌ Phone number cannot be empty")
        return False

    print()
    print(f"📱 Using phone: {phone}")
    print()
    print("=" * 80)
    print("CONNECTING TO TELEGRAM...")
    print("=" * 80)
    print()

    try:
        # Create client
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

        print("Connecting to Telegram servers...")
        await client.connect()
        print("✅ Connected!")

        # Check if already authorized
        if await client.is_user_authorized():
            me = await client.get_me()
            print()
            print("=" * 80)
            print("✅ ALREADY AUTHENTICATED!")
            print("=" * 80)
            print(f"Name: {me.first_name} {me.last_name or ''}")
            print(f"Username: @{me.username or 'none'}")
            print(f"Phone: {me.phone or phone}")
            print(f"User ID: {me.id}")
            print()
            await client.disconnect()
            return True

        print()
        print("=" * 80)
        print("STEP 2: REQUESTING VERIFICATION CODE")
        print("=" * 80)
        print()
        print(f"Sending code to {phone}...")

        # Request code
        await client.send_code_request(phone)

        print()
        print("✅ CODE SENT!")
        print()
        print("Check your Telegram app for the verification code.")
        print("It may arrive as:")
        print("  - Telegram message (if you have Telegram installed)")
        print("  - SMS text message")
        print()
        print("=" * 80)
        print("STEP 3: ENTER VERIFICATION CODE")
        print("=" * 80)
        print()
        print("IMPORTANT:")
        print("  - This script will wait INDEFINITELY for your input")
        print("  - NO TIMEOUT, NO AUTO-RESTART")
        print("  - Take your time, the session will stay open")
        print()

        # Wait indefinitely for code input
        code = input("Enter verification code: ").strip()

        if not code:
            print("❌ Code cannot be empty")
            await client.disconnect()
            return False

        print()
        print(f"Verifying code: {code[:2]}***{code[-2:]}")
        print()

        # Sign in with code
        try:
            await client.sign_in(phone, code)
            print("✅ CODE VERIFIED!")
        except Exception as e:
            print(f"❌ Sign in failed: {e}")
            print()
            print("Possible issues:")
            print("  - Code expired (request a new one)")
            print("  - Code is incorrect (check for typos)")
            print("  - 2FA enabled (password required)")

            # Check if 2FA password needed
            if "password" in str(e).lower() or "2fa" in str(e).lower():
                print()
                print("=" * 80)
                print("2FA PASSWORD REQUIRED")
                print("=" * 80)
                print()
                password = input("Enter your 2FA password: ").strip()
                if password:
                    try:
                        await client.sign_in(password=password)
                        print("✅ 2FA PASSWORD VERIFIED!")
                    except Exception as pw_error:
                        print(f"❌ 2FA verification failed: {pw_error}")
                        await client.disconnect()
                        return False
            else:
                await client.disconnect()
                return False

        # Get user info
        me = await client.get_me()

        print()
        print("=" * 80)
        print("✅ AUTHENTICATION SUCCESSFUL!")
        print("=" * 80)
        print()
        print(f"Name: {me.first_name} {me.last_name or ''}")
        print(f"Username: @{me.username or 'none'}")
        print(f"Phone: {me.phone or phone}")
        print(f"User ID: {me.id}")
        print()
        print(f"Session saved to: {SESSION_NAME}.session")
        print()
        print("You can now use this session in the main AIBI application.")
        print("The Web UI will automatically use this authenticated session.")
        print()

        await client.disconnect()
        return True

    except KeyboardInterrupt:
        print()
        print()
        print("❌ Authentication cancelled by user (Ctrl+C)")
        if 'client' in locals():
            await client.disconnect()
        return False

    except Exception as e:
        print()
        print(f"❌ Authentication failed: {e}")
        import traceback
        traceback.print_exc()
        if 'client' in locals():
            await client.disconnect()
        return False


if __name__ == "__main__":
    if API_ID == 0 or not API_HASH:
        print("❌ ERROR: Telegram credentials not found in .env")
        print()
        print("Please add to your .env file:")
        print("  TELEGRAM_API_ID=your_api_id")
        print("  TELEGRAM_API_HASH=your_api_hash")
        print()
        print("Get these from: https://my.telegram.org/apps")
        exit(1)

    try:
        success = asyncio.run(authenticate())
        if success:
            print()
            print("=" * 80)
            print("✅ ALL DONE!")
            print("=" * 80)
            print()
            print("Next steps:")
            print("  1. Run your main AIBI server: python main.py")
            print("  2. The server will use the authenticated session automatically")
            print("  3. No need to enter phone code again")
            print()
            exit(0)
        else:
            print()
            print("=" * 80)
            print("❌ AUTHENTICATION FAILED")
            print("=" * 80)
            print()
            print("Please try again or check your credentials")
            exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
