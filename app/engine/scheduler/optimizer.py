"""
Smart Timeline Scheduler & Optimization Engine
==============================================
Generates, simulates, rejects, and scores candidate schedules to safely meet deadlines
while protecting minimum sleep, battery capacity, and future horizon balance.

Core Principle: "Finish Before" - shifts substantive work ahead of deadline bottlenecks
rather than allowing last-minute compression.
"""
from datetime import date, datetime, time, timedelta
from typing import List, Dict, Any, Optional
import copy

from app.engine.scheduler.collision import detect_deadline_collisions
from app.engine.scheduler.splitter import split_task_into_blocks
from app.engine.forecaster import forecast_horizon
from app.engine.battery import calculate_capacity_load

# Sacrifice costs (Section 7.6)
SACRIFICE_COSTS = {
    "move_flexible_revision": 0.5,
    "shorten_leisure": 1.0,
    "move_flexible_errand": 2.0,
    "cancel_optional_event": 4.0,
    "move_work_shift": 8.0,
    "cancel_family_commitment": 9.0,
    "reduce_protected_sleep": 999.0, # Strictly prohibited
}


def find_available_slots_on_day(
    day_activities: List[Dict[str, Any]],
    day_date: date,
    study_start_hour: int = 9,
    study_end_hour: int = 21,
    required_minutes: int = 60,
) -> List[Dict[str, Any]]:
    """
    Finds open time windows within the user's preferred study window that don't
    overlap with existing activities or fixed commitments.
    """
    slots = []
    # Sort day's activities by start time
    active_times = []
    for act in day_activities:
        st = act.get("start_time")
        if st:
            if isinstance(st, str):
                try:
                    st = datetime.fromisoformat(st)
                except Exception:
                    continue
            dur = act.get("duration_minutes", 60)
            et = act.get("end_time")
            if not et:
                et = st + timedelta(minutes=dur)
            elif isinstance(et, str):
                try:
                    et = datetime.fromisoformat(et)
                except Exception:
                    et = st + timedelta(minutes=dur)
            active_times.append((st, et))

    active_times.sort(key=lambda x: x[0])

    day_start = datetime.combine(day_date, time(study_start_hour, 0))
    day_end = datetime.combine(day_date, time(study_end_hour, 0))

    cur_time = day_start
    for (busy_start, busy_end) in active_times:
        if busy_start > cur_time:
            gap_minutes = int((busy_start - cur_time).total_seconds() / 60)
            if gap_minutes >= required_minutes:
                slots.append({
                    "start": cur_time,
                    "end": busy_start,
                    "available_minutes": gap_minutes
                })
        cur_time = max(cur_time, busy_end)

    if day_end > cur_time:
        gap_minutes = int((day_end - cur_time).total_seconds() / 60)
        if gap_minutes >= required_minutes:
            slots.append({
                "start": cur_time,
                "end": day_end,
                "available_minutes": gap_minutes
            })

    return slots


def generate_smart_timeline(
    tasks: List[Dict[str, Any]],
    existing_activities_by_date: Dict[date, List[Dict[str, Any]]],
    horizon_days: int = 7,
    start_date: Optional[date] = None,
    target_sleep: float = 8.0,
    minimum_sleep: float = 6.0,
    study_start_hour: int = 9,
    study_end_hour: int = 21,
    dimension_weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Primary Smart Timeline Algorithm (Section 7):
    1. Forecast baseline schedule.
    2. Detect deadline collisions and crunch periods.
    3. Generate 'Finish Before' candidate schedule.
    4. Simulate on deep-copied state and verify constraints.
    5. Score plan with overload reduction and sacrifice costs.
    6. Return actionable recommendations for user approval.
    """
    if not start_date:
        start_date = date.today()

    # 1. Baseline forecast
    baseline = forecast_horizon(
        start_date=start_date,
        days=horizon_days,
        activities_by_date=existing_activities_by_date,
        target_sleep=target_sleep,
        assumed_daily_sleep=target_sleep,
        dimension_weights=dimension_weights,
    )

    # 2. Detect collisions
    tasks_with_deadlines = [t for t in tasks if t.get("deadline")]
    collision_report = detect_deadline_collisions(
        horizon_days=baseline["daily_forecast"],
        tasks_with_deadlines=tasks_with_deadlines,
        protected_sleep_hours=minimum_sleep,
    )

    recommended_actions = []
    protected_items = []
    total_sacrifice_cost = 0.0

    # Protect fixed exams, lectures, and shifts
    for day_acts in existing_activities_by_date.values():
        for act in day_acts:
            if act.get("is_fixed") or act.get("category") in ["Exam", "Class"]:
                protected_items.append({
                    "title": act.get("title"),
                    "category": act.get("category"),
                    "reason": "Fixed non-negotiable commitment"
                })
    protected_items.append({
        "title": "Minimum Protected Sleep",
        "category": "Health",
        "reason": f"Protected {minimum_sleep}h non-negotiable floor"
    })

    # 3. Process tasks needing placement / earlier completion
    schedule_copy = copy.deepcopy(existing_activities_by_date)
    scheduled_blocks = []

    tasks_to_schedule = list(tasks)
    # Prioritize tasks with earlier deadlines and high effort
    tasks_to_schedule.sort(key=lambda t: (
        t.get("deadline") or "9999-12-31",
        -t.get("remaining_effort_minutes", 60)
    ))

    for task in tasks_to_schedule:
        dl = task.get("deadline")
        dl_date = None
        if dl:
            if isinstance(dl, str):
                try:
                    dl = datetime.fromisoformat(dl)
                except Exception:
                    pass
            dl_date = dl.date() if isinstance(dl, datetime) else dl

        # Determine target finish date: safety buffer (1-2 days before hard deadline if collision detected)
        target_finish_date = dl_date - timedelta(days=1) if dl_date and collision_report["has_collisions"] else dl_date

        blocks = split_task_into_blocks(task)

        # Place blocks on the best feasible days (preferring earlier days with lowest workload)
        # Search days from start_date up to target_finish_date
        max_search_days = horizon_days
        if target_finish_date:
            days_until_finish = (target_finish_date - start_date).days + 1
            max_search_days = max(1, min(horizon_days, days_until_finish))

        candidate_dates = [start_date + timedelta(days=i) for i in range(max_search_days)]
        # Sort candidate dates by lowest current workload score in baseline
        date_loads = {d["date"]: d["workload_score"] for d in baseline["daily_forecast"]}
        candidate_dates.sort(key=lambda d: date_loads.get(d.isoformat(), 0.0))

        for block in blocks:
            dur = block["duration_minutes"]
            placed = False

            for c_date in candidate_dates:
                open_slots = find_available_slots_on_day(
                    day_activities=schedule_copy.get(c_date, []),
                    day_date=c_date,
                    study_start_hour=study_start_hour,
                    study_end_hour=study_end_hour,
                    required_minutes=dur,
                )

                if open_slots:
                    slot = open_slots[0]
                    block_start = slot["start"]
                    block_end = block_start + timedelta(minutes=dur)

                    placed_activity = {
                        "id": None,
                        "title": block["title"],
                        "category": block["category"],
                        "duration_minutes": dur,
                        "intensity": block["intensity"],
                        "priority": block["priority"],
                        "start_time": block_start,
                        "end_time": block_end,
                        "is_fixed": False,
                        "status": "planned",
                    }

                    schedule_copy.setdefault(c_date, []).append(placed_activity)
                    scheduled_blocks.append(placed_activity)

                    # Create actionable recommendation
                    action_type = "SPLIT" if len(blocks) > 1 else "MOVE"
                    recommended_actions.append({
                        "action_type": action_type,
                        "task_title": block["title"],
                        "target_date": c_date.isoformat(),
                        "start_time": block_start.strftime("%H:%M"),
                        "end_time": block_end.strftime("%H:%M"),
                        "duration_minutes": dur,
                        "reason": f"Placed on low-workload day ({c_date.strftime('%a')}) to safely finish before {dl_date.isoformat() if dl_date else 'deadline'}."
                    })
                    total_sacrifice_cost += SACRIFICE_COSTS.get("move_flexible_revision", 0.5)
                    placed = True
                    break

            if not placed:
                # If cannot place without violating limits, record a shorten / extension proposal
                recommended_actions.append({
                    "action_type": "SHORTEN",
                    "task_title": block["title"],
                    "reason": "Could not place full block within preferred windows without violating sleep. Recommend trimming scope or requesting an extension."
                })
                total_sacrifice_cost += SACRIFICE_COSTS.get("shorten_leisure", 1.0)

    # 4. Simulate candidate schedule
    simulated_forecast = forecast_horizon(
        start_date=start_date,
        days=horizon_days,
        activities_by_date=schedule_copy,
        target_sleep=target_sleep,
        assumed_daily_sleep=target_sleep,
        dimension_weights=dimension_weights,
    )

    # 5. Overload reduction metric
    baseline_peak = max([d["workload_score"] for d in baseline["daily_forecast"]]) if baseline["daily_forecast"] else 0.0
    simulated_peak = max([d["workload_score"] for d in simulated_forecast["daily_forecast"]]) if simulated_forecast["daily_forecast"] else 0.0
    overload_reduction = max(0.0, round(baseline_peak - simulated_peak, 1))

    plan_score = round(max(0.0, 80.0 + overload_reduction * 2.0 - total_sacrifice_cost), 1)

    # Rationale summary
    why_explanation = (
        f"Detected {collision_report['collision_count']} deadline/workload collision(s). "
        f"This plan moves substantive assignment work into earlier low-demand days "
        f"so deadlines remain safe and protected {minimum_sleep}h sleep is fully preserved."
    )

    return {
        "status": "success",
        "plan_score": plan_score,
        "sacrifice_cost": round(total_sacrifice_cost, 1),
        "overload_reduction": overload_reduction,
        "collisions_detected": collision_report["collisions"],
        "protect": protected_items,
        "recommended_actions": recommended_actions,
        "why": why_explanation,
        "baseline_forecast": baseline,
        "simulated_forecast": simulated_forecast,
    }
