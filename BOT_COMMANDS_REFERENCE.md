# Bot Commands Reference

## Quick Command Guide

### For Bot Owner (OWNER_TELEGRAM_ID)

#### `/check` - Manual Analysis Trigger
```
Command:     /check
Location:    Send directly to bot in Telegram
Purpose:     Manually trigger analysis of all chats
Response:    "✅ Analysis complete: X chats processed"
Time:        ~1-2 minutes (depends on chat volume)
Returns:     List of processed chats with confidence scores
```

**Flow**:
1. Owner sends `/check`
2. Bot calls `run_core_logic()` from main.py
3. All chats are analyzed
4. Results saved to `reports/` folder
5. Drafts/auto-replies sent based on confidence
6. Owner receives confirmation

---

#### `/report` - Analytics & Statistics
```
Command:     /report
Location:    Send directly to bot in Telegram
Purpose:     Get analytics summary of all processed chats
Response:    📊 ANALYTICS REPORT
             📁 Total Chats Processed: X
             ✅ High Confidence (≥80%): Y
             📝 Drafts/Replies: Z
             ━━━━━━━━━━━━━━━━━━━━
Time:        ~10 seconds
Returns:     Real-time statistics from reports/ folder
```

**What it scans**:
- `reports/` folder
- Count total report files
- Extract confidence scores
- Count drafts & auto-replies sent

**Example Output**:
```
📊 **ANALYTICS REPORT**

📁 Total Chats Processed: 4
✅ High Confidence (≥80%): 3
📝 Drafts/Replies: 2

━━━━━━━━━━━━━━━━━━━━
Report generation completed at 2026-02-02 15:30:45
```

---

#### `Звіт` - Excel Report Export
```
Command:     Звіт (Ukrainian for "Report")
Location:    Send to bot in Telegram
Purpose:     Generate Excel report with business data
Response:    📊 EXCEL REPORT SUMMARY
             📈 Statistics & data collection
             📉 Data points breakdown
Time:        ~15 seconds
Status:      ✅ Skeleton ready (full implementation coming)
```

**Collects**:
- Total chats analyzed
- Average confidence score
- Customer questions asked
- Revenue entries (from Trello)
- Business expenses (from logs)

**Example Output**:
```
📊 **EXCEL REPORT SUMMARY**

📈 Statistics:
  • Total Chats: 4
  • Average Confidence: 82.5%
  • Unique Questions: 12

📉 Data Points Collected:
  • Confidence Scores: 4
  • Customer Questions: 12
  • Revenue Entries: 0
  • Expense Entries: 0

✅ Excel export skeleton ready for implementation
```

---

## Button Actions (In Draft Messages)

### ✅ ВІДПРАВИТИ (SEND)
```
Button:    ✅ ВІДПРАВИТИ
Action:    Sends the draft message to the customer
Behavior:
  1. Updates button message with [SUCCESS]
  2. Sends draft to target chat
  3. Removes draft from memory
  4. Confirms to owner
```

### 📝 РЕДАГУВАТИ (EDIT)
```
Button:    📝 РЕДАГУВАТИ
Action:    Allows owner to edit the draft before sending
Behavior:
  1. Bot waits for owner's next message
  2. Uses the new text as the message
  3. Sends edited message to customer
  4. Confirms "Edited message sent"
  5. Removes original draft
```

### ❌ ПРОПУСТИТИ (SKIP)
```
Button:    ❌ ПРОПУСТИТИ
Action:    Deletes the draft without sending
Behavior:
  1. Removes draft from memory
  2. Updates button message with [SKIPPED BY USER]
  3. No message sent to customer
```

---

## System Commands (Internal)

### Draft System Integration
```python
# Auto triggered from analyze_single_chat()
if confidence > 0 and draft_bot_available:
    draft_system.add_draft(chat_id, chat_title, draft_text, confidence)
    await draft_bot.send_draft_for_review(...)
```

---

## Response Times

| Command | Time | Notes |
|---------|------|-------|
| `/check` | ~1-2 min | Processes all chats |
| `/report` | ~10 sec | Scans existing reports |
| `Звіт` (Excel) | ~15 sec | Collects and formats |
| Button actions | <1 sec | Immediate response |

---

## Error Handling

### If command fails:

```
❌ Analysis failed: TimeoutError: Request timed out
```

**Solutions**:
1. Check internet connection
2. Wait a few minutes and retry
3. Check Flask app is running
4. Check `.env` variables are correct

---

## Configuration

**Required `.env` variables**:
```
OWNER_TELEGRAM_ID=your_numeric_id
TELEGRAM_BOT_TOKEN=your_bot_token
TG_API_ID=your_api_id
TG_API_HASH=your_api_hash
```

**Optional**:
```
AUTO_SCHEDULER=false           # Manual mode (recommended)
ANALYSIS_CACHE_TTL_HOURS=1     # Cache lifetime
AUTO_REPLY_CONFIDENCE=85       # Threshold for auto-reply
```

---

## Troubleshooting

### "Unknown action" error
- Invalid button data
- Try clicking button again
- Restart bot if persists

### "/report shows empty results"
- No reports generated yet
- Run `/check` first to create reports
- Wait for analysis to complete

### "/check doesn't respond"
- Check Flask app is running
- Check bot is online in logs
- Verify OWNER_TELEGRAM_ID is correct

---

## New Features Summary

### ✅ Complete
- [x] Global state management (app_state.py)
- [x] Thread-safe bot instance access
- [x] `/check` command (manual analysis)
- [x] `/report` command (analytics dashboard)
- [x] Excel skeleton (ready for enhancement)
- [x] Clean code with perfect indentation
- [x] Error handling and logging

### 🚀 Ready for Implementation
- [ ] Full Excel export to file
- [ ] Database integration
- [ ] Historical trending dashboard
- [ ] Advanced filtering options

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-02 | Fresh restart - Global state management |

---
