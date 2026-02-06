"""
Draft Review Bot - Handles draft messages with inline buttons.
Enhanced with reporting and analytics commands.
FIXED: Proper entity fetching and event message handling.
"""

import os
import asyncio
import traceback
from pathlib import Path
from telethon import TelegramClient, events
from telethon.tl.types import Message
from telethon.tl.custom.button import Button
from auto_reply import draft_system
from telegram_service import TelegramService


# ============================================================================
# DRAFT REVIEW BOT CLASS
# ============================================================================

class DraftReviewBot:
    """
    Bulletproof bot for draft review using Bot API (not User Session).
    Features: Draft review with inline buttons, manual commands, analytics.
    """

    def __init__(self, api_id: int, api_hash: str, bot_token: str, owner_id: int):
        """Initialize bot with BOT TOKEN (not user session)"""
        self.api_id = api_id
        self.api_hash = api_hash
        self.bot_token = bot_token
        self.owner_id = owner_id
        self.session_name = "draft_bot_api"
        self.client = None
        self.tg_service = TelegramService(
            api_id,
            api_hash,
            bot_token,
            session_name="draft_bot_service"
        )
        self.waiting_for_edit = {}  # {chat_id: True} - waiting for edit
        self.connection_attempts = 0
        self.max_connection_attempts = 3

    async def start(self):
        """Start bot with auto-recovery on auth errors"""
        print(f"[DRAFT BOT] Starting bot...")

        # Connect using TelegramService
        if not await self.tg_service.connect():
            print("[ERROR] Failed to connect via TelegramService")
            return False

        # Use the service's connected client
        self.client = self.tg_service.client

        print("[DRAFT BOT] [OK] Bot authenticated with Bot API (stable mode)")
        print(f"[DRAFT BOT] Bot token ends with: ...{self.bot_token[-10:]}")

        # Register handlers
        self._register_button_handler()
        self._register_text_message_handler()

        print("[DRAFT BOT] Started and waiting for button interactions...")

        # Send startup notification to owner
        await self.send_startup_notification()

        self.connection_attempts = 0
        return True

    # ========================================================================
    # STARTUP NOTIFICATION
    # ========================================================================

    async def send_startup_notification(self):
        """Send system restart notification to owner"""
        from datetime import datetime

        if self.owner_id == 0 or self.owner_id is None:
            print("[WARNING] OWNER_TELEGRAM_ID not set - skipping startup notification")
            return

        startup_message = f"""
🤖 **SYSTEM RESTARTED**

✅ Bot is now ONLINE and ready to receive commands

Status:
  • Bot API: Connected
  • Token: Valid
  • Owner ID: {self.owner_id}
  • Restart Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Available Commands:
  • /check → Manual analysis trigger
  • /report → Analytics dashboard
  • Звіт → Excel report export

━━━━━━━━━━━━━━━━━━━━
System is ready to process drafts and commands.
"""

        try:
            success = await self.tg_service.send_message(
                recipient_id=self.owner_id,
                text=startup_message.strip()
            )

            if success:
                print(f"[DRAFT BOT] ✓ Startup notification sent to owner ({self.owner_id})")
            else:
                print(f"[DRAFT BOT] ✗ Failed to send startup notification")

        except Exception as e:
            print(f"[ERROR] Error sending startup notification: {e}")

    # ========================================================================
    # EVENT HANDLERS
    # ========================================================================

    def _register_button_handler(self):
        """Register callback query handler for inline buttons"""
        @self.client.on(events.CallbackQuery())
        async def button_handler(event):
            try:
                await self.handle_button_callback(event)
            except Exception as e:
                print(f"[ERROR] Button handler exception: {type(e).__name__}: {e}")
                try:
                    await event.answer(f"Error: {type(e).__name__}")
                except:
                    pass

    def _register_text_message_handler(self):
        """Register text message handler for commands and edit replies"""
        @self.client.on(events.NewMessage())
        async def text_handler(event):
            try:
                # Only process messages from owner
                if event.sender_id == self.owner_id:
                    message = await event.get_message()
                    message_text = message.text or ""
                    message_text_lower = message_text.strip().lower()

                    # ================================================================
                    # COMMAND: /check - Manual analysis trigger
                    # ================================================================
                    if message_text_lower == "/check":
                        print(f"[DRAFT BOT] Manual /check command received from owner")
                        await event.reply("🔍 Triggering manual analysis... This will take a moment...")
                        from main import run_core_logic
                        try:
                            result = await run_core_logic()
                            await event.reply(f"✅ Analysis complete: {result}")
                        except Exception as e:
                            error_msg = f"❌ Analysis failed: {type(e).__name__}: {str(e)}"
                            print(f"[ERROR] {error_msg}")
                            print(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
                            await event.reply(error_msg)

                    # ================================================================
                    # COMMAND: /report - Analytics report (scan reports/ folder)
                    # ================================================================
                    elif message_text_lower == "/report":
                        print(f"[DRAFT BOT] Analytics /report command received from owner")
                        await event.reply("📊 Scanning reports and generating analytics...")
                        try:
                            summary = await self.generate_analytics_report()
                            await event.reply(summary)
                        except Exception as e:
                            error_msg = f"❌ Report generation failed: {type(e).__name__}: {str(e)}"
                            print(f"[ERROR] {error_msg}")
                            print(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
                            await event.reply(error_msg)

                    # ================================================================
                    # COMMAND: Excel export for Звіт
                    # ================================================================
                    elif "Звіт" in message_text:
                        print(f"[DRAFT BOT] Report/Excel export command received from owner")
                        await event.reply("📊 Generating Excel report... This will take a moment...")
                        try:
                            await self.generate_excel_report(event)
                        except Exception as e:
                            error_msg = f"❌ Report generation failed: {type(e).__name__}: {str(e)}"
                            print(f"[ERROR] {error_msg}")
                            print(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
                            await event.reply(error_msg)

                    # ================================================================
                    # HANDLE: Edit text replies
                    # ================================================================
                    elif any(self.waiting_for_edit.values()):
                        await self._safe_execute(
                            self.handle_edit_text(event),
                            "edit text"
                        )
            except Exception as e:
                print(f"[ERROR] Text handler error: {type(e).__name__}: {e}")
                print(f"[ERROR] Full traceback:\n{traceback.format_exc()}")

    # ========================================================================
    # BUTTON HANDLING
    # ========================================================================

    async def handle_button_callback(self, event):
        """Handle inline button callbacks with proper feedback"""
        # Filter: only process if from owner
        if event.sender_id != self.owner_id:
            await event.answer("Unauthorized")
            return

        data = event.data.decode() if isinstance(event.data, bytes) else event.data

        try:
            # Parse button data: "send_12345", "edit_12345", "skip_12345"
            action, chat_id_str = data.split("_")
            chat_id = int(chat_id_str)

            print(f"[DRAFT BOT] Button clicked: {action} for chat {chat_id} by owner {event.sender_id}")

            if action == "send":
                # Show "thinking" notification
                await event.answer("Sending message...", alert=False)
                await self.approve_and_send(chat_id, event)

            elif action == "edit":
                # Show feedback and mark waiting
                await event.answer("Reply with the edited message", alert=False)
                self.waiting_for_edit[chat_id] = True
                # Update button message to show we're waiting
                try:
                    # CORRECT: Use (await event.get_message()).text
                    message = await event.get_message()
                    message_text = message.text or ""
                    await event.edit(
                        message_text + "\n\n[WAITING FOR YOUR EDIT...]",
                        buttons=None
                    )
                except Exception as e:
                    print(f"[ERROR] Failed to edit message: {type(e).__name__}: {e}")
                    print(f"[ERROR] Traceback: {traceback.format_exc()}")

            elif action == "skip":
                # Remove draft and confirm
                draft_system.remove_draft(chat_id)
                await event.answer("Draft deleted", alert=False)
                # Update message to show skipped
                try:
                    # CORRECT: Use (await event.get_message()).text
                    message = await event.get_message()
                    message_text = message.text or ""
                    await event.edit(
                        message_text + "\n\n[SKIPPED BY USER]",
                        buttons=None
                    )
                except Exception as e:
                    print(f"[ERROR] Failed to edit message: {type(e).__name__}: {e}")
                    print(f"[ERROR] Traceback: {traceback.format_exc()}")
                print(f"[DRAFT BOT] Draft skipped for chat {chat_id}")

            else:
                await event.answer("Unknown action", alert=True)

        except ValueError as e:
            print(f"[ERROR] Button data parse error: {e}")
            await event.answer("Invalid button data", alert=True)
        except Exception as e:
            print(f"[ERROR] Button callback error: {type(e).__name__}: {e}")
            print(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
            await event.answer(f"Error: {type(e).__name__}", alert=True)

    # ========================================================================
    # DRAFT MANAGEMENT
    # ========================================================================

    async def send_draft_for_review(
        self,
        chat_id: int,
        chat_title: str,
        draft_text: str,
        confidence: int
    ):
        """Send draft to owner for review with inline keyboard buttons"""
        print(f"DEBUG: Attempting to send draft to ID: {self.owner_id}")
        print(f"DEBUG: Owner ID type: {type(self.owner_id)}, chat_id type: {type(chat_id)}")

        if self.owner_id == 0 or self.owner_id is None:
            print("[WARNING] OWNER_TELEGRAM_ID not set in .env (owner_id=0 or None)")
            return

        # Format the draft message
        message = f"""NEW DRAFT FOR REVIEW

Chat: {chat_title}
AI Confidence: {confidence}%
Chat ID: {chat_id}

PROPOSED RESPONSE:
{draft_text}

━━━━━━━━━━━━━━━━━━━━
Choose action:
"""

        # Create inline keyboard buttons with Ukrainian text
        buttons = [
            [
                Button.inline("✅ ВІДПРАВИТИ", data=f"send_{chat_id}"),
                Button.inline("📝 РЕДАГУВАТИ", data=f"edit_{chat_id}"),
                Button.inline("❌ ПРОПУСТИТИ", data=f"skip_{chat_id}")
            ]
        ]

        # Use TelegramService to send message (includes retry logic)
        success = await self.tg_service.send_message(
            recipient_id=self.owner_id,
            text=message,
            buttons=buttons
        )

        if success:
            print(f"[DRAFT BOT] Draft sent to owner ({self.owner_id}) for review: {chat_title}")
        else:
            print(f"[ERROR] [FINAL_FAILURE] Draft could not be sent after retries")

    async def approve_and_send(self, chat_id: int, event):
        """Approve and send the draft"""
        draft = draft_system.get_draft(chat_id)

        if not draft:
            await event.answer("Draft not found", alert=True)
            try:
                message = await event.get_message()
                await event.edit("Draft not found - already deleted?")
            except Exception as e:
                print(f"[ERROR] Failed to edit message: {e}")
            return

        try:
            print(f"[DRAFT BOT] Sending draft to chat {chat_id}...")

            # CRITICAL FIX: Fetch the entity first before sending
            try:
                entity = await self.client.get_entity(chat_id)
                print(f"[DRAFT BOT] Entity fetched for chat {chat_id}: {entity}")
            except Exception as e:
                print(f"[ERROR] Failed to get entity for {chat_id}: {e}")
                await event.answer("Error: Cannot resolve recipient", alert=True)
                return

            # Now send the message to the resolved entity
            try:
                await self.client.send_message(entity, draft["draft"])
                print(f"[DRAFT BOT] Message sent to entity successfully")

                # Success! Update UI with confirmation
                await event.answer("Message delivered!", alert=False)
                try:
                    # CORRECT: Use (await event.get_message()).text
                    message = await event.get_message()
                    message_text = message.text or ""
                    await event.edit(
                        f"{message_text}\n\n[SUCCESS] Message sent to {draft['chat_title']}",
                        buttons=None
                    )
                except Exception as e:
                    print(f"[ERROR] Failed to edit message: {e}")

                # Remove draft
                draft_system.remove_draft(chat_id)
                print(f"[DRAFT BOT] Message delivered to chat {chat_id}")

            except Exception as send_error:
                print(f"[ERROR] Failed to send message: {type(send_error).__name__}: {send_error}")
                await event.answer("Failed to send message", alert=True)
                try:
                    message = await event.get_message()
                    message_text = message.text or ""
                    await event.edit(
                        f"{message_text}\n\n[ERROR] Failed to send - please retry",
                        buttons=None
                    )
                except Exception as e:
                    print(f"[ERROR] Failed to edit message: {e}")

        except Exception as e:
            print(f"[ERROR] Error in approve_and_send: {type(e).__name__}: {e}")
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            try:
                await event.answer(f"Error: {e}", alert=True)
            except:
                pass

    async def handle_edit_text(self, event):
        """Handle edited text when user sends new message after EDIT button"""
        try:
            # For NewMessage events, use await event.get_message() for proper async handling
            message = await event.get_message()
            new_text = message.text.strip() if message.text else ""
            if not new_text:
                return

            # Find which chat_id is waiting for edit
            chat_id = None
            for cid, waiting in list(self.waiting_for_edit.items()):
                if waiting:
                    chat_id = cid
                    break

            if not chat_id:
                return

            # Reset the waiting flag
            self.waiting_for_edit[chat_id] = False
            await self.send_edited_message(chat_id, new_text, event)

        except Exception as e:
            print(f"[ERROR] Error in handle_edit_text: {type(e).__name__}: {e}")
            print(f"[ERROR] Traceback: {traceback.format_exc()}")

    async def send_edited_message(self, chat_id: int, new_text: str, event):
        """Send edited message to chat"""
        draft = draft_system.get_draft(chat_id)

        if not draft:
            try:
                await event.reply("Draft not found - already sent?")
            except Exception as e:
                print(f"[ERROR] Failed to reply: {e}")
            return

        try:
            print(f"[DRAFT BOT] Sending edited message to chat {chat_id}...")

            # CRITICAL FIX: Fetch the entity first before sending
            try:
                entity = await self.client.get_entity(chat_id)
                print(f"[DRAFT BOT] Entity fetched for chat {chat_id}: {entity}")
            except Exception as e:
                print(f"[ERROR] Failed to get entity for {chat_id}: {e}")
                await event.reply("Error: Cannot resolve recipient")
                return

            # Now send the message to the resolved entity
            try:
                await self.client.send_message(entity, new_text)
                print(f"[DRAFT BOT] Edited message sent to entity successfully")

                # Confirm to owner
                try:
                    await event.reply(
                        f"[SUCCESS] Edited message sent to {draft['chat_title']}\n\n"
                        f"Original draft was replaced with your edits."
                    )
                except Exception as e:
                    print(f"[ERROR] Failed to send confirmation reply: {e}")

                # Remove draft
                draft_system.remove_draft(chat_id)
                print(f"[DRAFT BOT] Edited message delivered to chat {chat_id}")

            except Exception as send_error:
                print(f"[ERROR] Failed to send edited message: {type(send_error).__name__}: {send_error}")
                try:
                    await event.reply("[ERROR] Failed to send edited message. Please try again.")
                except Exception as e:
                    print(f"[ERROR] Failed to send error reply: {e}")
                print(f"[ERROR] Failed to send edited message to chat {chat_id}")

        except Exception as e:
            print(f"[ERROR] Error in send_edited_message: {type(e).__name__}: {e}")
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            try:
                await event.reply(f"[ERROR] Failed to send edited message: {e}")
            except:
                pass

    # ========================================================================
    # REPORTING & ANALYTICS
    # ========================================================================

    async def generate_analytics_report(self) -> str:
        """
        Scan reports/ folder and generate analytics summary.
        Returns a formatted summary string.
        """
        print("[DRAFT BOT] [REPORT] Starting analytics scan...")

        reports_dir = Path("reports")
        if not reports_dir.exists():
            return "❌ Reports folder not found"

        report_files = list(reports_dir.glob("*.txt"))
        if not report_files:
            return "❌ No reports found"

        print(f"[DRAFT BOT] [REPORT] Found {len(report_files)} report files")

        # Scan and summarize
        total_chats = len(report_files)
        high_confidence_count = 0
        drafted_count = 0

        for report_file in report_files:
            try:
                content = report_file.read_text(encoding="utf-8", errors="ignore")

                # Count high confidence reports
                if "ВПЕВНЕНІСТЬ ШІ:" in content:
                    lines = content.split("\n")
                    for line in lines:
                        if "ВПЕВНЕНІСТЬ ШІ:" in line:
                            try:
                                confidence = int(line.split(":")[1].strip())
                                if confidence >= 80:
                                    high_confidence_count += 1
                            except:
                                pass

                # Count drafts sent
                if "DRAFT FOR REVIEW" in content or "AUTO-REPLY SENT" in content:
                    drafted_count += 1

            except Exception as e:
                print(f"[ERROR] Error reading {report_file.name}: {e}")

        # Format response
        summary = f"""
📊 **ANALYTICS REPORT**

📁 Total Chats Processed: {total_chats}
✅ High Confidence (≥80%): {high_confidence_count}
📝 Drafts/Replies: {drafted_count}

━━━━━━━━━━━━━━━━━━━━
Report generation completed at {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        print(f"[DRAFT BOT] [REPORT] Analytics complete")
        return summary.strip()

    async def generate_excel_report(self, event):
        """
        Generate Excel report with comprehensive analytics data.
        Uses the excel_module for data collection and formatting.
        """
        print("[DRAFT BOT] [EXCEL] Starting Excel report generation...")

        try:
            from excel_module import get_excel_collector

            collector = get_excel_collector()

            # Collect all data from reports
            collector.collect_all_data()
            summary = collector.format_for_summary()

            # Send summary to user
            await event.reply(summary)

            # Prepare Excel sheets (ready for export)
            sheets_data = collector.prepare_excel_sheets()
            print(f"[DRAFT BOT] [EXCEL] Prepared {len(sheets_data)} sheets for export")

            # Try to export if openpyxl is available
            excel_file_path = collector.export_to_excel("AIBI_Report.xlsx")

            if excel_file_path:
                await event.reply(f"✅ Excel file ready: {excel_file_path}")
                print(f"[DRAFT BOT] [EXCEL] File exported successfully")
            else:
                await event.reply(
                    "⚠️ Excel file export requires openpyxl.\n"
                    "Install with: pip install openpyxl\n"
                    "Data collection is ready, awaiting library."
                )

            print("[DRAFT BOT] [EXCEL] Report generation complete")

        except Exception as e:
            await event.reply(f"❌ Error generating Excel: {e}")
            print(f"[ERROR] Excel generation error: {e}")

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    async def _safe_execute(self, coro, action_name: str):
        """Wrapper to safely execute operations and handle errors"""
        try:
            await coro
        except Exception as e:
            print(f"[ERROR] Error during {action_name}: {type(e).__name__}: {e}")

    async def stop(self):
        """Stop the bot"""
        await self.tg_service.disconnect()
        print("[DRAFT BOT] Stopped")


# ============================================================================
# BOT STARTUP FUNCTION
# ============================================================================

async def run_draft_bot():
    """Start bot for draft review using Bot API (not User Session)"""
    api_id = int(os.getenv("TG_API_ID"))
    api_hash = os.getenv("TG_API_HASH")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    owner_id = int(os.getenv("OWNER_TELEGRAM_ID", "0"))

    if not bot_token:
        print("[ERROR] TELEGRAM_BOT_TOKEN not set in .env")
        return None

    if owner_id == 0:
        print("[ERROR] OWNER_TELEGRAM_ID not set in .env")
        return None

    bot = DraftReviewBot(api_id, api_hash, bot_token, owner_id)
    success = await bot.start()

    if success:
        print("[DRAFT BOT] [OK] Bot is ready for draft review")
        return bot
    else:
        print("[ERROR] Failed to start draft bot")
        return None
