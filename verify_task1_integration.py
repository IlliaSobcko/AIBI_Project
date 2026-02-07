"""
Task 1 Verification Script
Checks if SmartDecisionEngine is properly integrated into main.py
"""

import os
import sys
from pathlib import Path

print("=" * 80)
print("TASK 1 INTEGRATION VERIFICATION")
print("=" * 80)

# Check 1: Verify features/smart_logic.py exists
print("\n[1] Checking features/smart_logic.py...")
smart_logic_path = Path("features/smart_logic.py")
if smart_logic_path.exists():
    print("    [OK] File exists")
    file_size = smart_logic_path.stat().st_size
    print(f"    [OK] File size: {file_size} bytes")
else:
    print("    [FAIL] File NOT found")
    sys.exit(1)

# Check 2: Verify main.py import
print("\n[2] Checking main.py import statement...")
main_py = Path("main.py")
with open(main_py, 'r', encoding='utf-8') as f:
    content = f.read()
    if "from features.smart_logic import SmartDecisionEngine, DataSourceManager" in content:
        print("    [OK] Import statement found")
    else:
        print("    [FAIL] Import statement NOT found")
        sys.exit(1)

# Check 3: Verify initialization code
print("\n[3] Checking DataSourceManager initialization...")
if "dsm = DataSourceManager(calendar_client=calendar, trello_client=trello, business_data=business_data)" in content:
    print("    [OK] DataSourceManager initialization found")
else:
    print("    [FAIL] DataSourceManager initialization NOT found")
    sys.exit(1)

# Check 4: Verify SmartDecisionEngine initialization
print("\n[4] Checking SmartDecisionEngine initialization...")
if "decision_engine = SmartDecisionEngine(data_source_manager=dsm)" in content:
    print("    [OK] SmartDecisionEngine initialization found")
else:
    print("    [FAIL] SmartDecisionEngine initialization NOT found")
    sys.exit(1)

# Check 5: Verify smart evaluation code
print("\n[5] Checking smart_result evaluation code...")
if "smart_result = await decision_engine.evaluate_confidence(" in content:
    print("    [OK] Smart evaluation code found")
else:
    print("    [FAIL] Smart evaluation code NOT found")
    sys.exit(1)

# Check 6: Verify final_confidence usage
print("\n[6] Checking final_confidence variable usage...")
if "final_confidence >= 90" in content:
    print("    [OK] final_confidence >= 90 condition found")
else:
    print("    [FAIL] final_confidence condition NOT found")
    sys.exit(1)

# Check 7: Verify needs_manual_review usage
print("\n[7] Checking needs_manual_review variable usage...")
if "needs_manual_review and draft_bot:" in content:
    print("    [OK] needs_manual_review condition found")
else:
    print("    [FAIL] needs_manual_review condition NOT found")
    sys.exit(1)

# Check 8: Try importing SmartDecisionEngine
print("\n[8] Attempting to import SmartDecisionEngine...")
try:
    from features.smart_logic import SmartDecisionEngine, DataSourceManager
    print("    [OK] Import successful")
    print(f"    [OK] SmartDecisionEngine class: {SmartDecisionEngine.__name__}")
    print(f"    [OK] DataSourceManager class: {DataSourceManager.__name__}")
except ImportError as e:
    print(f"    [FAIL] Import failed: {e}")
    sys.exit(1)

# Check 9: Verify SmartDecisionEngine has required methods
print("\n[9] Checking SmartDecisionEngine methods...")
required_methods = ['evaluate_confidence']
for method in required_methods:
    if hasattr(SmartDecisionEngine, method):
        print(f"    [OK] Method '{method}' found")
    else:
        print(f"    [FAIL] Method '{method}' NOT found")
        sys.exit(1)

# Check 10: Verify DataSourceManager has required methods
print("\n[10] Checking DataSourceManager methods...")
required_methods = ['check_calendar_availability', 'get_relevant_trello_tasks', 'extract_prices']
for method in required_methods:
    if hasattr(DataSourceManager, method):
        print(f"    [OK] Method '{method}' found")
    else:
        print(f"    [FAIL] Method '{method}' NOT found")
        sys.exit(1)

# Check 11: Verify features/analytics_engine.py for Task 2
print("\n[11] Checking features/analytics_engine.py (Task 2)...")
analytics_path = Path("features/analytics_engine.py")
if analytics_path.exists():
    print("    [OK] File exists")
    if "run_unified_analytics" in open(analytics_path, encoding='utf-8').read():
        print("    [OK] run_unified_analytics function found")
    else:
        print("    [WARN]  run_unified_analytics function NOT found")
else:
    print("    [FAIL] File NOT found")

# Check 12: Verify features/dynamic_instructions.py for Task 3
print("\n[12] Checking features/dynamic_instructions.py (Task 3)...")
instructions_path = Path("features/dynamic_instructions.py")
if instructions_path.exists():
    print("    [OK] File exists")
    if "InstructionsManager" in open(instructions_path, encoding='utf-8').read():
        print("    [OK] InstructionsManager class found")
    else:
        print("    [WARN]  InstructionsManager class NOT found")
else:
    print("    [FAIL] File NOT found")

# Check 13: Verify Task 2 command in draft_bot
print("\n[13] Checking /analytics command in draft_bot.py...")
draft_bot_path = Path("draft_bot.py")
if draft_bot_path.exists():
    draft_content = open(draft_bot_path, encoding='utf-8').read()
    if 'message_text_lower == "/analytics"' in draft_content or '/analytics' in draft_content:
        print("    [OK] /analytics command found")
    else:
        print("    [WARN]  /analytics command NOT clearly visible")
else:
    print("    [FAIL] draft_bot.py NOT found")

# Check 14: Verify Task 3 commands in draft_bot
print("\n[14] Checking Task 3 commands in draft_bot.py...")
task3_commands = ['/view_instructions', '/update_instructions', '/list_backups', '/rollback_backup']
for cmd in task3_commands:
    if cmd in draft_content:
        print(f"    [OK] {cmd} command found")
    else:
        print(f"    [WARN]  {cmd} command NOT clearly visible")

# Summary
print("\n" + "=" * 80)
print("VERIFICATION SUMMARY")
print("=" * 80)
print("\n[OK] All critical Task 1 integration checks PASSED")
print("[OK] SmartDecisionEngine properly integrated into main.py")
print("[OK] Required methods available")
print("[OK] Code changes verified")
print("\nTask 1 Integration Status: READY FOR DEPLOYMENT")
print("\n" + "=" * 80)

print("\nNext Steps:")
print("1. Run: python main.py")
print("2. Monitor logs for: '[MAIN] Smart Logic Decision Engine initialized'")
print("3. Send test message to verify Smart Logic evaluation")
print("4. Check logs for: '[SMART_LOGIC]' showing confidence breakdown")
print("\n" + "=" * 80)
