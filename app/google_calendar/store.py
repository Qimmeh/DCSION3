"""Process-local storage used until calendar credentials get a database model."""

from threading import RLock
from typing import Optional

from app.google_calendar.oauth import GoogleToken


class InMemoryCalendarStore:
    def __init__(self):
        self._tokens = {}
        self._timetables = {}
        self._lock = RLock()

    def save_token(self, user_id: int, token: GoogleToken) -> None:
        with self._lock:
            self._tokens[str(user_id)] = token

    def get_token(self, user_id: int) -> Optional[GoogleToken]:
        with self._lock:
            return self._tokens.get(str(user_id))

    def save_timetable(self, user_id: int, timetable: list[dict]) -> None:
        with self._lock:
            self._timetables[str(user_id)] = timetable

    def get_timetable(self, user_id: int) -> list[dict]:
        with self._lock:
            return list(self._timetables.get(str(user_id), []))

    def remove(self, user_id: int) -> None:
        with self._lock:
            self._tokens.pop(str(user_id), None)
            self._timetables.pop(str(user_id), None)
