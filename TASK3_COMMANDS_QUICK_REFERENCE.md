# Task 3: Dynamic Instructions - Commands Quick Reference

## New Commands in Draft Bot

All commands are now available in your draft bot. Send them via Telegram to the bot owner.

---

## Command 1: View Instructions

```
/view_instructions
```

**What it does:** Shows your current instructions and dynamic rules

**Response includes:**
- Core instructions (with character count)
- Dynamic rules (with character count)
- Number of available backups
- List of available commands

**Example Usage:**
```
You:  /view_instructions
Bot:  📋 CURRENT INSTRUCTIONS

      Core Instructions (2544 chars):
      Ти — бізнес-аналітик...

      Dynamic Rules (0 chars):
      [No dynamic rules yet]

      Backups Available: 0

      Available Commands:
        /update_instructions - Edit instructions
        /list_backups - Show available backups
        /rollback_backup - Restore from backup
```

---

## Command 2: Update Instructions

```
/update_instructions
```

**What it does:** Start interactive instruction update mode

**Supported Modes:**
- `REPLACE: [text]` - Replace all instructions with new text
- `APPEND: [text]` - Add text to the end of current instructions
- `PREPEND: [text]` - Add text to the beginning of current instructions
- `DYNAMIC: [text]` - Add a timestamped dynamic rule
- `CANCEL` - Cancel the update operation

**Features:**
- Automatic backup created before any changes
- Minimum 50 characters required for instructions
- Minimum 10 characters required for dynamic rules
- Confirms with backup filename

**Example Usage 1 - Append:**
```
You:  /update_instructions
Bot:  📝 INSTRUCTIONS UPDATE MODE

      Send your update in format:
        REPLACE: [new instructions text]
        APPEND: [text to add at end]
        PREPEND: [text to add at beginning]
        DYNAMIC: [new dynamic rule to add]
        CANCEL: Cancel this operation

You:  APPEND: Always verify client information before responding
Bot:  [OK] Instructions updated successfully (append mode)
      📦 Backup created: instructions_backup_20240215_143022.txt
```

**Example Usage 2 - Replace:**
```
You:  /update_instructions
Bot:  📝 INSTRUCTIONS UPDATE MODE...

You:  REPLACE: Full new instructions text here. Ти — AI асистент...
Bot:  [OK] Instructions updated successfully (replace mode)
      📦 Backup created: instructions_backup_20240215_143100.txt
```

**Example Usage 3 - Add Dynamic Rule:**
```
You:  /update_instructions
Bot:  📝 INSTRUCTIONS UPDATE MODE...

You:  DYNAMIC: New rule from voice command - Check system status first
Bot:  [OK] Dynamic rule added at 2024-02-15 14:31:22
      📦 Backup created: instructions_dynamic_backup_20240215_143122.txt
```

**Example Usage 4 - Cancel:**
```
You:  /update_instructions
Bot:  📝 INSTRUCTIONS UPDATE MODE...

You:  CANCEL
Bot:  ❌ Instruction update cancelled
```

---

## Command 3: List Backups

```
/list_backups
```

**What it does:** Show all available instruction backups (up to 10 most recent)

**Response includes:**
- Numbered list of backups
- Timestamps in format: `instructions_backup_YYYYMMDD_HHMMSS.txt`
- Usage example

**Example Usage:**
```
You:  /list_backups
Bot:  📦 AVAILABLE BACKUPS (Most recent first)

      1. instructions_backup_20240215_143100.txt
      2. instructions_backup_20240215_143022.txt
      3. instructions_backup_20240215_142900.txt

      Use: /rollback_backup [filename]
      Example: /rollback_backup instructions_backup_20240215_143100.txt
```

---

## Command 4: Rollback Backup

```
/rollback_backup [filename]
```

**What it does:** Restore instructions from a previous backup

**Parameters:**
- `[filename]` - The backup filename (copy from `/list_backups` output)

**Features:**
- Creates backup of current version before restoring
- Restores exact version from backup file
- Confirms with restored timestamp

**Example Usage:**
```
You:  /list_backups
Bot:  📦 AVAILABLE BACKUPS (Most recent first)
      1. instructions_backup_20240215_143100.txt
      2. instructions_backup_20240215_143022.txt

You:  /rollback_backup instructions_backup_20240215_143022.txt
Bot:  [OK] Restored from instructions_backup_20240215_143022.txt
```

---

## Usage Workflow

### Typical Update Workflow:

1. **View current state:**
   ```
   /view_instructions
   ```

2. **Start update:**
   ```
   /update_instructions
   ```

3. **Send update (choose one mode):**
   ```
   APPEND: Additional rule here
   ```

4. **Verify changes:**
   ```
   /view_instructions
   ```

5. **List all backups:**
   ```
   /list_backups
   ```

### If You Made a Mistake:

1. **List backups:**
   ```
   /list_backups
   ```

2. **Find the right backup:**
   Look for the timestamp before your mistake

3. **Rollback:**
   ```
   /rollback_backup instructions_backup_20240215_143000.txt
   ```

4. **Verify restored version:**
   ```
   /view_instructions
   ```

---

## Key Features

### Automatic Backups
- Every update creates automatic timestamped backup
- Stored in: `instructions_backup/` directory
- Format: `instructions_backup_YYYYMMDD_HHMMSS.txt`
- Keep up to 10 most recent backups
- Easy rollback if needed

### Input Validation
- **Minimum lengths:**
  - Instructions: 50 characters
  - Dynamic rules: 10 characters
- **Clear error messages** if validation fails
- **Prevents accidental empty updates**

### Error Handling
- All commands have try-catch error handling
- Descriptive error messages
- No data loss on errors
- Automatic backups protect your data

---

## Tips & Tricks

### Tip 1: Use APPEND for Incremental Updates
Rather than replacing everything, use APPEND to add rules:
```
APPEND: New guideline: Always prioritize client satisfaction
```

### Tip 2: Use DYNAMIC for Voice-Commanded Rules
When adding rules from voice commands:
```
DYNAMIC: New rule added via voice - Check inventory first
```

### Tip 3: Always Check Before Major Changes
Before replacing all instructions:
```
/view_instructions          # See what you have
/update_instructions        # Start update
REPLACE: [new content]      # Replace everything
/view_instructions          # Verify it worked
```

### Tip 4: Keep Timestamps Organized
Backup filenames include timestamps, so they're automatically:
- Sortable
- Chronological
- Easy to identify which version you want

### Tip 5: Test Updates Carefully
After updating:
```
/view_instructions          # Verify the change
/list_backups               # See backup was created
```

---

## Common Scenarios

### Scenario 1: Add a New Rule
```
/update_instructions
APPEND: New rule: Always mention our 24/7 support
```

### Scenario 2: Fix a Typo
```
/list_backups
/rollback_backup [backup_before_typo]
/update_instructions
APPEND: Corrected rule with proper spelling
```

### Scenario 3: Start Fresh
```
/update_instructions
REPLACE: Completely new instructions text...
```

### Scenario 4: Add Voice Command Rule
```
/update_instructions
DYNAMIC: Rule from voice: Check calendar before scheduling
```

---

## Error Messages & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| "Instructions too short" | < 50 characters | Add more content |
| "Invalid format" | Wrong mode syntax | Use REPLACE:/APPEND:/PREPEND:/DYNAMIC: |
| "Content after colon" | Missing text after mode | Add text: `APPEND: text here` |
| "Backup not found" | Wrong filename | Copy from `/list_backups` output |

---

## Quick Command Syntax

```
REPLACE: [new instructions] → Full replacement
APPEND: [text]             → Add to end
PREPEND: [text]            → Add to beginning
DYNAMIC: [rule]            → Timestamped dynamic rule
CANCEL                     → Cancel operation
```

---

## All New Commands at a Glance

| Command | Purpose | Usage |
|---------|---------|-------|
| `/view_instructions` | See current instructions | View + help |
| `/update_instructions` | Edit instructions | Interactive mode |
| `/list_backups` | See backup history | View list |
| `/rollback_backup` | Restore from backup | Restore version |

---

## What's Backed Up?

### Automatically Backed Up:
- ✅ All instruction changes
- ✅ Each update creates new backup
- ✅ Timestamped for easy tracking
- ✅ Old backups kept (up to 10)

### Included in Backup:
- Core instructions content
- All metadata
- Timestamps
- Full version history

### NOT Backed Up:
- Dynamic rules (separate file, separate backups)
- Temporary files
- Cache

---

## Advanced: Understanding Backups

### Backup File Format
```
instructions_backup_YYYYMMDD_HHMMSS.txt
                     │       │ │ │  │
                     │       │ │ │  └─ Seconds
                     │       │ │ └──── Minutes
                     │       │ └────── Hours
                     │       └──────── Day
                     └───────────────── Year-Month
```

Example: `instructions_backup_20240215_143022.txt`
- Year: 2024
- Month: 02 (February)
- Day: 15
- Time: 14:30:22 (2:30 PM and 22 seconds)

---

## Ready to Use!

All commands are now live and ready to use. Start with:

```
/view_instructions
```

Then explore the other commands!

**Need help?** Send `/update_instructions` and it will show you all available modes.

---

## Summary

✅ `/view_instructions` - See current state
✅ `/update_instructions` - Make changes (REPLACE/APPEND/PREPEND/DYNAMIC)
✅ `/list_backups` - See backup history
✅ `/rollback_backup` - Restore old version

**All with automatic backups and error handling!**
