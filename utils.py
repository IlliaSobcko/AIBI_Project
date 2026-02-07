import re
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class ChatHistory:
    chat_id: int
    chat_title: str
    chat_type: str
    text: str
    has_unreadable_files: bool = False  # True if message contains voice, audio, image, document, etc.

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