"""
Global Registry - Centralized access point for all bot instances and services.
This is the single source of truth for bot state across the Flask application.
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime

# ============================================================================
# LOGGER SETUP
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# GLOBAL REGISTRY CLASS
# ============================================================================

class GlobalRegistry:
    """
    Global service registry - singleton pattern.
    Manages all bot instances, event loops, and application state.
    """

    def __init__(self):
        """Initialize the registry"""
        self.draft_bot_instance: Optional[object] = None
        self.bot_event_loop: Optional[asyncio.AbstractEventLoop] = None
        self.is_bot_online: bool = False
        self.bot_start_time: Optional[datetime] = None
        self.excel_module_ready: bool = False
        self.last_restart: Optional[datetime] = None

        # Service status tracking
        self._services = {
            "draft_bot": False,
            "event_loop": False,
            "excel_module": False,
            "telegram_auth": False
        }

    # ========================================================================
    # BOT MANAGEMENT
    # ========================================================================

    def register_draft_bot(self, bot_instance, event_loop=None):
        """
        Register a draft bot instance in the registry.

        Args:
            bot_instance: DraftReviewBot instance
            event_loop: Optional event loop for the bot
        """
        self.draft_bot_instance = bot_instance
        self.bot_event_loop = event_loop
        self.is_bot_online = True
        self.bot_start_time = datetime.now()
        self.last_restart = datetime.now()
        self._services["draft_bot"] = True
        self._services["event_loop"] = event_loop is not None

        logger.info(f"[REGISTRY] [OK] Draft bot registered at {self.bot_start_time.isoformat()}")

    def get_draft_bot(self) -> Optional[object]:
        """
        Get the registered draft bot instance (thread-safe).

        Returns:
            DraftReviewBot instance if online, None otherwise
        """
        if self.draft_bot_instance and self.is_bot_online:
            return self.draft_bot_instance
        return None

    def get_event_loop(self) -> Optional[asyncio.AbstractEventLoop]:
        """Get the bot's event loop"""
        return self.bot_event_loop

    def unregister_draft_bot(self):
        """Unregister the draft bot (graceful shutdown)"""
        self.draft_bot_instance = None
        self.bot_event_loop = None
        self.is_bot_online = False
        self._services["draft_bot"] = False
        self._services["event_loop"] = False
        logger.info("[REGISTRY] Draft bot unregistered")

    # ========================================================================
    # EXCEL MODULE MANAGEMENT
    # ========================================================================

    def mark_excel_ready(self, ready: bool = True):
        """Mark Excel module as ready"""
        self.excel_module_ready = ready
        self._services["excel_module"] = ready
        status = "✓" if ready else "✗"
        logger.info(f"[REGISTRY] {status} Excel module status: {ready}")

    def is_excel_ready(self) -> bool:
        """Check if Excel module is ready"""
        return self.excel_module_ready

    # ========================================================================
    # SERVICE STATUS
    # ========================================================================

    def register_service(self, service_name: str, status: bool):
        """Register service status"""
        self._services[service_name] = status
        symbol = "✓" if status else "✗"
        logger.info(f"[REGISTRY] {symbol} Service '{service_name}': {status}")

    def get_service_status(self, service_name: str) -> bool:
        """Get service status"""
        return self._services.get(service_name, False)

    def get_all_services(self) -> dict:
        """Get all service statuses"""
        return self._services.copy()

    # ========================================================================
    # HEALTH CHECK
    # ========================================================================

    def health_check(self) -> dict:
        """
        Get comprehensive health status.

        Returns:
            Dictionary with system health information
        """
        uptime = None
        if self.bot_start_time:
            uptime = (datetime.now() - self.bot_start_time).total_seconds()

        return {
            "bot_online": self.is_bot_online,
            "bot_instance": self.draft_bot_instance is not None,
            "event_loop": self.bot_event_loop is not None,
            "excel_ready": self.excel_module_ready,
            "uptime_seconds": uptime,
            "bot_start_time": self.bot_start_time.isoformat() if self.bot_start_time else None,
            "last_restart": self.last_restart.isoformat() if self.last_restart else None,
            "services": self._services
        }

    # ========================================================================
    # STATUS REPORTING
    # ========================================================================

    def print_status(self):
        """Print formatted status to console"""
        health = self.health_check()

        print("\n" + "="*70)
        print("GLOBAL REGISTRY STATUS")
        print("="*70)
        print(f"Bot Online:           {health['bot_online']}")
        print(f"Bot Instance:         {health['bot_instance']}")
        print(f"Event Loop:           {health['event_loop']}")
        print(f"Excel Module Ready:   {health['excel_ready']}")

        if health['uptime_seconds']:
            minutes = int(health['uptime_seconds'] / 60)
            print(f"Uptime:               {minutes} minutes")

        print(f"\nBot Start Time:       {health['bot_start_time']}")
        print(f"Last Restart:         {health['last_restart']}")

        print("\nServices:")
        for service, status in health['services'].items():
            symbol = "[OK]" if status else "[--]"
            print(f"  {symbol} {service}: {status}")

        print("="*70 + "\n")

    def reset(self):
        """Reset registry to initial state"""
        self.draft_bot_instance = None
        self.bot_event_loop = None
        self.is_bot_online = False
        self.bot_start_time = None
        self.excel_module_ready = False
        self._services = {k: False for k in self._services}
        logger.info("[REGISTRY] Registry reset to initial state")


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_registry_instance: Optional[GlobalRegistry] = None


def get_registry() -> GlobalRegistry:
    """
    Get or create the global registry singleton.

    Returns:
        GlobalRegistry instance
    """
    global _registry_instance

    if _registry_instance is None:
        _registry_instance = GlobalRegistry()
        logger.info("[REGISTRY] ✓ Global Registry initialized")

    return _registry_instance


def reset_registry():
    """Reset the registry (for testing/shutdown)"""
    global _registry_instance

    if _registry_instance:
        _registry_instance.reset()
        _registry_instance = None
        logger.info("[REGISTRY] Registry reset")
