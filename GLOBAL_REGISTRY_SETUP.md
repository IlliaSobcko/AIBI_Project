# Global Registry System - Complete Setup Guide

## 🎯 What's New

A complete refresh of the bot initialization system with:
- **Global Registry** - Centralized bot instance management
- **Startup Notification** - Automatic message to owner on bot startup
- **Excel Module** - Production-ready data collection and export
- **Health Monitoring** - Real-time system status

---

## 🗂️ New Architecture

### Global Registry (global_registry.py)
```
┌─────────────────────────────────────────┐
│       GLOBAL REGISTRY (Singleton)       │
├─────────────────────────────────────────┤
│  • draft_bot_instance                   │
│  • bot_event_loop                       │
│  • is_bot_online (boolean)              │
│  • bot_start_time                       │
│  • excel_module_ready                   │
│  • Service status tracking              │
├─────────────────────────────────────────┤
│  Methods:                               │
│  • register_draft_bot()                 │
│  • get_draft_bot()                      │
│  • mark_excel_ready()                   │
│  • health_check()                       │
│  • print_status()                       │
└─────────────────────────────────────────┘
```

### Flask Server Access
```python
from global_registry import get_registry

registry = get_registry()
current_bot = registry.get_draft_bot()
health = registry.health_check()
```

---

## 🤖 Bot Initialization Flow

### Old Flow (Race Condition)
```
main.py starts
    ↓
bot_container = {"instance": None}  ← Global dict
    ↓
start_draft_bot_background()
    ↓
DraftReviewBot.start() runs
    ↓
bot_container["instance"] = bot  ← Unreliable
    ↓
❌ "available: False" errors
```

### New Flow (Thread-Safe)
```
main.py starts
    ↓
registry = get_registry()  ← Singleton
    ↓
start_draft_bot_background()
    ↓
DraftReviewBot.start() runs
    ↓
registry.register_draft_bot(bot, loop)  ← Thread-safe
    ↓
send_startup_notification()  ← Auto message
    ↓
Keep event loop running
    ↓
✅ Bot online & Flask can access it
```

---

## 📬 Startup Notification

### What Gets Sent
When the bot starts, it automatically sends a message to your Telegram ID:

```
🤖 **SYSTEM RESTARTED**

✅ Bot is now ONLINE and ready to receive commands

Status:
  • Bot API: Connected
  • Token: Valid
  • Owner ID: 8040716622
  • Restart Time: 2026-02-02 15:30:45

Available Commands:
  • /check → Manual analysis trigger
  • /report → Analytics dashboard
  • Звіт → Excel report export

━━━━━━━━━━━━━━━━━━━━
System is ready to process drafts and commands.
```

### Where It's Configured
```python
# In draft_bot.py - send_startup_notification()
# Uses OWNER_TELEGRAM_ID from .env
# Automatically called after bot.start()
```

### How to Know Bot is Online
1. ✅ You'll receive the "SYSTEM RESTARTED" message
2. ✅ Check server logs for `[REGISTRY] ✓ Draft bot registered`
3. ✅ Check `health_check()` shows `bot_online: True`

---

## 📊 Excel Module (Production-Ready)

### Features
- ✅ Collects data from reports/ folder
- ✅ Extracts confidence scores
- ✅ Counts auto-replies and drafts
- ✅ Collects customer questions
- ✅ Calculates statistics
- ✅ Prepares Excel sheet structure
- ✅ Ready for openpyxl integration

### Data Collected
```
📈 Chat Statistics:
  • Total chats processed
  • Average confidence score
  • High confidence count (≥80%)
  • Min/Max confidence ranges

📤 Response Statistics:
  • Auto-replies sent
  • Drafts for review
  • Total responses

💬 Question Analytics:
  • Customer questions list
  • Unique questions count

💰 Financial Data (Placeholder):
  • Revenue entries
  • Business expenses
```

### Usage
```python
from excel_module import get_excel_collector

collector = get_excel_collector()
collector.collect_all_data()
summary = collector.format_for_summary()
print(summary)

# Export to Excel
excel_file_path = collector.export_to_excel("AIBI_Report.xlsx")
```

### Excel Export (When openpyxl is installed)
```bash
pip install openpyxl
```

Then the bot can export full Excel files with sheets:
- **Summary** - Key metrics
- **Chat Analytics** - All chats processed
- **Confidence Scores** - Individual scores
- **Questions** - Unique customer questions

---

## 🚀 Quick Start

### 1. Verify .env Configuration
```
OWNER_TELEGRAM_ID=8040716622
TELEGRAM_BOT_TOKEN=8559587930:AAFhVnn1dM0x_SxYiMjgRsiK07lgpKvbi1Q
TG_API_ID=31354738
TG_API_HASH=994bfcb88ea4076d51a33c7e029a1d9a
```

### 2. Start Flask
```bash
cd D:\projects\AIBI_Project
python main.py
```

### 3. Watch Logs for Registry Status
```
[REGISTRY] ✓ Global Registry initialized
[DRAFT BOT] [STARTUP] Starting background bot listener...
[REGISTRY] ✓ Draft bot registered at 2026-02-02T15:30:45
[DRAFT BOT] ✓ Startup notification sent to owner (8040716622)
```

### 4. Check Your Telegram
You should receive:
```
🤖 **SYSTEM RESTARTED**
✅ Bot is now ONLINE...
```

### 5. Verify in Terminal
```
[GLOBAL REGISTRY] Health Status
================================================
Bot Online:           True
Bot Instance:         True
Event Loop:           True
Excel Module Ready:   True
Uptime:               2 minutes

Services:
  ✓ draft_bot: True
  ✓ event_loop: True
  ✓ excel_module: True
  ✓ telegram_auth: False
================================================
```

---

## 📋 New Files Created

### 1. global_registry.py (163 lines)
- GlobalRegistry class (singleton pattern)
- Thread-safe bot instance management
- Service status tracking
- Health check functionality
- Status reporting

### 2. excel_module.py (302 lines)
- ExcelDataCollector class
- Data collection from reports
- Statistics calculation
- Excel sheet preparation
- Export-ready structure

### 3. Updated draft_bot.py
- `send_startup_notification()` method
- Enhanced `generate_excel_report()`
- Integration with excel_module

### 4. Updated main.py
- Import and use global_registry
- Register bot in Global Registry
- Display registry health status
- Mark Excel module ready

---

## 🔍 Flask Server Integration

### Access Draft Bot from Flask Routes
```python
from global_registry import get_registry

@app.route('/api/bot-status')
def bot_status():
    registry = get_registry()
    health = registry.health_check()
    return jsonify(health)

@app.route('/api/send-message', methods=['POST'])
def send_message():
    bot = registry.get_draft_bot()
    if bot:
        # Use bot to send message
        pass
    else:
        return {"error": "Bot not online"}, 503
```

### Register Custom Services
```python
# Mark service as ready
registry.register_service("my_service", True)

# Check service status
is_ready = registry.get_service_status("my_service")

# Get all services
all_services = registry.get_all_services()
```

---

## 🔧 Configuration

### .env Variables Used
```
OWNER_TELEGRAM_ID=8040716622          # Who receives startup notification
TELEGRAM_BOT_TOKEN=8559587930:...      # New bot token
TG_API_ID=31354738                     # Your API ID
TG_API_HASH=994bfcb88...               # Your API hash
```

### Optional .env
```
AUTO_SCHEDULER=false                   # Manual or auto mode
ANALYSIS_CACHE_TTL_HOURS=1            # Cache lifetime
AUTO_REPLY_CONFIDENCE=85               # Auto-reply threshold
```

---

## 📊 System Status Display

### At Startup
The system automatically displays:

```
[GLOBAL REGISTRY] Health Status:
================================================
Bot Online:           True
Bot Instance:         True
Event Loop:           True
Excel Module Ready:   True
Uptime:               2 minutes
Bot Start Time:       2026-02-02T15:30:45
Last Restart:         2026-02-02T15:30:45

Services:
  ✓ draft_bot: True
  ✓ event_loop: True
  ✓ excel_module: True
  ✓ telegram_auth: False
================================================
```

### Programmatic Access
```python
registry = get_registry()
health = registry.health_check()

print(f"Bot online: {health['bot_online']}")
print(f"Uptime: {health['uptime_seconds']} seconds")
print(f"Services: {health['services']}")
```

---

## ✅ Verification Checklist

### At Startup
- [ ] See `[REGISTRY] ✓ Global Registry initialized` in logs
- [ ] See `[DRAFT BOT] [OK] Bot listener is ONLINE` in logs
- [ ] See `[REGISTRY] ✓ Draft bot registered` in logs
- [ ] Receive startup notification in Telegram
- [ ] See health status with all True values

### Commands
- [ ] Send `/check` - Should trigger analysis
- [ ] Send `/report` - Should show analytics
- [ ] Send `Звіт` - Should show Excel summary

### Excel Module
- [ ] Send `Звіт` command
- [ ] See data collection message
- [ ] See summary in Telegram
- [ ] (Optional) Install openpyxl and export file

---

## 🐛 Troubleshooting

### Bot doesn't start
```
[DRAFT BOT] [ERROR] Bot failed to start
→ Check TELEGRAM_BOT_TOKEN in .env
→ Check TG_API_ID and TG_API_HASH
→ Verify internet connection
```

### No startup notification
```
[DRAFT BOT] [WARNING] OWNER_TELEGRAM_ID not set
→ Add OWNER_TELEGRAM_ID=8040716622 to .env
→ Restart Flask app
```

### Registry shows False values
```
[REGISTRY] Health Status:
  Bot Online: False
→ Check bot startup logs for errors
→ Verify credentials in .env
→ Check if port 8080 is available
```

### Excel module issues
```
[DRAFT BOT] ⚠ openpyxl not installed
→ pip install openpyxl
→ Data collection works without it
→ File export requires the library
```

---

## 🚨 Important Notes

1. **Global Registry is a Singleton**
   - Only one instance across the application
   - Thread-safe for multi-threaded access
   - Persists for application lifetime

2. **Startup Notification**
   - Sent automatically on bot startup
   - Uses OWNER_TELEGRAM_ID from .env
   - Confirms bot is online and ready

3. **Excel Module Ready**
   - Data collection is complete
   - Export structure is prepared
   - Just needs openpyxl for file output
   - Can display summary without library

4. **Service Tracking**
   - Extensible for custom services
   - Each service has on/off status
   - Health check includes all services

---

## 📞 Support

### Check Status
```python
from global_registry import get_registry

registry = get_registry()
registry.print_status()
```

### Debug Info
```python
health = registry.health_check()
print(f"Bot: {health['bot_online']}")
print(f"Services: {health['services']}")
```

### Restart Registry
```python
from global_registry import reset_registry
reset_registry()
```

---

## Version Info

- **Version**: 2.0 (Global Registry Edition)
- **Date**: 2026-02-02
- **Status**: ✅ Production Ready
- **Dependencies**: No new dependencies (openpyxl optional)

---
