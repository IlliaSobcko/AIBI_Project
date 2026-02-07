from __future__ import annotations
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional
from telethon import TelegramClient
from telethon.tl.custom.dialog import Dialog
from telethon.tl.types import User, Chat, Channel
from utils import ChatHistory, ChatSummary
from dataclasses import dataclass

@dataclass
class TelegramConfig:
    api_id: int
    api_hash: str
    session_name: str

class TelegramCollector:
    def __init__(self, cfg):
        self.cfg = cfg
        self.client = TelegramClient(cfg.session_name, cfg.api_id, cfg.api_hash)

    async def __aenter__(self):
        await self.client.start()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.client.disconnect()

    async def list_dialogs(self, limit: Optional[int] = None):
        dialogs = []
        async for d in self.client.iter_dialogs(limit=limit):
            dialogs.append(d)
        return dialogs

    async def get_chats_with_counts(self, dialogs: Iterable[Dialog], start_date: datetime, end_date: datetime) -> List[ChatSummary]:
        """
        Get lightweight chat list with message counts (NO AI ANALYSIS - cost-free)

        Returns:
            List of ChatSummary objects for inbox display
        """
        results = []

        for d in dialogs:
            # Filter: only people and groups
            ent = d.entity
            chat_type = "user" if isinstance(ent, User) else "group" if isinstance(ent, (Chat, Channel)) else "unknown"
            if chat_type == "unknown":
                continue

            message_count = 0
            last_message_date = None

            # Count messages in date range
            async for msg in self.client.iter_messages(d.entity, limit=100):
                if not msg.date:
                    continue

                # Check if message is in date range
                if msg.date < start_date:
                    break

                if start_date <= msg.date <= end_date:
                    message_count += 1
                    if last_message_date is None:
                        last_message_date = msg.date

            if message_count > 0:
                results.append(ChatSummary(
                    chat_id=ent.id,
                    chat_title=d.name or "Untitled",
                    chat_type=chat_type,
                    message_count=message_count,
                    last_message_date=last_message_date,
                    has_unread=d.unread_count > 0 if hasattr(d, 'unread_count') else False,
                    analyzed=False
                ))

        return results

    async def collect_history_last_days(self, dialogs: Iterable[Dialog], days: int) -> List[ChatHistory]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        results = []

        for d in dialogs:
            # Фільтруємо: тільки люди та групи
            ent = d.entity
            chat_type = "user" if isinstance(ent, User) else "group" if isinstance(ent, (Chat, Channel)) else "unknown"
            if chat_type == "unknown": continue

            lines = []
            has_unreadable_files = False

            async for msg in self.client.iter_messages(d.entity, limit=100):
                if not msg.date or msg.date < since: break

                # Check for unreadable media (voice, audio, image, document, video, etc.)
                if msg.media:
                    media_type = type(msg.media).__name__
                    # Mark as unreadable if it's any kind of non-text media
                    has_unreadable_files = True
                    # Add a marker showing unreadable file was present
                    lines.append(f"[{msg.date.isoformat()}] [FILE: {media_type}]")
                else:
                    # Only add text messages
                    text = (msg.message or "").strip()
                    if text:
                        lines.append(f"[{msg.date.isoformat()}] {text}")

            if lines:
                lines.reverse()
                results.append(ChatHistory(
                    chat_id=ent.id,
                    chat_title=d.name or "Untitled",
                    chat_type=chat_type,
                    text="\n".join(lines),
                    has_unreadable_files=has_unreadable_files
                ))
        return results