# Startup Verification Guide

## 🚀 Starting the System

### Step 1: Verify .env
```bash
cat .env | grep -E "OWNER_TELEGRAM_ID|TELEGRAM_BOT_TOKEN|TG_API"
```

Expected output:
```
TG_API_ID=31354738
TG_API_HASH=994bfcb88ea4076d51a33c7e029a1d9a
TELEGRAM_BOT_TOKEN=8559587930:AAFhVnn1dM0x_SxYiMjgRsiK07lgpKvbi1Q
OWNER_TELEGRAM_ID=8040716622
```

### Step 2: Start Flask
```bash
cd D:\projects\AIBI_Project
python main.py
```

---

## ✅ Startup Sequence (What You'll See)

### Phase 1: Initialization (First 5 seconds)
```
================================================================================
>>> STARTING AIBI SERVER - Global Registry Edition
================================================================================

[STARTUP] Initializing background services...
[REGISTRY] ✓ Global Registry initialized
[SYSTEM] Background bot thread started
```

### Phase 2: Bot Connection (Next 10 seconds)
```
[DRAFT BOT] [STARTUP] Starting background bot listener...
[DRAFT BOT] [CONFIG] Owner ID: 8040716622
[DRAFT BOT] [CONFIG] Bot token: 8559587930...bi1Q
[DRAFT BOT] [OK] Bot authenticated with Bot API (stable mode)
[DRAFT BOT] Bot token ends with: ...bi1Q
```

### Phase 3: Startup Notification (Next 5 seconds)
```
[DRAFT BOT] Started and waiting for button interactions...
[DRAFT BOT] ✓ Startup notification sent to owner (8040716622)
[REGISTRY] ✓ Draft bot registered at 2026-02-02T15:30:45
```

### Phase 4: System Ready (Final status)
```
[SERVER] Configuration:
[SERVER] - Running on http://0.0.0.0:8080
[SERVER] - Scheduled tasks every 20 minutes
[SERVER] - Draft bot listener (continuous)
[SERVER] - /check command support (manual trigger)
[SERVER] - /report command support (analytics)
[SERVER] - Startup notification enabled
[SERVER] - Excel reporting module ready
[SERVER] - Auto-recovery enabled for network issues

[SERVER] Available endpoints:
[SERVER] - GET  http://0.0.0.0:8080/            (Status page)
[SERVER] - GET  http://0.0.0.0:8080/force_run   (Manual analysis)
[SERVER] - MSG  /check (via Telegram)            (Manual analysis)
[SERVER] - MSG  /report (via Telegram)           (Analytics report)
[SERVER] - MSG  Звіт (via Telegram)              (Excel export)

[GLOBAL REGISTRY] Health Status:
================================================
Bot Online:           True
Bot Instance:         True
Event Loop:           True
Excel Module Ready:   True
Uptime:               2 seconds
Bot Start Time:       2026-02-02T15:30:45
Last Restart:         2026-02-02T15:30:45

Services:
  ✓ draft_bot: True
  ✓ event_loop: True
  ✓ excel_module: True
  ✓ telegram_auth: False
================================================

================================================================================
```

---

## 📱 Telegram Verification

### Step 1: Check Notification
Open Telegram and check that you received:

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

### Step 2: Test Commands
Send these to your bot:

#### Test 1: /check Command
```
Send: /check
Wait: ~1-2 minutes
Expected: 🔍 Triggering manual analysis...
Then: ✅ Analysis complete: X chats processed
```

#### Test 2: /report Command
```
Send: /report
Wait: ~10 seconds
Expected: 📊 Scanning reports and generating analytics...
Then: 📊 **ANALYTICS REPORT** with statistics
```

#### Test 3: Звіт (Excel Report)
```
Send: Звіт
Wait: ~15 seconds
Expected: 📊 Generating Excel report...
Then: 📊 **EXCEL REPORT SUMMARY** with data
```

---

## 🔍 Server Verification

### Check Logs for Key Messages

```bash
# Look for these success messages:
grep -i "registry.*initialized" *.py
grep -i "draft bot.*registered" main.py
grep -i "startup notification sent" draft_bot.py
```

### Expected Key Messages
```
✅ [REGISTRY] ✓ Global Registry initialized
✅ [DRAFT BOT] [OK] Bot listener is ONLINE
✅ [DRAFT BOT] ✓ Startup notification sent
✅ [REGISTRY] ✓ Draft bot registered
✅ [GLOBAL REGISTRY] Health Status shows all True
```

### Get Registry Status Programmatically
```python
from global_registry import get_registry

registry = get_registry()
health = registry.health_check()

print(f"Bot Online: {health['bot_online']}")
print(f"Uptime: {health['uptime_seconds']} seconds")
print(f"Services: {health['services']}")
```

---

## ⚠️ Potential Issues & Solutions

### Issue 1: Bot doesn't come online
```
Logs show:
[DRAFT BOT] [ERROR] Failed to connect via TelegramService

Solution:
1. Check TELEGRAM_BOT_TOKEN in .env is correct
2. Verify TG_API_ID and TG_API_HASH are valid
3. Check internet connection
4. Wait 30 seconds and restart Flask
```

### Issue 2: No startup notification received
```
Logs show:
[DRAFT BOT] [WARNING] OWNER_TELEGRAM_ID not set

Solution:
1. Add to .env: OWNER_TELEGRAM_ID=8040716622
2. Restart Flask app
3. Check Telegram for notification
```

### Issue 3: Registry health shows False
```
Logs show:
Bot Online:           False
Bot Instance:         False
Event Loop:           False

Solution:
1. Check bot startup error messages above
2. Verify all credentials in .env
3. Check firewall isn't blocking port 8080
4. Restart Flask with full debug output
```

### Issue 4: Excel module not ready
```
Logs show:
Excel Module Ready:   False

Solution:
1. The Excel module initializes on startup
2. Should see [DRAFT BOT] [EXCEL] in logs
3. If missing, check for errors above
4. Restart Flask
```

---

## 🔄 Full Verification Flow

### 1️⃣ Start Flask
```bash
python main.py
```

### 2️⃣ Watch For All These Messages
- ✅ `[REGISTRY] ✓ Global Registry initialized`
- ✅ `[DRAFT BOT] [OK] Bot listener is ONLINE`
- ✅ `[DRAFT BOT] ✓ Startup notification sent`
- ✅ `Bot Online: True`
- ✅ `Bot Instance: True`
- ✅ `Event Loop: True`
- ✅ `Excel Module Ready: True`

### 3️⃣ Check Telegram
- ✅ Receive "SYSTEM RESTARTED" message
- ✅ Confirm timestamp is recent

### 4️⃣ Test Commands
- ✅ Send `/check` → works
- ✅ Send `/report` → works
- ✅ Send `Звіт` → works

### 5️⃣ Monitor for 5 Minutes
- ✅ No error messages
- ✅ Bot stays online
- ✅ Commands respond quickly

---

## 📊 Success Criteria

| Check | Expected | Actual |
|-------|----------|--------|
| Startup notification received | Yes | ___ |
| `/check` command works | Yes | ___ |
| `/report` command works | Yes | ___ |
| `Звіт` command works | Yes | ___ |
| Registry health all True | Yes | ___ |
| No error messages | Yes | ___ |
| Bot online continuously | Yes | ___ |

---

## 🎯 Troubleshooting Commands

### View Registry Status
```python
from global_registry import get_registry
registry = get_registry()
registry.print_status()
```

### Check Bot Instance
```python
from global_registry import get_registry
registry = get_registry()
bot = registry.get_draft_bot()
print(f"Bot available: {bot is not None}")
```

### View All Services
```python
from global_registry import get_registry
registry = get_registry()
services = registry.get_all_services()
print(services)
```

### Check Excel Module
```python
from excel_module import get_excel_collector
collector = get_excel_collector()
summary = collector.get_summary()
print(summary)
```

---

## 📝 Log Examples

### ✅ Successful Startup
```
[2026-02-02 15:30:45] [REGISTRY] ✓ Global Registry initialized
[2026-02-02 15:30:45] [SYSTEM] Background bot thread started
[2026-02-02 15:30:47] [DRAFT BOT] [STARTUP] Starting background bot listener...
[2026-02-02 15:30:47] [DRAFT BOT] [OK] Bot authenticated with Bot API
[2026-02-02 15:30:48] [DRAFT BOT] ✓ Startup notification sent to owner
[2026-02-02 15:30:48] [REGISTRY] ✓ Draft bot registered
[2026-02-02 15:30:49] [GLOBAL REGISTRY] Health Status printed
```

### ❌ Startup Issues
```
[DRAFT BOT] [ERROR] Failed to connect via TelegramService
→ Problem with Telegram credentials

[DRAFT BOT] [WARNING] OWNER_TELEGRAM_ID not set
→ Missing .env variable

[REGISTRY] Health Status shows False values
→ Bot not registered successfully
```

---

## 🚀 Next Steps After Verification

1. ✅ Confirm all checks pass
2. ✅ Let bot run for 5 minutes with no errors
3. ✅ Test each command manually
4. ✅ Send test message to verify drafts work
5. ✅ Run `/check` to trigger full analysis
6. ✅ Check Excel report with `Звіт`

---

## 📞 Quick Support

### Everything working?
Great! Your system is ready for production.

### Getting an error?
1. Check the "Potential Issues" section above
2. Verify all .env variables are set
3. Check logs for exact error message
4. Restart Flask: Stop (Ctrl+C) and run again

### Still stuck?
Check these files for more details:
- `GLOBAL_REGISTRY_SETUP.md` - System architecture
- `BOT_COMMANDS_REFERENCE.md` - Command documentation
- `IMPLEMENTATION_CHECKLIST.md` - Detailed verification

---
