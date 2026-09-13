"""
Burnout Risk API Blueprint (/api/v1/burnout-risk)
=================================================
Provides endpoints for querying product-level sustained strain,
trend trajectories, and multi-factor diagnostic explanations.
"""
from datetime import date, datetime, timedelta
from flask import jsonify, g, request
from app.extensions import db
from app.api import api_bp, require_user
from app.models import Activity, BatterySnapshot, RecoveryRecord, Profile
from app.engine.burnout import compute_burnout_score
from app.engine.battery import (
    calculate_starting_battery,
    compute_daily_battery_projection,
)
from app.engine.scoring import score_activity
from app.engine.workload import calculate_daily_workload


@api_bp.route("/burnout-risk", methods=["GET"])
@require_user
def get_burnout_risk():
    """
    Returns the current burnout risk score, risk level, multi-day trend,
    and structured primary/secondary problem diagnostics.
    """
    user = g.current_api_user
    today = date.today()

    profile = Profile.query.filter_by(user_id=user.id).first()
    target_sleep = profile.target_sleep_hours if profile else 8.0
    weights = profile.dimension_weights if profile else None

    # 1. Fetch or compute today's battery snapshot
    today_snap = BatterySnapshot.query.filter_by(user_id=user.id, date=today).first()
    if today_snap:
        current_capacity_load = today_snap.capacity_load
        recovery_debt = today_snap.recovery_debt
    else:
        # Compute on the fly
        today_rec = RecoveryRecord.query.filter_by(user_id=user.id, date=today).first()
        actual_sleep = today_rec.actual_sleep_hours if today_rec else target_sleep
        recovery_debt = today_rec.recovery_debt_carried if today_rec else 0.0

        start_bat = calculate_starting_battery(actual_sleep, target_sleep, recovery_debt)
        start_dt = datetime.combine(today, datetime.min.time())
        end_dt = datetime.combine(today, datetime.max.time())
        today_acts = Activity.query.filter(
            Activity.user_id == user.id,
            Activity.start_time >= start_dt,
            Activity.start_time <= end_dt,
            Activity.status != 'cancelled'
        ).all()
        scored_list = [score_activity(a) for a in today_acts]
        workload_res = calculate_daily_workload(scored_list, today_acts, dimension_weights=weights)
        b_data = compute_daily_battery_projection(start_bat, [a.to_dict() for a in today_acts], recovery_debt, workload_res["overall_score"])
        current_capacity_load = b_data["capacity_load"]

    # 2. Fetch past 7 days capacity load history
    past_days = [today - timedelta(days=i) for i in range(1, 8)]
    past_snaps = BatterySnapshot.query.filter(
        BatterySnapshot.user_id == user.id,
        BatterySnapshot.date.in_(past_days)
    ).order_by(BatterySnapshot.date.asc()).all()
    capacity_history = [s.capacity_load for s in past_snaps]

    # 3. Fetch past recent sleep records
    recent_recs = RecoveryRecord.query.filter(
        RecoveryRecord.user_id == user.id,
        RecoveryRecord.date.in_(past_days)
    ).all()
    sleep_deficits = [r.sleep_deficit_hours for r in recent_recs]

    # 4. Project future 3-7 days capacity load
    future_capacity_loads = []
    for offset in range(1, 4):
        f_date = today + timedelta(days=offset)
        f_start = datetime.combine(f_date, datetime.min.time())
        f_end = datetime.combine(f_date, datetime.max.time())
        f_acts = Activity.query.filter(
            Activity.user_id == user.id,
            Activity.start_time >= f_start,
            Activity.start_time <= f_end,
            Activity.status != 'cancelled'
        ).all()
        if f_acts:
            scored_f = [score_activity(a) for a in f_acts]
            f_workload = calculate_daily_workload(scored_f, f_acts, dimension_weights=weights)["overall_score"]
            # Estimate assuming baseline battery
            f_battery = max(10.0, 100.0 - (len(f_acts) * 8.0))
            f_load = (f_workload / f_battery) * 100.0
            future_capacity_loads.append(round(f_load, 1))
        else:
            future_capacity_loads.append(30.0)

    # Compute comprehensive burnout score and diagnostics
    burnout_report = compute_burnout_score(
        current_capacity_load=current_capacity_load,
        recovery_debt_hours=recovery_debt,
        capacity_loads_history=capacity_history,
        recent_sleep_deficits=sleep_deficits,
        future_capacity_loads=future_capacity_loads,
    )

    return jsonify({
        "status": "success",
        "date": today.isoformat(),
        "report": burnout_report
    })
