# Telegram Bot Troubleshooting Guide

## Issue: "Telegram buttons don't work"

### Quick Checks:

#### 1. Check .env Configuration

Verify these values in your `.env` file:

```env
TELEGRAM_BOT_TOKEN=8559587930:AAHWVuTnShyFJDUbxugxgMk4shCVV-QTcGI
OWNER_TELEGRAM_ID=8040716622
```

**Important**:
- `TELEGRAM_BOT_TOKEN` must be from @BotFather
- `OWNER_TELEGRAM_ID` must be YOUR user ID (not the bot's ID)

#### 2. Check Bot Connection

When server starts, you should see:

```
[DRAFT BOT] [STARTUP] Starting background bot listener...
[TG_SERVICE] >>> Connecting to Telegram...
[DRAFT BOT] [OK] Bot authenticated with Bot API (stable mode)
[DRAFT BOT] Started - listening for button interactions...
```

**If you see timeout errors:**
- Delete session files: `rm draft_bot_service.session*`
- Restart server

#### 3. Check for Startup Notification

When bot connects successfully, you should receive THIS message in Telegram:

```
🤖 SYSTEM RESTARTED

✅ Bot is now ONLINE and ready to receive commands

Status:
  - Bot API: Connected
  - Token: Valid
  - Owner ID: 8040716622
  - Restart Time: 2026-02-07 14:30:00

Available Commands:
  - /check: Manual analysis trigger
  - /status: System status
  - /clear: Clear waiting states
```

**If you DON'T receive this message:**
- Bot didn't connect
- Check logs for errors
- Verify bot token is correct

---

## Common Issues & Solutions

### Issue 1: Buttons Don't Respond

**Symptoms:**
- You click SEND/EDIT/SKIP buttons
- Nothing happens
- No feedback

**Causes:**
1. Bot not fully initialized
2. Event handler not registered
3. Owner ID mismatch

**Solutions:**

**A. Check Server Logs**
```bash
# In server output, look for:
[DRAFT BOT] Button clicked: send for chat 12345 by owner 8040716622
```

If you DON'T see this when clicking buttons → Handler not registered

**B. Verify Owner ID**
```bash
# Run this to get your ID:
python get_my_telegram_id.py
```

Compare with `OWNER_TELEGRAM_ID` in `.env`

**C. Restart Bot**
1. Stop server (Ctrl+C)
2. Delete session: `rm draft_bot_service.session*`
3. Start server: `python main.py`
4. Wait 30 seconds for bot connection
5. Check for startup notification

---

### Issue 2: Bot Sends Drafts But Buttons Missing

**Symptoms:**
- Draft message appears
- No buttons below message

**Causes:**
1. Old Telegram client
2. Bot API limitations
3. Message too long

**Solutions:**

**A. Check Message Format**
Draft should look like:
```
🔔 NEW DRAFT FOR REVIEW

📱 Chat: Customer Name
🎯 Confidence: 72%
💬 Message: "Hello, can you help..."

📝 DRAFT REPLY:
"Thank you for your message..."

[THREE BUTTONS APPEAR HERE]
```

**B. Update Telegram App**
- Android/iOS: Update from store
- Desktop: Download latest from telegram.org

---

### Issue 3: Buttons Work But Message Not Sent

**Symptoms:**
- Click SEND button
- See "Sending message..." notification
- Message never appears in target chat

**Causes:**
1. Bot doesn't have access to target chat
2. Target user blocked bot
3. Chat ID is incorrect

**Solutions:**

**A. Check Logs for Errors**
```bash
# Look for:
[ERROR] Failed to send message: User not found
[ERROR] Failed to send message: Bot was blocked by user
```

**B. Verify Chat Access**
The bot can ONLY send messages to:
- Users who have started the bot (`/start`)
- Chats where bot is a member

**Fix**: Target user must:
1. Open bot in Telegram
2. Send `/start` command
3. Then drafts can be sent

---

### Issue 4: /check Command Doesn't Work

**Symptoms:**
- Send `/check` to bot
- No response

**Solutions:**

**A. Check If Bot Is Running**
```bash
# Look for this in logs:
[DRAFT BOT] Started - listening for button interactions AND new messages...
```

**B. Send Directly to Bot**
- Don't send `/check` in a group
- Send it in private message to bot
- Must be from owner account

**C. Check Command Handler**
```bash
# Logs should show:
[DRAFT BOT] Manual /check command received from owner
[DRAFT BOT] Clearing any waiting states before analysis...
```

---

## Testing Steps

### Test 1: Bot Alive Test

1. Start server: `python main.py`
2. Wait 30 seconds
3. Check Telegram for startup notification
4. **PASS**: Notification received
5. **FAIL**: No notification → Bot not connected

### Test 2: Button Test

1. Trigger analysis to get a draft:
   - Send test message to any chat
   - Wait for draft to appear
2. Draft should have 3 buttons
3. Click SKIP button
4. **PASS**: Message updates to "[SKIPPED BY USER]"
5. **FAIL**: No change → Button handler not working

### Test 3: SEND Button Test

1. Get a new draft
2. Click SEND button
3. Check target chat
4. **PASS**: Message sent to chat
5. **FAIL**: No message → Permission issue

### Test 4: EDIT Button Test

1. Get a new draft
2. Click EDIT button
3. Message should update: "[WAITING FOR YOUR EDIT...]"
4. Send new message text
5. **PASS**: New text sent to target chat
6. **FAIL**: Nothing happens → Edit handler not working

### Test 5: /check Command Test

1. Open bot in Telegram
2. Send: `/check`
3. **PASS**: Bot replies "[CHECK] Clearing states and triggering manual analysis..."
4. **FAIL**: No response → Command handler not registered

---

## Debug Mode

To see detailed button events:

1. Stop server
2. Edit `draft_bot.py`, line 547:
```python
print(f"[DRAFT BOT] Button clicked: {action} for chat {chat_id} by owner {event.sender_id}")
```

3. Restart server
4. Click any button
5. Check logs for the debug message

**If you see the debug message:**
- Handler IS working
- Issue is in approve_and_send() or other methods

**If you DON'T see the debug message:**
- Handler NOT registered
- Event not reaching callback
- Restart bot

---

## Nuclear Option: Full Reset

If nothing works:

```bash
# 1. Stop server
Ctrl+C

# 2. Delete ALL session files
rm *.session*
rm *.db
rm *.journal

# 3. Verify .env
cat .env | grep TELEGRAM_BOT_TOKEN
cat .env | grep OWNER_TELEGRAM_ID

# 4. Test bot token with curl
curl -X POST https://api.telegram.org/bot<YOUR_TOKEN>/getMe

# 5. Restart
python main.py

# 6. Wait 60 seconds for full initialization

# 7. Check for startup notification
```

---

## Current Status Check

Run this command to check current configuration:

```bash
python -c "
from dotenv import load_dotenv
import os
load_dotenv()

print('Configuration Check:')
print(f'  Bot Token: ...{os.getenv(\"TELEGRAM_BOT_TOKEN\", \"NOT_SET\")[-10:]}')
print(f'  Owner ID: {os.getenv(\"OWNER_TELEGRAM_ID\", \"NOT_SET\")}')
print(f'  TG API ID: {os.getenv(\"TG_API_ID\", \"NOT_SET\")}')
print()
print('Expected Owner ID: 8040716622')
print('Bot Token should end with: ...7lgpKvbi1Q')
"
```

---

## Next Steps

1. **If bot connects but buttons don't work:**
   - Check owner ID matches
   - Delete session and restart
   - Verify button click events in logs

2. **If bot doesn't connect:**
   - Verify bot token with BotFather
   - Check network connectivity
   - Delete session files

3. **If messages don't send:**
   - Verify target user started the bot
   - Check bot permissions
   - Look for API errors in logs

4. **If still stuck:**
   - Share last 100 lines of server output
   - Share screenshot of button message
   - Share /check command response
