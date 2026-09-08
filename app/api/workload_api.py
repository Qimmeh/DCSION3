"""
Workload API Endpoints
======================
GET /api/v1/workload/today
GET /api/v1/workload/week
"""
from datetime import date, datetime, timedelta
from flask import jsonify, g, request
from app.api import api_bp, require_user
from app.extensions import db
from app.models import Activity, WorkloadSnapshot, WorkloadEvent, Profile
from app.engine import (
    score_activity,
    calculate_daily_workload,
    calculate_weekly_workload,
)


@api_bp.route("/workload/today", methods=["GET"])
@require_user
def get_workload_today():
    """
    Returns acute daily workload, 5 stat cards, peak load penalty,
    schedule compression, and limiting factor.
    """
    user = g.current_api_user
    target_date = date.today()

    # Query activities for today
    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())

    activities = Activity.query.filter(
        Activity.user_id == user.id,
        Activity.start_time >= start_dt,
        Activity.start_time <= end_dt,
        Activity.status != "cancelled"
    ).order_by(Activity.start_time.asc()).all()

    # User profile preferences
    profile = Profile.query.filter_by(user_id=user.id).first()
    weights = profile.dimension_weights if profile else None

    # Calculate scores on the fly
    scored_list = [score_activity(act) for act in activities]
    calc_result = calculate_daily_workload(scored_list, activities, dimension_weights=weights)

    # Persist or update today's snapshot for analytics
    snap = WorkloadSnapshot.query.filter_by(
        user_id=user.id, date=target_date, snapshot_type="daily"
    ).first()
    if not snap:
        snap = WorkloadSnapshot(user_id=user.id, date=target_date, snapshot_type="daily")
        db.session.add(snap)

    snap.academic_load = calc_result["dimension_pressures"]["academic"]
    snap.work_load = calc_result["dimension_pressures"]["work"]
    snap.social_load = calc_result["dimension_pressures"]["social"]
    snap.health_load = calc_result["dimension_pressures"]["health"]
    snap.errands_load = calc_result["dimension_pressures"]["errands"]
    snap.overall_score = calc_result["overall_score"]
    snap.peak_penalty = calc_result["peak_penalty"]
    snap.compression_penalty = calc_result["compression_penalty"]
    snap.recovery_deficit_penalty = calc_result["recovery_deficit"]
    snap.status_level = calc_result["status_level"]
    snap.limiting_factor = calc_result["limiting_factor"]
    db.session.commit()

    return jsonify({
        "status": "success",
        "date": target_date.isoformat(),
        "workload": calc_result,
        "activity_count": len(activities),
        "activities": [a.to_dict() for a in activities],
    })


@api_bp.route("/workload/week", methods=["GET"])
@require_user
def get_workload_week():
    """
    Returns rolling 7-day Weekly Workload, sustained overload penalties,
    burn rate status, and recent daily trend.
    """
    user = g.current_api_user
    today = date.today()
    seven_days_ago = today - timedelta(days=6)

    snapshots = WorkloadSnapshot.query.filter(
        WorkloadSnapshot.user_id == user.id,
        WorkloadSnapshot.date >= seven_days_ago,
        WorkloadSnapshot.date <= today,
        WorkloadSnapshot.snapshot_type == "daily"
    ).order_by(WorkloadSnapshot.date.asc()).all()

    daily_data = [s.to_dict() for s in snapshots]

    # If fewer than 7 days recorded, pad with neutral baseline
    if len(daily_data) < 7:
        pad_count = 7 - len(daily_data)
        baseline = daily_data[-1]["overall_score"] if daily_data else 30.0
        daily_data = [{"overall_score": baseline} for _ in range(pad_count)] + daily_data

    weekly_calc = calculate_weekly_workload(daily_data)

    return jsonify({
        "status": "success",
        "week_ending": today.isoformat(),
        "weekly_workload": weekly_calc,
    })


@api_bp.route("/workload/forecast", methods=["GET"])
@require_user
def get_workload_forecast():
    """
    Returns a forward 7 to 14 day lookahead horizon forecasting
    workload scores, battery drain, and capacity loads.
    """
    from collections import defaultdict
    from app.engine.forecaster import forecast_horizon

    user = g.current_api_user
    today = date.today()

    days_param = request.args.get("days", 7)
    try:
        days = int(days_param)
    except (TypeError, ValueError):
        days = 7
    days = max(1, min(days, 14))

    horizon_end = today + timedelta(days=days)
    start_dt = datetime.combine(today, datetime.min.time())
    end_dt = datetime.combine(horizon_end, datetime.max.time())

    activities = Activity.query.filter(
        Activity.user_id == user.id,
        Activity.start_time >= start_dt,
        Activity.start_time <= end_dt,
        Activity.status != "cancelled"
    ).order_by(Activity.start_time.asc()).all()

    # Group activities by date
    acts_by_date = defaultdict(list)
    for act in activities:
        if act.start_time:
            acts_by_date[act.start_time.date()].append(act.to_dict())

    profile = Profile.query.filter_by(user_id=user.id).first()
    target_sleep = profile.target_sleep_hours if profile else 8.0
    weights = profile.dimension_weights if profile else None

    # Get current battery snapshot for today if available
    today_snap = BatterySnapshot.query.filter_by(user_id=user.id, date=today).first()
    init_battery = today_snap.current_battery if today_snap else 85.0
    init_debt = today_snap.recovery_debt if today_snap else 0.0

    forecast = forecast_horizon(
        start_date=today,
        days=days,
        activities_by_date=acts_by_date,
        initial_battery=init_battery,
        initial_debt=init_debt,
        target_sleep=target_sleep,
        assumed_daily_sleep=target_sleep,
        dimension_weights=weights,
    )

    return jsonify({
        "status": "success",
        "forecast": forecast
    })

