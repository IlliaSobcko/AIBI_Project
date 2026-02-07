import os
import json
import traceback
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from pathlib import Path

SCOPES = ['https://www.googleapis.com/auth/calendar']

class GoogleCalendarClient:
    def __init__(self, credentials_file: str = "credentials.json"):
        self.credentials_file = credentials_file
        self.service = None
        self.creds = None

    def authenticate(self):
        """Authenticate using Service Account credentials from JSON file"""
        if not Path(self.credentials_file).exists():
            raise FileNotFoundError(
                f"File {self.credentials_file} not found. "
                "Please place your Google Service Account credentials.json in the project directory"
            )

        try:
            # Load Service Account credentials from JSON file
            self.creds = Credentials.from_service_account_file(
                self.credentials_file,
                scopes=SCOPES
            )

            # Build the Calendar API service
            self.service = build('calendar', 'v3', credentials=self.creds)

            print(f"[GOOGLE CALENDAR] Successfully authenticated using Service Account")
            print(f"[GOOGLE CALENDAR] Project: {self.creds.project_id}")
            print(f"[GOOGLE CALENDAR] Service Account Email: {self.creds.service_account_email}")

            return self.service

        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON in {self.credentials_file}")
            print(f"[ERROR] {type(e).__name__}: {e}")
            raise
        except KeyError as e:
            print(f"[ERROR] Missing required field in credentials.json: {e}")
            print(f"[ERROR] Make sure your credentials.json contains all required Service Account fields")
            raise
        except Exception as e:
            print(f"[ERROR] Authentication failed:")
            print(f"[ERROR] {type(e).__name__}: {e}")
            print(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
            raise

    def create_event(self, summary: str, description: str, start_time: datetime, duration_minutes: int = 30, calendar_id: str = 'primary'):
        """Create event in Google Calendar"""
        if not self.service:
            self.authenticate()

        try:
            end_time = start_time + timedelta(minutes=duration_minutes)

            event = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'Europe/Kiev',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'Europe/Kiev',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 10},
                    ],
                },
            }

            result = self.service.events().insert(calendarId=calendar_id, body=event).execute()
            print(f"[GOOGLE CALENDAR] Event created: {result.get('id')} - {summary}")
            return result

        except Exception as e:
            print(f"[ERROR] Failed to create calendar event:")
            print(f"[ERROR] {type(e).__name__}: {e}")
            print(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
            raise

    def create_reminder_from_report(self, chat_title: str, report: str, confidence: int, reminder_time: datetime):
        """Create calendar reminder from AI analysis report"""
        try:
            summary = f"[{confidence}%] Report Review: {chat_title}"
            description = f"AI Analysis Report:\n\n{report}"

            print(f"[GOOGLE CALENDAR] Creating reminder for: {chat_title}")
            return self.create_event(summary, description, reminder_time, duration_minutes=15)

        except Exception as e:
            print(f"[ERROR] Failed to create reminder:")
            print(f"[ERROR] {type(e).__name__}: {e}")
            print(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
            raise
