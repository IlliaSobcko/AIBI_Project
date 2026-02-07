# LIVE TESTING INSTRUCTIONS
## AIBI Project - All Tasks Integration Test

**Server Status:** ✅ RUNNING on http://0.0.0.0:8080
**Log File:** `aibi_server.log` (updated in real-time)
**Start Time:** 2024-02-15

---

## 🚀 Server is Ready for Testing

The AIBI project server is running with all three tasks integrated:
- ✅ Task 1: Smart Logic Decision Engine (in main.py)
- ✅ Task 2: Analytics Engine (/analytics command)
- ✅ Task 3: Dynamic Instructions (/view_instructions, /update_instructions, etc.)

---

## Test Schedule

### Phase 1: Verify Smart Logic (Task 1)
**What:** Send a message/command to trigger analysis
**Expected:** See Task 1 initialization in logs

**Commands:**
- Send any message to a Telegram chat the bot monitors
- OR send `/check` to the draft bot for manual analysis

**What to Look For in Logs:**
```
[MAIN] Smart Logic Decision Engine initialized
[SMART_LOGIC] DataSourceManager initialized
  Calendar available: True/False
  Trello available: True/False
  Business data: XXXX chars     <-- KEY: Must NOT be 0

[SMART_LOGIC] '[Chat Name]': Base=XX% -> Final=YY% (Sources: {'ai': XX, 'calendar': XX, 'trello': XX, 'price_list': XX})
```

**CRITICAL VERIFICATION:**
- [ ] "Business data: XXXX chars" appears (not 0)
- [ ] Sources dictionary has all 4 keys
- [ ] Final confidence calculated correctly

---

### Phase 2: Test Analytics Command (Task 2)
**What:** Send /analytics command to draft bot
**Expected:** See analytics summary and file creation

**Command:**
```
Send to draft bot: /analytics
```

**What to Look For in Logs:**
```
[LOAD] Running unified analytics...
[OK] UNIFIED ANALYTICS COMPLETE
Total deals analyzed
Win rate percentage
File: unified_analytics.xlsx created
```

**Expected Result in Chat:**
```
[OK] UNIFIED ANALYTICS COMPLETE

[DEALS]
  Total: X
  Wins: X (X.X%)
  Losses: X
  Unknown: X

[REVENUE]
  Total: $XXX,XXX.XX
  Avg/Win: $XXX,XXX.XX

[CUSTOMERS]
  Unique: X

[FORMAT BREAKDOWN]
  Format A Wins/Losses
  Format B Wins/Losses

[TOP WINNING FAQs]
  FAQ 1 (Nx)
  FAQ 2 (Nx)
  ...

[FILE]
  Report: unified_analytics.xlsx
```

**CRITICAL VERIFICATION:**
- [ ] Command recognized (no error)
- [ ] Statistics displayed
- [ ] unified_analytics.xlsx created in project root
- [ ] Excel file has 3 sheets

---

### Phase 3: Test Dynamic Instructions (Task 3)
**What:** Send instruction management commands
**Expected:** See instructions displayed and updated

**Commands:**

**3.1 View Instructions:**
```
Send to draft bot: /view_instructions
```

**What to Look For:**
- Current instructions displayed
- Character count shown
- Backup count shown

**3.2 Update Instructions:**
```
Send to draft bot: /update_instructions
Then reply: APPEND: This is a test rule
```

**What to Look For:**
```
[OK] Instructions updated successfully
📦 Backup created: instructions_backup_YYYYMMDD_HHMMSS.txt
```

**Check Logs For:**
- No errors
- Backup file created in instructions_backup/
- Confirmation message sent

**3.3 List Backups:**
```
Send to draft bot: /list_backups
```

**What to Look For:**
- List of backup files
- Timestamps visible
- Instructions for rollback shown

**3.4 Rollback (If needed):**
```
Send to draft bot: /rollback_backup instructions_backup_YYYYMMDD_HHMMSS.txt
```

**What to Look For:**
- Restoration confirmed
- New backup created (backup of current before restoring)

---

## Error Detection Guide

### 🔴 CRITICAL ERRORS (Stop Immediately)

These require immediate fixing:

**1. Module Import Error**
```
ImportError: No module named 'features.smart_logic'
ModuleNotFoundError: No module named 'features'
```
→ **Fix:** Verify features/smart_logic.py exists

**2. SmartLogic Initialization Error**
```
[CRITICAL] SmartDecisionEngine initialization failed
AttributeError: 'NoneType' has no attribute...
```
→ **Fix:** Check main.py lines 205-213 are correct

**3. Business Data Error**
```
Business data: 0 chars
Cannot read business_data.txt
```
→ **Fix:** Create/populate business_data.txt with sample data

**4. Traceback/Exception**
```
Traceback (most recent call last):
  File "main.py", line XXX, in ...
```
→ **Fix:** I will debug and fix the code

### 🟡 WARNINGS (Monitor)

These are usually OK but worth monitoring:

```
[WARNING] SmartLogic not available
[WARNING] Calendar not available
[WARNING] Trello not available
[WARNING] Draft bot not connected
FutureWarning: You are using Python...
```

### ✅ GOOD SIGNS

These indicate everything is working:

```
[OK] Processed: [Chat Name]
[SMART_LOGIC] '[Chat]': Base=XX% -> Final=YY%
[AUTO-REPLY] Sent
[DRAFT] Sent
[OK] UNIFIED ANALYTICS COMPLETE
[OK] Instructions updated
```

---

## Testing Workflow

### Step 1: Initial Verification
```bash
# In project directory, verify files exist:
ls -la features/smart_logic.py
ls -la features/analytics_engine.py
ls -la features/dynamic_instructions.py
ls -la business_data.txt
```

### Step 2: Monitor Initial Logs
```bash
# Watch logs in real-time:
tail -f aibi_server.log
```

### Step 3: Send Test Message (Task 1)
- Send a message to a Telegram chat the bot monitors
- Watch logs for Task 1 initialization

### Step 4: Test Analytics (Task 2)
- Ensure reports/ folder has sample .txt files
- Send `/analytics` to draft bot
- Verify response and xlsx file creation

### Step 5: Test Instructions (Task 3)
- Send `/view_instructions`
- Send `/update_instructions` and try APPEND mode
- Send `/list_backups` to verify backup created
- Optionally send `/rollback_backup` to restore

### Step 6: Monitor for Errors
- Watch logs continuously
- Look for any [ERROR] or Traceback messages
- Note any warnings

---

## Key Files to Check

**Business Data File:**
```
File: business_data.txt
Expected: Sample prices/services data
What Task 1 looks for: Keyword matching in message text
```

**Reports Folder (for Task 2):**
```
Folder: reports/
Expected: Sample .txt files with Format A or Format B reports
Files: report_1.txt, report_2.txt, etc.
```

**Backup Folder (created by Task 3):**
```
Folder: instructions_backup/
Created: When /update_instructions is used
Contains: instructions_backup_YYYYMMDD_HHMMSS.txt files
```

**Analytics Output:**
```
File: unified_analytics.xlsx
Created: When /analytics command is run
Location: Project root
```

---

## Troubleshooting

### If Task 1 Doesn't Initialize

**Symptoms:**
```
No [MAIN] Smart Logic Decision Engine initialized in logs
No [SMART_LOGIC] output when message processed
```

**Check:**
1. Is main.py running? (check server logs)
2. Did you send a message/command to trigger analysis?
3. Are line 22, 205-213, 255-277 in main.py correct?

**Fix:**
1. Verify main.py has the Task 1 integration code
2. Send a test message or `/check` command
3. Watch logs for initialization

### If Task 2 (/analytics) Doesn't Work

**Symptoms:**
```
Command not recognized
No summary displayed
```

**Check:**
1. Is reports/ folder empty?
2. Does draft_bot.py have the /analytics handler?
3. Are there sample reports in reports/ folder?

**Fix:**
1. Create sample report files in reports/
2. Verify draft_bot.py lines 193-265 are correct
3. Restart server if code was modified

### If Task 3 (/view_instructions) Doesn't Work

**Symptoms:**
```
Command not recognized
Instructions not displayed
```

**Check:**
1. Does draft_bot.py have Task 3 command handlers?
2. Is instructions.txt readable?
3. Are the state variables set up correctly?

**Fix:**
1. Verify draft_bot.py has all Task 3 code
2. Check instructions.txt exists and is readable
3. Restart server if code was modified

### If "Business data: 0 chars" Appears

**Critical Issue:** Smart Logic can't read business_data.txt

**Symptoms:**
```
[SMART_LOGIC] DataSourceManager initialized
  Business data: 0 chars    <-- THIS IS WRONG
```

**Fix:**
1. Create business_data.txt if missing:
   ```
   Our Services:
   - Premium Package: $5,000/month
   - Standard Package: $2,500/month
   - Basic Package: $999/month
   ```
2. Or populate it with your actual pricing
3. Restart server
4. Send test message again
5. Verify character count increases

---

## Commands Summary

**From Telegram:**
```
/check                              - Trigger manual analysis (Task 1)
/analytics                          - Run analytics (Task 2)
/view_instructions                  - View instructions (Task 3)
/update_instructions                - Edit instructions (Task 3)
/list_backups                       - Show backups (Task 3)
/rollback_backup [filename]         - Restore from backup (Task 3)
```

**From Browser:**
```
http://0.0.0.0:8080/               - Status page
http://0.0.0.0:8080/force_run      - Manual analysis trigger
```

**From CLI:**
```
tail -f aibi_server.log             - Watch logs in real-time
python verify_task1_integration.py  - Verify integration
python monitor_errors.py            - Monitor for errors
```

---

## Success Criteria

### Task 1 (Smart Logic)
✅ Server starts without error
✅ Task 1 initializes on first message/command
✅ Business data character count shown (non-zero)
✅ Final confidence calculated and logged
✅ Auto-reply or Draft decision made correctly

### Task 2 (Analytics)
✅ /analytics command recognized
✅ Summary statistics displayed
✅ unified_analytics.xlsx created
✅ Excel file has 3 sheets with correct data
✅ No errors in logs

### Task 3 (Dynamic Instructions)
✅ /view_instructions command recognized
✅ /update_instructions works with APPEND/REPLACE/PREPEND/DYNAMIC modes
✅ Backup files created automatically
✅ /list_backups shows history
✅ /rollback_backup restores correctly

---

## What I'm Monitoring For

I will continuously watch the logs for:

**🔴 CRITICAL (will stop and fix immediately):**
- ImportError, ModuleNotFoundError
- AttributeError, NameError, TypeError
- Traceback messages
- "[CRITICAL]" or "[FATAL]" prefixes
- "Cannot read business_data.txt"
- "Business data: 0 chars" (after initialization)

**🟡 WARNINGS (will track and investigate):**
- [ERROR] prefixes
- [WARNING] prefixes (except FutureWarning)
- Exception messages
- Failed operation messages

**✅ SUCCESS (will track activity):**
- [MAIN] Smart Logic initialized
- [SMART_LOGIC] analysis output
- [AUTO-REPLY] or [DRAFT] decisions
- [OK] UNIFIED ANALYTICS COMPLETE
- [OK] Instructions updated

---

## Ready to Test!

**Server is running. Proceed with:**

1. **Send a test message** to trigger Task 1 analysis
2. **Send /analytics** to test Task 2
3. **Send /view_instructions** to test Task 3
4. **Monitor logs** for any errors
5. **Report any issues** - I'll fix immediately

I will monitor the logs (`aibi_server.log`) in real-time and intercept any errors as they occur.

**Current Status:** ✅ READY FOR TESTING

Start whenever you're ready!
