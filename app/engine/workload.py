"""
Daily & Weekly Workload Calculation Engine
==========================================
Computes:
  1. Five-dimensional normalized loads (Academic, Work, Social, Health, Errands)
  2. Acute Daily Workload with Peak Penalties and Compression Modifiers
  3. Rolling 7-Day Weekly Workload & Burn Rate Accumulation
"""
from datetime import date, timedelta
from typing import List, Dict, Any
from app.engine.taxonomy import FIVE_STATS

DEFAULT_WEIGHTS = {
    "academic": 0.25,
    "work": 0.20,
    "social": 0.15,
    "health": 0.25,
    "errands": 0.15,
}


def clamp(val: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
    return max(min_val, min(val, max_val))


def calculate_compression_penalty(total_occupied_minutes: int, waking_minutes: int = 960) -> float:
    """
    Section 16.2 - Schedule compression penalty.
    Measures loss of usable breathing room and fragmented transitions.
    waking_minutes defaults to 16 hours (960 min).
    """
    occupancy = total_occupied_minutes / max(waking_minutes, 1)

    if occupancy < 0.50:
        return 0.0
    elif occupancy <= 0.65:
        return 2.0
    elif occupancy <= 0.75:
        return 6.0
    elif occupancy <= 0.85:
        return 12.0
    elif occupancy <= 0.95:
        return 18.0
    else:
        return 25.0


def calculate_peak_penalty(activities: List[Any]) -> float:
    """
    Section 16.3 - Peak Load Penalty.
    Detects when multiple high-intensity or demanding blocks overlap or run back-to-back.
    """
    if not activities:
        return 0.0

    high_intensity_count = 0
    max_continuous_minutes = 0

    for act in activities:
        intensity = getattr(act, "intensity", "Medium") if not isinstance(act, dict) else act.get("intensity", "Medium")
        cont_mins = getattr(act, "continuous_minutes", 60) if not isinstance(act, dict) else act.get("continuous_minutes", 60)
        
        if intensity in ["High", "Extreme"]:
            high_intensity_count += 1
        if cont_mins > max_continuous_minutes:
            max_continuous_minutes = cont_mins

    penalty = 0.0
    if high_intensity_count >= 3:
        penalty += 10.0
    elif high_intensity_count >= 2:
        penalty += 5.0

    # Continuous block > 3 hours without breaks
    if max_continuous_minutes >= 240:
        penalty += 10.0
    elif max_continuous_minutes >= 180:
        penalty += 5.0

    return min(penalty, 20.0)


def calculate_recovery_deficit(activities: List[Any], recovery_windows: List[Any] = None) -> float:
    """
    Section 16.4 - Missing recovery windows, late-night strain, or missed meal/rest times.
    """
    late_night_count = 0
    total_recovery_minutes = 0

    for act in activities:
        st = getattr(act, "start_time", None) if not isinstance(act, dict) else act.get("start_time")
        rec_type = getattr(act, "recovery_type", None) if not isinstance(act, dict) else act.get("recovery_type")
        dur = getattr(act, "duration_minutes", 0) if not isinstance(act, dict) else act.get("duration_minutes", 0)

        if st and hasattr(st, "hour"):
            if st.hour >= 23 or st.hour < 5:
                late_night_count += 1

        if rec_type in ["sleep", "nap", "rest", "meal", "walk"]:
            total_recovery_minutes += (dur or 0)

    deficit = 0.0
    if late_night_count > 0:
        deficit += (late_night_count * 5.0)

    # Less than 6 hours of total recovery blocks
    if total_recovery_minutes < 360:
        deficit += 8.0

    return min(deficit, 20.0)


def calculate_daily_workload(
    activity_scores_list: List[Dict[str, Any]],
    activities: List[Any],
    dimension_weights: Dict[str, float] = None,
) -> Dict[str, Any]:
    """
    Section 16 - Computes daily workload state:
      Daily Workload = clamp(Weighted Dimension Pressure + Peak Penalty + Compression Penalty + Recovery Deficit, 0, 100)
    """
    weights = dimension_weights or DEFAULT_WEIGHTS

    # Sum display scores per stat
    stat_totals = {s: 0.0 for s in FIVE_STATS}
    total_occupied_minutes = 0

    for scored, act in zip(activity_scores_list, activities):
        scores = scored.get("scores", {})
        for s in FIVE_STATS:
            stat_totals[s] += scores.get(s, {}).get("display", 0.0)

        dur = getattr(act, "duration_minutes", 60) if not isinstance(act, dict) else act.get("duration_minutes", 60)
        # Exclude pure sleep from occupied waking time
        rec_type = getattr(act, "recovery_type", None) if not isinstance(act, dict) else act.get("recovery_type")
        if rec_type != "sleep":
            total_occupied_minutes += (dur or 0)

    # Normalize each dimension to 0 - 100 UX scale
    # Reference baseline: 80 raw points in a single dimension represents 100% saturation
    dimension_pressures = {}
    for s in FIVE_STATS:
        raw_val = stat_totals[s]
        # Allow negative for net recovery, clamp display
        dimension_pressures[s] = clamp(raw_val * (100.0 / 75.0), 0.0, 100.0)

    weighted_pressure = sum(
        dimension_pressures[s] * weights.get(s, 0.20) for s in FIVE_STATS
    )

    peak_penalty = calculate_peak_penalty(activities)
    compression_penalty = calculate_compression_penalty(total_occupied_minutes)
    recovery_deficit = calculate_recovery_deficit(activities)

    overall_score = clamp(
        weighted_pressure + peak_penalty + compression_penalty + recovery_deficit,
        0.0,
        100.0,
    )

    # Determine limiting factor
    limiting_factor = max(dimension_pressures, key=dimension_pressures.get)

    # Status level classification
    if overall_score < 70.0:
        status_level = "normal"
    elif overall_score < 85.0:
        status_level = "elevated"
    elif overall_score < 90.0:
        status_level = "high"
    else:
        status_level = "critical"

    return {
        "overall_score": round(overall_score, 1),
        "status_level": status_level,
        "limiting_factor": limiting_factor.capitalize(),
        "dimension_pressures": {k: round(v, 1) for k, v in dimension_pressures.items()},
        "weighted_pressure": round(weighted_pressure, 1),
        "peak_penalty": round(peak_penalty, 1),
        "compression_penalty": round(compression_penalty, 1),
        "recovery_deficit": round(recovery_deficit, 1),
        "total_occupied_minutes": total_occupied_minutes,
    }


def calculate_weekly_workload(daily_snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Section 17 - Rolling 7-day Weekly Workload & Burn Rate calculation:
      Weekly Workload = clamp(Rolling accumulated load + Sustained Overload Penalty - Recovery Credits, 0, 100)
    """
    if not daily_snapshots:
        return {
            "overall_score": 0.0,
            "burn_rate": 0.0,
            "status_level": "normal",
            "sustained_overload_days": 0,
            "weekly_trend": [],
        }

    scores = [s.get("overall_score", 0.0) for s in daily_snapshots]
    avg_score = sum(scores) / len(scores)

    # Count consecutive days >= 85%
    sustained_overload_days = sum(1 for sc in scores if sc >= 85.0)

    sustained_penalty = 0.0
    if sustained_overload_days >= 4:
        sustained_penalty = 12.0
    elif sustained_overload_days >= 2:
        sustained_penalty = 6.0

    weekly_score = clamp(avg_score + sustained_penalty, 0.0, 100.0)

    if weekly_score < 70.0:
        status_level = "normal"
    elif weekly_score < 85.0:
        status_level = "elevated"
    elif weekly_score < 90.0:
        status_level = "high"
    else:
        status_level = "critical"

    return {
        "overall_score": round(weekly_score, 1),
        "burn_rate": round(avg_score, 1),
        "status_level": status_level,
        "sustained_overload_days": sustained_overload_days,
        "weekly_trend": [round(s, 1) for s in scores],
    }
