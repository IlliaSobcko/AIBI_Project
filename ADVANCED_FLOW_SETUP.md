# 🚀 Advanced AI Flow - Setup Guide

## Overview

The Advanced AI Flow enables intelligent auto-responses with human oversight:

- **High Confidence (>85%)**: Auto-reply during working hours using business data
- **Low Confidence (<85%)**: Send draft to you for review via Telegram
- **Human Control**: Approve with `SEND`, edit with `EDIT`, or skip with `SKIP`

---

## 📋 Setup Steps

### Step 1: Get Your Telegram ID

Run this command to get your Telegram user ID:

```bash
python get_my_telegram_id.py
```

This will output something like:
```
==================================================
ВАШ TELEGRAM ID:
  ID: 123456789
  Username: @yourusername
  Ім'я: Your Name
==================================================

Додайте це значення в .env файл:
OWNER_TELEGRAM_ID=123456789
```

### Step 2: Update .env File

Open `.env` and update these values:

```env
# Enable Google Calendar
ENABLE_GOOGLE_CALENDAR=true

# Your Telegram ID (from Step 1)
OWNER_TELEGRAM_ID=123456789

# Auto-reply settings (optional, defaults shown)
AUTO_REPLY_CONFIDENCE=85
WORKING_HOURS_START=9
WORKING_HOURS_END=18
```

### Step 3: Customize Business Data

Edit `business_data.txt` to include your actual business information:
- Company name and services
- Pricing and timelines
- Contact information
- Common response templates

### Step 4: Verify credentials.json

Make sure `credentials.json` from Google Cloud Console is in the project root:
```
D:\projects\AIBI_Project\credentials.json
```

---

## 🎯 How It Works

### Scenario 1: High Confidence Auto-Reply

**When:**
- AI confidence > 85%
- Current time is within working hours (9am-6pm by default)
- Message requires a response

**What happens:**
1. AI analyzes the chat and generates a reply using `business_data.txt`
2. Reply is automatically sent to the client
3. Action logged in the report file

**Example:**
```
Client: "Скільки коштує розробка бота?"
AI: "Дякую за інтерес! Розробка чат-бота коштує від $1,000.
     Точну вартість розрахую після обговорення деталей.
     Коли зможемо поговорити?"
[AUTO-REPLY SENT - Confidence: 92%]
```

### Scenario 2: Low Confidence Draft Review

**When:**
- AI confidence < 85%
- Message requires a response

**What happens:**
1. AI generates a draft reply
2. Draft is sent to YOU in Telegram with:
   - Chat name and confidence level
   - Proposed reply text
   - Chat ID for commands
3. You review and decide:
   - `SEND {chat_id}` - Send as-is
   - `EDIT {chat_id}` - Edit before sending (bot will ask for new text)
   - `SKIP {chat_id}` - Don't respond

**Example Telegram message you'll receive:**
```
🔔 НОВА ЧЕРНЕТКА ДЛЯ РОЗГЛЯДУ

📱 Чат: Important Client
🎯 Впевненість AI: 72%
🔢 Chat ID: 123456789

📝 ЗАПРОПОНОВАНА ВІДПОВІДЬ:
Дякую за запит! Потрібно уточнити деталі вашого проекту.
Коли зможемо обговорити це детальніше?

━━━━━━━━━━━━━━━━━━━━
Команди:
• SEND 123456789 - відправити як є
• EDIT 123456789 - редагувати (надішли новий текст)
• SKIP 123456789 - пропустити
```

---

## 📝 Commands Reference

### SEND Command
Approves and sends the draft as-is.

```
SEND 123456789
```

Response: `✅ Відправлено в чат: Important Client`

### EDIT Command
Allows you to modify the draft before sending.

```
EDIT 123456789
```

Bot will reply: `✏️ Окей, надішли новий текст для чату 123456789`

Then you send your edited message:
```
Дякую за запит! Ми спеціалізуємося на AI-рішеннях.
Давайте обговоримо ваш проект завтра о 15:00?
```

Response: `✅ Відредагований текст відправлено в чат: Important Client`

### SKIP Command
Ignores the draft (no message will be sent).

```
SKIP 123456789
```

Response: `⏭️ Чернетку для чату 123456789 пропущено`

---

## ⚙️ Configuration Options

### .env Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTO_REPLY_CONFIDENCE` | 85 | Minimum confidence for auto-reply |
| `WORKING_HOURS_START` | 9 | Start of working hours (24h format) |
| `WORKING_HOURS_END` | 18 | End of working hours (24h format) |
| `OWNER_TELEGRAM_ID` | required | Your Telegram user ID |
| `ENABLE_GOOGLE_CALENDAR` | true | Enable/disable Calendar integration |

### Adjusting Auto-Reply Threshold

**More conservative** (fewer auto-replies):
```env
AUTO_REPLY_CONFIDENCE=90
```

**More aggressive** (more auto-replies):
```env
AUTO_REPLY_CONFIDENCE=80
```

### Adjusting Working Hours

**Early bird** (7am-3pm):
```env
WORKING_HOURS_START=7
WORKING_HOURS_END=15
```

**Night owl** (12pm-8pm):
```env
WORKING_HOURS_START=12
WORKING_HOURS_END=20
```

---

## 🔍 Testing the Flow

### Test Auto-Reply

1. Make sure it's within working hours
2. Trigger analysis: `curl http://127.0.0.1:8080/force_run`
3. Check console for: `[AUTO-REPLY] Відправлено автовідповідь...`
4. Check the chat for the auto-sent message

### Test Draft Review

1. Temporarily set `AUTO_REPLY_CONFIDENCE=99` in .env (forces draft mode)
2. Restart server
3. Trigger analysis
4. Check your Telegram for draft approval message
5. Test commands: `SEND`, `EDIT`, `SKIP`

---

## 📊 Logs and Reports

All actions are logged in the report files (`reports/*.txt`):

```
ЗВІТ ПО ЧАТУ: Important Client
ДАТА: 2026-01-26 23:45
ВПЕВНЕНІСТЬ ШІ: 92%
==============================
[Analysis report here...]

[AUTO-REPLY SENT]
Reply Confidence: 89%
Message: Дякую за інтерес! Розробка чат-бота...
```

Or for drafts:
```
[DRAFT FOR REVIEW]
Reply Confidence: 72%
Draft: Дякую за запит! Потрібно уточнити...
```

---

## 🐛 Troubleshooting

### Draft bot not sending messages

1. Check `OWNER_TELEGRAM_ID` is set correctly in `.env`
2. Run `python get_my_telegram_id.py` to verify your ID
3. Make sure the ID is a number, not a username

### Auto-replies not working

1. Check current time is within `WORKING_HOURS_START` and `WORKING_HOURS_END`
2. Verify AI confidence is > `AUTO_REPLY_CONFIDENCE` threshold
3. Check console logs for errors

### "credentials.json not found"

1. Download credentials.json from Google Cloud Console
2. Place it in `D:\projects\AIBI_Project\credentials.json`
3. Set `ENABLE_GOOGLE_CALENDAR=true` in .env

---

## 🎓 Best Practices

### 1. Start Conservative
Begin with high thresholds and adjust down:
```env
AUTO_REPLY_CONFIDENCE=90  # Start here
```

### 2. Monitor First Week
Check all auto-replies in reports to ensure quality:
```bash
grep -r "AUTO-REPLY SENT" reports/
```

### 3. Update business_data.txt Regularly
Keep pricing, services, and templates current.

### 4. Review Draft Statistics
Track how many drafts you approve vs. edit:
```bash
grep -r "DRAFT FOR REVIEW" reports/ | wc -l
```

### 5. Use EDIT Frequently
Build a library of good responses by editing drafts.

---

## 🚀 Next Steps

1. Run `python get_my_telegram_id.py`
2. Update `.env` with your Telegram ID
3. Customize `business_data.txt`
4. Restart the server
5. Monitor first few auto-replies
6. Adjust confidence threshold as needed

**Your Advanced AI Flow is ready!** 🎉
