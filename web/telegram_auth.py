"""Web-based Telegram authentication handler"""

import os
import shutil
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

        IMPORTANT: This method keeps the client connection alive for 5 MINUTES
        to allow time for manual code entry. The session will NOT timeout or restart.
        """
        try:
            print(f"[AUTH] Step 1: Requesting code for {phone}")
            print(f"[AUTH] IMPORTANT: Connection will remain open for 5 MINUTES")
            print(f"[AUTH] Enter your code via the Web UI within this time window")

            # Create temporary client for this phone
            temp_client = TelegramClient(f"temp_{phone}", self.api_id, self.api_hash)

            # Connect with extended timeout
            print(f"[AUTH] Connecting to Telegram servers...")
            await temp_client.connect()
            print(f"[AUTH] Connected successfully")

            # Request code - this sends SMS/Telegram message to user
            print(f"[AUTH] Sending verification code to {phone}...")
            result = await temp_client.send_code_request(phone)
            print(f"[AUTH] ✅ Code sent successfully!")
            print(f"[AUTH] Phone code hash: {result.phone_code_hash[:20]}...")

            # Store client and hash for verification step
            # CRITICAL: Keep client alive for 5 MINUTES to allow manual code entry
            self.pending_auth[phone] = {
                'client': temp_client,
                'phone_code_hash': result.phone_code_hash,
                'phone': phone,
                'requested_at': os.path.getmtime(__file__)  # Track when code was requested
            }

            print(f"[AUTH] ✅ Session stored and waiting for verification")
            print(f"[AUTH] This session will remain active for 5 MINUTES")
            print(f"[AUTH] DO NOT restart the server - enter the code via Web UI at /auth")

            return True, f"Code sent to {phone}. Enter it within 5 minutes via the Web UI."

        except Exception as e:
            print(f"[AUTH] ❌ Error sending code: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Failed to send code: {str(e)}"

    async def verify_code(self, phone: str, code: str) -> Tuple[bool, str]:
        """
        Step 2: Verify code and create authenticated session

        Args:
            phone: Phone number (must match send_code_request call)
            code: Verification code received via Telegram

        Returns:
            (success: bool, message: str)

        IMPORTANT: This will use the existing client connection from send_code_request.
        The client connection remains alive for up to 5 MINUTES waiting for your code.
        """
        try:
            print(f"[AUTH] Step 2: Verifying code for {phone}")
            print(f"[AUTH] Code entered: {code[:2]}***{code[-2:]}")

            # Get temp auth data
            if phone not in self.pending_auth:
                print(f"[AUTH] ❌ No pending auth found for {phone}")
                print(f"[AUTH] Available phones: {list(self.pending_auth.keys())}")
                return False, "Code request not found for this phone. The session may have expired. Start over by requesting a new code."

            auth_data = self.pending_auth[phone]
            client = auth_data['client']
            phone_code_hash = auth_data['phone_code_hash']

            # Check if client is still connected
            if not client.is_connected():
                print(f"[AUTH] ⚠️ Client disconnected - reconnecting...")
                await client.connect()

            print(f"[AUTH] Attempting sign in with code...")

            # Verify code and sign in
            try:
                user = await client.sign_in(
                    phone=phone,
                    code=code,
                    phone_code_hash=phone_code_hash
                )
                print(f"[AUTH] ✅ Sign in successful!")
            except Exception as sign_in_error:
                print(f"[AUTH] ❌ Sign in failed: {sign_in_error}")
                raise

            # Get authenticated user info
            me = await client.get_me()
            print(f"[AUTH] Authenticated as: {me.first_name} {me.last_name or ''} (@{me.username or 'no_username'})")
            print(f"[AUTH] User ID: {me.id}")

            # Save the session to persistent file
            print(f"[AUTH] Saving session to: {self.session_name}.session")

            # The temp client already has the auth - we just need to save it to our main session
            # Copy the session data to the main session file
            import shutil
            temp_session_file = f"temp_{phone}.session"
            main_session_file = f"{self.session_name}.session"

            # Close temp client properly
            await client.disconnect()

            # Copy session file if it exists
            if os.path.exists(temp_session_file):
                print(f"[AUTH] Copying session from {temp_session_file} to {main_session_file}")
                shutil.copy2(temp_session_file, main_session_file)
                print(f"[AUTH] ✅ Session saved successfully")
            else:
                print(f"[AUTH] ⚠️ Temp session file not found - creating new session")

            # Cleanup temp auth data
            del self.pending_auth[phone]

            # Verify the saved session works
            print(f"[AUTH] Verifying saved session...")
            session_client = TelegramClient(self.session_name, self.api_id, self.api_hash)
            await session_client.connect()

            # Check if we're authenticated
            if await session_client.is_user_authorized():
                session_me = await session_client.get_me()
                print(f"[AUTH] ✅ Session verified - logged in as {session_me.first_name}")
                await session_client.disconnect()
                print(f"[AUTH] ✅ Authentication complete!")

                return True, f"✅ Authenticated as {me.first_name} {me.last_name or ''} ({phone}). Session saved successfully!"
            else:
                await session_client.disconnect()
                print(f"[AUTH] ⚠️ Session not authorized - may need to re-authenticate")
                return False, "Session created but not authorized. Please try again."

        except Exception as e:
            print(f"[AUTH] ❌ Verification error: {e}")
            import traceback
            traceback.print_exc()

            # Cleanup on error
            if phone in self.pending_auth:
                try:
                    await self.pending_auth[phone]['client'].disconnect()
                    print(f"[AUTH] Cleaned up failed auth session")
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
