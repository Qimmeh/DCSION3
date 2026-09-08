"""
Deterministic Battery & Recovery Engine
========================================
Calculates available user capacity, recovery debt, activity battery drain,
restoration from recovery activities, and the Capacity Load metric:

    CapacityLoad = Workload / max(Battery, BatteryFloor) * 100

Adheres strictly to the Ambient Workload Manager Technical Specification:
- Workload measures demand.
- Battery measures capacity.
- Sleep has a protected minimum (never sacrificed).
- Battery is clamped between 0 and 100.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, time

BATTERY_FLOOR = 10.0
BATTERY_CEILING = 100.0
DEBT_CAP_HOURS = 8.0
DEBT_DECAY_RATE = 0.85 # Daily carry-over retention factor
DEBT_PENALTY_PER_HOUR = 5.0 # Battery % lost per hour of accumulated debt

# Base drain rates in battery % points per 60 minutes
BASE_DRAIN_RATES = {
    "academic": 5.0,
    "work": 6.0,
    "social": 2.0,
    "health": 7.0,
    "errands": 3.5,
    "other": 4.0,
}

# Base recovery rates in battery % points per 60 minutes
BASE_RECOVERY_RATES = {
    "nap": 10.0,
    "rest": 8.0,
    "meal": 4.0,
    "walk": 6.0,
    "social_disconnect": 5.0,
    "outdoor_walk": 6.0,
    "disconnect": 6.0,
}

INTENSITY_DRAIN_MULTIPLIERS = {
    "low": 0.7,
    "medium": 1.0,
    "high": 1.35,
    "extreme": 1.7,
    "critical": 1.7,
}


def sleep_recovery_curve(actual_hours: float) -> float:
    """
    Normalized sleep recovery factor:
      6h ≈ 65%, 7h ≈ 80%, 8h ≈ 100%, 9h ≈ 105%, 10h ≈ 110%.
    Smoothly interpolates between anchor points and clamps.
    """
    if actual_hours <= 0:
        return 0.0

    anchors = [
        (0.0, 0.0),
        (3.0, 20.0),
        (4.0, 35.0),
        (5.0, 50.0),
        (6.0, 65.0),
        (7.0, 80.0),
        (8.0, 100.0),
        (9.0, 105.0),
        (10.0, 110.0),
    ]

    if actual_hours >= anchors[-1][0]:
        return anchors[-1][1]

    for i in range(len(anchors) - 1):
        x0, y0 = anchors[i]
        x1, y1 = anchors[i + 1]
        if x0 <= actual_hours <= x1:
            fraction = (actual_hours - x0) / (x1 - x0)
            return y0 + fraction * (y1 - y0)

    return 100.0


def calculate_recovery_debt(
    previous_debt: float,
    target_sleep: float,
    actual_sleep: float,
    additional_recovery_hours: float = 0.0,
) -> Dict[str, float]:
    """
    Calculates sleep deficit, recovery debt repayment, and updated recovery debt:
      SleepDeficit = max(0, TargetSleep - ActualSleep)
      RecoveryApplied = max(0, ActualSleep - TargetSleep) + additional_recovery
      RecoveryDebt = clamp(previous_debt * decay + SleepDeficit - RecoveryApplied, 0, DebtCap)
    """
    target_sleep = target_sleep if target_sleep is not None else 8.0
    actual_sleep = actual_sleep if actual_sleep is not None else target_sleep
    previous_debt = previous_debt if previous_debt is not None else 0.0
    additional_recovery_hours = additional_recovery_hours if additional_recovery_hours is not None else 0.0

    sleep_deficit = max(0.0, target_sleep - actual_sleep)
    sleep_surplus = max(0.0, actual_sleep - target_sleep)
    total_recovery_applied = sleep_surplus + additional_recovery_hours

    carried_debt = max(0.0, previous_debt) * DEBT_DECAY_RATE
    net_debt = carried_debt + sleep_deficit - total_recovery_applied
    updated_debt = max(0.0, min(DEBT_CAP_HOURS, net_debt))

    return {
        "sleep_deficit": round(sleep_deficit, 2),
        "recovery_applied": round(total_recovery_applied, 2),
        "updated_debt": round(updated_debt, 2),
    }


def calculate_starting_battery(
    actual_sleep: float,
    target_sleep: float = 8.0,
    recovery_debt: float = 0.0,
) -> float:
    """
    Calculates StartBattery (at the beginning of the usable day) based on sleep duration
    and carried recovery debt.
    """
    actual_sleep = actual_sleep if actual_sleep is not None else 8.0
    target_sleep = target_sleep if target_sleep is not None else 8.0
    recovery_debt = recovery_debt if recovery_debt is not None else 0.0

    raw_recovery = sleep_recovery_curve(actual_sleep)
    debt_penalty = recovery_debt * DEBT_PENALTY_PER_HOUR
    start_battery = raw_recovery - debt_penalty
    return max(10.0, min(BATTERY_CEILING, round(start_battery, 1)))


def calculate_activity_battery_drain(
    category: Optional[str],
    duration_minutes: Optional[int],
    intensity: Optional[str] = "Medium",
    continuous_minutes: Optional[int] = 60,
    start_time: Optional[datetime] = None,
) -> float:
    """
    Calculates battery consumed by an active task:
      BatteryDrain = BaseDrain * DurationMult * IntensityMult * ContinuityMod * TimingMod
    """
    cat_str = (category or "Other").lower()
    base_rate = BASE_DRAIN_RATES.get(cat_str, 4.0)
    dur_mins = max(1, duration_minutes or 60)
    duration_mult = max(0.1, dur_mins / 60.0)

    int_str = (intensity or "Medium").lower()
    intensity_mult = INTENSITY_DRAIN_MULTIPLIERS.get(int_str, 1.0)

    cont_mins = max(dur_mins, continuous_minutes or dur_mins)
    continuity_mod = 1.0
    if cont_mins > 180:
        continuity_mod = 1.30
    elif cont_mins > 120:
        continuity_mod = 1.15

    # Timing modifier (late night work drains more battery)
    timing_mod = 1.0
    if start_time:
        hour = start_time.hour
        if hour >= 22 or hour < 6:
            timing_mod = 1.25
        elif hour >= 20:
            timing_mod = 1.10

    drain = base_rate * duration_mult * intensity_mult * continuity_mod * timing_mod
    return round(drain, 2)


def calculate_recovery_restoration(
    recovery_type: Optional[str],
    duration_minutes: Optional[int],
) -> float:
    """
    Calculates capacity restored by recovery events (naps, rest, meals, walks).
    """
    rtype = (recovery_type or "rest").lower()
    base_rate = BASE_RECOVERY_RATES.get(rtype, 6.0)
    dur_mins = max(1, duration_minutes or 60)
    hours = max(0.1, dur_mins / 60.0)

    restoration = base_rate * hours

    # Specific daily caps per recovery event
    if rtype == "nap":
        restoration = min(15.0, restoration) # single nap cap
    elif rtype == "rest":
        restoration = min(12.0, restoration)
    elif rtype == "meal":
        restoration = min(6.0, restoration)

    return round(restoration, 2)


def evaluate_battery_state(battery_score: float) -> str:
    """
    Maps a battery score to a UX state label:
      80-100%: healthy
      60-79%: reduced
      40-59%: low
      20-39%: very_low
      0-19%: critical
    """
    score = float(battery_score if battery_score is not None else 100.0)
    if score >= 80.0:
        return "healthy"
    elif score >= 60.0:
        return "reduced"
    elif score >= 40.0:
        return "low"
    elif score >= 20.0:
        return "very_low"
    return "critical"


def calculate_capacity_load(workload_score: float, battery_score: float) -> float:
    """
    CapacityLoad = Workload / max(Battery, BatteryFloor) * 100
    Separates demand from capacity.
    Example: Workload 82%, Battery 65% -> 126.15% Capacity Load.
    """
    w_score = max(0.0, float(workload_score if workload_score is not None else 0.0))
    b_score = float(battery_score if battery_score is not None else 100.0)
    effective_battery = max(BATTERY_FLOOR, b_score)
    load = (w_score / effective_battery) * 100.0
    return round(load, 1)


def compute_daily_battery_projection(
    start_battery: float,
    activities: List[Dict[str, Any]],
    recovery_debt: float = 0.0,
    workload_score: float = 0.0,
) -> Dict[str, Any]:
    """
    Deterministic calculation of a day's battery trajectory:
      StartBattery -> activities drain / restore -> CurrentBattery & ProjectedBattery -> CapacityLoad.
    """
    total_drain = 0.0
    total_recovery = 0.0
    drain_details = []
    recovery_details = []

    for act in activities:
        rec_type = act.get("recovery_type")
        category = act.get("category") or "Other"
        duration = int(act.get("duration_minutes") or 60)
        intensity = act.get("intensity") or "Medium"
        continuous = int(act.get("continuous_minutes") or duration)
        start_time = act.get("start_time")
        if isinstance(start_time, str):
            try:
                start_time = datetime.fromisoformat(start_time)
            except Exception:
                start_time = None

        if rec_type:
            restore_pts = calculate_recovery_restoration(rec_type, duration)
            total_recovery += restore_pts
            recovery_details.append({
                "activity_id": act.get("id"),
                "title": act.get("title"),
                "recovery_type": rec_type,
                "duration_minutes": duration,
                "restored_points": restore_pts,
            })
        else:
            drain_pts = calculate_activity_battery_drain(
                category=category,
                duration_minutes=duration,
                intensity=intensity,
                continuous_minutes=continuous,
                start_time=start_time,
            )
            total_drain += drain_pts
            drain_details.append({
                "activity_id": act.get("id"),
                "title": act.get("title"),
                "category": category,
                "duration_minutes": duration,
                "drain_points": drain_pts,
            })

    # Net battery calculation
    current_battery = max(0.0, min(BATTERY_CEILING, start_battery - total_drain + total_recovery))
    current_battery = round(current_battery, 1)
    capacity_load = calculate_capacity_load(workload_score, current_battery)
    battery_state = evaluate_battery_state(current_battery)

    return {
        "start_battery": start_battery,
        "total_drain": round(total_drain, 1),
        "total_recovery": round(total_recovery, 1),
        "current_battery": current_battery,
        "projected_battery": current_battery,
        "recovery_debt": round(recovery_debt, 2),
        "capacity_load": capacity_load,
        "battery_state": battery_state,
        "drain_breakdown": drain_details,
        "recovery_breakdown": recovery_details,
    }
