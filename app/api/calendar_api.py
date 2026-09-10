"""Google Calendar OAuth and in-memory timetable endpoints."""

from datetime import date, timedelta
import os

from flask import g, jsonify, redirect, request, session

from app.api import api_bp, require_user
from app.google_calendar import (
    GoogleCalendarService,
    GoogleOAuthClient,
    InMemoryCalendarStore,
)
from app.google_calendar.oauth import new_oauth_state


calendar_store = InMemoryCalendarStore()


def _oauth_client() -> GoogleOAuthClient:
    return GoogleOAuthClient(
        client_id=os.environ.get("GOOGLE_CLIENT_ID", ""),
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", ""),
        redirect_uri=os.environ.get(
            "GOOGLE_REDIRECT_URI",
            "http://localhost:5000/api/v1/calendar/oauth/callback",
        ),
        scope=os.environ.get(
            "GOOGLE_CALENDAR_SCOPE",
            "https://www.googleapis.com/auth/calendar.readonly",
        ),
    )


def _calendar_service() -> GoogleCalendarService:
    return GoogleCalendarService(_oauth_client(), calendar_store)


@api_bp.route("/calendar/oauth/start", methods=["GET"])
@require_user
def calendar_oauth_start():
    state = new_oauth_state()
    session["google_calendar_oauth_state"] = state
    session["google_calendar_oauth_user_id"] = g.current_api_user.id
    try:
        authorization_url = _oauth_client().build_authorization_url(state)
    except ValueError as error:
        session.pop("google_calendar_oauth_state", None)
        session.pop("google_calendar_oauth_user_id", None)
        return jsonify({"error": "Google OAuth is not configured", "message": str(error)}), 503
    return redirect(authorization_url)


@api_bp.route("/calendar/oauth/callback", methods=["GET"])
def calendar_oauth_callback():
    expected_state = session.pop("google_calendar_oauth_state", None)
    user_id = session.pop("google_calendar_oauth_user_id", None)
    print("State:", request.args.get("state"))
    print("Expected state", expected_state)
    if not expected_state or not user_id or request.args.get("state") != expected_state:
        return jsonify({"error": "Invalid or expired OAuth state"}), 400
    if request.args.get("error"):
        return jsonify({"error": request.args["error"]}), 400

    try:
        token = _oauth_client().exchange_code(request.args.get("code", ""))
        calendar_store.save_token(user_id, token)
    except (ValueError, RuntimeError, OSError) as error:
        return jsonify({"error": "Google OAuth failed", "message": str(error)}), 502

    return redirect("/?calendar=connected")


@api_bp.route("/calendar/timetable", methods=["GET"])
@require_user
def get_calendar_timetable():
    today = date.today()
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
