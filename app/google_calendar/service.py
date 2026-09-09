"""Google Calendar API client and timetable normalization."""

from datetime import date, datetime, time, timedelta, timezone
import json
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from app.google_calendar.oauth import GoogleOAuthClient
from app.google_calendar.store import InMemoryCalendarStore


CALENDAR_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


class GoogleCalendarService:
    def __init__(self, oauth_client: GoogleOAuthClient, store: InMemoryCalendarStore):
        self.oauth_client = oauth_client
        self.store = store

    def get_access_token(self, user_id: int) -> str:
        token = self.store.get_token(user_id)
        if not token:
            raise LookupError("Google Calendar is not connected")
        if token.is_expired():
            if not token.refresh_token:
                raise RuntimeError("Google access token expired and no refresh token is available")
            token = self.oauth_client.refresh_access_token(token.refresh_token)
            self.store.save_token(user_id, token)
        return token.access_token

    def fetch_timetable(
        self,
        user_id: int,
        start: date,
        end: date,
        calendar_id: str = "primary",
    ) -> list[dict]:
        if end < start:
            raise ValueError("The timetable end date must not be before the start date")
        access_token = self.get_access_token(user_id)
        events = []
        page_token = None
        time_min = datetime.combine(start, time.min, tzinfo=timezone.utc)
        time_max = datetime.combine(end + timedelta(days=1), time.min, tzinfo=timezone.utc)

        while True:
            params = {
                "singleEvents": "true",
                "orderBy": "startTime",
                "timeMin": time_min.isoformat().replace("+00:00", "Z"),
                "timeMax": time_max.isoformat().replace("+00:00", "Z"),
                "maxResults": "2500",
            }
            if page_token:
                params["pageToken"] = page_token
            encoded_calendar_id = quote(calendar_id, safe="")
            url = (
                "https://www.googleapis.com/calendar/v3/calendars/"
                f"{encoded_calendar_id}/events?{urlencode(params)}"
            )
            payload = self._get_json(url, access_token)
            events.extend(self._normalize_event(event) for event in payload.get("items", []))
            page_token = payload.get("nextPageToken")
            if not page_token:
                break

        return events

    @staticmethod
    def _get_json(url: str, access_token: str) -> dict:
        request = Request(url, headers={"Authorization": f"Bearer {access_token}"})
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _normalize_event(event: dict) -> dict:
        start = event.get("start", {})
        end = event.get("end", {})
        return {
            "id": event.get("id"),
            "title": event.get("summary", ""),
            "description": event.get("description"),
            "location": event.get("location"),
            "start": start.get("dateTime") or start.get("date"),
            "end": end.get("dateTime") or end.get("date"),
            "all_day": bool(start.get("date")),
            "status": event.get("status"),
            "html_link": event.get("htmlLink"),
        }
