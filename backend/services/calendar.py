import os
import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'credentials.json'

def get_calendar_service():
    """Authenticates and returns the Google Calendar service."""
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        return None
    
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=creds)
    return service

# For testing, we keep an in-memory calendar if credentials are not provided.
_DUMMY_EVENTS = []

def check_calendar_availability(time_min: str, time_max: str) -> dict:
    """Checks for free/busy times in the given window."""
    service = get_calendar_service()
    calendar_id = os.getenv('TARGET_CALENDAR_ID', 'primary')
    if service:
        # Actual Google Calendar API Call
        body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "items": [{"id": calendar_id}] # Use the target calendar
        }
        eventsResult = service.freebusy().query(body=body).execute()
        return eventsResult['calendars'][calendar_id]
    else:
        # Dummy behavior
        print(f"[DUMMY CALENDAR] Checking availability from {time_min} to {time_max}")
        # Always return free for dummy unless we explicitly mock conflicts
        return {"busy": []}

def schedule_meeting(summary: str, start_time: str, end_time: str) -> dict:
    """Creates a calendar event."""
    service = get_calendar_service()
    calendar_id = os.getenv('TARGET_CALENDAR_ID', 'primary')
    if service:
        event = {
            'summary': summary,
            'start': {'dateTime': start_time},
            'end': {'dateTime': end_time},
        }
        event_result = service.events().insert(calendarId=calendar_id, body=event).execute()
        return {"status": "success", "eventLink": event_result.get('htmlLink')}
    else:
        # Dummy behavior
        print(f"[DUMMY CALENDAR] Scheduled '{summary}' from {start_time} to {end_time}")
        _DUMMY_EVENTS.append({
            'summary': summary,
            'start': start_time,
            'end': end_time
        })
        return {"status": "success", "eventLink": "http://dummy.calendar.link"}

def find_reference_event(query: str) -> dict:
    """Searches for events matching a query to find reference times."""
    service = get_calendar_service()
    calendar_id = os.getenv('TARGET_CALENDAR_ID', 'primary')
    time_min = datetime.datetime.utcnow().isoformat() + 'Z'
    
    if service:
        events_result = service.events().list(
            calendarId=calendar_id, timeMin=time_min,
            maxResults=10, singleEvents=True,
            orderBy='startTime', q=query).execute()
        events = events_result.get('items', [])
        if events:
            return {"found": True, "event": events[0]}
        return {"found": False}
    else:
        # Dummy behavior
        print(f"[DUMMY CALENDAR] Searching for reference event: {query}")
        return {"found": False, "message": "Dummy calendar has no future reference events"}

def get_current_time() -> str:
    """Returns the current time with Day of Week so the LLM understands context and timezone."""
    now = datetime.datetime.now().astimezone()
    return f"{now.strftime('%A')}, {now.isoformat(timespec='seconds')}"
