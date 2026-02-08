"""
Draft Review Bot - Handles draft messages with inline buttons.
Enhanced with reporting and analytics commands.
FIXED: Proper entity fetching and event message handling.
"""

import os
import asyncio
import traceback
from datetime import datetime
from pathlib import Path
from telethon import TelegramClient, events
from telethon.tl.types import Message
from telethon.tl.custom.button import Button
from auto_reply import draft_system
from telegram_service import TelegramService
from features.smart_enhancements import AutoBookingManager
from knowledge_base_storage import get_knowledge_base


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
        self.check_in_progress = False  # Prevent duplicate /check commands
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
        self._register_command_handler()
        self._register_text_message_handler()
        self._register_new_message_handler()

        print("[DRAFT BOT] Started - listening for commands, buttons, and new messages...")

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
[BOT] **SYSTEM RESTARTED**

[OK] Bot is now ONLINE and ready to receive commands

Status:
  - Bot API: Connected
  - Token: Valid
  - Owner ID: {self.owner_id}
  - Restart Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Available Commands:
  - /check: Manual analysis trigger
  - /report: Analytics dashboard
  - Звіт: Excel report export

--------------------
System is ready to process drafts and commands.
"""

        try:
            success = await self.tg_service.send_message(
                recipient_id=self.owner_id,
                text=startup_message.strip()
            )

            if success:
                print(f"[DRAFT BOT] [OK] Startup notification sent to owner ({self.owner_id})")
            else:
                print(f"[DRAFT BOT] [ERROR] Failed to send startup notification")

        except Exception as e:
            print(f"[ERROR] Error sending startup notification: {e}")

    # ========================================================================
    # EVENT HANDLERS
    # ========================================================================

    def _register_button_handler(self):
        """Register callback query handler for inline buttons"""
        # FIX: CallbackQuery doesn't accept from_users parameter
        # Instead, filter by sender_id inside the handler
        @self.client.on(events.CallbackQuery())
        async def button_handler(event):
            try:
                # Security: Only process callbacks from owner
                if event.sender_id != self.owner_id:
                    print(f"[SECURITY] Ignoring callback from non-owner: {event.sender_id}")
                    await event.answer("Unauthorized", alert=True)
                    return

                await self.handle_button_callback(event)
            except Exception as e:
                print(f"[ERROR] Button handler exception: {type(e).__name__}: {e}")
                try:
                    await event.answer(f"Error: {type(e).__name__}")
                except:
                    pass

    def _register_command_handler(self):
        """Register handler for bot commands (/export, /check)"""
        @self.client.on(events.NewMessage(from_users=self.owner_id, pattern=r'^/'))
        async def command_handler(event):
            try:
                command = event.message.text.strip().lower()
                print(f"[COMMAND] Received command: {command}")

                if command == '/check':
                    # Prevent duplicate execution
                    if self.check_in_progress:
                        await event.reply("[WAIT] Analysis already in progress, please wait...")
                        print("[DRAFT BOT] [CHECK] Ignoring duplicate command - analysis already running")
                        return

                    self.check_in_progress = True
                    try:
                        await event.reply("[OK] Manual analysis triggered via /check command")
                        print("[DRAFT BOT] Manual /check command received from owner")
                        print("[DRAFT BOT] Clearing any waiting states before analysis...")
                        self.waiting_for_edit.clear()
                        print(f"[DRAFT BOT] Waiting states cleared: {len(self.waiting_for_edit)} items removed")

                        # Trigger analysis - pass bot instance directly
                        from main import run_core_logic
                        print("[DRAFT BOT] [CHECK] Starting run_core_logic() to reanalyze recent messages...")
                        await run_core_logic(draft_bot_param=self)  # Pass bot by reference
                        print("[DRAFT BOT] [CHECK] Analysis completed")
                    finally:
                        self.check_in_progress = False

                elif command == '/export':
                    await event.reply("[PROCESSING] Generating finance export... Please wait.")
                    print("[FINANCE EXPORT] Command received from owner")

                    # Generate finance report
                    try:
                        from features.smart_enhancements import finance_exporter
                        from main import fetch_chats_only

                        # Fetch recent chats
                        chats = await fetch_chats_only(limit=100, hours_ago=168)  # Last week

                        # Generate Excel report
                        excel_path = finance_exporter.generate_excel_report(chats, [])

                        if excel_path and os.path.exists(excel_path):
                            await self.client.send_file(
                                self.owner_id,
                                excel_path,
                                caption="[SUCCESS] Finance Export Report"
                            )
                            print(f"[FINANCE EXPORT] [SUCCESS] Report sent: {excel_path}")
                        else:
                            await event.reply("[ERROR] Failed to generate report")
                            print("[FINANCE EXPORT] [ERROR] Excel file not created")

                    except Exception as export_error:
                        await event.reply(f"[ERROR] Export failed: {export_error}")
                        print(f"[FINANCE EXPORT] [ERROR] {export_error}")
                        print(f"[FINANCE EXPORT] Traceback:\n{traceback.format_exc()}")

                else:
                    print(f"[COMMAND] Unknown command: {command}")

            except Exception as e:
                print(f"[ERROR] Command handler exception: {type(e).__name__}: {e}")
                try:
                    await event.reply(f"[ERROR] {type(e).__name__}: {e}")
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

                # Store message in registry for Web UI display
                try:
                    from main import BOT_REGISTRY
                    chat_id = event.chat_id if hasattr(event, 'chat_id') else event.sender_id
                    message_data = {
                        "message_id": event.id,
                        "chat_id": chat_id,
                        "sender_id": event.sender_id,
                        "sender_name": sender_name,
                        "text": message_text[:500],  # Store preview
                        "date": event.date.isoformat() if hasattr(event, 'date') else datetime.now().isoformat()
                    }
                    BOT_REGISTRY.add_message(chat_id, message_data)
                except Exception as e:
                    print(f"[WARNING] Failed to store message in registry: {e}")

                # INTERACTIVE MANAGER MODE: Generate AI draft and send with action buttons
                if self.owner_id and event.sender_id != self.owner_id:
                    try:
                        # Generate AI draft using auto_reply system
                        print(f"[DRAFT BOT] [AI DRAFT] Generating response for chat {event.sender_id}...")

                        # Load business data and instructions
                        business_data_path = Path("business_data.txt")
                        instructions_path = Path("instructions.txt")

                        business_data = ""
                        instructions = ""

                        if business_data_path.exists():
                            business_data = business_data_path.read_text(encoding='utf-8')

                        if instructions_path.exists():
                            instructions = instructions_path.read_text(encoding='utf-8')

                        # Generate AI draft
                        try:
                            draft_text = await draft_system.generate_reply(
                                message_text=message_text,
                                business_data=business_data,
                                instructions=instructions,
                                chat_title=sender_name
                            )
                            print(f"[DRAFT BOT] [AI DRAFT] Generated {len(draft_text)} chars")
                        except Exception as draft_error:
                            print(f"[DRAFT BOT] [AI DRAFT] Generation failed: {draft_error}")
                            draft_text = "[AI draft generation failed - respond manually]"

                        # Create notification with AI draft and interactive buttons
                        notification = (
                            f"NEW MESSAGE from {sender_name} (ID: {event.sender_id})\n\n"
                            f"MESSAGE:\n{message_text[:300]}\n\n"
                            f"AI DRAFT:\n{draft_text}\n\n"
                            f"Choose action:"
                        )

                        # Create inline buttons for interactive management
                        buttons = [
                            [
                                Button.inline("[OK] Send Response", f"send_{event.sender_id}"),
                                Button.inline("[EDIT] Edit Draft", f"edit_{event.sender_id}"),
                            ],
                            [
                                Button.inline("[X] Ignore", f"skip_{event.sender_id}"),
                            ]
                        ]

                        # Send notification with buttons
                        await self.tg_service.send_message(
                            recipient_id=self.owner_id,
                            text=notification,
                            buttons=buttons
                        )

                        print(f"[DRAFT BOT] [INTERACTIVE] Sent notification to owner with 3 action buttons")

                    except Exception as e:
                        print(f"[WARNING] Failed to send interactive notification: {e}")
                        import traceback
                        traceback.print_exc()

            except Exception as e:
                print(f"[ERROR] New message handler exception: {type(e).__name__}: {e}")

    def _register_text_message_handler(self):
        """Register text message handler for commands and edit replies"""
        @self.client.on(events.NewMessage())
        async def text_handler(event):
            try:
                # Only process messages from owner
                if event.sender_id == self.owner_id:
                    message = event.message
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
                            result = await run_core_logic(draft_bot_param=self)  # Pass bot by reference

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
                    # COMMAND: /generate_faq - AI Self-Learning Knowledge Base Update
                    # ================================================================
                    elif message_text_lower == "/generate_faq":
                        print(f"[DRAFT BOT] /generate_faq command received from owner")
                        await event.reply("📚 [AI LEARNING] Generating FAQ from successful reply patterns...")
                        try:
                            kb_storage = get_knowledge_base()

                            # Get statistics
                            stats = kb_storage.get_statistics()
                            total_patterns = stats['total_patterns']

                            if total_patterns == 0:
                                await event.reply("⚠️ No successful patterns found yet!\n\nApprove some drafts first using the [Send] button, then try again.")
                                return

                            # Generate FAQ
                            result = kb_storage.generate_faq("dynamic_instructions.txt")

                            if result['success']:
                                success_msg = f"""✅ **Knowledge Base Updated!**

📊 **Statistics:**
• Total Successful Cases: {result['total_patterns']}
• Topics Identified: {result['topics_identified']}
• File: dynamic_instructions.txt

🎯 **Impact:**
The AI will now use these {result['total_patterns']} successful patterns to:
✓ Match your communication style
✓ Provide consistent responses
✓ Learn from approved replies

📈 **Self-Learning Active:**
Every time you click [Send], the AI learns and improves!
"""
                                await event.reply(success_msg)
                                print(f"[AI LEARNING] ✓ FAQ generated with {result['total_patterns']} patterns")
                            else:
                                error_msg = f"❌ Failed to generate FAQ: {result.get('error', 'Unknown error')}"
                                await event.reply(error_msg)

                        except Exception as e:
                            error_msg = f"[ERROR] FAQ generation failed: {type(e).__name__}: {str(e)}"
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

                            response = f"""[INFO] **CURRENT INSTRUCTIONS**

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

                        help_text = """[EDIT] **INSTRUCTIONS UPDATE MODE**

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

                            response = "[BACKUP] **AVAILABLE BACKUPS** (Most recent first)\n\n"
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
            action, chat_id_str = data.split("_", 1)  # Split on first underscore only
            chat_id = int(chat_id_str)

            print(f"[DRAFT BOT] Button clicked: {action} for chat {chat_id} by owner {event.sender_id}")

            if action == "send":
                # Show "thinking" notification
                await event.answer("Sending message...", alert=False)
                await self.approve_and_send(chat_id, event)

            elif action == "confirm":
                # Handle confirmation of edited draft
                await event.answer("Sending edited message...", alert=False)
                await self.send_confirmed_edit(chat_id, event)

            elif action == "edit":
                # Show feedback and mark waiting
                await event.answer("Reply with the edited message", alert=False)
                self.waiting_for_edit[chat_id] = True
                # Update button message to show we're waiting
                try:
                    # For CallbackQuery, fetch message asynchronously
                    message = await event.get_message()
                    message_text = message.text or ""
                    await event.edit(
                        message_text + "\n\n[WAITING FOR YOUR EDIT...]",
                        buttons=None
                    )

                    # Send clear confirmation message
                    await self.tg_service.send_message(
                        self.owner_id,
                        "✍️ **I am listening. Please type the new response below:**\n\nSend your edited message and I'll forward it to the client.",
                        buttons=None
                    )
                    print(f"[DRAFT BOT] Edit confirmation message sent to owner")
                except Exception as e:
                    print(f"[ERROR] Failed to edit message: {type(e).__name__}: {e}")
                    print(f"[ERROR] Traceback: {traceback.format_exc()}")

            elif action == "skip":
                # Remove draft and confirm
                draft_system.remove_draft(chat_id)
                await event.answer("Draft deleted", alert=False)
                # Update message to show skipped
                try:
                    # For CallbackQuery, fetch message asynchronously
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
        message = f"""[BOT] **NEW DRAFT FOR REVIEW**

**Chat**: {chat_title}
**AI Confidence**: {confidence}%
**Chat ID**: {chat_id}

**PROPOSED RESPONSE:**
{draft_text}

--------------------
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
        """
        Approve and send the draft using DIRECT method (same as Quick_test.py)

        This uses the exact working TelegramClient method proven in Quick_test.py:
        - Create TelegramClient('aibi_session')
        - Connect
        - Send message
        - Disconnect

        ENHANCEMENTS:
        - Logs approved replies for Knowledge Base analysis
        - Detects meeting requests and auto-creates Google Calendar events
        """
        # Get draft from AI message (extract from button callback message)
        try:
            # For CallbackQuery, fetch message asynchronously
            message = await event.get_message()
            message_text = message.text or ""

            # Extract chat title and original message for logging
            chat_title = "Unknown"
            original_message = ""
            if "NEW MESSAGE from" in message_text:
                try:
                    chat_title = message_text.split("NEW MESSAGE from ")[1].split(" (")[0].strip()
                    original_message = message_text.split("MESSAGE:\n")[1].split("\n\nAI DRAFT:")[0].strip()
                except:
                    pass

            # Extract AI draft from notification message
            # Format: "NEW MESSAGE from...\n\nMESSAGE:\n...\n\nAI DRAFT:\n{draft}\n\nChoose action:"
            if "AI DRAFT:" in message_text:
                draft_text = message_text.split("AI DRAFT:")[1].split("\n\nChoose action:")[0].strip()
            else:
                # Fallback: try to get from draft_system
                draft = draft_system.get_draft(chat_id)
                if draft:
                    draft_text = draft["draft"]
                    chat_title = draft.get("chat_title", "Unknown")
                    original_message = draft.get("original_message", "")
                else:
                    await event.answer("Draft not found", alert=True)
                    await event.edit("Draft not found - already deleted?")
                    return

            print(f"[DRAFT BOT] [DIRECT SEND] Sending to chat {chat_id}")
            print(f"[DRAFT BOT] [DIRECT SEND] Message length: {len(draft_text)} chars")

            # DIRECT METHOD - Same as Quick_test.py (proven to work)
            from telethon import TelegramClient

            api_id = int(os.getenv("TG_API_ID"))
            api_hash = os.getenv("TG_API_HASH")

            print(f"[DRAFT BOT] [DIRECT SEND] Creating TelegramClient with aibi_session")
            client = TelegramClient('aibi_session', api_id, api_hash)

            try:
                print(f"[DRAFT BOT] [DIRECT SEND] Connecting...")
                await client.connect()

                if not await client.is_user_authorized():
                    raise Exception("Session not authorized")

                print(f"[DRAFT BOT] [DIRECT SEND] Sending message to {chat_id}...")
                # EXACT same call that worked in Quick_test.py
                await client.send_message(chat_id, draft_text)

                print(f"[DRAFT BOT] [DIRECT SEND] [SUCCESS] Message sent!")

                # === ENHANCEMENT 1: Log approved reply for Knowledge Base ===
                # === AI SELF-LEARNING: Capture Success Pattern ===
                try:
                    kb_storage = get_knowledge_base()
                    confidence = 90  # Default confidence for manually approved replies

                    # Save to successful_replies.json
                    success = kb_storage.add_successful_reply(
                        chat_id=chat_id,
                        chat_title=chat_title,
                        client_question=original_message,
                        approved_response=draft_text,
                        confidence=confidence
                    )

                    if success:
                        print(f"[AI LEARNING] ✓ Success pattern captured from '{chat_title}'")
                        print(f"[AI LEARNING] Total patterns: {len(kb_storage.data['replies'])}")
                    else:
                        print(f"[AI LEARNING] [WARN] Failed to save pattern")

                except Exception as kb_error:
                    print(f"[AI LEARNING] [ERROR] Failed to capture pattern: {kb_error}")
                    import traceback
                    traceback.print_exc()

                # === ENHANCEMENT 2: Auto-Booking for meeting requests ===
                try:
                    from features.smart_enhancements import AutoBookingManager
                    from calendar_client import GoogleCalendarClient

                    calendar = GoogleCalendarClient()
                    auto_booking = AutoBookingManager(calendar)

                    meeting_info = await auto_booking.detect_meeting_request(original_message, draft_text)
                    if meeting_info:
                        print(f"[AUTO-BOOKING] Meeting detected! Creating calendar event...")
                        await auto_booking.create_pending_meeting(
                            chat_id=chat_id,
                            chat_title=chat_title,
                            message_text=original_message,
                            meeting_info=meeting_info
                        )
                        print(f"[AUTO-BOOKING] [SUCCESS] Calendar event created for {chat_title}")
                except Exception as booking_error:
                    print(f"[AUTO-BOOKING] [ERROR] Failed to create event: {booking_error}")

                # Success! Update UI
                await event.answer("Message delivered!", alert=False)
                try:
                    await event.edit(
                        f"{message_text}\n\n[SUCCESS] Message sent to chat {chat_id}",
                        buttons=None
                    )
                except Exception as e:
                    print(f"[ERROR] Failed to edit message: {e}")

                # Remove draft
                draft_system.remove_draft(chat_id)

            except Exception as send_error:
                print(f"[DRAFT BOT] [DIRECT SEND] [ERROR] {send_error}")
                await event.answer("Failed to send message", alert=True)
                try:
                    await event.edit(
                        f"{message_text}\n\n[ERROR] Failed to send - please retry",
                        buttons=None
                    )
                except:
                    pass
            finally:
                await client.disconnect()
                print(f"[DRAFT BOT] [DIRECT SEND] Disconnected")

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
            # For NewMessage events, event.message is a direct property
            message = event.message
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

            # ENHANCED: Show confirmation button instead of sending immediately
            draft = draft_system.get_draft(chat_id)
            if not draft:
                await event.reply("[ERROR] Draft not found - already sent?")
                return

            # Show new draft with confirmation button
            confirmation_message = (
                f"[EDITED DRAFT] for {draft['chat_title']} (ID: {chat_id})\n\n"
                f"NEW TEXT:\n{new_text}\n\n"
                f"Confirm to send this edited version:"
            )

            confirm_button = [
                [Button.inline("[SEND] Confirm & Send", f"confirm_{chat_id}")]
            ]

            # Store the edited text temporarily
            if not hasattr(self, 'pending_edits'):
                self.pending_edits = {}
            self.pending_edits[chat_id] = new_text

            await event.reply(confirmation_message, buttons=confirm_button)
            print(f"[DRAFT BOT] Edited draft shown with confirmation button for chat {chat_id}")

        except Exception as e:
            print(f"[ERROR] Error in handle_edit_text: {type(e).__name__}: {e}")
            print(f"[ERROR] Traceback: {traceback.format_exc()}")

    async def send_confirmed_edit(self, chat_id: int, event):
        """
        Send confirmed edited message using DIRECT method (same as Quick_test.py)
        This is called after user confirms the edited draft
        """
        try:
            # Get the pending edited text
            if not hasattr(self, 'pending_edits') or chat_id not in self.pending_edits:
                await event.answer("Edit text not found", alert=True)
                await event.edit("[ERROR] Edit text was lost - please try again")
                return

            edited_text = self.pending_edits[chat_id]
            # For CallbackQuery, fetch message asynchronously
            message = await event.get_message()
            message_text = message.text or ""

            print(f"[DRAFT BOT] [DIRECT SEND] Sending edited message to chat {chat_id}")
            print(f"[DRAFT BOT] [DIRECT SEND] Message length: {len(edited_text)} chars")

            # DIRECT METHOD - Same as Quick_test.py (proven to work)
            from telethon import TelegramClient

            api_id = int(os.getenv("TG_API_ID"))
            api_hash = os.getenv("TG_API_HASH")

            print(f"[DRAFT BOT] [DIRECT SEND] Creating TelegramClient with aibi_session")
            client = TelegramClient('aibi_session', api_id, api_hash)

            try:
                print(f"[DRAFT BOT] [DIRECT SEND] Connecting...")
                await client.connect()

                if not await client.is_user_authorized():
                    raise Exception("Session not authorized")

                print(f"[DRAFT BOT] [DIRECT SEND] Sending edited message to {chat_id}...")
                # EXACT same call that worked in Quick_test.py
                await client.send_message(chat_id, edited_text)

                print(f"[DRAFT BOT] [DIRECT SEND] [SUCCESS] Edited message sent!")

                # Success! Update UI
                await event.answer("Edited message delivered!", alert=False)
                try:
                    await event.edit(
                        f"{message_text}\n\n[SUCCESS] Edited message sent to chat {chat_id}",
                        buttons=None
                    )
                except Exception as e:
                    print(f"[ERROR] Failed to edit message: {e}")

                # Clean up
                del self.pending_edits[chat_id]
                draft_system.remove_draft(chat_id)

            except Exception as send_error:
                print(f"[DRAFT BOT] [DIRECT SEND] [ERROR] {send_error}")
                await event.answer("Failed to send edited message", alert=True)
                try:
                    await event.edit(
                        f"{message_text}\n\n[ERROR] Failed to send - please retry",
                        buttons=None
                    )
                except:
                    pass
            finally:
                await client.disconnect()
                print(f"[DRAFT BOT] [DIRECT SEND] Disconnected")

        except Exception as e:
            print(f"[ERROR] Error in send_confirmed_edit: {type(e).__name__}: {e}")
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            try:
                await event.answer(f"Error: {e}", alert=True)
            except:
                pass

    async def send_edited_message(self, chat_id: int, new_text: str, event):
        """DEPRECATED: Old method - now using send_confirmed_edit with Direct Send"""
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

[DATA] Total Chats Processed: {total_chats}
[OK] High Confidence (≥80%): {high_confidence_count}
[DRAFT] Drafts/Replies: {drafted_count}

--------------------
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
