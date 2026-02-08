import re
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

@dataclass
class ChatHistory:
    chat_id: int
    chat_title: str
    chat_type: str
    text: str
    has_unreadable_files: bool = False  # True if message contains voice, audio, image, document, etc.
    last_sender_id: Optional[int] = None  # ID of who sent the last message
    owner_id: Optional[int] = None  # Owner's Telegram ID for comparison
    recent_messages: Optional[List[dict]] = None  # Last 10-15 messages with sender info

    def __post_init__(self):
        if self.recent_messages is None:
            self.recent_messages = []

    def is_owner_last_speaker(self) -> bool:
        """Check if owner was the last person to speak"""
        return self.last_sender_id is not None and self.last_sender_id == self.owner_id

    def get_unanswered_client_messages(self) -> List[dict]:
        """Get consecutive client messages at the end that haven't been answered"""
        if not self.recent_messages or not self.owner_id:
            return []

        unanswered = []
        for msg in reversed(self.recent_messages):
            if msg.get('sender_id') == self.owner_id:
                break  # Owner replied, stop here
            unanswered.insert(0, msg)

        return unanswered

    def get_owner_messages_for_style(self) -> List[dict]:
        """Get owner's recent messages for style mimicry"""
        if not self.owner_id:
            return []

        return [msg for msg in self.recent_messages if msg.get('sender_id') == self.owner_id]

@dataclass
class ChatSummary:
    """Summary of a chat for inbox list display"""
    chat_id: int
    chat_title: str
    chat_type: str  # "user" or "group"
    message_count: int
    last_message_date: Optional[datetime] = None
    has_unread: bool = False
    analyzed: bool = False

def read_instructions(path: str = "instructions.txt") -> str:
    p = Path(path)
    if not p.exists():
        # Створюємо файл, якщо його немає, щоб не було помилки
        p.write_text("Ти — бізнес-аналітик. Зроби короткий звіт.", encoding="utf-8")
    return p.read_text(encoding="utf-8")

def sanitize_filename(name: str) -> str:
    # Прибираємо символи, які Windows забороняє в назвах файлів
    return re.sub(r"[\\/:*?\"<>|]+", "_", name)[:100]

def ensure_dir(path: str):
    Path(path).mkdir(parents=True, exist_ok=True)