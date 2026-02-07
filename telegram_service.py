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
        for attempt in range(3):
            try:
                print(f"[TG_SERVICE] Connection attempt {attempt + 1}/3...")
                self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
                await self.client.connect()
                await self.client.start(bot_token=self.bot_token)
                print("[TG_SERVICE] [OK] Connected to Telegram with Bot API")
                return True
            except AuthKeyUnregisteredError as e:
                print(f"[TG_SERVICE] [ERROR] AuthKeyUnregisteredError: {e}")
                await self._recover_from_auth_error()
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                print(f"[TG_SERVICE] [ERROR] Connection error: {type(e).__name__}: {e}")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)

        print("[TG_SERVICE] [ERROR] Failed to connect after 3 attempts")
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
        if not self.client:
            print("[TG_SERVICE] [ERROR] Client not connected")
            return False

        for attempt in range(self.max_retries):
            try:
                # DIRECT INT ID - Critical to avoid GetUsersRequest error
                await self.client.send_message(
                    int(recipient_id),  # Use int directly, no entity lookup
                    text,
                    buttons=buttons
                )
                print(f"[TG_SERVICE] [OK] Message sent to {recipient_id}")
                return True

            except AuthKeyUnregisteredError as e:
                print(f"[TG_SERVICE] [ERROR] Auth error on attempt {attempt + 1}/{self.max_retries}")
                await self._recover_from_auth_error()
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

            except Exception as e:
                print(f"[TG_SERVICE] [ERROR] Error on attempt {attempt + 1}/{self.max_retries}")
                print(f"[TG_SERVICE] {type(e).__name__}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    print(f"[TG_SERVICE] Full traceback:\n{traceback.format_exc()}")

        print(f"[TG_SERVICE] [ERROR] Failed to send message after {self.max_retries} attempts")
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
