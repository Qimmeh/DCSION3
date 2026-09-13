"""
Battery & Recovery API Blueprint (/api/v1/battery)
===================================================
Provides endpoints for querying today's battery capacity, logging sleep sessions,
and evaluating capacity load relative to workload demand.
"""
from datetime import datetime, date, timedelta
from flask import jsonify, request, g
from app.extensions import db
from app.api import api_bp, require_user
from app.models import Activity, BatterySnapshot, RecoveryRecord, Profile, WorkloadSnapshot
from app.engine.battery import (
    calculate_starting_battery,
    calculate_recovery_debt,
    calculate_capacity_load,
    compute_daily_battery_projection,
    evaluate_battery_state,
)
from app.engine.workload import calculate_daily_workload


@api_bp.route("/battery/today", methods=["GET"])
@require_user
def get_battery_today():
    """
    Returns today's battery capacity, recovery debt, activity drains, and capacity load.
    """
    user = g.current_api_user
    today = date.today()

    # Get or create user profile for sleep targets
    profile = Profile.query.filter_by(user_id=user.id).first()
    target_sleep = profile.target_sleep_hours if profile else 8.0

    # Check yesterday's recovery record for carried debt
    yesterday = today - timedelta(days=1)
    prev_rec = RecoveryRecord.query.filter_by(user_id=user.id, date=yesterday).first()
    prev_debt = prev_rec.recovery_debt_carried if prev_rec else 0.0

    # Check today's sleep record
    today_rec = RecoveryRecord.query.filter_by(user_id=user.id, date=today).first()
    actual_sleep = today_rec.actual_sleep_hours if today_rec else target_sleep
    current_debt = today_rec.recovery_debt_carried if today_rec else prev_debt

    start_battery = calculate_starting_battery(
        actual_sleep=actual_sleep,
        target_sleep=target_sleep,
        recovery_debt=current_debt,
    )

    # Fetch today's activities
    start_dt = datetime.combine(today, datetime.min.time())
    end_dt = datetime.combine(today, datetime.max.time())
    activities = Activity.query.filter(
        Activity.user_id == user.id,
        Activity.start_time >= start_dt,
        Activity.start_time <= end_dt,
        Activity.status != 'cancelled'
    ).all()

    activity_dicts = [a.to_dict() for a in activities]

    # Calculate today's workload score
    from app.engine.scoring import score_activity
    scored_list = [score_activity(a) for a in activities]
    weights = profile.dimension_weights if profile else None
    workload_res = calculate_daily_workload(scored_list, activities, dimension_weights=weights)
    overall_workload = workload_res["overall_score"]

    # Compute battery projection
    battery_data = compute_daily_battery_projection(
        start_battery=start_battery,
        activities=activity_dicts,
        recovery_debt=current_debt,
        workload_score=overall_workload,
    )
    battery_data["workload_score"] = overall_workload

    # Upsert BatterySnapshot
    snapshot = BatterySnapshot.query.filter_by(user_id=user.id, date=today).first()
    if not snapshot:
        snapshot = BatterySnapshot(
            user_id=user.id,
            date=today,
        )
        db.session.add(snapshot)

    snapshot.start_battery = battery_data["start_battery"]
    snapshot.drain = battery_data["total_drain"]
    snapshot.recovery = battery_data["total_recovery"]
    snapshot.current_battery = battery_data["current_battery"]
    snapshot.projected_battery = battery_data["projected_battery"]
    snapshot.recovery_debt = battery_data["recovery_debt"]
    snapshot.capacity_load = battery_data["capacity_load"]
    snapshot.battery_state = battery_data["battery_state"]
    snapshot.details = {
        "workload_score": overall_workload,
        "drain_breakdown": battery_data["drain_breakdown"],
        "recovery_breakdown": battery_data["recovery_breakdown"],
    }
    db.session.commit()

    return jsonify({
        "status": "success",
        "date": today.isoformat(),
        "battery": battery_data
    })


@api_bp.route("/battery/log-sleep", methods=["POST"])
@require_user
def log_sleep():
    """
    Logs actual sleep duration and updates the recovery debt and starting battery.
    """
    user = g.current_api_user
    data = request.get_json() or {}

    log_date_str = data.get("date")
    target_date = date.fromisoformat(log_date_str) if log_date_str else date.today()

    actual_sleep = float(data.get("actual_sleep_hours", 8.0))
    naps_min = int(data.get("naps_minutes", 0))
    notes = data.get("notes", "")

    profile = Profile.query.filter_by(user_id=user.id).first()
    target_sleep = float(data.get("target_sleep_hours") or (profile.target_sleep_hours if profile else 8.0))

    # Carried debt from previous day
    prev_date = target_date - timedelta(days=1)
    prev_rec = RecoveryRecord.query.filter_by(user_id=user.id, date=prev_date).first()
    prev_debt = prev_rec.recovery_debt_carried if prev_rec else 0.0

    debt_info = calculate_recovery_debt(
        previous_debt=prev_debt,
        target_sleep=target_sleep,
        actual_sleep=actual_sleep,
        additional_recovery_hours=naps_min / 60.0
    )

    # Upsert RecoveryRecord
    record = RecoveryRecord.query.filter_by(user_id=user.id, date=target_date).first()
    if not record:
        record = RecoveryRecord(user_id=user.id, date=target_date)
        db.session.add(record)

    record.actual_sleep_hours = actual_sleep
    record.target_sleep_hours = target_sleep
    record.sleep_deficit_hours = debt_info["sleep_deficit"]
    record.recovery_debt_carried = debt_info["updated_debt"]
    record.naps_minutes = naps_min
    record.notes = notes
    db.session.commit()

    start_battery = calculate_starting_battery(
        actual_sleep=actual_sleep,
        target_sleep=target_sleep,
        recovery_debt=debt_info["updated_debt"],
    )

    return jsonify({
        "status": "success",
        "message": "Sleep and recovery logged successfully",
        "record": record.to_dict(),
        "start_battery": start_battery
    })
