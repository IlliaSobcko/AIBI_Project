# LIVE MONITORING DASHBOARD
## Real-Time Testing Session

**Session Start Time:** 2024-02-15
**Project Status:** RUNNING
**Server Address:** http://0.0.0.0:8080

---

## Server Status ✅

```
[STARTUP SEQUENCE VERIFIED]
✓ Flask server: RUNNING on http://0.0.0.0:8080
✓ Draft bot listener: ACTIVE (continuous monitoring)
✓ Background services: INITIALIZED
✓ Scheduler: MANUAL MODE (on-demand)
```

### Available Commands
- **Web UI:** http://0.0.0.0:8080/
- **Manual Trigger:** http://0.0.0.0:8080/force_run
- **Telegram:** Send `/check` to draft bot

---

## What to Monitor For

### Task 1: Smart Logic (Main.py)
When a message is analyzed, you should see:

```
[MAIN] Smart Logic Decision Engine initialized
[SMART_LOGIC] DataSourceManager initialized
  Calendar available: True/False
  Trello available: True/False
  Business data: XXXX chars

[SMART_LOGIC] '[Chat Name]': Base=XX% -> Final=YY% (Sources: {'ai': XX, 'calendar': XX, 'trello': XX, 'price_list': XX})
```

**CRITICAL CHECK:**
- [ ] Look for: `[MAIN] Smart Logic Decision Engine initialized`
- [ ] Verify: `Business data: ` appears (means business_data.txt was read)
- [ ] Verify: Character count shown (e.g., "Business data: 2500 chars")

### Task 2: Analytics Engine (Draft Bot)
When you send `/analytics` command:

```
[LOAD] Running unified analytics (Format A + B reports)...
[OK] UNIFIED ANALYTICS COMPLETE

[DEALS]
  Total: X
  Wins: X (X.X%)
  ...

[FILE]
  Report: unified_analytics.xlsx
```

**CRITICAL CHECK:**
- [ ] Command `/analytics` is recognized
- [ ] Summary statistics displayed
- [ ] No error messages

### Task 3: Dynamic Instructions (Draft Bot)
When you send `/view_instructions`:

```
📋 CURRENT INSTRUCTIONS
Core Instructions (XXXX chars):
...
```

**CRITICAL CHECK:**
- [ ] Command `/view_instructions` is recognized
- [ ] Current instructions displayed
- [ ] Character count shown

---

## Test Scenarios

### Scenario 1: Send /check to Manual Analysis
**Action:**
1. Find bot owner ID (in logs or config)
2. Send message to bot: `/check`
3. Monitor console for analysis

**Expected Output:**
```
[TG_SERVICE] Message from [chat_name]
[OK] Processed: [chat_name]
[SMART_LOGIC] '[chat_name]': Base=XX% -> Final=YY% (Sources: {...})
[AUTO-REPLY] or [DRAFT] sent
```

**Critical Indicators:**
- ✓ [SMART_LOGIC] line appears (Task 1 initialized)
- ✓ Base % and Final % both shown
- ✓ Sources dictionary has all 4 keys: 'ai', 'calendar', 'trello', 'price_list'
- ✓ Business data chars shown in init message

### Scenario 2: Test /analytics Command
**Action:**
1. Send `/analytics` to draft bot
2. Monitor for response and file generation

**Expected Output:**
```
[LOAD] Running unified analytics...
[OK] UNIFIED ANALYTICS COMPLETE
[STATS] Total: 3, Wins: 2 (66.7%), ...
```

**Check For:**
- ✓ Command recognized (no error)
- ✓ Summary displays correctly
- ✓ unified_analytics.xlsx created in project root

### Scenario 3: Test /view_instructions
**Action:**
1. Send `/view_instructions` to draft bot
2. Verify current instructions displayed

**Expected Output:**
```
📋 CURRENT INSTRUCTIONS
Core Instructions (2544 chars):
Ти — бізнес-аналітик...
```

**Check For:**
- ✓ Command recognized
- ✓ Instructions text displayed
- ✓ Character count shown

### Scenario 4: Test /update_instructions
**Action:**
1. Send `/update_instructions`
2. Reply with: `APPEND: New test rule`

**Expected Output:**
```
📝 INSTRUCTIONS UPDATE MODE
[OK] Instructions updated successfully
📦 Backup created: instructions_backup_YYYYMMDD_HHMMSS.txt
```

**Check For:**
- ✓ Update mode started
- ✓ Update accepted
- ✓ Backup file created
- ✓ Confirmation message

---

## Error Detection Strategy

### Critical Errors (STOP immediately)
These require immediate code fixes:

```
[ERROR] Module not found
[ERROR] SmartDecisionEngine initialization failed
[ERROR] Cannot access business_data.txt
Traceback (most recent call last):
ImportError:
AttributeError:
NameError:
```

### Warnings (Monitor, may be OK)
These are usually fine but worth monitoring:

```
[WARNING] SmartLogic not available
[WARNING] Calendar not available
[WARNING] Trello not available
FutureWarning:
DeprecationWarning:
```

---

## Business Data Verification

**Critical Check for Smart Logic:**

In logs, you MUST see:
```
[SMART_LOGIC] DataSourceManager initialized
  Calendar available: True/False
  Trello available: True/False
  Business data: XXXX chars    <--- THIS MUST NOT BE 0
```

If `Business data: 0 chars`, this means:
1. business_data.txt file is missing
2. business_data.txt is empty
3. read_instructions() failed to read it

**To Fix:**
1. Create/populate business_data.txt with sample prices
2. Restart server
3. Verify character count increases

---

## Task 1 Confidence Calculation Verification

When a message is analyzed, verify the calculation is correct:

**Example Log:**
```
[SMART_LOGIC] 'Chat Name': Base=85% -> Final=91% (Sources: {'ai': 85, 'calendar': 100, 'trello': 50, 'price_list': 100})
```

**Manual Calculation Check:**
```
Sources provided:
  ai: 85 (weight 0.60)
  calendar: 100 (weight 0.20)
  trello: 50 (weight 0.10)
  price_list: 100 (weight 0.10)

Calculation:
  (85 × 0.60) + (100 × 0.20) + (50 × 0.10) + (100 × 0.10)
= 51 + 20 + 5 + 10
= 86%

If Final shows 91%, the calculation might be different than expected.
Check SmartDecisionEngine._calculate_final_score() for actual formula.
```

---

## Real-Time Log Monitoring

### Watch for These Patterns

**Good Signs:**
```
✓ [MAIN] Smart Logic Decision Engine initialized
✓ [SMART_LOGIC] '[Chat]': Base=XX% -> Final=YY%
✓ [AUTO-REPLY] or [DRAFT] decision made
✓ [OK] UNIFIED ANALYTICS COMPLETE
✓ [OK] Instructions updated
```

**Bad Signs:**
```
✗ Module not found
✗ ImportError
✗ Cannot read business_data.txt
✗ SmartLogic evaluation failed
✗ Traceback/Exception
```

---

## Testing Checklist

### Before Running Tests
- [ ] main.py is running (see server output)
- [ ] Flask bound to http://0.0.0.0:8080
- [ ] Draft bot listener active
- [ ] No startup errors in output

### During Testing
- [ ] Check logs for Task 1 initialization (send /check or message)
- [ ] Check logs for Task 2 command working (send /analytics)
- [ ] Check logs for Task 3 command working (send /view_instructions)
- [ ] Monitor for any [ERROR] messages
- [ ] Verify business_data.txt is being read (check char count)

### After Tests
- [ ] Summarize any errors found
- [ ] Check file modifications (if any /update_instructions used)
- [ ] Verify unified_analytics.xlsx created (if /analytics used)
- [ ] Check instructions_backup/ for backups (if /update_instructions used)

---

## If You Find an Error

### Step 1: Capture the Error
Copy the full error message/traceback from console

### Step 2: Stop the Server
- Press CTRL+C in the terminal running main.py
- Wait for it to shut down gracefully (or force kill if hung)

### Step 3: Report the Error
Provide:
1. Full error message/traceback
2. What action triggered it
3. Which task it affects (1, 2, or 3)

### Step 4: I Will Fix It
- Identify the root cause
- Fix the code in the affected module
- Restart the server
- Re-test

---

## Commands Available for Testing

### Telegram Bot Commands
Send these to the draft bot (via Telegram):

**Task 1 (Automatic):**
- Send any message to trigger analysis
- Or send `/check` for manual analysis

**Task 2 (Analytics):**
- `/analytics` - Run unified analytics on reports/

**Task 3 (Dynamic Instructions):**
- `/view_instructions` - View current instructions
- `/update_instructions` - Edit instructions
- `/list_backups` - Show backup history
- `/rollback_backup [filename]` - Restore from backup

### Web Dashboard
Visit these in your browser:

- `http://localhost:8080/` - Status page
- `http://localhost:8080/force_run` - Trigger manual analysis

---

## Expected Behavior

### On Startup
✓ Server starts on port 8080
✓ Flask server running
✓ Draft bot listener active
✓ No critical errors

### On First Message Analysis
✓ [SMART_LOGIC] initialization logged
✓ Business data character count shown
✓ AI confidence + Final confidence shown
✓ Auto-reply or Draft decision made

### On /analytics Command
✓ Summary statistics returned
✓ unified_analytics.xlsx created
✓ All 3 sheets populated

### On /view_instructions
✓ Current instructions displayed
✓ Character count shown

### On /update_instructions
✓ Update modes explained
✓ Backup created on save
✓ Confirmation message sent

---

## Next Steps

1. **Verify Startup** - Check if all initialization messages appear
2. **Send Test Message** - Trigger first analysis (should see Task 1 init)
3. **Test /analytics** - Verify Task 2 works
4. **Test /view_instructions** - Verify Task 3 works
5. **Monitor for Errors** - Watch console continuously
6. **Report Issues** - If any errors occur, I'll fix them immediately

---

**Status: SERVER RUNNING - READY FOR TESTING**

Proceed with your tests. I will monitor the logs in real-time and intercept any errors immediately.
