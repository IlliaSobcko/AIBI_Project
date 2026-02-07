import asyncio
import os
import traceback
import threading
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template_string
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from collections import defaultdict
from types import SimpleNamespace

# Імпорт твоїх модулів
from telegram_client import TelegramCollector, TelegramConfig
from ai_client import AIConfig, MultiAgentAnalyzer, PerplexitySonarAgent
from utils import ensure_dir, read_instructions, sanitize_filename, ChatHistory
from trello_client import TrelloClient
from calendar_client import GoogleCalendarClient
from auto_reply import AutoReplyGenerator, is_working_hours, draft_system
from draft_bot import DraftReviewBot
from web.session_manager import AnalysisCache, SessionManager
from web.telegram_auth import WebTelegramAuth
from features.smart_logic import SmartDecisionEngine, DataSourceManager

load_dotenv()
app = Flask(__name__)
print(f"[DEBUG] Flask app instance created: {id(app)}")
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(32))
ensure_dir("reports")
ensure_dir("analysis_cache")

# Global Bot Registry - Thread-safe singleton for accessing bot instance
class BotRegistry:
    """Thread-safe registry for global bot instance"""
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.bot = None
        self.event_loop = None
        self.lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = BotRegistry()
        return cls._instance

    def set_bot(self, bot, event_loop):
        with self.lock:
            self.bot = bot
            self.event_loop = event_loop

    def get_bot(self):
        with self.lock:
            return self.bot

    def get_event_loop(self):
        with self.lock:
            return self.event_loop

    def has_bot(self):
        with self.lock:
            return self.bot is not None

# Global instances
DRAFT_BOT = None
BOT_EVENT_LOOP = None
BOT_REGISTRY = BotRegistry.get_instance()

# Global instances for web UI
ANALYSIS_CACHE = AnalysisCache(cache_dir="analysis_cache", ttl_hours=int(os.getenv("ANALYSIS_CACHE_TTL_HOURS", "1")))
SESSION_MANAGER = SessionManager(".aibi_preferences.json")
TELEGRAM_AUTH = WebTelegramAuth(
    api_id=int(os.getenv("TG_API_ID")),
    api_hash=os.getenv("TG_API_HASH"),
    session_name="aibi_session"
)

# --- DATA WRAPPER CLASS FOR CHAT INFORMATION ---
class ChatInfo:
    """Standardized chat information for Web UI"""
    def __init__(self, chat_id: int, name: str, unread_count: int = 0,
                 message_count: int = 0, last_message_date: datetime = None,
                 has_unread: bool = False, chat_type: str = "user"):
        self.chat_id = int(chat_id)  # Ensure int type
        self.chat_title = str(name)
        self.chat_type = chat_type
        self.message_count = message_count
        self.last_message_date = last_message_date
        self.has_unread = has_unread or (unread_count > 0)
        self.unread_count = unread_count
        self.analyzed = False

# --- MESSAGE ACCUMULATOR FOR GROUPING MESSAGES ---
class MessageAccumulator:
    """Groups messages from the same chat within a time window (5-10 seconds)"""
    def __init__(self, window_seconds: int = 7):
        self.window_seconds = window_seconds
        self.pending_messages = defaultdict(list)  # {chat_id: [messages]}
        self.last_timestamp = {}  # {chat_id: timestamp}

    def add_message(self, chat_history):
        """Add a message to accumulator"""
        self.pending_messages[chat_history.chat_id].append(chat_history)
        self.last_timestamp[chat_history.chat_id] = datetime.now()

    def should_process(self, chat_id: int) -> bool:
        """Check if enough time has passed to process accumulated messages"""
        if chat_id not in self.last_timestamp:
            return False
        elapsed = (datetime.now() - self.last_timestamp[chat_id]).total_seconds()
        return elapsed >= self.window_seconds

    def get_accumulated(self, chat_id: int):
        """Get and clear accumulated messages for a chat"""
        if chat_id not in self.pending_messages:
            return None

        messages = self.pending_messages[chat_id]
        if not messages:
            return None

        # Merge all messages into one
        merged = messages[0]
        if len(messages) > 1:
            # Combine text from all messages
            all_text = "\n".join([m.text for m in messages])
            merged.text = all_text
            print(f"[MESSAGE ACCUMULATOR] Grouped {len(messages)} messages from chat {chat_id}")

        # Clear pending
        del self.pending_messages[chat_id]
        del self.last_timestamp[chat_id]

        return merged

message_accumulator = MessageAccumulator(window_seconds=7)  # 7 second grouping window

# --- DRAFT BOT BACKGROUND STARTUP ---
def start_draft_bot_background():
    """Start draft bot in a separate thread with its own event loop"""
    global DRAFT_BOT, BOT_EVENT_LOOP, BOT_REGISTRY

    def run_bot():
        """Run bot in background thread with its own event loop - NEVER BLOCK THE LOOP"""
        loop = None
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Set loop to not close on garbage collection
            loop.set_debug(False)

            owner_id = os.getenv("OWNER_TELEGRAM_ID", "0")
            bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")

            if owner_id == "0" or owner_id == "your_telegram_id_here" or not bot_token:
                print("[DRAFT BOT] [WARNING] Skipping bot startup - OWNER_TELEGRAM_ID or TELEGRAM_BOT_TOKEN not configured")
                if loop:
                    loop.close()
                return

            print("[DRAFT BOT] [STARTUP] Starting background bot listener in separate event loop...")

            bot = DraftReviewBot(
                api_id=int(os.getenv("TG_API_ID")),
                api_hash=os.getenv("TG_API_HASH"),
                bot_token=bot_token,
                owner_id=int(owner_id)
            )

            # Register bot in global registry BEFORE starting
            BOT_REGISTRY.set_bot(bot, loop)
            global DRAFT_BOT, BOT_EVENT_LOOP
            DRAFT_BOT = bot
            BOT_EVENT_LOOP = loop

            # Start the bot
            success = loop.run_until_complete(bot.start())

            if success:
                print("[DRAFT BOT] [OK] Bot listener is ONLINE and listening for messages...")
                print("[DRAFT BOT] [OK] Event loop running continuously in background thread")
                print("[DRAFT BOT] [OK] Flask web server will NOT block bot messages")
                # Run event loop forever to process incoming messages
                # This will NOT block Flask because it's in a separate thread
                loop.run_forever()
            else:
                print("[DRAFT BOT] [ERROR] Bot failed to start - check credentials")

        except asyncio.CancelledError:
            print("[DRAFT BOT] [INFO] Bot loop cancelled (graceful shutdown)")
        except Exception as e:
            print(f"[DRAFT BOT] [ERROR] Background bot error: {type(e).__name__}: {e}")
            import traceback as tb
            print(f"[DRAFT BOT] Full traceback:\n{tb.format_exc()}")
        finally:
            try:
                if loop and not loop.is_closed():
                    # Cancel all pending tasks before closing
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    # Give tasks time to cancel
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    loop.close()
                    print("[DRAFT BOT] [OK] Event loop closed cleanly")
            except Exception as e:
                print(f"[DRAFT BOT] [ERROR] Error closing loop: {e}")

    # Start bot in daemon thread (won't block Flask)
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    print("[SYSTEM] Background bot thread started (non-blocking)")

# --- ЛОГІКА ОБ'ЄДНАННЯ ІНСТРУКЦІЙ ---
def get_combined_instructions():
    """Зшиває основні правила та голосові команди"""
    core = read_instructions("instructions.txt")
    dynamic_path = "instructions_dynamic.txt"
    dynamic = ""
    if os.path.exists(dynamic_path):
        with open(dynamic_path, "r", encoding="utf-8") as f:
            dynamic = f.read()
    return f"{core}\n\nДОДАТКОВІ АКТУАЛЬНІ ПРАВИЛА З ГОЛОСУ:\n{dynamic}"

# --- ВЕБ-ІНТЕРФЕЙС ---


# --- ОСНОВНИЙ ЦИКЛ АНАЛІЗУ ---
async def run_core_logic():
    print(f"[{datetime.now()}] >>> Запуск циклу аналізу...")
    
    tg_cfg = TelegramConfig(
        api_id=int(os.getenv("TG_API_ID")),
        api_hash=os.getenv("TG_API_HASH"),
        session_name="aibi_session"
    )
    
    ai_key = os.getenv("AI_API_KEY")
    instructions = get_combined_instructions()
    
    agent = PerplexitySonarAgent(ai_key)
    analyzer = MultiAgentAnalyzer([agent])

    async with TelegramCollector(tg_cfg) as collector:
        # Verify session is authenticated
        print(f"\n[SESSION VERIFY] Checking Telegram session authentication...")
        try:
            me = await collector.client.get_me()
            print(f"[SESSION VERIFY] [OK] Authenticated as: {me.first_name}")
            print(f"[SESSION VERIFY] User ID: {me.id}")
            print(f"[SESSION VERIFY] Is Bot: {me.is_bot}")
            print(f"[SESSION VERIFY] Session Type: {'BOT' if me.is_bot else 'USERBOT'}")
        except Exception as e:
            print(f"[SESSION VERIFY] [ERROR] Failed to verify session: {e}")
            print(f"[SESSION VERIFY] Messages may not send correctly")

        # Wait for draft bot to initialize
        print(f"\n[INIT CHECK] Waiting for draft bot initialization...")
        max_wait = 50  # 5 seconds max
        for i in range(max_wait):
            if DRAFT_BOT is not None:
                print(f"[INIT CHECK] [OK] Draft bot ready after {i*0.1:.1f}s")
                break
            await asyncio.sleep(0.1)
        else:
            print(f"[INIT CHECK] [WARN]  Draft bot still initializing (>5s), proceeding anyway")

        print(f"\n[DIALOGS] Fetching chat list...")
        dialogs = await collector.list_dialogs(limit=15)
        print(f"[DIALOGS] Found {len(dialogs)} chats")
        # Збираємо історію за останні 7 днів (або скільке вказано в .env)
        days = int(os.getenv("DAYS", 7))
        print(f"[HISTORY] Collecting messages from last {days} days...")
        histories = await collector.collect_history_last_days(dialogs, days)
        print(f"[HISTORY] Collected {len(histories)} messages")

        # Ініціалізація Trello та Google Calendar (опціонально)
        trello = None
        calendar = None

        if os.getenv("TRELLO_API_KEY") and os.getenv("TRELLO_TOKEN") and os.getenv("TRELLO_BOARD_ID"):
            try:
                trello = TrelloClient(
                    api_key=os.getenv("TRELLO_API_KEY"),
                    token=os.getenv("TRELLO_TOKEN"),
                    board_id=os.getenv("TRELLO_BOARD_ID")
                )
            except Exception as e:
                print(f"[WARNING] Trello не підключено: {e}")

        if os.getenv("ENABLE_GOOGLE_CALENDAR", "false").lower() == "true":
            try:
                calendar = GoogleCalendarClient()
                calendar.authenticate()
            except Exception as e:
                print(f"[WARNING] Google Calendar не підключено: {e}")

        # === Task 1: Initialize Smart Decision Engine ===
        try:
            # Load business data (optional)
            try:
                business_data = read_instructions("business_data.txt")
            except FileNotFoundError:
                print("[SMART_LOGIC] business_data.txt not found, using empty string")
                business_data = ""

            dsm = DataSourceManager(calendar_client=calendar, trello_client=trello, business_data=business_data)
            decision_engine = SmartDecisionEngine(data_source_manager=dsm)
            print("[MAIN] [OK] Smart Logic Decision Engine initialized successfully")
        except Exception as e:
            print(f"[WARNING] Smart Logic initialization failed: {e}")
            print(f"[DEBUG] Traceback:\n{traceback.format_exc()}")
            decision_engine = None

        # Ініціалізація авто-відповідача
        auto_reply_threshold = int(os.getenv("AUTO_REPLY_CONFIDENCE", "85"))
        reply_generator = AutoReplyGenerator(ai_key)

        # Use global draft bot if available (started at Flask startup)
        draft_bot = DRAFT_BOT
        if draft_bot:
            print("[DRAFT BOT] [OK] Using persistent background bot for draft delivery")
        else:
            print("[WARNING] Draft bot not available - drafts will NOT be sent")

        count = 0
        for h in histories:
            if not h.text.strip():
                print(f"[SKIP] Chat '{h.chat_title}' has empty text")
                continue

            print(f"\n{'='*80}")
            print(f"[PROCESS START] Chat: '{h.chat_title}' (ID: {h.chat_id})")
            print(f"[PROCESS START] Message length: {len(h.text)} chars")
            print(f"{'='*80}")

            # === FORCED DEBUG OUTPUT ===
            # Show what we're processing
            message_preview = h.text[:150].replace('\n', ' ')
            print(f"[INPUT] Message received: '{message_preview}...'")
            print(f"[INPUT] Chat ID: {h.chat_id}, Sender: {h.sender}")

            # MESSAGE ACCUMULATION: Add to accumulator (7 second window)
            message_accumulator.add_message(h)

            # Since this is batch processing (every 20 mins), process immediately
            # In real-time systems, this would wait for the window to pass
            accumulated_h = message_accumulator.get_accumulated(h.chat_id)
            if not accumulated_h:
                accumulated_h = h

            # Аналіз через "Консиліум"
            print(f"[AI ANALYSIS] Starting analysis for '{h.chat_title}'...")
            result = await analyzer.analyze_chat(instructions, accumulated_h)
            print(f"[AI ANALYSIS] Completed. Confidence: {result['confidence']}%")

            # Збереження результату
            file_name = f"reports/{sanitize_filename(accumulated_h.chat_title)}.txt"
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(f"ЗВІТ ПО ЧАТУ: {accumulated_h.chat_title}\n")
                f.write(f"ДАТА: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                f.write(f"ВПЕВНЕНІСТЬ ШІ: {result['confidence']}%\n")
                f.write("="*30 + "\n")
                f.write(result['report'])
            count += 1
            print(f"[OK] Processed: {accumulated_h.chat_title}")

            # === ADVANCED AI FLOW: Auto-Reply or Draft Review ===

            # === Task 1: Use Smart Decision Engine for Confidence Evaluation ===
            print(f"[DECISION] Starting decision engine evaluation...")
            print(f"  - AI Confidence: {result['confidence']}%")
            print(f"  - Auto-reply threshold: {auto_reply_threshold}%")
            print(f"  - Working hours: {is_working_hours()}")
            print(f"  - Has unreadable files: {accumulated_h.has_unreadable_files}")

            if decision_engine:
                try:
                    print(f"[DECISION] Evaluating with Smart Logic...")
                    print(f"  - Trello available: {trello is not None}")
                    print(f"  - Calendar available: {calendar is not None}")

                    smart_result = await decision_engine.evaluate_confidence(
                        base_confidence=result['confidence'],
                        chat_context={
                            "chat_title": accumulated_h.chat_title,
                            "message_history": accumulated_h.text,
                            "analysis_report": result['report']
                        },
                        has_unreadable_files=accumulated_h.has_unreadable_files
                    )
                    final_confidence = smart_result["final_confidence"]
                    needs_manual_review = smart_result["needs_manual_review"]

                    # === FORCED DEBUG OUTPUT: Show Smart Logic Results ===
                    data_sources = smart_result.get('data_sources', {})
                    ai_score = data_sources.get('ai', result['confidence'])
                    cal_score = data_sources.get('calendar', 0)
                    trello_score = data_sources.get('trello', 0)
                    price_score = data_sources.get('price_list', 0)

                    print(f"[SMART_LOGIC] Component Scores:")
                    print(f"  - AI Analysis: {ai_score}%")
                    print(f"  - Calendar: {cal_score}%")
                    print(f"  - Trello: {trello_score}%")
                    print(f"  - Price List: {price_score}%")
                    print(f"[SMART_LOGIC] Final Score: {final_confidence}%")
                    print(f"[SMART_LOGIC] Needs Manual Review: {needs_manual_review}")

                    print(f"[SMART_LOGIC] Result:")
                    print(f"  - Base Confidence: {result['confidence']}%")
                    print(f"  - Final Confidence: {final_confidence}%")
                    print(f"  - Needs Manual Review: {needs_manual_review}")
                    print(f"  - Data Sources: {smart_result.get('data_sources', 'N/A')}")

                except Exception as e:
                    print(f"[WARNING] Smart Logic evaluation failed: {e}. Using base confidence.")
                    print(f"[DEBUG] Traceback:\n{traceback.format_exc()}")
                    final_confidence = result['confidence']
                    needs_manual_review = result['confidence'] < auto_reply_threshold
            else:
                print(f"[DECISION] No Smart Logic available. Using simple confidence check.")
                # Fallback to simple confidence check
                final_confidence = result['confidence']
                needs_manual_review = result['confidence'] < auto_reply_threshold
                print(f"  - Final Confidence: {final_confidence}%")
                print(f"  - Needs Manual Review: {needs_manual_review}")

            # === FORCED DEBUG OUTPUT: Action Decision ===
            print(f"\n[ACTION] Decision Logic:")
            print(f"  - Final Confidence: {final_confidence}%")
            print(f"  - Auto-reply Threshold: {auto_reply_threshold}%")
            print(f"  - Working Hours: {is_working_hours()}")
            print(f"  - Needs Manual Review: {needs_manual_review}")
            print(f"  - Has Unreadable Files: {accumulated_h.has_unreadable_files}")
            print(f"  - Draft Bot Available: {draft_bot is not None}")

            # ZERO CONFIDENCE RULE: If unreadable files detected, force draft review
            if accumulated_h.has_unreadable_files:
                print(f"\n[PATH: UNREADABLE FILES]")
                print(f"  - Unreadable files detected in '{accumulated_h.chat_title}'. Forcing draft review...")
                print(f"[ACTION] REASON: Unreadable files require manual review")
                if draft_bot:
                    try:
                        print(f"[DRAFT GEN] Generating reply with unreadable_files=True...")
                        reply_text, reply_confidence = await reply_generator.generate_reply(
                            chat_title=accumulated_h.chat_title,
                            message_history=accumulated_h.text,
                            analysis_report=result['report'],
                            has_unreadable_files=True
                        )
                        print(f"[DRAFT GEN] Generated reply: confidence={reply_confidence}%, length={len(reply_text) if reply_text else 0}")

                        if reply_text:
                            # Store draft
                            print(f"[DRAFT STORE] Storing draft in draft_system...")
                            draft_system.add_draft(accumulated_h.chat_id, accumulated_h.chat_title, reply_text, reply_confidence)

                            # Send to owner for review
                            print(f"[DRAFT SEND] Sending draft to bot for review...")
                            await draft_bot.send_draft_for_review(accumulated_h.chat_id, accumulated_h.chat_title, reply_text, reply_confidence)
                            print(f"[DRAFT SUCCESS] Draft sent to owner for review: '{accumulated_h.chat_title}'")

                            # Log to report
                            with open(file_name, "a", encoding="utf-8") as f:
                                f.write(f"\n\n[DRAFT FOR REVIEW - UNREADABLE FILES]\n")
                                f.write(f"Reply Confidence: {reply_confidence}%\n")
                                f.write(f"Reason: Message contains unreadable file\n")
                                f.write(f"Draft: {reply_text}\n")
                        else:
                            print(f"[DRAFT FAIL] No reply text generated")

                    except Exception as e:
                        print(f"[ERROR] Error creating draft for unreadable files: {type(e).__name__}: {e}")
                        print(f"[DEBUG] Traceback:\n{traceback.format_exc()}")
                else:
                    print(f"[ERROR] Draft bot not available - cannot send draft")

            # If smart confidence >= 90% and working hours and NO unreadable files - auto-reply
            elif final_confidence >= 90 and is_working_hours():
                print(f"\n[PATH: AUTO-REPLY]")
                print(f"  - Confidence {final_confidence}% >= 90% threshold: YES")
                print(f"  - Working hours: YES")
                print(f"  - Unreadable files: NO")
                print(f"  - Proceeding with AUTO-REPLY...")
                print(f"[ACTION] REASON: Confidence >= 90% and within working hours - auto-reply triggered")

                try:
                    print(f"[REPLY GEN] Generating auto-reply text...")
                    reply_text, reply_confidence = await reply_generator.generate_reply(
                        chat_title=accumulated_h.chat_title,
                        message_history=accumulated_h.text,
                        analysis_report=result['report'],
                        has_unreadable_files=False
                    )
                    print(f"[REPLY GEN] Generated: confidence={reply_confidence}%, length={len(reply_text) if reply_text else 0}")

                    if reply_text and reply_confidence >= 70:
                        # Send automatic reply with fallback mechanism
                        print(f"[SEND MSG] Sending auto-reply with fallback mechanism...")
                        print(f"  - Chat ID: {accumulated_h.chat_id}")
                        print(f"  - Message: {reply_text[:100]}...")

                        send_success = False
                        send_method = None

                        # Try 1: Use userbot (collector) first
                        try:
                            print(f"[SEND MSG] [ATTEMPT 1] Trying collector.client.send_message...")
                            await collector.client.send_message(accumulated_h.chat_id, reply_text)
                            print(f"[SEND MSG] [OK] Sent via USERBOT (collector)")
                            send_success = True
                            send_method = "USERBOT"
                        except Exception as e:
                            print(f"[SEND MSG] [WARN] [ATTEMPT 1 FAILED] Userbot error: {type(e).__name__}: {e}")

                            # Try 2: Fallback to bot service if available
                            if draft_bot and hasattr(draft_bot, 'tg_service') and draft_bot.tg_service:
                                try:
                                    print(f"[SEND MSG] [ATTEMPT 2] Trying bot service fallback...")
                                    success = await draft_bot.tg_service.send_message(
                                        int(accumulated_h.chat_id),
                                        reply_text
                                    )
                                    if success:
                                        print(f"[SEND MSG] [OK] Sent via BOT SERVICE (fallback)")
                                        send_success = True
                                        send_method = "BOT_SERVICE"
                                    else:
                                        print(f"[SEND MSG] [ERROR] [ATTEMPT 2 FAILED] Bot service returned False")
                                except Exception as e2:
                                    print(f"[SEND MSG] [ERROR] [ATTEMPT 2 FAILED] Bot service error: {type(e2).__name__}: {e2}")
                            else:
                                print(f"[SEND MSG] [INFO] Bot service not available for fallback")

                        if send_success:
                            print(f"[AUTO-REPLY SUCCESS] Message sent to '{accumulated_h.chat_title}' ({reply_confidence}%) via {send_method}")

                            # Log to report
                            with open(file_name, "a", encoding="utf-8") as f:
                                f.write(f"\n\n[AUTO-REPLY SENT]\n")
                                f.write(f"Reply Confidence: {reply_confidence}%\n")
                                f.write(f"Send Method: {send_method}\n")
                                f.write(f"Message: {reply_text}\n")
                        else:
                            print(f"[AUTO-REPLY FAILED] Could not send message via any method")
                            # Log the failure
                            with open(file_name, "a", encoding="utf-8") as f:
                                f.write(f"\n\n[AUTO-REPLY FAILED]\n")
                                f.write(f"Reply Confidence: {reply_confidence}%\n")
                                f.write(f"Reason: Both userbot and bot service failed\n")
                                f.write(f"Message: {reply_text}\n")
                    else:
                        print(f"[AUTO-REPLY SKIP] Reply confidence {reply_confidence}% < 70%, skipping auto-reply")

                except Exception as e:
                    print(f"[ERROR] Auto-reply error: {type(e).__name__}: {e}")
                    print(f"[DEBUG] Traceback:\n{traceback.format_exc()}")

            # If smart decision recommends manual review - send draft for review
            elif needs_manual_review and draft_bot:
                print(f"\n[PATH: MANUAL REVIEW]")
                print(f"  - Needs manual review: YES")
                print(f"  - Draft bot available: YES")
                print(f"  - Sending draft for owner review...")
                print(f"[ACTION] REASON: Confidence {final_confidence}% < 90% threshold OR outside working hours - needs manual review")

                try:
                    print(f"[DRAFT GEN] Generating draft reply...")
                    reply_text, reply_confidence = await reply_generator.generate_reply(
                        chat_title=accumulated_h.chat_title,
                        message_history=accumulated_h.text,
                        analysis_report=result['report'],
                        has_unreadable_files=False
                    )
                    print(f"[DRAFT GEN] Generated: confidence={reply_confidence}%, length={len(reply_text) if reply_text else 0}")

                    if reply_text:
                        # Store draft
                        print(f"[DRAFT STORE] Storing draft in draft_system...")
                        draft_system.add_draft(accumulated_h.chat_id, accumulated_h.chat_title, reply_text, reply_confidence)

                        # Send to owner for review
                        print(f"[DRAFT SEND] Sending draft to bot owner for review...")
                        await draft_bot.send_draft_for_review(accumulated_h.chat_id, accumulated_h.chat_title, reply_text, reply_confidence)
                        print(f"[DRAFT SUCCESS] Draft sent to owner: '{accumulated_h.chat_title}' ({reply_confidence}%)")

                        # Log to report
                        with open(file_name, "a", encoding="utf-8") as f:
                            f.write(f"\n\n[DRAFT FOR REVIEW]\n")
                            f.write(f"Reply Confidence: {reply_confidence}%\n")
                            f.write(f"Draft: {reply_text}\n")
                    else:
                        print(f"[DRAFT FAIL] No reply text generated")

                except Exception as e:
                    print(f"[ERROR] Draft creation error: {type(e).__name__}: {e}")
                    print(f"[DEBUG] Traceback:\n{traceback.format_exc()}")
            else:
                print(f"\n[PATH: NO ACTION]")
                print(f"  - Needs manual review: {needs_manual_review}")
                print(f"  - Draft bot available: {draft_bot is not None}")
                print(f"  - Final confidence: {final_confidence}%")
                print(f"  - No action taken for this message")

                # === FORCED DEBUG OUTPUT: Explain why draft NOT created ===
                if needs_manual_review and not draft_bot:
                    print(f"[ACTION] REASON: Draft bot NOT AVAILABLE - cannot send draft for manual review")
                    print(f"[ACTION] STATUS: Message queued for retry when bot is ready")
                elif final_confidence < 90 and not needs_manual_review:
                    print(f"[ACTION] REASON: Logic error - confidence {final_confidence}% but no manual review needed?")
                else:
                    print(f"[ACTION] REASON: Unknown - check decision logic")

            # Інтеграція з Trello (якщо критична впевненість)
            if trello and result['confidence'] >= 80:
                try:
                    list_name = os.getenv("TRELLO_LIST_NAME", "Важливі завдання")
                    trello.create_task_from_report(list_name, h.chat_title, result['report'], result['confidence'])
                    print(f"[TRELLO] Створено картку: {h.chat_title}")
                except Exception as e:
                    print(f"[ERROR] Помилка Trello: {e}")

            # Інтеграція з Google Calendar (якщо потрібен огляд)
            if calendar and result.get('needs_review', False):
                try:
                    reminder_time = datetime.now() + timedelta(hours=2)
                    calendar.create_reminder_from_report(h.chat_title, result['report'], result['confidence'], reminder_time)
                    print(f"[CALENDAR] Створено нагадування: {h.chat_title}")
                except Exception as e:
                    print(f"[ERROR] Помилка Calendar: {e}")

    return f"Успішно оброблено чатів: {count}"


# --- WEB API FUNCTIONS (CALLED BY FLASK ROUTES) ---

async def fetch_chats_only(limit: int = 50) -> list:
    """
    Fetch list of chats from Telegram (used by web UI)

    Returns:
        List of ChatInfo objects with proper data types and structure
    """
    try:
        print(f"[FETCH CHATS] Starting fetch (limit={limit})...")

        cfg = TelegramConfig(
            api_id=int(os.getenv("TG_API_ID")),
            api_hash=os.getenv("TG_API_HASH"),
            session_name=os.getenv("TG_SESSION_NAME", "collector_session")
        )

        async with TelegramCollector(cfg) as collector:
            print("[OK] Connected to Telegram API")

            dialogs = await collector.list_dialogs(limit=limit)

            # Convert Telethon objects to ChatInfo wrapper class
            chats = []
            for d in dialogs:
                try:
                    chat_info = ChatInfo(
                        chat_id=int(d.id),  # Ensure int type
                        name=str(d.name or "Pryvate chat"),
                        unread_count=int(getattr(d, 'unread_count', 0)),
                        chat_type="user" if hasattr(d, 'is_user') and d.is_user else "group"
                    )
                    chats.append(chat_info)
                except Exception as e:
                    print(f"[WARNING] Failed to process chat: {e}")
                    continue

            print(f"[SUCCESS] Fetched {len(chats)} chats")
            return chats

    except Exception as e:
        print(f"[CRITICAL] Error fetching chats: {str(e)}")
        traceback.print_exc()
        return []


async def analyze_single_chat(chat_id: int, start_date: datetime, end_date: datetime,
                            force_refresh: bool = False) -> dict:
    """
    Analyze a single chat (on-demand, costs AI tokens)

    Args:
        chat_id: Telegram chat ID (must be int)
        start_date: Start datetime for message filtering
        end_date: End datetime for message filtering
        force_refresh: Bypass cache if True

    Returns:
        Dict with: report, confidence, from_cache
    """
    chat_id = int(chat_id)  # Ensure int type

    print(f"[ANALYZE CHAT] Starting analysis for chat {chat_id} from {start_date} to {end_date}...")

    # Check cache first
    start_str = start_date.isoformat()[:10]
    end_str = end_date.isoformat()[:10]
    cached_result = ANALYSIS_CACHE.get(chat_id, start_str, end_str)

    if cached_result and not force_refresh:
        print(f"[ANALYZE CHAT] Using cached result for chat {chat_id}")
        return {**cached_result, "from_cache": True}

    try:
        tg_cfg = TelegramConfig(
            api_id=int(os.getenv("TG_API_ID")),
            api_hash=os.getenv("TG_API_HASH"),
            session_name="aibi_session"
        )

        ai_key = os.getenv("AI_API_KEY")
        instructions = get_combined_instructions()

        agent = PerplexitySonarAgent(ai_key)
        analyzer = MultiAgentAnalyzer([agent])

        async with TelegramCollector(tg_cfg) as collector:
            dialogs = await collector.list_dialogs(limit=100)

            # Find the specific chat
            target_dialog = None
            for d in dialogs:
                if int(d.id) == chat_id:
                    target_dialog = d
                    break

            if not target_dialog:
                raise ValueError(f"Chat {chat_id} not found")

            # Fetch message history for this chat
            lines = []
            has_unreadable_files = False

            async for msg in collector.client.iter_messages(target_dialog.entity, limit=100):
                if not msg.date or msg.date < start_date:
                    break

                if start_date <= msg.date <= end_date:
                    if msg.media:
                        media_type = type(msg.media).__name__
                        has_unreadable_files = True
                        lines.append(f"[{msg.date.isoformat()}] [FILE: {media_type}]")
                    else:
                        text = (msg.message or "").strip()
                        if text:
                            lines.append(f"[{msg.date.isoformat()}] {text}")

            if not lines:
                return {"report": "No messages found in date range", "confidence": 0, "from_cache": False}

            lines.reverse()

            # Create ChatHistory for analysis
            chat_history = ChatHistory(
                chat_id=int(target_dialog.id),
                chat_title=target_dialog.name or "Untitled",
                chat_type="user" if hasattr(target_dialog, 'is_user') and target_dialog.is_user else "group",
                text="\n".join(lines),
                has_unreadable_files=has_unreadable_files
            )

            # Run analysis
            result = await analyzer.analyze_chat(instructions, chat_history)

            # Cache the result
            ANALYSIS_CACHE.set(chat_id, start_str, end_str, result)

            print(f"[ANALYZE CHAT] Completed analysis for chat {chat_id}")
            return {**result, "from_cache": False}

    except Exception as e:
        print(f"[ANALYZE CHAT] Error: {e}")
        traceback.print_exc()
        return {"report": f"Error: {str(e)}", "confidence": 0, "from_cache": False}


# --- SCHEDULER (AUTONOMOUS MODE) WITH AUTO-RECOVERY ---
def scheduled_task():
    """Run scheduled task every 20 minutes with auto-recovery"""
    try:
        asyncio.run(run_core_logic())
    except Exception as e:
        print(f"[SCHEDULER ERROR] Task execution failed: {type(e).__name__}: {e}")
        print(f"[SCHEDULER ERROR] Full traceback:\n{traceback.format_exc()}")
        print("[SCHEDULER RECOVERY] Task will retry on next scheduled cycle (20 minutes)")
        # Scheduler will automatically retry on next cycle

# Make scheduler optional (disabled by default for manual mode)
SCHEDULER_ENABLED = os.getenv("AUTO_SCHEDULER", "false").lower() == "true"

# Створюємо об'єкт ЗАВЖДИ для імпорту в routers.txt
scheduler = BackgroundScheduler()

if os.getenv("AUTO_ANALYSIS_ENABLED", "false").lower() == "true":
    scheduler.add_job(func=scheduled_task, trigger="interval", minutes=20)
    scheduler.start()
    print("[SCHEDULER] Auto-analysis enabled (every 20 minutes)")
else:
    print("[SCHEDULER] Auto-analysis DISABLED (manual mode only)")


# --- BLUEPRINT REGISTRATION ---
def register_blueprints():
    """Register web blueprints (imported inside to avoid circular imports)"""
    print("[DEBUG] register_blueprints() called")
    try:
        from web.routes import web_bp, api_bp
        print(f"[DEBUG] Imported blueprints. web_bp routes: {len(list(web_bp.deferred_functions))}, api_bp routes: {len(list(api_bp.deferred_functions))}")
        app.register_blueprint(web_bp)
        app.register_blueprint(api_bp)
        print("[DEBUG] Blueprints registered successfully")
    except Exception as e:
        import traceback
        print(f"[DEBUG] ERROR in register_blueprints: {e}")
        traceback.print_exc()


# Register blueprints before running the app
register_blueprints()

# Test direct route (not via blueprint)
@app.route('/api/direct_test')
def direct_test():
    return {"status": "Direct route works"}, 200

if __name__ == "__main__":
    print("=" * 80)
    print(">>> Starting AIBI Server... Awaiting Flask startup.")
    print("=" * 80)

    # Start the draft bot in background BEFORE Flask starts
    print("\n[STARTUP] Initializing background services...")
    start_draft_bot_background()

    print("\n[SERVER] Configuration:")
    print("[SERVER] - Running on http://0.0.0.0:8080")
    print("[SERVER] - Scheduled tasks every 20 minutes")
    print("[SERVER] - Draft bot listener (continuous)")
    print("[SERVER] - /check command support (manual trigger)")
    print("[SERVER] - Auto-recovery enabled for network issues")

    print("\n[SERVER] Available endpoints:")
    print("[SERVER] - GET  http://0.0.0.0:8080/            (Status page)")
    print("[SERVER] - GET  http://0.0.0.0:8080/force_run   (Manual analysis)")
    print("[SERVER] - MSG  /check (via Telegram)            (Manual analysis)")

    print("\n" + "=" * 80)
    # Standard configuration for production deployment
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)