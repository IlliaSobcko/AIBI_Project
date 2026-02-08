from __future__ import annotations
import asyncio
import os
import shutil
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
        # Use a temporary session copy to avoid database locks
        self.temp_session = f"{cfg.session_name}_temp_{os.getpid()}"

        # Copy session file if it exists
        if os.path.exists(f"{cfg.session_name}.session"):
            try:
                shutil.copy(f"{cfg.session_name}.session", f"{self.temp_session}.session")
                print(f"[TELEGRAM COLLECTOR] Using temporary session copy: {self.temp_session}")
            except Exception as e:
                print(f"[TELEGRAM COLLECTOR] [WARN] Could not copy session: {e}, using original")
                self.temp_session = cfg.session_name
        else:
            self.temp_session = cfg.session_name

        self.client = TelegramClient(self.temp_session, cfg.api_id, cfg.api_hash)

    async def __aenter__(self):
        await self.client.start()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.client.disconnect()

        # Clean up temporary session file
        if self.temp_session != self.cfg.session_name:
            try:
                if os.path.exists(f"{self.temp_session}.session"):
                    os.remove(f"{self.temp_session}.session")
                if os.path.exists(f"{self.temp_session}.session-journal"):
                    os.remove(f"{self.temp_session}.session-journal")
                print(f"[TELEGRAM COLLECTOR] Cleaned up temporary session: {self.temp_session}")
            except Exception as e:
                print(f"[TELEGRAM COLLECTOR] [WARN] Could not cleanup temp session: {e}")

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

    async def collect_history_last_days(self, dialogs: Iterable[Dialog], days: int, owner_id: int = None) -> List[ChatHistory]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        results = []

        # Get owner's user ID if not provided
        if owner_id is None:
            me = await self.client.get_me()
            owner_id = me.id if me else None

        for d in dialogs:
            # Фільтруємо: тільки люди та групи
            ent = d.entity
            chat_type = "user" if isinstance(ent, User) else "group" if isinstance(ent, (Chat, Channel)) else "unknown"
            if chat_type == "unknown": continue

            lines = []
            recent_messages = []
            has_unreadable_files = False
            last_sender_id = None

            async for msg in self.client.iter_messages(d.entity, limit=100):
                if not msg.date or msg.date < since: break

                # Track sender for recent messages (last 15)
                if len(recent_messages) < 15:
                    msg_data = {
                        'sender_id': msg.sender_id,
                        'date': msg.date.isoformat(),
                        'text': (msg.message or "").strip() if not msg.media else f"[FILE: {type(msg.media).__name__}]",
                        'is_owner': msg.sender_id == owner_id if owner_id else False
                    }
                    recent_messages.append(msg_data)

                    # Track last sender
                    if last_sender_id is None:
                        last_sender_id = msg.sender_id

                # Check for unreadable media (voice, audio, image, document, video, etc.)
                if msg.media:
                    media_type = type(msg.media).__name__
                    # Mark as unreadable if it's any kind of non-text media
                    has_unreadable_files = True
                    # Add sender label
                    sender_label = "ME" if msg.sender_id == owner_id else "CLIENT"
                    lines.append(f"[{msg.date.isoformat()}] [{sender_label}] [FILE: {media_type}]")
                else:
                    # Only add text messages with sender label
                    text = (msg.message or "").strip()
                    if text:
                        sender_label = "ME" if msg.sender_id == owner_id else "CLIENT"
                        lines.append(f"[{msg.date.isoformat()}] [{sender_label}] {text}")

            if lines:
                lines.reverse()
                recent_messages.reverse()
                results.append(ChatHistory(
                    chat_id=ent.id,
                    chat_title=d.name or "Untitled",
                    chat_type=chat_type,
                    text="\n".join(lines),
                    has_unreadable_files=has_unreadable_files,
                    last_sender_id=last_sender_id,
                    owner_id=owner_id,
                    recent_messages=recent_messages
                ))
        return results