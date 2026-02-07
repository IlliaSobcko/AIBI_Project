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

# Global draft bot instance - runs continuously in background
DRAFT_BOT = None
BOT_EVENT_LOOP = None

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
    global DRAFT_BOT, BOT_EVENT_LOOP

    def run_bot():
        """Run bot in background thread with its own event loop"""
        try:
            BOT_EVENT_LOOP = asyncio.new_event_loop()
            asyncio.set_event_loop(BOT_EVENT_LOOP)

            owner_id = os.getenv("OWNER_TELEGRAM_ID", "0")
            bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")

            if owner_id == "0" or owner_id == "your_telegram_id_here" or not bot_token:
                print("[DRAFT BOT] [WARNING] Skipping bot startup - OWNER_TELEGRAM_ID or TELEGRAM_BOT_TOKEN not configured")
                return

            print("[DRAFT BOT] [STARTUP] Starting background bot listener...")

            DRAFT_BOT = DraftReviewBot(
                api_id=int(os.getenv("TG_API_ID")),
                api_hash=os.getenv("TG_API_HASH"),
                bot_token=bot_token,
                owner_id=int(owner_id)
            )

            success = BOT_EVENT_LOOP.run_until_complete(DRAFT_BOT.start())

            if success:
                print("[DRAFT BOT] [OK] Bot listener is ONLINE - Ready to receive buttons & commands")
                # Keep event loop running to process events
                BOT_EVENT_LOOP.run_forever()
            else:
                print("[DRAFT BOT] [ERROR] Bot failed to start")

        except Exception as e:
            print(f"[DRAFT BOT] [ERROR] Background bot error: {type(e).__name__}: {e}")
            print(f"[DRAFT BOT] Full traceback:\n{traceback.format_exc()}")

    # Start bot in daemon thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    print("[SYSTEM] Background bot thread started")

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
        dialogs = await collector.list_dialogs(limit=15)
        # Збираємо історію за останні 7 днів (або скільки вказано в .env)
        days = int(os.getenv("DAYS", 7))
        histories = await collector.collect_history_last_days(dialogs, days)

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
            business_data = read_instructions("business_data.txt", default="")
            dsm = DataSourceManager(calendar_client=calendar, trello_client=trello, business_data=business_data)
            decision_engine = SmartDecisionEngine(data_source_manager=dsm)
            print("[MAIN] Smart Logic Decision Engine initialized")
        except Exception as e:
            print(f"[WARNING] Smart Logic not available: {e}")
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
            if not h.text.strip(): continue

            # MESSAGE ACCUMULATION: Add to accumulator (7 second window)
            message_accumulator.add_message(h)

            # Since this is batch processing (every 20 mins), process immediately
            # In real-time systems, this would wait for the window to pass
            accumulated_h = message_accumulator.get_accumulated(h.chat_id)
            if not accumulated_h:
                accumulated_h = h

            # Аналіз через "Консиліум"
            result = await analyzer.analyze_chat(instructions, accumulated_h)

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
            if decision_engine:
                try:
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
                    print(f"[SMART_LOGIC] '{accumulated_h.chat_title}': Base={result['confidence']}% -> Final={final_confidence}% (Sources: {smart_result['data_sources']})")
                except Exception as e:
                    print(f"[WARNING] Smart Logic evaluation failed: {e}. Using base confidence.")
                    final_confidence = result['confidence']
                    needs_manual_review = result['confidence'] < auto_reply_threshold
            else:
                # Fallback to simple confidence check
                final_confidence = result['confidence']
                needs_manual_review = result['confidence'] < auto_reply_threshold

            # ZERO CONFIDENCE RULE: If unreadable files detected, force draft review
            if accumulated_h.has_unreadable_files:
                print(f"[ZERO CONFIDENCE] Unreadable files detected in '{accumulated_h.chat_title}'. Sending to draft...")
                if draft_bot:
                    try:
                        reply_text, reply_confidence = await reply_generator.generate_reply(
                            chat_title=accumulated_h.chat_title,
                            message_history=accumulated_h.text,
                            analysis_report=result['report'],
                            has_unreadable_files=True
                        )

                        if reply_text:
                            # Store draft
                            draft_system.add_draft(accumulated_h.chat_id, accumulated_h.chat_title, reply_text, reply_confidence)

                            # Send to owner for review
                            await draft_bot.send_draft_for_review(accumulated_h.chat_id, accumulated_h.chat_title, reply_text, reply_confidence)
                            print(f"[DRAFT] Unreadable files - Draft sent: '{accumulated_h.chat_title}'")

                            # Log to report
                            with open(file_name, "a", encoding="utf-8") as f:
                                f.write(f"\n\n[DRAFT FOR REVIEW - UNREADABLE FILES]\n")
                                f.write(f"Reply Confidence: {reply_confidence}%\n")
                                f.write(f"Reason: Message contains unreadable file\n")
                                f.write(f"Draft: {reply_text}\n")

                    except Exception as e:
                        print(f"[ERROR] Error creating draft for unreadable files: {e}")

            # If smart confidence >= 90% and working hours and NO unreadable files - auto-reply
            elif final_confidence >= 90 and is_working_hours():
                try:
                    reply_text, reply_confidence = await reply_generator.generate_reply(
                        chat_title=accumulated_h.chat_title,
                        message_history=accumulated_h.text,
                        analysis_report=result['report'],
                        has_unreadable_files=False
                    )

                    if reply_text and reply_confidence >= 70:
                        # Send automatic reply
                        await collector.client.send_message(accumulated_h.chat_id, reply_text)
                        print(f"[AUTO-REPLY] Sent to '{accumulated_h.chat_title}' ({reply_confidence}%)")

                        # Log to report
                        with open(file_name, "a", encoding="utf-8") as f:
                            f.write(f"\n\n[AUTO-REPLY SENT]\n")
                            f.write(f"Reply Confidence: {reply_confidence}%\n")
                            f.write(f"Message: {reply_text}\n")
                    else:
                        print(f"[AUTO-REPLY] Low confidence ({reply_confidence}%), skipping")

                except Exception as e:
                    print(f"[ERROR] Auto-reply error: {e}")

            # If smart decision recommends manual review - send draft for review
            elif needs_manual_review and draft_bot:
                try:
                    reply_text, reply_confidence = await reply_generator.generate_reply(
                        chat_title=accumulated_h.chat_title,
                        message_history=accumulated_h.text,
                        analysis_report=result['report'],
                        has_unreadable_files=False
                    )

                    if reply_text:
                        # Store draft
                        draft_system.add_draft(accumulated_h.chat_id, accumulated_h.chat_title, reply_text, reply_confidence)

                        # Send to owner for review
                        await draft_bot.send_draft_for_review(accumulated_h.chat_id, accumulated_h.chat_title, reply_text, reply_confidence)
                        print(f"[DRAFT] Draft sent: '{accumulated_h.chat_title}' ({reply_confidence}%)")

                        # Log to report
                        with open(file_name, "a", encoding="utf-8") as f:
                            f.write(f"\n\n[DRAFT FOR REVIEW]\n")
                            f.write(f"Reply Confidence: {reply_confidence}%\n")
                            f.write(f"Draft: {reply_text}\n")

                except Exception as e:
                    print(f"[ERROR] Draft creation error: {e}")

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