# Refactoring Plan: Human-Like AI Assistant

## Changes Required:

### 1. Enhanced Message Collection (telegram_client.py)
- Modify `collect_history_last_days` to include sender information (owner vs client)
- Track last 10-15 messages with sender IDs
- Identify who sent the last message

### 2. Self-Filter Logic (main.py - run_core_logic)
- Check if owner was the last speaker → return confidence 0
- Skip processing if owner replied last
- Only process chats where client needs a response

### 3. Style Mimicry (ai_client.py or new prompting)
- Extract owner's past messages from chat history
- Analyze owner's tone, vocabulary, response length
- Instruct AI to match owner's communication style

### 4. Multi-Message Grouping (main.py)
- Detect if last 2-3 messages are all from client
- Group them as one context for response
- Generate cohesive reply addressing all points

### 5. Button Handler Fixes (draft_bot.py)
- Already done: handle_edit_text uses event.message
- Verify handle_button_callback uses event.message correctly

## Implementation:
