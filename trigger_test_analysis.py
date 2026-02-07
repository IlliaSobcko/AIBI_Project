#!/usr/bin/env python3
"""
Quick script to trigger test analysis and see verbose debugging output.
This runs run_core_logic() once to process all messages with detailed logging.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Import main
from main import run_core_logic

async def main():
    print("=" * 80)
    print("MANUAL TEST TRIGGER - run_core_logic()")
    print("=" * 80)
    print("\nThis will process all messages with VERBOSE debugging output.")
    print("Watch the console for detailed logs showing:")
    print("  - Which chats are being processed")
    print("  - AI confidence scores")
    print("  - Smart Logic decisions")
    print("  - Draft generation")
    print("  - Message sending attempts")
    print("  - Telegram service status")
    print("\n" + "=" * 80 + "\n")

    result = await run_core_logic()
    print(f"\n{'=' * 80}")
    print(f"RESULT: {result}")
    print("=" * 80)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
