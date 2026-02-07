# Quick Setup Checklist

## Prerequisites

- [ ] Python 3.10+ installed
- [ ] All dependencies installed: `pip install -r requirements.txt`
- [ ] `.env` file exists with required variables

## Required .env Variables

Check that your `.env` file has these:

```env
# REQUIRED - Telegram
[ ] TG_API_ID=your_number
[ ] TG_API_HASH=your_hash
[ ] TELEGRAM_BOT_TOKEN=your_bot_token
[ ] OWNER_TELEGRAM_ID=your_telegram_id

# REQUIRED - AI
[ ] AI_API_KEY=your_api_key

# OPTIONAL - Trello (can be skipped)
[ ] TRELLO_API_KEY=...
[ ] TRELLO_TOKEN=...
[ ] TRELLO_BOARD_ID=...

# OPTIONAL - Calendar (can be skipped)
[ ] ENABLE_GOOGLE_CALENDAR=false
```

**Don't have TELEGRAM_BOT_TOKEN?**
1. Open Telegram
2. Search for @BotFather
3. Send `/newbot`
4. Follow the prompts
5. Copy the token to .env

## Startup Steps

### Step 1: Start the System
```bash
cd D:\projects\AIBI_Project
python main.py
```

### Step 2: Wait for Bot to Come Online
Look for this message (wait up to 10-15 seconds):
```
[DRAFT BOT] [OK] Bot listener is ONLINE - Ready to receive buttons & commands
```

### Step 3: Verify Everything Works
Send a message to your bot in Telegram:
```
/check
```

Expected response (in Telegram):
```
🔍 Triggering manual analysis... This will take a moment...
[After 30-60 seconds]
✅ Analysis complete: X chats processed
```

### Step 4: Check Web Interface
Open browser: http://localhost:8080/

Should see:
```
🚀 AI Бізнес-Асистент
Статус: Система активна
⚡ ПРИМУСОВА ПЕРЕВІРКА ЗАРАЗ
```

## Testing the System

### Test 1: Manual Analysis Trigger
[ ] Send `/check` to bot in Telegram
[ ] Bot responds with "Triggering manual analysis..."
[ ] Bot responds with "Analysis complete"

### Test 2: Web Trigger
[ ] Visit http://localhost:8080/force_run
[ ] System processes messages
[ ] Page shows results

### Test 3: Draft Button Functionality
[ ] Trigger analysis (Step 3 or Test 2)
[ ] Look for draft message in Telegram
[ ] Draft should have 3 buttons:
   - [ ] ✅ ВІДПРАВИТИ (Send)
   - [ ] 📝 РЕДАГУВАТИ (Edit)
   - [ ] ❌ ПРОПУСТИТИ (Skip)
[ ] Click SKIP button
[ ] Message should show [SKIPPED BY USER]

### Test 4: Auto-Recovery
[ ] System running successfully
[ ] Disconnect internet for 10 seconds
[ ] Reconnect internet
[ ] Check console - should see "Retrying..." messages
[ ] System should continue working normally

## Troubleshooting

### Problem: "Bot listener is not online"
**Solution**:
1. Check console for error messages (look for [ERROR])
2. Verify TELEGRAM_BOT_TOKEN in .env is correct
3. Check internet connection
4. Wait 15-20 seconds (first connection takes time)
5. If still failing, restart: CTRL+C, then `python main.py` again

### Problem: "/check command doesn't work"
**Solution**:
1. Make sure you're sending to the bot (not a group chat)
2. Verify OWNER_TELEGRAM_ID in .env matches your ID
3. Wait for "Bot listener is ONLINE" message before testing
4. Check console for error messages

### Problem: "Buttons don't respond"
**Solution**:
1. Make sure bot is online (see console message)
2. Click button within 30 seconds of draft arrival
3. Check console for error messages starting with [ERROR]
4. Try different button (maybe one is broken)
5. Restart and try again

### Problem: "Draft not sent, error in console"
**Solution**:
1. Read the error message carefully
2. If "ConnectionError": Check internet connection
3. If "Unauthorized": Verify TELEGRAM_BOT_TOKEN is valid
4. If "User not found": Verify OWNER_TELEGRAM_ID is correct
5. System will auto-retry (up to 2 times)
6. Check next scheduled cycle (20 minutes)

## How It Works

```
You send /check to bot
    ↓
Bot receives message (draft_bot.py handler)
    ↓
Triggers run_core_logic() in main.py
    ↓
Analyzes Telegram messages from last 7 days
    ↓
Creates drafts for low-confidence messages
    ↓
Sends drafts to you in Telegram with buttons
    ↓
You click button to approve/edit/reject
    ↓
System executes your choice
```

## Console Output Meanings

```
[STARTUP]     - System is initializing
[SERVER]      - Flask web server events
[DRAFT BOT]   - Bot listener events
[SCHEDULER]   - Scheduled analysis events
[OK]          - Operation succeeded
[WARNING]     - Non-critical issue
[ERROR]       - Error occurred (system retries automatically)
```

## Key Console Messages

**Good signs**:
- `[DRAFT BOT] [OK] Bot listener is ONLINE`
- `[DRAFT BOT] Draft sent to owner...`
- `[DRAFT BOT] Button clicked: send...`
- `[DRAFT BOT] Message delivered to chat`

**Bad signs**:
- `[ERROR] Background bot error:`
- `[ERROR] Attempt X/2 - Error sending draft:`
- `[ERROR] [FINAL_FAILURE] Draft could not be sent`

## Performance Expectations

| Operation | Time |
|-----------|------|
| System startup | 5-10 seconds |
| Bot connection | 10-15 seconds |
| Analysis run | 30-120 seconds |
| Draft delivery | 1-5 seconds |
| Button response | <1 second |

## Daily Operation

**Option 1: Always Running**
- Start system once with `python main.py`
- Leave it running 24/7
- Analysis runs every 20 minutes automatically
- Bot listens for `/check` command anytime

**Option 2: Manual Runs**
- Start system with `python main.py`
- Send `/check` when you want analysis
- Stop with CTRL+C when done
- Restart next time you need it

**Option 3: Scheduled Background**
- Use Windows Task Scheduler to auto-start
- System runs in background
- Open cmd to see logs anytime
- Stop with CTRL+C when needed

## Support Commands

In Telegram, send to bot:

```
/check        - Trigger manual analysis
```

That's it! Just one command.

## Verification Checklist

Before considering setup complete:

- [ ] System starts without errors
- [ ] Console shows "Bot listener is ONLINE"
- [ ] `/check` command works in Telegram
- [ ] Bot responds with status message
- [ ] Web interface accessible at http://localhost:8080/
- [ ] Draft messages appear with buttons
- [ ] Buttons respond to clicks
- [ ] No errors in console output

## You're Ready! 🎉

If all checkboxes are checked, your system is ready for production use.

**Need help?** Check the error message in console - it usually tells you exactly what's wrong.
