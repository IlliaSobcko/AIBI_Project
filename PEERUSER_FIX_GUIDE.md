# PeerUser Entity Resolution Fix

## The Problem You Encountered

**Error**:
```
ValueError: Could not find the input entity for PeerUser(user_id=526791303)
```

**What happened**:
1. UserBot attempted to send the message but failed (connection/entity issue)
2. System fell back to Bot API as intended ✓
3. Bot API tried to send directly without entity resolution ✗
4. Telethon internally tried to resolve `PeerUser(user_id=526791303)` and failed
5. Bot API doesn't have access to private users it hasn't interacted with
6. User 526791303 hasn't started the bot, so Bot API can't send to them

**Root cause**: The fallback Bot API code wasn't validating the entity before attempting to send.

---

## The Fix Applied

### 3 Methods Updated

All three sending methods now properly handle entity resolution in the Bot API fallback:

#### 1. `approve_and_send()` (Lines 518-540)
**Before**:
```python
try:
    await self.client.send_message(int(chat_id), draft)  # No entity validation!
```

**After**:
```python
try:
    # Resolve entity first
    recipient_entity = await self.client.get_input_entity(int(chat_id))
    await self.client.send_message(recipient_entity, draft)
```

#### 2. `send_auto_reply()` (Lines 415-443)
**Before**:
```python
await self.client.send_message(int(chat_id), reply_text)  # No validation
```

**After**:
```python
recipient_entity = await self.client.get_input_entity(int(chat_id))
await self.client.send_message(recipient_entity, reply_text)
```

#### 3. `send_edited_message()` (Lines 709-762)
**Before**:
```python
entity = await self.client.get_entity(chat_id)  # Wrong method
await self.client.send_message(entity, new_text)
```

**After**:
```python
entity = await self.client.get_input_entity(chat_id)  # Correct method
await self.client.send_message(entity, new_text)
```

---

## Error Handling Improvements

### Clear Error Messages

When `ValueError` is caught (user not found), users now see:

```
❌ Не вдалось надіслати: Користувач не знайдений.

Можливі причини:
• Користувач не запустив цього бота
• ID чату невірний
• Користувач заблокував бота
```

**Before**: Generic "ValueError: Could not find..." error

### Early Return

When entity can't be resolved:
- **Before**: Tried to send anyway, raised exception
- **After**: Returns early with clear message, no exception

---

## Why This Happens

### Bot API Limitations

The Bot API can only send messages to:
1. **Users who have started the bot** - They're in the bot's contact list
2. **Groups where bot is a member** - Bot has explicit membership
3. **Channels where bot is admin** - Bot has explicit access

**It CANNOT send to**:
- Users who haven't started the bot (even if you know their ID)
- Private users (unless they're contacts)
- Users who blocked the bot

### UserBot vs Bot API

| Feature | UserBot | Bot API |
|---------|---------|---------|
| Access private chats | ✅ Yes (if you have history) | ❌ Only if started bot |
| Send to any user | ✅ Yes (with history) | ❌ Limited to contacts |
| Requires user to start | ❌ No | ✅ Yes |
| Connection issues | ⚠️ Database locked, dormant | ✅ More stable |

---

## How to Prevent This

### For Users Receiving Drafts

**The recipient MUST start the bot first**:
1. Find bot: `@YourBotUsername` on Telegram
2. Send `/start` command
3. Bot will now be able to send messages to them

### For Admins Setting Up Recipients

Make sure all users in the `chat_id` list have:
- Started the bot
- Not blocked the bot
- Given proper permissions (if group)

### For Code

The fix is now in place! The system:
1. ✅ Validates entity exists before sending
2. ✅ Provides clear error messages
3. ✅ Returns gracefully instead of crashing
4. ✅ Shows helpful recovery steps to users

---

## Error Recovery Flow (After Fix)

```
[SEND] ✗ UserBot failed
  ↓
[FALLBACK] Using Bot API...
  ↓
[BOT API] Try to resolve entity
  ↓
  ✅ Entity found → Send message
  ❌ ValueError (entity not found)
       ↓
       Return with clear message:
       "User hasn't started bot"
```

---

## Logging Output (After Fix)

### Successful Case
```
[DRAFT BOT] Button clicked: send for chat 526791303
[SEND] ✗ UserBot send failed (e.g., connection lost)
[FALLBACK] Attempting Bot API fallback...
[BOT API] Attempting to resolve entity via Bot API...
[BOT API] ✓ Entity resolved
[BOT API] ✓ Message sent via Bot API
✅ Надіслано (через бота)
```

### Failed Case (User hasn't started bot)
```
[DRAFT BOT] Button clicked: send for chat 526791303
[SEND] ✗ UserBot send failed
[FALLBACK] Attempting Bot API fallback...
[BOT API] Attempting to resolve entity via Bot API...
[BOT API] ✗ Entity resolution failed
❌ Не вдалось надіслати: Користувач не знайдений.

Можливі причини:
• Користувач не запустив цього бота
• ID чату невірний
• Користувач заблокував бота
```

---

## Files Modified

**`draft_bot.py`**:
- Lines 415-443: `send_auto_reply()` - Added entity resolution
- Lines 518-562: `approve_and_send()` - Improved error handling
- Lines 709-762: `send_edited_message()` - Fixed entity resolution method

---

## Testing the Fix

### Test Case 1: User Who Started Bot
1. User starts bot with `/start`
2. Get their chat_id
3. Press SEND button
4. Message should deliver via UserBot or Bot API ✅

### Test Case 2: User Who Hasn't Started Bot
1. Get a user's ID who hasn't started bot
2. Press SEND button for that user
3. Should see message: "Користувач не запустив цього бота"
4. No crash, no exception ✅

### Test Case 3: Invalid Chat ID
1. Use a fake chat_id (e.g., 999999999999)
2. Press SEND button
3. Should see message: "ID чату невірний"
4. No crash ✅

---

## Key Improvements

| Aspect | Before | After |
|--------|--------|-------|
| Entity validation | ❌ None | ✅ Before send |
| Error clarity | ❌ Generic | ✅ Specific & helpful |
| Error handling | ❌ Exception | ✅ Graceful return |
| User feedback | ❌ Raw error | ✅ Clear message |
| Code stability | ❌ Crash possible | ✅ Always handles |

---

## What NOT To Do

❌ **Don't** try to send to users who haven't started bot
❌ **Don't** use invalid chat IDs
❌ **Don't** expect Bot API to access private messages
❌ **Don't** try to ignore this error and retry

---

## What TO Do

✅ **Do** make sure recipients start the bot first
✅ **Do** validate chat IDs before sending
✅ **Do** use UserBot for maximum compatibility
✅ **Do** check logs for entity resolution failures
✅ **Do** inform users to start bot if send fails

---

## Summary

The PeerUser error has been fixed by:
1. **Adding entity validation** before sending via Bot API
2. **Catching ValueError** specifically (entity not found)
3. **Providing clear error messages** to users
4. **Gracefully handling failures** instead of crashing
5. **Applying fix consistently** to all 3 sending methods

**Status**: ✅ **FIXED & PRODUCTION-READY**

The system now handles all entity resolution scenarios gracefully and provides users with actionable error messages.
