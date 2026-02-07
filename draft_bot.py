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
        self.waiting_for_instructions = False  # NEW: Track instruction update state
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
        self._register_new_message_handler()

        print("[DRAFT BOT] Started - listening for button interactions AND new messages...")

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

[OK] Bot is now ONLINE and ready to receive commands

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

    def _register_new_message_handler(self):
        """Register handler for new messages from all users (for forwarding to analysis)"""
        @self.client.on(events.NewMessage(incoming=True))
        async def new_message_handler(event):
            try:
                # Skip messages from owner (handled by text handler)
                if event.sender_id == self.owner_id:
                    return

                # Skip bot messages
                if event.sender_id == 777000:  # Telegram notification ID
                    return

                # Log incoming message
                sender = await event.get_sender()
                sender_name = sender.first_name if hasattr(sender, 'first_name') else str(sender.id)
                message_text = event.message.text or "[Non-text message]"

                print(f"[DRAFT BOT] [NEW MESSAGE] From {sender_name} (ID: {event.sender_id}): {message_text[:100]}")

                # Forward message notification to owner for awareness
                if self.owner_id and event.sender_id != self.owner_id:
                    try:
                        notification = f"📨 New message from {sender_name}:\n\n{message_text[:200]}"
                        if len(message_text) > 200:
                            notification += "..."

                        await self.tg_service.send_message(
                            recipient_id=self.owner_id,
                            text=notification
                        )
                    except Exception as e:
                        print(f"[WARNING] Failed to forward notification: {e}")

            except Exception as e:
                print(f"[ERROR] New message handler exception: {type(e).__name__}: {e}")

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
                        print(f"[DRAFT BOT] Clearing any waiting states before analysis...")

                        # Clear all waiting states to unblock any pending operations
                        self.waiting_for_edit.clear()
                        self.waiting_for_instructions = False
                        print(f"[DRAFT BOT] Waiting states cleared: {len(self.waiting_for_edit)} items removed")

                        await event.reply("[CHECK] Clearing states and triggering manual analysis of last 10 messages... This will take a moment...")
                        from main import run_core_logic
                        try:
                            print(f"[DRAFT BOT] [CHECK] Starting run_core_logic() to reanalyze recent messages...")
                            result = await run_core_logic()

                            success_msg = f"""[OK] ANALYSIS COMPLETE

[RESULT] {result}

[NOTES]
• All states cleared before analysis
• Checked and processed recent messages
• Drafts sent for any messages needing review
• Check console for detailed debug output with [INPUT], [SMART_LOGIC], [ACTION] lines
"""
                            await event.reply(success_msg)
                            print(f"[DRAFT BOT] [CHECK] Analysis complete - user notified")
                        except Exception as e:
                            error_msg = f"[ERROR] Analysis failed: {type(e).__name__}: {str(e)}"
                            print(f"[ERROR] {error_msg}")
                            print(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
                            await event.reply(error_msg)

                    # ================================================================
                    # COMMAND: /report - Analytics report (scan reports/ folder)
                    # ================================================================
                    elif message_text_lower == "/report":
                        print(f"[DRAFT BOT] Analytics /report command received from owner")
                        await event.reply("[STATS] Scanning reports and generating analytics...")
                        try:
                            summary = await self.generate_analytics_report()
                            await event.reply(summary)
                        except Exception as e:
                            error_msg = f"[ERROR] Report generation failed: {type(e).__name__}: {str(e)}"
                            print(f"[ERROR] {error_msg}")
                            print(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
                            await event.reply(error_msg)

                    # ================================================================
                    # COMMAND: Excel export for Звіт
                    # ================================================================
                    elif "Звіт" in message_text:
                        print(f"[DRAFT BOT] Report/Excel export command received from owner")
                        await event.reply("[STATS] Generating Excel report... This will take a moment...")
                        try:
                            await self.generate_excel_report(event)
                        except Exception as e:
                            error_msg = f"[ERROR] Report generation failed: {type(e).__name__}: {str(e)}"
                            print(f"[ERROR] {error_msg}")
                            print(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
                            await event.reply(error_msg)

                    # ================================================================
                    # COMMAND: /analytics - Unified analytics (Format A + B reports)
                    # ================================================================
                    elif message_text_lower == "/analytics":
                        print(f"[DRAFT BOT] /analytics command received from owner")
                        await event.reply("[LOAD] Running unified analytics (Format A + B reports)...")

                        try:
                            from features.analytics_engine import run_unified_analytics

                            # Run analytics
                            result = await run_unified_analytics(
                                reports_folder='reports',
                                output_file='unified_analytics.xlsx'
                            )

                            if result["success"]:
                                summary = result["summary"]

                                # Build formatted response
                                response = f"""[OK] UNIFIED ANALYTICS COMPLETE

[DEALS]
  Total: {summary['total_deals']}
  Wins: {summary['total_wins']} ({summary['win_rate']:.1f}%)
  Losses: {summary['total_losses']}
  Unknown: {summary['total_unknown']}

[REVENUE]
  Total: ${summary['total_revenue']:,.2f}
  Avg/Win: ${summary['avg_win_revenue']:,.2f}

[CUSTOMERS]
  Unique: {summary['customer_count']}

[FORMAT BREAKDOWN]
  Format A Wins: {summary['format_breakdown']['format_a_wins']}
  Format A Losses: {summary['format_breakdown']['format_a_losses']}
  Format B Wins: {summary['format_breakdown']['format_b_wins']}
  Format B Losses: {summary['format_breakdown']['format_b_losses']}

[TOP WINNING FAQs]"""

                                # Add top FAQs
                                if summary['top_winning_faqs']:
                                    for i, (faq, count) in enumerate(summary['top_winning_faqs'][:5], 1):
                                        response += f"\n  {i}. {faq} ({count}x)"
                                else:
                                    response += "\n  [No FAQs found in winning deals]"

                                response += f"\n\n[FILE]\n  Report: {result['file_path']}"

                                await event.reply(response)
                                print(f"[DRAFT BOT] [ANALYTICS] Complete - saved to {result['file_path']}")
                            else:
                                error_msg = f"[ERROR] Analytics failed: {result['message']}"
                                print(f"[DRAFT BOT] {error_msg}")
                                await event.reply(error_msg)

                        except Exception as e:
                            error_msg = f"[ERROR] {type(e).__name__}: {str(e)}"
                            print(f"[DRAFT BOT] {error_msg}")
                            print(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
                            await event.reply(error_msg)

                    # ================================================================
                    # COMMAND: /view_instructions - View current instructions
                    # ================================================================
                    elif message_text_lower == "/view_instructions":
                        print(f"[DRAFT BOT] /view_instructions command received from owner")
                        try:
                            from features.dynamic_instructions import get_instructions_manager
                            manager = get_instructions_manager()

                            current = manager.get_current_instructions()
                            dynamic = manager.get_dynamic_instructions()
                            stats = manager.get_stats()

                            # Build response
                            core_preview = current[:400] + "..." if len(current) > 400 else current
                            dynamic_preview = dynamic[:300] + "..." if len(dynamic) > 300 else dynamic

                            response = f"""📋 **CURRENT INSTRUCTIONS**

**Core Instructions** ({stats['instructions_size']} chars):
{core_preview}

**Dynamic Rules** ({stats['dynamic_size']} chars):
{dynamic_preview}

**Backups Available**: {stats['backup_count']}

Available Commands:
  /update_instructions - Edit instructions
  /list_backups - Show available backups
  /rollback_backup - Restore from backup
"""
                            await event.reply(response)
                        except Exception as e:
                            error_msg = f"[ERROR] Error: {type(e).__name__}: {str(e)}"
                            print(f"[ERROR] {error_msg}")
                            await event.reply(error_msg)

                    # ================================================================
                    # COMMAND: /update_instructions - Start instruction update flow
                    # ================================================================
                    elif message_text_lower.startswith("/update_instructions"):
                        print(f"[DRAFT BOT] /update_instructions command received from owner")
                        self.waiting_for_instructions = True

                        help_text = """📝 **INSTRUCTIONS UPDATE MODE**

Send your update in format:
  REPLACE: [new instructions text]
  APPEND: [text to add at end]
  PREPEND: [text to add at beginning]
  DYNAMIC: [new dynamic rule to add]
  CANCEL: Cancel this operation

Examples:
  APPEND: Always mention 24/7 customer support availability
  DYNAMIC: New rule: Check current system status before responding
  REPLACE: [Full new instructions text here...]

Note: Automatic backup will be created before changes.
"""
                        await event.reply(help_text)

                    # ================================================================
                    # COMMAND: /list_backups - List available backups
                    # ================================================================
                    elif message_text_lower == "/list_backups":
                        print(f"[DRAFT BOT] /list_backups command received from owner")
                        try:
                            from features.dynamic_instructions import get_instructions_manager
                            manager = get_instructions_manager()

                            backups = manager.list_backups(limit=10)

                            if not backups:
                                await event.reply("[ERROR] No backups available yet")
                                return

                            response = "📦 **AVAILABLE BACKUPS** (Most recent first)\n\n"
                            for i, backup in enumerate(backups, 1):
                                response += f"{i}. {backup}\n"

                            response += "\nUse: /rollback_backup [filename]\nExample: /rollback_backup instructions_backup_20240215_120000.txt"
                            await event.reply(response)
                        except Exception as e:
                            error_msg = f"[ERROR] Error: {type(e).__name__}: {str(e)}"
                            print(f"[ERROR] {error_msg}")
                            await event.reply(error_msg)

                    # ================================================================
                    # COMMAND: /rollback_backup - Restore from specific backup
                    # ================================================================
                    elif message_text_lower.startswith("/rollback_backup"):
                        print(f"[DRAFT BOT] /rollback_backup command received from owner")
                        try:
                            from features.dynamic_instructions import get_instructions_manager

                            # Parse backup filename from command
                            parts = message_text.split(maxsplit=1)
                            if len(parts) < 2:
                                await event.reply("Usage: /rollback_backup [filename]\nExample: /rollback_backup instructions_backup_20240215_120000.txt")
                                return

                            backup_filename = parts[1].strip()
                            manager = get_instructions_manager()

                            result = await manager.rollback_to_backup(backup_filename)
                            await event.reply(
                                f"{'[OK]' if result['success'] else '[ERROR]'} {result['message']}"
                            )
                        except Exception as e:
                            error_msg = f"[ERROR] Error: {type(e).__name__}: {str(e)}"
                            print(f"[ERROR] {error_msg}")
                            await event.reply(error_msg)

                    # ================================================================
                    # HANDLE: Instructions update processing
                    # ================================================================
                    elif self.waiting_for_instructions and message_text:
                        print(f"[DRAFT BOT] Processing instruction update")
                        try:
                            from features.dynamic_instructions import get_instructions_manager
                            manager = get_instructions_manager()

                            text = message_text.strip()

                            # Check for cancel
                            if text.upper() == "CANCEL":
                                self.waiting_for_instructions = False
                                await event.reply("[ERROR] Instruction update cancelled")
                                return

                            # Process based on mode
                            result = None

                            if text.startswith("REPLACE:"):
                                new_content = text[8:].strip()
                                if not new_content:
                                    await event.reply("[ERROR] REPLACE mode requires content after the colon")
                                    return
                                result = await manager.update_instructions(new_content, mode="replace")

                            elif text.startswith("APPEND:"):
                                new_content = text[7:].strip()
                                if not new_content:
                                    await event.reply("[ERROR] APPEND mode requires content after the colon")
                                    return
                                result = await manager.update_instructions(new_content, mode="append")

                            elif text.startswith("PREPEND:"):
                                new_content = text[8:].strip()
                                if not new_content:
                                    await event.reply("[ERROR] PREPEND mode requires content after the colon")
                                    return
                                result = await manager.update_instructions(new_content, mode="prepend")

                            elif text.startswith("DYNAMIC:"):
                                new_rule = text[8:].strip()
                                if not new_rule:
                                    await event.reply("[ERROR] DYNAMIC mode requires content after the colon")
                                    return
                                result = await manager.update_dynamic_instructions(new_rule)

                            else:
                                await event.reply("[ERROR] Invalid format. Use REPLACE:/APPEND:/PREPEND:/DYNAMIC:/CANCEL")
                                return

                            # Send result
                            if result:
                                await event.reply(
                                    f"{'[OK]' if result['success'] else '[ERROR]'} {result['message']}"
                                )

                                if result.get('backup_path'):
                                    await event.reply(f"📦 Backup created: {result['backup_path']}")

                            self.waiting_for_instructions = False

                        except Exception as e:
                            error_msg = f"[ERROR] Error: {type(e).__name__}: {str(e)}"
                            print(f"[ERROR] {error_msg}")
                            await event.reply(error_msg)
                            self.waiting_for_instructions = False

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
        print(f"\n[DRAFT SEND START] Attempting to send draft for review...")
        print(f"[DRAFT SEND] Owner ID: {self.owner_id} (type: {type(self.owner_id).__name__})")
        print(f"[DRAFT SEND] Chat ID: {chat_id} (title: {chat_title})")
        print(f"[DRAFT SEND] Draft text length: {len(draft_text)} chars")
        print(f"[DRAFT SEND] Confidence: {confidence}%")

        if self.owner_id == 0 or self.owner_id is None:
            print(f"[ERROR] OWNER_TELEGRAM_ID not configured! owner_id={self.owner_id}")
            print(f"[ERROR] Set OWNER_TELEGRAM_ID in .env and restart the server")
            return

        print(f"[DRAFT SEND] Owner ID is valid: {self.owner_id}")
        print(f"[DRAFT SEND] TelegramService available: {self.tg_service is not None}")
        print(f"[DRAFT SEND] TelegramService client connected: {self.tg_service.client is not None if self.tg_service else False}")

        # Format the draft message
        message = f"""🤖 **NEW DRAFT FOR REVIEW**

**Chat**: {chat_title}
**AI Confidence**: {confidence}%
**Chat ID**: {chat_id}

**PROPOSED RESPONSE:**
{draft_text}

━━━━━━━━━━━━━━━━━━━━
**Choose action:**
"""

        # Create inline keyboard buttons with Ukrainian text
        buttons = [
            [
                Button.inline("[OK] SEND NOW", data=f"send_{chat_id}"),
                Button.inline("📝 EDIT", data=f"edit_{chat_id}"),
                Button.inline("[ERROR] SKIP", data=f"skip_{chat_id}")
            ]
        ]

        # Use TelegramService to send message (includes retry logic)
        print(f"[DRAFT SEND] Calling tg_service.send_message()...")
        try:
            success = await self.tg_service.send_message(
                recipient_id=self.owner_id,
                text=message,
                buttons=buttons
            )

            if success:
                print(f"[DRAFT SUCCESS] [OK] Draft message delivered to owner ({self.owner_id})")
                print(f"[DRAFT SUCCESS] Chat: {chat_title}")
            else:
                print(f"[DRAFT FAILED] [ERROR] Draft message FAILED after retries")
                print(f"[DRAFT FAILED] TelegramService returned False")
                print(f"[DRAFT FAILED] Check OWNER_TELEGRAM_ID or Telegram connection")

        except Exception as e:
            print(f"[DRAFT ERROR] [ERROR] Exception while sending draft: {type(e).__name__}: {e}")
            print(f"[DRAFT ERROR] Traceback:\n{traceback.format_exc()}")

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
            return "[ERROR] Reports folder not found"

        report_files = list(reports_dir.glob("*.txt"))
        if not report_files:
            return "[ERROR] No reports found"

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
[STATS] **ANALYTICS REPORT**

📁 Total Chats Processed: {total_chats}
[OK] High Confidence (≥80%): {high_confidence_count}
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
                await event.reply(f"[OK] Excel file ready: {excel_file_path}")
                print(f"[DRAFT BOT] [EXCEL] File exported successfully")
            else:
                await event.reply(
                    "[WARN] Excel file export requires openpyxl.\n"
                    "Install with: pip install openpyxl\n"
                    "Data collection is ready, awaiting library."
                )

            print("[DRAFT BOT] [EXCEL] Report generation complete")

        except Exception as e:
            await event.reply(f"[ERROR] Error generating Excel: {e}")
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
