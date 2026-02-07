#!/bin/bash
# Run AIBI Server with Real-Time Monitoring
# This script starts the server and monitors for critical errors

cd "$(dirname "$0")"

echo "================================================================================"
echo "AIBI PROJECT - SERVER WITH REAL-TIME MONITORING"
echo "================================================================================"
echo ""
echo "Starting server..."
echo ""

# Start server in background
python main.py > aibi_server.log 2>&1 &
SERVER_PID=$!

echo "[OK] Server started with PID: $SERVER_PID"
echo ""
echo "Monitoring log file: aibi_server.log"
echo ""
echo "Press Ctrl+C to stop monitoring (server will continue running)"
echo ""
echo "================================================================================"
echo ""

# Function to check for errors
check_for_errors() {
    local errors=$(grep -E "\[ERROR\]|Traceback|ImportError|ModuleNotFoundError" aibi_server.log | tail -5)
    if [ ! -z "$errors" ]; then
        echo "🔴 CRITICAL ERRORS DETECTED:"
        echo "$errors"
        echo ""
        return 1
    fi
    return 0
}

# Function to check for task activity
check_task_activity() {
    echo ""
    echo "Task Activity:"
    echo "  Task 1 (Smart Logic): $(grep -c '\[SMART_LOGIC\]' aibi_server.log) detections"
    echo "  Task 2 (Analytics): $(grep -c 'UNIFIED ANALYTICS' aibi_server.log) runs"
    echo "  Task 3 (Instructions): $(grep -c '\[INSTRUCTIONS\]' aibi_server.log) updates"
    echo ""
}

# Tail the log file with color highlighting
echo "Real-time log output:"
echo ""

tail -f aibi_server.log | while IFS= read -r line; do
    # Highlight different message types
    if echo "$line" | grep -q "ERROR\|CRITICAL\|Traceback"; then
        echo -e "\033[91m$line\033[0m"  # Red
    elif echo "$line" | grep -q "WARNING"; then
        echo -e "\033[93m$line\033[0m"  # Yellow
    elif echo "$line" | grep -q "\[OK\]\|\[SMART_LOGIC\]\|\[MAIN\]"; then
        echo -e "\033[92m$line\033[0m"  # Green
    elif echo "$line" | grep -q "initialized\|Running\|running"; then
        echo -e "\033[94m$line\033[0m"  # Blue
    else
        echo "$line"
    fi
done

# Cleanup on exit
trap "echo ''; echo 'Stopping monitoring...'; kill $SERVER_PID 2>/dev/null; exit 0" INT TERM

wait $SERVER_PID
