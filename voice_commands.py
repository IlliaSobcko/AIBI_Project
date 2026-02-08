"""
Voice Commands Module - Phase 3: Voice Integration

This module handles:
1. Voice message transcription using Whisper
2. Command recognition (Звіт, Експорт, Напиши...)
3. Safety checks (owner ID only)
4. Voice-triggered actions (Excel export, draft generation)
"""

import os
import re
import tempfile
from pathlib import Path
from typing import Optional, Dict, List
import asyncio


class VoiceCommandProcessor:
    """
    Processes voice commands from owner using Whisper transcription.

    Supported Commands:
    - "Звіт" or "Експорт" → Generate and send Excel report
    - "Напиши [Ім'я]" → Generate draft for client using Golden Examples
    """

    def __init__(self, owner_id: int):
        """Initialize voice command processor"""
        self.owner_id = owner_id
        self.whisper_model = None
        self._load_whisper()

    def _load_whisper(self):
        """Load Whisper model for transcription"""
        try:
            import whisper
            # Use 'base' model for balance of speed and accuracy
            # Options: tiny, base, small, medium, large
            print(f"[VOICE] Loading Whisper model...")
            self.whisper_model = whisper.load_model("base")
            print(f"[VOICE] ✓ Whisper model loaded successfully")
        except ImportError:
            print(f"[VOICE] [ERROR] Whisper library not installed")
            print(f"[VOICE] [FIX] Install with: pip install openai-whisper")
            self.whisper_model = None
        except Exception as e:
            print(f"[VOICE] [ERROR] Failed to load Whisper model: {e}")
            self.whisper_model = None

    async def transcribe_voice_message(self, voice_file_path: str) -> Optional[str]:
        """
        Transcribe voice message to text using Whisper.

        Args:
            voice_file_path: Path to downloaded voice/audio file

        Returns:
            Transcribed text or None if failed
        """
        if not self.whisper_model:
            print(f"[VOICE] [ERROR] Whisper model not available")
            return None

        try:
            print(f"[VOICE] Transcribing audio file: {voice_file_path}")

            # Run Whisper in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.whisper_model.transcribe(
                    voice_file_path,
                    language="uk",  # Ukrainian
                    fp16=False  # CPU compatibility
                )
            )

            transcribed_text = result["text"].strip()
            print(f"[VOICE] ✓ Transcription: '{transcribed_text}'")

            return transcribed_text

        except Exception as e:
            print(f"[VOICE] [ERROR] Transcription failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def recognize_command(self, transcribed_text: str) -> Dict:
        """
        Recognize command from transcribed text.

        Supported Commands:
        1. "Звіт" or "Експорт" → Excel report
        2. "Напиши [Ім'я]" → Draft generation

        Args:
            transcribed_text: Transcribed voice message text

        Returns:
            {
                "command": "report" | "draft" | "unknown",
                "params": {...},
                "original_text": str
            }
        """
        text_lower = transcribed_text.lower().strip()

        # Command 1: Excel Report
        if any(keyword in text_lower for keyword in ["звіт", "експорт", "report", "export"]):
            print(f"[VOICE] ✓ Recognized command: EXCEL REPORT")
            return {
                "command": "report",
                "params": {},
                "original_text": transcribed_text
            }

        # Command 2: Draft Generation
        # Pattern: "Напиши [Ім'я]" or "Напиши клієнту [Ім'я]"
        draft_patterns = [
            r'напиши\s+(?:клієнту\s+)?(.+)',  # "Напиши [Ім'я]" or "Напиши клієнту [Ім'я]"
            r'написати\s+(?:клієнту\s+)?(.+)',  # "Написати [Ім'я]"
            r'відповісти\s+(.+)',  # "Відповісти [Ім'я]"
            r'draft\s+(?:for\s+)?(.+)',  # "Draft for [Name]" (English)
        ]

        for pattern in draft_patterns:
            match = re.search(pattern, text_lower)
            if match:
                client_name = match.group(1).strip()
                print(f"[VOICE] ✓ Recognized command: DRAFT for '{client_name}'")
                return {
                    "command": "draft",
                    "params": {
                        "client_name": client_name
                    },
                    "original_text": transcribed_text
                }

        # Unknown command
        print(f"[VOICE] [WARN] Unknown command: '{transcribed_text}'")
        return {
            "command": "unknown",
            "params": {},
            "original_text": transcribed_text
        }

    async def execute_report_command(self, event, draft_bot) -> bool:
        """
        Execute Excel report generation and send to owner.

        Args:
            event: Telegram event
            draft_bot: DraftReviewBot instance

        Returns:
            True if successful
        """
        try:
            print(f"[VOICE] [REPORT] Generating Excel report...")

            # Send initial notification
            await event.reply("📊 [VOICE COMMAND] Generating Excel report...")

            # Generate Excel report
            from excel_module import get_excel_collector

            collector = get_excel_collector()
            collector.collect_all_data()
            excel_path = collector.export_to_excel("AIBI_Voice_Report.xlsx")

            if excel_path and Path(excel_path).exists():
                print(f"[VOICE] [REPORT] ✓ Excel generated: {excel_path}")

                # Send Excel file to owner
                await draft_bot.client.send_file(
                    self.owner_id,
                    excel_path,
                    caption="✅ Voice Command: Excel Report Generated"
                )

                print(f"[VOICE] [REPORT] ✓ Excel sent to owner")
                return True
            else:
                await event.reply("❌ [VOICE COMMAND] Failed to generate Excel report")
                return False

        except Exception as e:
            print(f"[VOICE] [REPORT] [ERROR] {e}")
            import traceback
            traceback.print_exc()
            await event.reply(f"❌ [VOICE COMMAND] Error: {e}")
            return False

    async def execute_draft_command(
        self,
        event,
        draft_bot,
        client_name: str
    ) -> bool:
        """
        Execute draft generation for specified client using Golden Examples.

        Args:
            event: Telegram event
            draft_bot: DraftReviewBot instance
            client_name: Client name to generate draft for

        Returns:
            True if successful
        """
        try:
            print(f"[VOICE] [DRAFT] Generating draft for '{client_name}'...")

            # Send initial notification
            await event.reply(f"✍️ [VOICE COMMAND] Generating draft for '{client_name}'...")

            # Find matching client in recent chats
            from telegram_client import TelegramCollector
            from dotenv import load_dotenv
            load_dotenv()

            tg_cfg = {
                "api_id": int(os.getenv("TG_API_ID")),
                "api_hash": os.getenv("TG_API_HASH"),
                "session_name": "aibi_session"
            }

            # Search for client
            async with TelegramCollector(tg_cfg) as collector:
                dialogs = await collector.client.get_dialogs(limit=50)

                # Find matching dialog
                matching_dialog = None
                client_name_lower = client_name.lower()

                for dialog in dialogs:
                    dialog_title = dialog.title or ""
                    if client_name_lower in dialog_title.lower():
                        matching_dialog = dialog
                        break

                if not matching_dialog:
                    await event.reply(f"❌ [VOICE COMMAND] Client '{client_name}' not found in recent chats")
                    return False

                print(f"[VOICE] [DRAFT] ✓ Found client: {matching_dialog.title}")

                # Collect message history (last 10 messages)
                histories = await collector.collect_history_last_days(
                    [matching_dialog],
                    days=7,
                    owner_id=self.owner_id
                )

                if not histories:
                    await event.reply(f"❌ [VOICE COMMAND] No messages found for '{client_name}'")
                    return False

                h = histories[0]

                # Get Golden Examples from knowledge base
                from knowledge_base_storage import get_knowledge_base
                kb_storage = get_knowledge_base()

                relevant_examples = kb_storage.get_relevant_examples(
                    client_question=h.text,
                    chat_title=h.chat_title,
                    limit=5
                )

                # Build enhanced instructions with Golden Examples
                from utils import read_instructions

                base_instructions = read_instructions()
                enhanced_instructions = base_instructions

                if relevant_examples:
                    print(f"[VOICE] [DRAFT] ✓ Injecting {len(relevant_examples)} Golden Examples")

                    examples_section = "\n\n" + "="*80 + "\n"
                    examples_section += "🏆 GOLDEN EXAMPLES (Voice Command - Match This Style):\n"
                    examples_section += "="*80 + "\n"

                    for i, example in enumerate(relevant_examples, 1):
                        examples_section += f"\nExample {i}:\n"
                        examples_section += f"Client: {example['chat_title']}\n"
                        examples_section += f"Question: {example['client_question'][:200]}\n"
                        examples_section += f"✅ Approved Response: {example['approved_response'][:300]}\n"
                        examples_section += f"(Used {example.get('used_count', 0)} times)\n"
                        examples_section += "-"*80 + "\n"

                    examples_section += "\n🎯 MATCH THE TONE AND STYLE FROM THESE GOLDEN EXAMPLES.\n"
                    examples_section += "="*80 + "\n"

                    enhanced_instructions = base_instructions + examples_section

                # Generate draft using AI
                from ai_client import MultiAgentAnalyzer, PerplexitySonarAgent

                perplexity_key = os.getenv("PERPLEXITY_API_KEY")
                agents = [PerplexitySonarAgent(perplexity_key, "sonar")]
                analyzer = MultiAgentAnalyzer(agents)

                print(f"[VOICE] [DRAFT] Generating AI response...")
                result = await analyzer.analyze_chat(enhanced_instructions, h)

                draft_text = result.get('report', 'No draft generated')
                confidence = result.get('confidence', 0)

                print(f"[VOICE] [DRAFT] ✓ Draft generated (Confidence: {confidence}%)")

                # Send draft with buttons
                notification = f"""🎤 **VOICE COMMAND - DRAFT GENERATED**

**Client**: {h.chat_title}
**AI Confidence**: {confidence}%

**Last Messages** (Context):
{h.text[:500]}...

**✍️ GENERATED DRAFT**:
{draft_text}

--------------------
**Choose action:**
"""

                from telethon.tl.custom.button import Button

                buttons = [
                    [
                        Button.inline("✅ SEND NOW", data=f"send_{h.chat_id}"),
                        Button.inline("📝 EDIT", data=f"edit_{h.chat_id}"),
                        Button.inline("❌ SKIP", data=f"skip_{h.chat_id}")
                    ]
                ]

                # Send draft to owner
                await draft_bot.tg_service.send_message(
                    recipient_id=self.owner_id,
                    text=notification,
                    buttons=buttons
                )

                print(f"[VOICE] [DRAFT] ✓ Draft sent to owner with buttons")
                return True

        except Exception as e:
            print(f"[VOICE] [DRAFT] [ERROR] {e}")
            import traceback
            traceback.print_exc()
            await event.reply(f"❌ [VOICE COMMAND] Error: {e}")
            return False


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_voice_processor_instance: Optional[VoiceCommandProcessor] = None


def get_voice_processor(owner_id: int) -> VoiceCommandProcessor:
    """Get or create voice command processor singleton"""
    global _voice_processor_instance

    if _voice_processor_instance is None:
        _voice_processor_instance = VoiceCommandProcessor(owner_id)

    return _voice_processor_instance
