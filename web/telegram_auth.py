"""Web-based Telegram authentication handler"""

import os
from typing import Dict, Tuple, Optional
from telethon import TelegramClient


class WebTelegramAuth:
    """Handles Telegram authentication via web interface (phone + code)"""

    def __init__(self, api_id: int, api_hash: str, session_name: str = "aibi_session"):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        # Store temporary client instances during auth process
        self.pending_auth: Dict[str, Dict] = {}

    async def send_code_request(self, phone: str) -> Tuple[bool, str]:
        """
        Step 1: Send verification code to phone

        Args:
            phone: Phone number with country code (e.g., "+1234567890")

        Returns:
            (success: bool, message: str)
        """
        try:
            # Create temporary client for this phone
            temp_client = TelegramClient(f"temp_{phone}", self.api_id, self.api_hash)
            await temp_client.connect()

            # Request code
            result = await temp_client.send_code_request(phone)

            # Store client and hash for verification step
            self.pending_auth[phone] = {
                'client': temp_client,
                'phone_code_hash': result.phone_code_hash,
                'phone': phone
            }

            return True, f"Code sent to {phone}"

        except Exception as e:
            return False, f"Failed to send code: {str(e)}"

    async def verify_code(self, phone: str, code: str) -> Tuple[bool, str]:
        """
        Step 2: Verify code and create authenticated session

        Args:
            phone: Phone number (must match send_code_request call)
            code: Verification code received via Telegram

        Returns:
            (success: bool, message: str)
        """
        try:
            # Get temp auth data
            if phone not in self.pending_auth:
                return False, "Code request not found for this phone. Start over."

            auth_data = self.pending_auth[phone]
            client = auth_data['client']
            phone_code_hash = auth_data['phone_code_hash']

            # Verify code and sign in
            await client.sign_in(
                phone=phone,
                code=code,
                phone_code_hash=phone_code_hash
            )

            # Get authenticated user info
            me = await client.get_me()

            # Disconnect and cleanup
            await client.disconnect()
            del self.pending_auth[phone]

            # Create new session with authenticated credentials
            # The TelegramClient will now use the session file for future connections
            session_client = TelegramClient(self.session_name, self.api_id, self.api_hash)
            await session_client.connect()

            # Sign in again to create persistent session
            await session_client.sign_in(
                phone=phone,
                code=code,
                phone_code_hash=phone_code_hash
            )

            await session_client.disconnect()

            return True, f"Authenticated as {me.first_name} ({phone})"

        except Exception as e:
            # Cleanup on error
            if phone in self.pending_auth:
                try:
                    await self.pending_auth[phone]['client'].disconnect()
                except:
                    pass
                del self.pending_auth[phone]

            return False, f"Verification failed: {str(e)}"

    async def is_session_valid(self) -> bool:
        """Check if session file exists and is valid"""
        try:
            client = TelegramClient(self.session_name, self.api_id, self.api_hash)
            if not client.session.auth_key:
                return False

            await client.connect()
            me = await client.get_me()
            await client.disconnect()
            return me is not None

        except Exception:
            return False
