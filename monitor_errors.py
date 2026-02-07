#!/usr/bin/env python3
"""
Real-time Error Monitor for AIBI Project
Continuously monitors aibi_server.log for errors and warnings
"""

import time
import os
from pathlib import Path
from datetime import datetime

# Color codes for terminal output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

# Critical error patterns to detect
CRITICAL_PATTERNS = [
    'Traceback',
    'ImportError',
    'ModuleNotFoundError',
    'AttributeError',
    'NameError',
    'TypeError',
    'ValueError',
    'KeyError',
    'FileNotFoundError',
    'PermissionError',
    '[CRITICAL]',
    '[FATAL]',
]

# Warning patterns to detect
WARNING_PATTERNS = [
    '[ERROR]',
    '[WARNING]',
    'Exception',
    'Failed',
    'Error:',
]

# Expected patterns (Task 1, 2, 3)
EXPECTED_PATTERNS = {
    'task1_init': '[MAIN] Smart Logic Decision Engine initialized',
    'task1_eval': '[SMART_LOGIC]',
    'task1_business': 'Business data:',
    'task2_analytics': '[LOAD] Running unified analytics',
    'task3_update': '[INSTRUCTIONS]',
}

def print_header():
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}AIBI PROJECT - REAL-TIME ERROR MONITOR{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.RESET}\n")
    print(f"{Colors.GREEN}[OK] Monitoring started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}")
    print(f"{Colors.GREEN}[OK] Log file: aibi_server.log{Colors.RESET}\n")
    print(f"{Colors.BLUE}Critical errors detected: Will alert immediately{Colors.RESET}")
    print(f"{Colors.YELLOW}Warnings detected: Will log for review{Colors.RESET}")
    print(f"{Colors.CYAN}Expected patterns: Will track Task 1, 2, 3 activity{Colors.RESET}\n")
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.RESET}\n")

def monitor_logs(log_file='aibi_server.log', check_interval=2):
    """Monitor log file for errors and expected patterns"""

    log_path = Path(log_file)
    if not log_path.exists():
        print(f"{Colors.RED}[FAIL] Log file not found: {log_file}{Colors.RESET}")
        return False

    print_header()

    # Track what we've seen
    last_size = 0
    seen_errors = []
    seen_warnings = []
    found_patterns = {}

    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Read initial file
            lines = f.readlines()
            last_size = f.tell()

            print(f"{Colors.GREEN}[OK] Initial read: {len(lines)} lines{Colors.RESET}\n")

        # Monitor loop
        print(f"{Colors.CYAN}Monitoring... (Press Ctrl+C to stop){Colors.RESET}\n")

        while True:
            time.sleep(check_interval)

            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    current_size = f.seek(0, 2)  # Go to end

                    # If file grew, read new content
                    if current_size > last_size:
                        f.seek(last_size)
                        new_lines = f.readlines()
                        last_size = current_size

                        # Check each new line
                        for line in new_lines:
                            # Check for critical errors
                            for pattern in CRITICAL_PATTERNS:
                                if pattern in line:
                                    if line not in seen_errors:
                                        print(f"{Colors.RED}{Colors.BOLD}[CRITICAL ERROR DETECTED]{Colors.RESET}")
                                        print(f"{Colors.RED}{line.strip()}{Colors.RESET}\n")
                                        seen_errors.append(line)

                            # Check for warnings
                            for pattern in WARNING_PATTERNS:
                                if pattern in line:
                                    if line not in seen_warnings and 'WARNING:' not in line:
                                        print(f"{Colors.YELLOW}[WARNING]{Colors.RESET} {line.strip()}")
                                        seen_warnings.append(line)

                            # Check for expected patterns (Task 1, 2, 3)
                            for task_key, pattern in EXPECTED_PATTERNS.items():
                                if pattern in line and task_key not in found_patterns:
                                    found_patterns[task_key] = line
                                    if 'task1' in task_key:
                                        print(f"{Colors.GREEN}[TASK 1]{Colors.RESET} {line.strip()}")
                                    elif 'task2' in task_key:
                                        print(f"{Colors.GREEN}[TASK 2]{Colors.RESET} {line.strip()}")
                                    elif 'task3' in task_key:
                                        print(f"{Colors.GREEN}[TASK 3]{Colors.RESET} {line.strip()}")

                            # Print important lines
                            if any(x in line for x in ['[OK]', '[AUTO-REPLY]', '[DRAFT]', '[SMART_LOGIC]']):
                                if 'FutureWarning' not in line:
                                    print(f"{Colors.CYAN}{line.strip()}{Colors.RESET}")

            except IOError:
                pass  # File might be rotated or temporarily unavailable

    except KeyboardInterrupt:
        print(f"\n\n{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.RESET}")
        print(f"{Colors.YELLOW}Monitoring stopped by user{Colors.RESET}")
        print(f"{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.RESET}\n")

        # Summary
        print(f"{Colors.BOLD}Summary:{Colors.RESET}")
        print(f"  Critical Errors: {len(seen_errors)}")
        print(f"  Warnings: {len(seen_warnings)}")
        print(f"  Tasks Detected: {len(found_patterns)}")

        if found_patterns:
            print(f"\n{Colors.BOLD}Task Activity:{Colors.RESET}")
            for key, line in found_patterns.items():
                print(f"  {key}: {line.strip()[:60]}...")

        return True

if __name__ == '__main__':
    monitor_logs()
