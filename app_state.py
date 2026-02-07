"""
Global application state management for AIBI system.
This module ensures single instance access to shared resources like DRAFT_BOT.
"""

import asyncio
from typing import Optional

# ============================================================================
# GLOBAL STATE CONTAINER
# ============================================================================

class AppState:
    """Thread-safe global state container for application instances"""

    def __init__(self):
        """Initialize state container"""
        self.draft_bot_instance: Optional[object] = None
        self.bot_event_loop: Optional[asyncio.AbstractEventLoop] = None
        self.is_bot_online: bool = False

    def set_draft_bot(self, bot_instance):
        """Set the global draft bot instance"""
        self.draft_bot_instance = bot_instance
        if bot_instance:
            self.is_bot_online = True
            print("[APP_STATE] ✓ Draft bot instance registered")
        else:
            self.is_bot_online = False
            print("[APP_STATE] ✗ Draft bot instance cleared")

    def get_draft_bot(self):
        """Get the global draft bot instance"""
        if self.draft_bot_instance and self.is_bot_online:
            return self.draft_bot_instance
        return None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        """Set the bot's event loop"""
        self.bot_event_loop = loop
        if loop:
            print("[APP_STATE] ✓ Event loop registered")

    def get_event_loop(self) -> Optional[asyncio.AbstractEventLoop]:
        """Get the bot's event loop"""
        return self.bot_event_loop

    def reset(self):
        """Reset all state (useful for graceful shutdown)"""
        self.draft_bot_instance = None
        self.bot_event_loop = None
        self.is_bot_online = False
        print("[APP_STATE] ✓ State reset complete")

    def health_check(self) -> dict:
        """Get health status of the app"""
        return {
            "bot_online": self.is_bot_online,
            "bot_instance": self.draft_bot_instance is not None,
            "event_loop": self.bot_event_loop is not None
        }


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

# Global instance - can be imported anywhere
app_state = AppState()


def get_app_state() -> AppState:
    """Get the global application state"""
    return app_state
