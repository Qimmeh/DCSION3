"""
Core Activity Scoring Engine
============================
Evaluates structured activity attributes and calculates both raw and display
workload contribution scores for all 5 dimensions.
"""
from typing import Dict, Any
from app.engine.taxonomy import FIVE_STATS, get_default_stat_vector
from app.engine.multipliers import (
    duration_multiplier,
    continuity_multiplier,
    timing_multiplier,
    intensity_multiplier,
)

PER_ACTIVITY_CAP = 40.0
RECOVERY_MAX_CAP = -40.0


def score_activity(
    activity_dict_or_obj: Any,
    personal_context_modifier: float = 1.0,
    per_activity_cap: float = PER_ACTIVITY_CAP,
) -> Dict[str, Any]:
    """
    Section 12 - Core deterministic scoring function.

    Computes:
      Raw Score = Base Rate * Duration Hours * DurationMult * IntensityMult * ContinuityMod * TimingMod * ContextMod
      Display Score = min(Raw Score, Cap) (or max(Raw Score, -Cap) for recovery)
    """
    # Extract attributes safely whether input is a dict or SQLAlchemy model
    if isinstance(activity_dict_or_obj, dict):
        d = activity_dict_or_obj
        stat_vector = d.get("stat_vector")
        activity_type = d.get("activity_type")
        category = d.get("category")
        duration_minutes = d.get("duration_minutes", 60)
        continuous_minutes = d.get("continuous_minutes", duration_minutes)
        start_time = d.get("start_time")
        intensity = d.get("intensity", "Medium")
        recovery_type = d.get("recovery_type")
    else:
        obj = activity_dict_or_obj
        stat_vector = getattr(obj, "stat_vector", None)
        activity_type = getattr(obj, "activity_type", None)
        category = getattr(obj, "category", None)
        duration_minutes = getattr(obj, "duration_minutes", 60) or 60
        continuous_minutes = getattr(obj, "continuous_minutes", duration_minutes) or duration_minutes
        start_time = getattr(obj, "start_time", None)
        intensity = getattr(obj, "intensity", "Medium")
        recovery_type = getattr(obj, "recovery_type", None)

    # Resolve stat vector defaults if not explicitly provided
    if not stat_vector or not any(stat_vector.values()):
        stat_vector = get_default_stat_vector(activity_type=activity_type, category=category)

    hours = max(0.1, duration_minutes / 60.0)
    dur_mult = duration_multiplier(hours)
    cont_mult = continuity_multiplier(continuous_minutes)
    time_mult = timing_multiplier(start_time)
    int_mult = intensity_multiplier(intensity)
    ctx_mult = personal_context_modifier or 1.0

    scores = {}
    is_recovery = bool(recovery_type)

    for stat in FIVE_STATS:
        base_rate = float(stat_vector.get(stat, 0.0))

        # Positive workload contribution
        if base_rate > 0.0:
            raw = base_rate * hours * dur_mult * cont_mult * time_mult * int_mult * ctx_mult
            display = min(raw, per_activity_cap)
        # Negative workload contribution (Recovery)
        elif base_rate < 0.0:
            # Recovery doesn't multiply fatigue; it restores capacity
            raw = base_rate * hours * dur_mult
            display = max(raw, RECOVERY_MAX_CAP)
            is_recovery = True
        else:
            raw = 0.0
            display = 0.0

        scores[stat] = {
            "raw": round(raw, 2),
            "display": round(display, 2),
        }

    return {
        "scores": scores,
        "modifiers": {
            "duration": dur_mult,
            "intensity": int_mult,
            "continuity": cont_mult,
            "timing": time_mult,
            "context": ctx_mult,
        },
        "is_recovery": is_recovery,
        "duration_hours": round(hours, 2),
    }
