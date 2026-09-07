"""
Deterministic Multipliers & Modifiers
=====================================
Calculates non-linear fatigue, marathon continuity penalties,
late-night timing shifts, and relative intensity levels.
"""
from datetime import datetime, time


def duration_multiplier(hours: float) -> float:
    """
    Section 8 - Non-linear duration modifier.
    Compounds fatigue as duration increases.
    """
    if hours <= 0.25: # 0 - 15 min
        return 0.25
    elif hours <= 0.5: # 15 - 30 min
        return 0.45
    elif hours <= 1.0: # 30 - 60 min
        return 0.75
    elif hours <= 2.0: # 1 - 2 hours
        return 1.00
    elif hours <= 3.0: # 2 - 3 hours
        return 1.20
    elif hours <= 4.0: # 3 - 4 hours
        return 1.45
    elif hours <= 6.0: # 4 - 6 hours
        return 1.75
    elif hours <= 8.0: # 6 - 8 hours
        return 2.10
    else:              # 8 hours+
        return 2.50


def continuity_multiplier(continuous_minutes: int) -> float:
    """
    Section 9 - Continuous block modifier.
    Penalizes long uninterrupted cognitive or physical sprints without breaks.
    """
    hours = (continuous_minutes or 60) / 60.0
    if hours < 1.0:
        return 1.00
    elif hours <= 2.0:
        return 1.05
    elif hours <= 3.0:
        return 1.12
    elif hours <= 4.0:
        return 1.20
    elif hours <= 6.0:
        return 1.35
    else:
        return 1.50


def timing_multiplier(dt_or_time) -> float:
    """
    Section 10 - Time-of-day modifier.
    Measures late-day fatigue and recovery-window displacement.
    """
    if not dt_or_time:
        return 1.00

    if isinstance(dt_or_time, datetime):
        t = dt_or_time.time()
    elif isinstance(dt_or_time, time):
        t = dt_or_time
    else:
        return 1.00

    hour = t.hour + (t.minute / 60.0)

    # 08:00 - 20:00 -> 1.00
    if 8.0 <= hour < 20.0:
        return 1.00
    # 20:00 - 23:00 -> 1.10
    elif 20.0 <= hour < 23.0:
        return 1.10
    # 23:00 - 02:00 -> 1.25
    elif hour >= 23.0 or hour < 2.0:
        return 1.25
    # 02:00 - 08:00 -> 1.40 (Severe recovery displacement)
    else:
        return 1.40


def intensity_multiplier(intensity_str: str) -> float:
    """
    Section 11 - Intensity multiplier relative to activity taxonomy.
    """
    if not intensity_str:
        return 1.00

    val = intensity_str.strip().capitalize()
    if val == "Low":
        return 0.60
    elif val == "Medium":
        return 1.00
    elif val == "High":
        return 1.35
    elif val == "Extreme":
        return 1.70
    return 1.00
