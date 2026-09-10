"""Google Calendar OAuth and in-memory timetable endpoints."""

from datetime import date, datetime, timedelta, timezone
import os

from flask import current_app, g, jsonify, redirect, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.api import api_bp, require_user
from app.google_calendar import (
    GoogleCalendarService,
    GoogleOAuthClient,
    InMemoryCalendarStore,
)
from app.google_calendar.oauth import new_oauth_state


calendar_store = InMemoryCalendarStore()
MALAYSIA_TIMEZONE = timezone(timedelta(hours=8))


def _oauth_client() -> GoogleOAuthClient:
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI")
    if not redirect_uri:
        try:
            from flask import has_request_context, request
            if has_request_context():
                redirect_uri = request.host_url.rstrip("/") + "/api/v1/calendar/oauth/callback"
        except Exception:
            pass
    if not redirect_uri:
        redirect_uri = "http://localhost:5000/api/v1/calendar/oauth/callback"

    return GoogleOAuthClient(
        client_id=os.environ.get("GOOGLE_CLIENT_ID", ""),
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", ""),
        redirect_uri=redirect_uri,
        scope=os.environ.get(
            "GOOGLE_CALENDAR_SCOPE",
            "https://www.googleapis.com/auth/calendar.readonly",
        ),
    )


def _calendar_service() -> GoogleCalendarService:
    return GoogleCalendarService(_oauth_client(), calendar_store)


def _oauth_state_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="google-calendar-oauth")


@api_bp.route("/calendar/oauth/start", methods=["GET"])
@require_user
def calendar_oauth_start():
    state = _oauth_state_serializer().dumps({
        "nonce": new_oauth_state(),
        "user_id": g.current_api_user.id,
    })
    try:
        authorization_url = _oauth_client().build_authorization_url(state)
    except ValueError as error:
        return jsonify({"error": "Google OAuth is not configured", "message": str(error)}), 503
    return redirect(authorization_url)


@api_bp.route("/calendar/oauth/callback", methods=["GET"])
def calendar_oauth_callback():
    state = request.args.get("state", "")
    try:
        state_data = _oauth_state_serializer().loads(state, max_age=600)
    except (BadSignature, SignatureExpired):
        return jsonify({"error": "Invalid or expired OAuth state"}), 400
    user_id = state_data.get("user_id")
    if not user_id:
        return jsonify({"error": "Invalid OAuth state payload"}), 400
    if request.args.get("error"):
        return jsonify({"error": request.args["error"]}), 400

    try:
        token = _oauth_client().exchange_code(request.args.get("code", ""))
        calendar_store.save_token(user_id, token)
    except (ValueError, RuntimeError, OSError) as error:
        return jsonify({"error": "Google OAuth failed", "message": str(error)}), 502

    return redirect("/timetable.html?calendar=connected")


@api_bp.route("/calendar/timetable", methods=["GET"])
@require_user
def get_calendar_timetable():
    today = datetime.now(MALAYSIA_TIMEZONE).date()
    try:
        start = date.fromisoformat(request.args.get("start", today.isoformat()))
        end = date.fromisoformat(
            request.args.get("end", (today + timedelta(days=7)).isoformat())
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    try:
        events = _calendar_service().fetch_timetable(
            g.current_api_user.id,
            start,
            end,
            request.args.get("calendar_id", "primary"),
        )
    except LookupError as error:
        return jsonify({"error": str(error)}), 401
    except ValueError as error:
        return jsonify({"error": "Google OAuth is not configured", "message": str(error)}), 503
    except (RuntimeError, OSError) as error:
        return jsonify({"error": "Unable to fetch Google Calendar", "message": str(error)}), 502

    calendar_store.save_pending_timetable(g.current_api_user.id, events)
    return jsonify({"status": "success", "count": len(events), "timetable": events})


@api_bp.route("/calendar/timetable/confirm", methods=["POST"])
@require_user
def confirm_calendar_timetable():
    if not calendar_store.confirm_pending_timetable(g.current_api_user.id):
        return jsonify({"error": "No pending timetable preview"}), 409
    return jsonify({"status": "confirmed"})


@api_bp.route("/calendar/timetable/pending", methods=["DELETE"])
@require_user
def discard_calendar_timetable():
    calendar_store.discard_pending_timetable(g.current_api_user.id)
    return jsonify({"status": "discarded"})


@api_bp.route("/calendar/timetable/memory", methods=["GET"])
@require_user
def get_cached_calendar_timetable():
    return jsonify({
        "status": "success",
        "count": len(calendar_store.get_timetable(g.current_api_user.id)),
        "timetable": calendar_store.get_timetable(g.current_api_user.id),
    })


@api_bp.route("/calendar/disconnect", methods=["POST"])
@require_user
def disconnect_calendar():
    calendar_store.remove(g.current_api_user.id)
    return jsonify({"status": "disconnected"})
