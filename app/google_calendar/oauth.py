"""OAuth 2.0 helpers for Google Calendar."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import secrets
from typing import Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen


GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
CALENDAR_READONLY_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"


@dataclass(frozen=True)
class GoogleToken:
    access_token: str
    refresh_token: Optional[str]
    expires_at: datetime
    token_type: str = "Bearer"

    def is_expired(self, leeway_seconds: int = 60) -> bool:
        return datetime.now(timezone.utc) >= (
            self.expires_at - timedelta(seconds=leeway_seconds)
        )


class GoogleOAuthClient:
    """Creates Google consent URLs and exchanges or refreshes OAuth tokens."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scope: str = CALENDAR_READONLY_SCOPE,
    ):
        if not client_id or not client_secret or not redirect_uri:
            raise ValueError("Google OAuth client_id, client_secret, and redirect_uri are required")
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scope = scope

    def build_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": self.scope,
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "state": state,
        }
        return f"{GOOGLE_AUTHORIZE_URL}?{urlencode(params)}"

    def exchange_code(self, code: str) -> GoogleToken:
        if not code:
            raise ValueError("Authorization code is required")
        payload = self._post_token_request(
            {
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri,
            }
        )
        return self._token_from_response(payload)

    def refresh_access_token(self, refresh_token: str) -> GoogleToken:
        if not refresh_token:
            raise ValueError("Refresh token is required")
        payload = self._post_token_request(
            {
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
        )
        refreshed = self._token_from_response(payload)
        return GoogleToken(
            access_token=refreshed.access_token,
            refresh_token=refreshed.refresh_token or refresh_token,
            expires_at=refreshed.expires_at,
            token_type=refreshed.token_type,
        )

    def _post_token_request(self, values: dict) -> dict:
        body = urlencode(
            {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                **values,
            }
        ).encode("utf-8")
        request = Request(
            GOOGLE_TOKEN_URL,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if "access_token" not in payload:
            raise RuntimeError("Google token response did not contain an access token")
        return payload

    @staticmethod
    def _token_from_response(payload: dict) -> GoogleToken:
        expires_in = int(payload.get("expires_in", 3600))
        return GoogleToken(
            access_token=payload["access_token"],
            refresh_token=payload.get("refresh_token"),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
            token_type=payload.get("token_type", "Bearer"),
        )


def new_oauth_state() -> str:
    return secrets.token_urlsafe(32)
