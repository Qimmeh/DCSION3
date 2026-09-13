"""
Recovery Windows & Protocol API Endpoints
========================================
GET  /api/v1/recovery/windows
POST /api/v1/recovery/protect
"""
from datetime import datetime, timedelta
from flask import jsonify, request, g
from app.api import api_bp, require_user
from app.extensions import db
from app.models import RecoveryWindow


@api_bp.route("/recovery/windows", methods=["GET"])
@require_user
def list_recovery_windows():
    """
    Section 25 - Returns protected recovery blocks for the current user.
    """
    user = g.current_api_user
    windows = RecoveryWindow.query.filter_by(user_id=user.id).order_by(RecoveryWindow.start_time.asc()).all()
    return jsonify({
        "status": "success",
        "count": len(windows),
        "recovery_windows": [w.to_dict() for w in windows]
    })


@api_bp.route("/recovery/protect", methods=["POST"])
@require_user
def protect_recovery_window():
    """
    Creates a protected recovery block where non-critical notifications are suppressed
    and the scheduler refuses to clobber the time.
    Payload:
    {
      "start_time": "2026-09-07T18:00:00",
      "duration_minutes": 90,
      "recovery_type": "rest",
      "recommended_actions": ["Get food outside", "Take a short walk"]
    }
    """
    user = g.current_api_user
    data = request.get_json() or {}

    start_str = data.get("start_time")
    duration_mins = int(data.get("duration_minutes", 60))
    start_time = datetime.fromisoformat(start_str) if start_str else datetime.utcnow()
    end_time = start_time + timedelta(minutes=duration_mins)

    window = RecoveryWindow(
        user_id=user.id,
        start_time=start_time,
        end_time=end_time,
        duration_minutes=duration_mins,
        recovery_type=data.get("recovery_type", "rest"),
        is_protected=True,
        suppress_notifications=bool(data.get("suppress_notifications", True)),
        recommended_actions=data.get("recommended_actions", ["Get food outside", "Take a walk", "Fully disconnect"])
    )
    db.session.add(window)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Protected recovery window established.",
        "recovery_window": window.to_dict()
    }), 201
