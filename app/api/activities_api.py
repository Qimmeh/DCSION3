"""
Activities API Endpoints
========================
GET  /api/v1/activities
POST /api/v1/activities
POST /api/v1/activities/<id>/extend
POST /api/v1/activities/<id>/complete
"""
from datetime import datetime, date, timedelta
from flask import jsonify, request, g
from app.api import api_bp, require_user
from app.extensions import db
from app.models import Activity, WorkloadEvent
from app.engine import score_activity, get_default_stat_vector


@api_bp.route("/activities", methods=["GET"])
@require_user
def list_activities():
    """
    List user activities with optional ?date=YYYY-MM-DD or ?status=planned filter.
    """
    user = g.current_api_user
    query = Activity.query.filter_by(user_id=user.id)

    date_str = request.args.get("date")
    if date_str:
        try:
            target_date = date.fromisoformat(date_str)
            start_dt = datetime.combine(target_date, datetime.min.time())
            end_dt = datetime.combine(target_date, datetime.max.time())
            query = query.filter(Activity.start_time >= start_dt, Activity.start_time <= end_dt)
        except ValueError:
            return jsonify({"error": "Invalid date format, use YYYY-MM-DD"}), 400

    status = request.args.get("status")
    if status:
        query = query.filter_by(status=status)

    activities = query.order_by(Activity.start_time.asc()).all()
    return jsonify({
        "status": "success",
        "count": len(activities),
        "activities": [a.to_dict() for a in activities]
    })


@api_bp.route("/activities", methods=["POST"])
@require_user
def create_activity():
    """
    Create a new structured activity.
    Automatically assigns default 5D stat rates if omitted,
    calculates the workload contribution, and creates a WorkloadEvent record.
    """
    user = g.current_api_user
    data = request.get_json() or {}

    title = data.get("title")
    if not title:
        return jsonify({"error": "Title is required"}), 400

    category = data.get("category", "Academic")
    activity_type = data.get("activity_type")
    stat_vector = data.get("stat_vector")
    if not stat_vector:
        stat_vector = get_default_stat_vector(activity_type=activity_type, category=category)

    # Timing
    start_time_str = data.get("start_time")
    duration_minutes = int(data.get("duration_minutes", 60) or 60)

    if start_time_str:
        start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
    else:
        start_time = datetime.utcnow()

    end_time = start_time + timedelta(minutes=duration_minutes)

    deadline_str = data.get("deadline")
    deadline = None
    if deadline_str:
        try:
            deadline = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
        except Exception:
            deadline = None

    activity = Activity(
        user_id=user.id,
        title=title,
        description=data.get("description"),
        category=category,
        activity_type=activity_type,
        stat_vector=stat_vector,
        start_time=start_time,
        end_time=end_time,
        duration_minutes=duration_minutes,
        continuous_minutes=int(data.get("continuous_minutes", duration_minutes) or duration_minutes),
        intensity=data.get("intensity", "Medium"),
        priority=data.get("priority", "Medium"),
        is_fixed=bool(data.get("is_fixed", False)),
        deadline=deadline,
        estimated_effort_minutes=int(data.get("estimated_effort_minutes") or duration_minutes),
        remaining_effort_minutes=int(data.get("remaining_effort_minutes") or duration_minutes),
        minimum_block_minutes=int(data.get("minimum_block_minutes") or 30),
        maximum_block_minutes=int(data.get("maximum_block_minutes") or 180),
        splittable=bool(data.get("splittable", True)),
        flexibility=data.get("flexibility", "movable"),
        consequence_cost=float(data.get("consequence_cost", 2.0) or 2.0),
        preferred_windows=data.get("preferred_windows") or [],
        recovery_type=data.get("recovery_type"),
        status="planned"
    )
    db.session.add(activity)
    db.session.flush()

    # Calculate workload score
    scored = score_activity(activity)
    scores = scored["scores"]
    modifiers = scored["modifiers"]

    event = WorkloadEvent(
        activity_id=activity.id,
        user_id=user.id,
        date=start_time.date(),
        academic_raw=scores["academic"]["raw"],
        academic_display=scores["academic"]["display"],
        work_raw=scores["work"]["raw"],
        work_display=scores["work"]["display"],
        social_raw=scores["social"]["raw"],
        social_display=scores["social"]["display"],
        health_raw=scores["health"]["raw"],
        health_display=scores["health"]["display"],
        errands_raw=scores["errands"]["raw"],
        errands_display=scores["errands"]["display"],
        duration_multiplier=modifiers["duration"],
        intensity_multiplier=modifiers["intensity"],
        continuity_modifier=modifiers["continuity"],
        timing_modifier=modifiers["timing"],
        is_recovery=scored["is_recovery"]
    )
    db.session.add(event)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Activity created and scored successfully",
        "activity": activity.to_dict(),
        "workload_score": scored
    }), 201


@api_bp.route("/activities/<int:activity_id>/extend", methods=["POST"])
@require_user
def extend_activity(activity_id):
    """
    Section 23 - Assumed-Complete quick action:
    Extend task by 15 or 30 minutes and re-score load.
    Payload: {"minutes": 15} or {"minutes": 30}
    """
    user = g.current_api_user
    activity = Activity.query.filter_by(id=activity_id, user_id=user.id).first_or_404()

    data = request.get_json() or {}
    extra_minutes = int(data.get("minutes", 15))

    activity.duration_minutes = (activity.duration_minutes or 60) + extra_minutes
    activity.continuous_minutes = (activity.continuous_minutes or 60) + extra_minutes
    if activity.end_time:
        activity.end_time = activity.end_time + timedelta(minutes=extra_minutes)
    activity.status = "extended"

    # Recalculate score
    scored = score_activity(activity)
    scores = scored["scores"]

    # Update corresponding WorkloadEvent
    event = WorkloadEvent.query.filter_by(activity_id=activity.id).first()
    if event:
        event.academic_raw = scores["academic"]["raw"]
        event.academic_display = scores["academic"]["display"]
        event.work_raw = scores["work"]["raw"]
        event.work_display = scores["work"]["display"]
        event.health_raw = scores["health"]["raw"]
        event.health_display = scores["health"]["display"]

    db.session.commit()

    return jsonify({
        "status": "success",
        "message": f"Activity extended by {extra_minutes} minutes",
        "activity": activity.to_dict(),
        "new_score": scored
    })


@api_bp.route("/activities/<int:activity_id>/complete", methods=["POST"])
@require_user
def complete_activity(activity_id):
    """
    Marks an activity as completed.
    """
    user = g.current_api_user
    activity = Activity.query.filter_by(id=activity_id, user_id=user.id).first_or_404()

    activity.status = "completed"
    activity.completed_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Activity marked as completed",
        "activity": activity.to_dict()
    })
