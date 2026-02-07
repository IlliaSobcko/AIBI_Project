#!/bin/bash
# Continuous Log Monitor with Error Detection

LOG_FILE="aibi_server.log"
LAST_CHECK=0
CHECK_INTERVAL=3  # Check every 3 seconds

echo "========================================="
echo "CONTINUOUS LOG MONITOR - STARTED"
echo "========================================="
echo "Monitoring: $LOG_FILE"
echo "Checking every $CHECK_INTERVAL seconds"
echo ""
echo "Watching for:"
echo "  🟢 Task initialization and activity"
echo "  🟡 Warnings"
echo "  🔴 Critical errors"
echo ""
echo "Press Ctrl+C to stop"
echo "========================================="
echo ""

while true; do
    sleep $CHECK_INTERVAL
    
    # Get current line count
    CURRENT_LINES=$(wc -l < "$LOG_FILE" 2>/dev/null || echo 0)
    
    if [ $CURRENT_LINES -gt $LAST_CHECK ]; then
        # New lines found
        NEW_LINES=$((CURRENT_LINES - LAST_CHECK))
        
        # Get new content
        tail -n $NEW_LINES "$LOG_FILE" | while read -r line; do
            # Check for critical errors
            if echo "$line" | grep -qE "Traceback|ImportError|ModuleNotFoundError|AttributeError|NameError|TypeError|KeyError|FileNotFoundError|Fatal|CRITICAL"; then
                echo "[🔴 ERROR] $line"
            # Check for task activity
            elif echo "$line" | grep -qE "\[MAIN\]|\[SMART_LOGIC\]|\[INSTRUCTIONS\]|UNIFIED ANALYTICS"; then
                echo "[🟢 ACTIVITY] $line"
            # Check for warnings
            elif echo "$line" | grep -qE "\[WARNING\]\[ERROR\]|Exception|Failed"; then
                echo "[🟡 WARNING] $line"
            # Check for successful operations
            elif echo "$line" | grep -qE "\[OK\]|initialized|running|completed|created"; then
                echo "[✅ SUCCESS] $line"
            fi
        done
        
        LAST_CHECK=$CURRENT_LINES
    fi
done
