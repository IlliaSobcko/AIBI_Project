"""Standalone Telegram message service using direct int IDs (no GetUsersRequest)"""

import asyncio
import traceback
from pathlib import Path
from telethon import TelegramClient
from telethon.errors import AuthKeyUnregisteredError


class TelegramService:
    """Simple service for sending Telegram messages using direct integer IDs"""

    def __init__(self, api_id: int, api_hash: str, bot_token: str, session_name: str = "tg_service"):
        """Initialize Telegram service with bot token"""
        self.api_id = api_id
        self.api_hash = api_hash
        self.bot_token = bot_token
        self.session_name = session_name
        self.client = None
        self.max_retries = 2

    async def connect(self):
        """Connect to Telegram using bot token"""
        print(f"\n[TG_SERVICE] >>> Connecting to Telegram...")
        print(f"[TG_SERVICE] API ID: {self.api_id}")
        print(f"[TG_SERVICE] API Hash: {'*' * 10}...")
        print(f"[TG_SERVICE] Bot Token: ...{self.bot_token[-10:]}")
        print(f"[TG_SERVICE] Session: {self.session_name}")

        for attempt in range(3):
            try:
                print(f"\n[TG_SERVICE] [ATTEMPT {attempt + 1}/3] Creating TelegramClient...")
                self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)

                print(f"[TG_SERVICE] [ATTEMPT {attempt + 1}/3] Connecting to Telegram servers...")
                await self.client.connect()
                print(f"[TG_SERVICE] [ATTEMPT {attempt + 1}/3] [OK] TCP connection established")

                print(f"[TG_SERVICE] [ATTEMPT {attempt + 1}/3] Starting with bot token...")
                await self.client.start(bot_token=self.bot_token)
                print(f"[TG_SERVICE] [ATTEMPT {attempt + 1}/3] [OK] Bot authenticated")

                # Verify connection
                me = await self.client.get_me()
                print(f"[TG_SERVICE] [OK] [SUCCESS] Connected as bot: @{me.username if me.username else 'no_username'}")
                print(f"[TG_SERVICE] [OK] Bot ID: {me.id}")
                print(f"[TG_SERVICE] [OK] Bot is valid: {me.is_bot}")
                print(f"[TG_SERVICE] [OK] Session is active and ready for messaging")
                return True

            except AuthKeyUnregisteredError as e:
                print(f"[TG_SERVICE] [ERROR] [AUTH ERROR] Attempt {attempt + 1}/3")
                print(f"[TG_SERVICE] Error: {e}")
                print(f"[TG_SERVICE] Cleaning up session files...")
                await self._recover_from_auth_error()
                if attempt < 2:
                    wait_time = 2 ** attempt
                    print(f"[TG_SERVICE] Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)

            except Exception as e:
                print(f"[TG_SERVICE] [ERROR] [ERROR] Attempt {attempt + 1}/3: {type(e).__name__}")
                print(f"[TG_SERVICE] Message: {e}")
                if attempt < 2:
                    wait_time = 2 ** attempt
                    print(f"[TG_SERVICE] Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"[TG_SERVICE] [LAST ATTEMPT] Traceback:\n{traceback.format_exc()}")

        print(f"\n[TG_SERVICE] [ERROR] [CRITICAL FAILURE] Could not connect after 3 attempts")
        print(f"[TG_SERVICE] Check your Telegram credentials and internet connection")
        return False

    async def send_message(self, recipient_id: int, text: str, buttons=None):
        """
        Send a message to a recipient using direct int ID (no entity lookup).

        Args:
            recipient_id: Integer Telegram user ID (not username)
            text: Message text
            buttons: Optional Telethon button objects

        Returns:
            True if successful, False otherwise
        """
        print(f"\n[TG_SERVICE] >>> send_message() called")
        print(f"[TG_SERVICE] Recipient ID: {recipient_id} (type: {type(recipient_id).__name__})")
        print(f"[TG_SERVICE] Text length: {len(text)} chars")
        print(f"[TG_SERVICE] Has buttons: {buttons is not None}")
        print(f"[TG_SERVICE] Client connected: {self.client is not None and self.client.is_connected() if self.client else False}")

        if not self.client:
            print(f"[TG_SERVICE] [ERROR] [ERROR] Client is None!")
            return False

        if not self.client.is_connected():
            print(f"[TG_SERVICE] [ERROR] [ERROR] Client not connected to Telegram!")
            return False

        print(f"[TG_SERVICE] [OK] Client is ready. Starting message send attempts...")

        for attempt in range(self.max_retries):
            try:
                print(f"[TG_SERVICE] [ATTEMPT {attempt + 1}/{self.max_retries}] Sending message...")
                # DIRECT INT ID - Critical to avoid GetUsersRequest error
                await self.client.send_message(
                    int(recipient_id),  # Use int directly, no entity lookup
                    text,
                    buttons=buttons
                )
                print(f"[TG_SERVICE] [OK] [SUCCESS] Message delivered to {recipient_id}")
                return True

            except AuthKeyUnregisteredError as e:
                print(f"[TG_SERVICE] [WARN]  [AUTH ERROR] Attempt {attempt + 1}/{self.max_retries}")
                print(f"[TG_SERVICE] Error: {e}")
                await self._recover_from_auth_error()
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"[TG_SERVICE] Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)

            except Exception as e:
                print(f"[TG_SERVICE] [ERROR] [ERROR] Attempt {attempt + 1}/{self.max_retries}")
                print(f"[TG_SERVICE] Exception: {type(e).__name__}: {e}")
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"[TG_SERVICE] Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"[TG_SERVICE] [LAST ATTEMPT FAILED] Full traceback:\n{traceback.format_exc()}")

        print(f"[TG_SERVICE] [ERROR] [FINAL FAILURE] Could not send message after {self.max_retries} attempts")
        return False

    async def disconnect(self):
        """Disconnect from Telegram"""
        if self.client and self.client.is_connected():
            await self.client.disconnect()
            print("[TG_SERVICE] [OK] Disconnected from Telegram")

    async def _recover_from_auth_error(self):
        """Clean up session files after auth error"""
        try:
            session_files = [
                f"{self.session_name}.session",
                f"{self.session_name}.session-journal",
                f"{self.session_name}.db",
                f"{self.session_name}-journal",
            ]

            for session_file in session_files:
                session_path = Path(session_file)
                if session_path.exists():
                    session_path.unlink()
                    print(f"[TG_SERVICE] [OK] Cleaned: {session_file}")

            if self.client and self.client.is_connected():
                await self.client.disconnect()
        except Exception as e:
            print(f"[TG_SERVICE] [ERROR] Recovery error: {type(e).__name__}: {e}")
