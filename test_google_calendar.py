import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from calendar_client import GoogleCalendarClient


def test_google_calendar():
    """Test Google Calendar Service Account authentication and event creation"""

    credentials_file = "credentials.json"

    # Check if credentials file exists
    if not Path(credentials_file).exists():
        print("[ERROR] credentials.json not found!")
        print("[ERROR] Please place your Google Service Account JSON file in the project directory")
        print("[INFO] Service Account JSON should contain:")
        print("       - type: service_account")
        print("       - project_id")
        print("       - private_key")
        print("       - client_email")
        return

    print("[TEST] Starting Google Calendar authentication test...")
    print(f"[TEST] Using credentials file: {credentials_file}")

    try:
        # Initialize calendar client
        calendar = GoogleCalendarClient(credentials_file)

        # Authenticate
        print("\n[TEST] Authenticating with Google Calendar API...")
        service = calendar.authenticate()

        if service:
            print("[OK] Successfully authenticated!")

            # Test creating an event
            print("\n[TEST] Creating test event...")
            test_time = datetime.now() + timedelta(hours=2)

            event = calendar.create_event(
                summary="Test Event from AIBI",
                description="This is a test event created by the AIBI system",
                start_time=test_time,
                duration_minutes=30
            )

            if event:
                print(f"[OK] Test event created successfully!")
                print(f"[OK] Event ID: {event.get('id')}")
                print(f"[OK] Event link: {event.get('htmlLink')}")

        else:
            print("[ERROR] Authentication failed - service is None")

    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
    except Exception as e:
        print(f"[ERROR] Test failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_google_calendar()
