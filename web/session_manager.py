"""Session management, user preferences, and analysis caching"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


class AnalysisCache:
    """File-based cache for analysis results to reduce AI costs"""

    def __init__(self, cache_dir: str = "analysis_cache", ttl_hours: int = 1):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_hours = ttl_hours

    def _get_cache_key(self, chat_id: int, start_date: str, end_date: str) -> str:
        """Generate cache key from chat_id and date range"""
        return f"{chat_id}_{start_date.replace(':', '-')}_{end_date.replace(':', '-')}"

    def _get_cache_file(self, cache_key: str) -> Path:
        """Get cache file path"""
        return self.cache_dir / f"{cache_key}.json"

    def get(self, chat_id: int, start_date: str, end_date: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached analysis if within TTL"""
        cache_key = self._get_cache_key(chat_id, start_date, end_date)
        cache_file = self._get_cache_file(cache_key)

        if not cache_file.exists():
            return None

        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            cached_at = datetime.fromisoformat(data['cached_at'])

            # Check if cache is still valid
            if datetime.now() - cached_at < timedelta(hours=self.ttl_hours):
                return data['result']
            else:
                # Cache expired - delete it
                cache_file.unlink()
                return None
        except (json.JSONDecodeError, KeyError, ValueError):
            # Invalid cache file - delete it
            cache_file.unlink()
            return None

    def set(self, chat_id: int, start_date: str, end_date: str, result: Dict[str, Any]) -> None:
        """Cache analysis result"""
        cache_key = self._get_cache_key(chat_id, start_date, end_date)
        cache_file = self._get_cache_file(cache_key)

        data = {
            "cached_at": datetime.now().isoformat(),
            "chat_id": chat_id,
            "start_date": start_date,
            "end_date": end_date,
            "result": result
        }

        cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def clear(self) -> None:
        """Clear all cached analyses"""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()

    def clear_for_chat(self, chat_id: int) -> None:
        """Clear cache for specific chat"""
        for cache_file in self.cache_dir.glob(f"{chat_id}_*.json"):
            cache_file.unlink()


class SessionManager:
    """Manage user session preferences and settings"""

    def __init__(self, prefs_file: str = ".aibi_preferences.json"):
        self.prefs_file = Path(prefs_file)
        self._load_preferences()

    def _load_preferences(self) -> None:
        """Load preferences from file or initialize defaults"""
        if self.prefs_file.exists():
            try:
                self.preferences = json.loads(self.prefs_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                self.preferences = self._get_defaults()
        else:
            self.preferences = self._get_defaults()

    def _get_defaults(self) -> Dict[str, Any]:
        """Get default preferences"""
        return {
            "default_date_hours": int(os.getenv("DEFAULT_DATE_HOURS", "24")),
            "auto_scheduler_enabled": os.getenv("AUTO_SCHEDULER", "false").lower() == "true",
            "analysis_cache_ttl_hours": int(os.getenv("ANALYSIS_CACHE_TTL_HOURS", "1")),
            "authenticated": False,
            "last_auth": None,
            "favorite_chats": []  # List of chat IDs to show first
        }

    def save(self) -> None:
        """Save preferences to file"""
        self.prefs_file.write_text(
            json.dumps(self.preferences, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def get(self, key: str, default: Any = None) -> Any:
        """Get preference value"""
        return self.preferences.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set preference value"""
        self.preferences[key] = value
        self.save()

    def mark_authenticated(self) -> None:
        """Mark user as authenticated"""
        self.set("authenticated", True)
        self.set("last_auth", datetime.now().isoformat())

    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return self.preferences.get("authenticated", False)

    def toggle_scheduler(self, enabled: bool) -> None:
        """Toggle auto-scheduler setting"""
        self.set("auto_scheduler_enabled", enabled)

    def is_scheduler_enabled(self) -> bool:
        """Check if auto-scheduler is enabled"""
        return self.preferences.get("auto_scheduler_enabled", False)

    def add_favorite_chat(self, chat_id: int) -> None:
        """Add chat to favorites"""
        favorites = self.preferences.get("favorite_chats", [])
        if chat_id not in favorites:
            favorites.append(chat_id)
            self.set("favorite_chats", favorites)

    def remove_favorite_chat(self, chat_id: int) -> None:
        """Remove chat from favorites"""
        favorites = self.preferences.get("favorite_chats", [])
        if chat_id in favorites:
            favorites.remove(chat_id)
            self.set("favorite_chats", favorites)

    def get_favorite_chats(self) -> list:
        """Get list of favorite chat IDs"""
        return self.preferences.get("favorite_chats", [])
