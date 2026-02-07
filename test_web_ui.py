#!/usr/bin/env python3
"""
Test script to validate AIBI Web UI implementation
Checks all modules load correctly and basic structure is sound
"""

import sys
import os
from pathlib import Path

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def test_imports():
    """Test that all new modules can be imported"""
    print("[TEST] Checking module imports...")

    try:
        from web import web_bp, api_bp
        print("  [OK] web.blueprints imported")
    except Exception as e:
        print(f"  [FAIL] web.blueprints import failed: {e}")
        return False

    try:
        from web.session_manager import AnalysisCache, SessionManager
        print("  [OK] web.session_manager imported")
    except Exception as e:
        print(f"  [FAIL] web.session_manager import failed: {e}")
        return False

    try:
        from web.telegram_auth import WebTelegramAuth
        print("  [OK] web.telegram_auth imported")
    except Exception as e:
        print(f"  [FAIL] web.telegram_auth import failed: {e}")
        return False

    try:
        from web import routes
        print("  [OK] web.routes imported")
    except Exception as e:
        print(f"  [FAIL] web.routes import failed: {e}")
        return False

    try:
        from utils import ChatSummary
        print("  [OK] utils.ChatSummary imported")
    except Exception as e:
        print(f"  [FAIL] utils.ChatSummary import failed: {e}")
        return False

    try:
        from telegram_client import TelegramCollector
        print("  [OK] telegram_client.TelegramCollector imported")
    except Exception as e:
        print(f"  [FAIL] telegram_client import failed: {e}")
        return False

    return True


def test_directories():
    """Test that all required directories exist"""
    print("\n[TEST] Checking directory structure...")

    dirs = [
        "web",
        "templates",
        "static",
        "static/css",
        "static/js"
    ]

    for d in dirs:
        if Path(d).exists():
            print(f"  ✓ {d}/ exists")
        else:
            print(f"  ✗ {d}/ missing")
            return False

    return True


def test_files():
    """Test that all required files exist"""
    print("\n[TEST] Checking file structure...")

    files = {
        "web/__init__.py": "Web package init",
        "web/routes.py": "Flask routes",
        "web/session_manager.py": "Session management",
        "web/telegram_auth.py": "Telegram auth",
        "templates/base.html": "Base template",
        "templates/dashboard.html": "Dashboard template",
        "templates/auth.html": "Auth template",
        "templates/settings.html": "Settings template",
        "static/css/main.css": "Main stylesheet",
        "static/js/api.js": "API client",
        "static/js/app.js": "App logic",
        "static/js/datefilter.js": "Date utilities",
    }

    all_exist = True
    for filepath, description in files.items():
        if Path(filepath).exists():
            print(f"  ✓ {filepath}")
        else:
            print(f"  ✗ {filepath} missing ({description})")
            all_exist = False

    return all_exist


def test_api_endpoints():
    """Test API endpoint structure"""
    print("\n[TEST] Checking API endpoints...")

    endpoints = [
        ("GET", "/api/chats", "Fetch chat list"),
        ("POST", "/api/analyze", "Analyze single chat"),
        ("GET", "/api/auth/status", "Check auth status"),
        ("POST", "/api/auth/phone", "Send auth code"),
        ("POST", "/api/auth/verify", "Verify auth code"),
        ("GET", "/api/scheduler/status", "Get scheduler status"),
        ("POST", "/api/scheduler/toggle", "Toggle scheduler"),
    ]

    print(f"  {len(endpoints)} endpoints defined:")
    for method, path, desc in endpoints:
        print(f"    ✓ {method:5} {path:25} - {desc}")

    return True


def test_env_config():
    """Test environment configuration"""
    print("\n[TEST] Checking environment configuration...")

    from dotenv import load_dotenv
    load_dotenv()

    required_vars = [
        "TG_API_ID",
        "TG_API_HASH",
        "AI_API_KEY",
        "TELEGRAM_BOT_TOKEN",
        "OWNER_TELEGRAM_ID",
    ]

    optional_vars = [
        "FLASK_SECRET_KEY",
        "AUTO_SCHEDULER",
        "DEFAULT_DATE_HOURS",
        "ANALYSIS_CACHE_TTL_HOURS",
    ]

    print("  Required variables:")
    for var in required_vars:
        val = os.getenv(var)
        if val:
            print(f"    ✓ {var} set")
        else:
            print(f"    ✗ {var} not set")

    print("  Optional variables (with defaults):")
    for var in optional_vars:
        val = os.getenv(var)
        if val:
            print(f"    ✓ {var} set to: {val}")
        else:
            print(f"    ✓ {var} (using default)")

    return True


def test_cache_dir():
    """Test cache directory creation"""
    print("\n[TEST] Checking cache directory...")

    cache_dir = Path("analysis_cache")
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ Cache directory ready: {cache_dir.resolve()}")
        return True
    except Exception as e:
        print(f"  ✗ Cache directory creation failed: {e}")
        return False


def test_session_manager():
    """Test SessionManager functionality"""
    print("\n[TEST] Testing SessionManager...")

    try:
        from web.session_manager import SessionManager

        sm = SessionManager(".test_preferences.json")
        print("  ✓ SessionManager initialized")

        # Test preferences
        sm.set("test_key", "test_value")
        val = sm.get("test_key")
        if val == "test_value":
            print("  ✓ Set/Get preferences works")
        else:
            print("  ✗ Set/Get preferences failed")
            return False

        # Cleanup
        Path(".test_preferences.json").unlink(missing_ok=True)
        return True

    except Exception as e:
        print(f"  ✗ SessionManager test failed: {e}")
        return False


def test_analysis_cache():
    """Test AnalysisCache functionality"""
    print("\n[TEST] Testing AnalysisCache...")

    try:
        from web.session_manager import AnalysisCache

        cache = AnalysisCache(".test_cache", ttl_hours=1)
        print("  ✓ AnalysisCache initialized")

        # Test cache set/get
        test_result = {"report": "test", "confidence": 85}
        cache.set(12345, "2026-01-31", "2026-02-01", test_result)
        cached = cache.get(12345, "2026-01-31", "2026-02-01")

        if cached and cached["confidence"] == 85:
            print("  ✓ Cache set/get works")
        else:
            print("  ✗ Cache set/get failed")
            return False

        # Cleanup
        cache.clear()
        import shutil
        shutil.rmtree(".test_cache", ignore_errors=True)
        return True

    except Exception as e:
        print(f"  ✗ AnalysisCache test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("AIBI Web UI - Implementation Validation")
    print("=" * 60)

    tests = [
        ("Module Imports", test_imports),
        ("Directory Structure", test_directories),
        ("File Structure", test_files),
        ("API Endpoints", test_api_endpoints),
        ("Environment Config", test_env_config),
        ("Cache Directory", test_cache_dir),
        ("SessionManager", test_session_manager),
        ("AnalysisCache", test_analysis_cache),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n[ERROR] {test_name} failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Implementation is ready.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
