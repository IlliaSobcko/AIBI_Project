# Verbose Debugging Findings - Message Flow Analysis

**Date**: 2026-02-07
**Status**: DEBUGGING COMPLETE - Root Causes Identified

---

## 🔍 KEY FINDINGS

### ✅ Messages ARE Being "Sent" (But May Not Arrive)

The verbose logs show:
```
[SEND MSG] Sending auto-reply via collector.client.send_message...
[AUTO-REPLY SUCCESS] Message sent to 'Send_Message_telegram' (95%)
```

**The collector says "SUCCESS" but messages don't appear in Telegram.**

This suggests the messages are being queued locally but not actually delivered to Telegram.

---

## 🚨 ROOT CAUSES IDENTIFIED

### 1. **CRITICAL: Two Different Telegram Sessions**

**In run_core_logic():**
- Uses `aibi_session` for TelegramCollector
- Message sending happens via `collector.client.send_message()`
- This is a USERBOT session, not a BOT

**In Draft Bot:**
- Uses `draft_bot_service` for DraftReviewBot
- Bot token authentication (different from userbot)
- Separate event loop in separate thread

**The Problem**:
- `aibi_session` may not be properly authenticated
- May not have permission to send in certain chats
- May be marked as read-only

### 2. **Missing Smart Logic (Easy Fix)**

Error in logs:
```
[WARNING] Smart Logic not available: read_instructions() got an unexpected keyword argument 'default'
```

**Cause**: Line 278 in main.py calls:
```python
business_data = read_instructions("business_data.txt", default="")
```

But `read_instructions()` doesn't accept `default` parameter.

**Fix**: Either remove the parameter or add it to the function definition.

### 3. **DRAFT BOT NOT AVAILABLE**

Error in logs:
```
[WARNING] Draft bot not available - drafts will NOT be sent
```

**Why**: The bot thread is still connecting during run_core_logic().
The bot hasn't finished initialization when run_core_logic() starts.

**Timeline Problem**:
1. Flask startup begins
2. Bot thread starts (async connection)
3. run_core_logic() immediately runs (doesn't wait for bot)
4. run_core_logic() checks `draft_bot = DRAFT_BOT` - still None!
5. Auto-reply proceeds but bot is unavailable

---

## 🔧 RECOMMENDED FIXES

### FIX #1: Verify Session Status

Add a check to see if `aibi_session` is authenticated and can send:

```python
# In run_core_logic(), after creating collector:
async with TelegramCollector(tg_cfg) as collector:
    # Check if session is valid
    try:
        me = await collector.client.get_me()
        print(f"[SESSION] Authenticated as: {me}")
        print(f"[SESSION] Is bot: {me.is_bot}")
        print(f"[SESSION] Session type: {'BOT' if me.is_bot else 'USERBOT'}")
    except Exception as e:
        print(f"[ERROR] Session check failed: {e}")
```

### FIX #2: Fix Smart Logic read_instructions() call

Change:
```python
business_data = read_instructions("business_data.txt", default="")
```

To:
```python
try:
    business_data = read_instructions("business_data.txt")
except FileNotFoundError:
    business_data = ""
```

### FIX #3: Wait for Bot Initialization

Add delay in run_core_logic() to ensure bot is ready:

```python
# Wait for draft bot to initialize (max 5 seconds)
for i in range(50):
    if DRAFT_BOT is not None:
        print(f"[INIT] Draft bot ready")
        break
    await asyncio.sleep(0.1)
else:
    print(f"[WARNING] Draft bot still initializing, proceeding anyway")
```

### FIX #4: Implement Fallback for Send Failures

If `collector.client.send_message()` returns an error, try using the bot instead:

```python
try:
    # Try collector (userbot session)
    await collector.client.send_message(accumulated_h.chat_id, reply_text)
    print(f"[SEND] ✅ Sent via collector")
except Exception as e:
    print(f"[SEND] ⚠️  Collector failed: {e}")
    # Fallback: use bot if available
    if draft_bot and draft_bot.tg_service:
        try:
            success = await draft_bot.tg_service.send_message(accumulated_h.chat_id, reply_text)
            if success:
                print(f"[SEND] ✅ Sent via bot (fallback)")
        except Exception as e2:
            print(f"[SEND] ❌ Both methods failed: {e2}")
```

---

## 📊 TEST RESULTS FROM VERBOSE OUTPUT

Successfully processed 4 chats:

1. **Send_Message_telegram** (ID: 8244511048)
   - AI Confidence: 98% → Final: 98%
   - Path: AUTO-REPLY
   - Status: "Message sent" ✅ (but user doesn't see it)

2. **AIBI_Secretary_Bot** (ID: 8559587930)
   - AI Confidence: 92% → Final: 92%
   - Path: AUTO-REPLY
   - Trello: Created card
   - Calendar: Created event
   - Status: "Message sent" ✅ (but user doesn't see it)

3. **Chat** (ID: 526791303)
   - AI Confidence: 98% → Final: 98%
   - Path: AUTO-REPLY
   - Status: "Message sent" ✅ (but user doesn't see it)

4. **Telegram** (ID: 777000)
   - AI Confidence: 100% → Final: 100%
   - REPLY GEN: 0 length (EMPTY REPLY!)
   - Status: SKIPPED (confidence < 70%)

---

## 🎯 NEXT STEPS

1. **Verify Session**: Check if aibi_session is properly authenticated
2. **Fix Smart Logic**: Remove invalid `default=` parameter
3. **Wait for Bot**: Ensure draft bot is ready before run_core_logic()
4. **Add Fallback**: Use bot as fallback if collector fails
5. **Test Again**: Run trigger_test_analysis.py to verify fixes

---

## 📝 HOW TO TEST

Run with verbose logging to see message flow:

```bash
python trigger_test_analysis.py 2>&1 | grep -E "\[SEND\]|\[SUCCESS\]|\[ERROR\]"
```

Watch for:
- `[SEND MSG]` - Message about to be sent
- `[AUTO-REPLY SUCCESS]` - Says it was sent (but might be lying)
- `[ERROR]` - Actual errors from Telegram

---

## 🔴 THE REAL ISSUE

The bot is saying "SUCCESS" but messages aren't arriving. This means:

1. The Telegram API isn't rejecting the message (no error)
2. But the message isn't visible to the recipient

**Possible Causes**:
- Wrong chat ID
- Wrong authentication (read-only session)
- Session is blocked
- Using userbot instead of bot account
- Rate limit silently dropped the message

**Most Likely**: `aibi_session` is a userbot that needs proper login authentication, not just bot token.

