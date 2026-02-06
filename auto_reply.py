import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Tuple
from openai import AsyncOpenAI

def is_working_hours() -> bool:
    """
    Перевіряє, чи зараз робочі години (UKRAINE TIME, UTC+2/UTC+3)

    Server runs in UTC, but clients are in Ukraine timezone.
    Automatically handles DST transitions.
    """
    start = int(os.getenv("WORKING_HOURS_START", "9"))
    end = int(os.getenv("WORKING_HOURS_END", "18"))

    # Get current UTC time
    now_utc = datetime.now(timezone.utc)

    # Ukraine timezone offset: UTC+2 (winter) or UTC+3 (summer DST)
    # DST in Ukraine: last Sunday in March -> last Sunday in October
    year = now_utc.year
    march_last_sunday = _get_last_sunday_of_month(year, 3)
    october_last_sunday = _get_last_sunday_of_month(year, 10)

    if march_last_sunday <= now_utc.date() < october_last_sunday:
        # DST period: UTC+3
        ukraine_offset = timedelta(hours=3)
    else:
        # Standard time: UTC+2
        ukraine_offset = timedelta(hours=2)

    # Convert UTC to Ukraine time
    now_ukraine = now_utc + ukraine_offset
    current_hour = now_ukraine.hour

    return start <= current_hour < end


def _get_last_sunday_of_month(year: int, month: int) -> datetime:
    """Get the last Sunday of a given month (used for DST calculation)"""
    if month == 12:
        # If December, next month is January of next year
        next_month_first = datetime(year + 1, 1, 1)
    else:
        next_month_first = datetime(year, month + 1, 1)

    # Go back to the last day of the target month
    last_day = next_month_first - timedelta(days=1)

    # Go back to the last Sunday
    days_since_sunday = (last_day.weekday() - 6) % 7  # 6 is Sunday
    return (last_day - timedelta(days=days_since_sunday)).date()

def load_business_data() -> str:
    """Завантажує бізнес-інформацію"""
    path = Path("business_data.txt")
    if not path.exists():
        return "Компанія: AIBI Solutions. Спеціалізуємося на AI-автоматизації."
    return path.read_text(encoding="utf-8")

class AutoReplyGenerator:
    def __init__(self, ai_api_key: str):
        self.client = AsyncOpenAI(
            api_key=ai_api_key,
            base_url="https://api.perplexity.ai"
        )
        self.business_data = load_business_data()

    async def generate_reply(
        self,
        chat_title: str,
        message_history: str,
        analysis_report: str,
        has_unreadable_files: bool = False
    ) -> Tuple[str, int]:
        """
        Генерує автоматичну відповідь на основі аналізу та бізнес-даних

        Returns:
            (reply_text, confidence): Текст відповіді та впевненість (0-100)
        """

        # ZERO CONFIDENCE RULE: If unreadable files present, return immediately
        if has_unreadable_files:
            unreadable_message = "Kliyent nadislav fayl, yakiy ya ne mozhu prochytaty, tomu ya ne vidpoviv avtomatychno."
            return unreadable_message, 0

        prompt = f"""Ти - бізнес-асистент. На основі аналізу переписки та бізнес-даних, склади КОРОТКУ (2-4 речення) професійну відповідь клієнту.

БІЗНЕС-ДАНІ:
{self.business_data}

ЧАТ: {chat_title}

АНАЛІЗ ПЕРЕПИСКИ:
{analysis_report}

ОСТАННЯ ЧАСТИНА ІСТОРІЇ:
{message_history[-1000:]}

ПРАВИЛА:
1. Відповідь має бути природною, не копіюй текст з business_data дослівно
2. Якщо клієнт запитує ціну - вкажи орієнтовну з business_data
3. Якщо запитує термін - вкажи орієнтовний термін
4. Завжди пропонуй наступний крок (дзвінок, зустріч, більше інфо)
5. Тон: професійний, дружній, не офіційний
6. Максимум 2-4 речення

Поверни JSON:
{{
    "reply": "текст відповіді тут",
    "confidence": 0-100,
    "reasoning": "чому обрано такий варіант"
}}
"""

        try:
            resp = await self.client.chat.completions.create(
                model="sonar",
                messages=[
                    {"role": "system", "content": "Ти - AI асистент для складання бізнес-відповідей."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )

            result = self._parse_response(resp.choices[0].message.content)
            return result["reply"], result["confidence"]

        except Exception as e:
            print(f"[ERROR] Помилка генерації відповіді: {e}")
            return "", 0

    def _parse_response(self, text: str) -> dict:
        """Парсить JSON відповідь"""
        import re
        import json

        try:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return {
                    "reply": data.get("reply", ""),
                    "confidence": int(data.get("confidence", 0)),
                    "reasoning": data.get("reasoning", "")
                }
        except:
            pass

        return {"reply": "", "confidence": 0, "reasoning": "Parsing error"}

class DraftReviewSystem:
    def __init__(self):
        self.pending_drafts = {}  # {chat_id: {"draft": text, "chat_title": str, "timestamp": datetime}}

    def add_draft(self, chat_id: int, chat_title: str, draft_text: str, confidence: int):
        """Додає чернетку для розгляду"""
        self.pending_drafts[chat_id] = {
            "draft": draft_text,
            "chat_title": chat_title,
            "confidence": confidence,
            "timestamp": datetime.now()
        }

    def get_draft(self, chat_id: int) -> Optional[dict]:
        """Отримує чернетку по chat_id"""
        return self.pending_drafts.get(chat_id)

    def remove_draft(self, chat_id: int):
        """Видаляє чернетку після обробки"""
        if chat_id in self.pending_drafts:
            del self.pending_drafts[chat_id]

    def get_all_pending(self) -> dict:
        """Повертає всі чернетки, що очікують розгляду"""
        return self.pending_drafts

# Глобальний екземпляр для зберігання чернеток
draft_system = DraftReviewSystem()
