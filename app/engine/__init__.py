"""
Deterministic Workload & Capacity Engine
========================================
Independent pure-Python algorithms for workload calculation,
activity scoring, capacity simulation, and schedule rebalancing.
"""
from app.engine.taxonomy import get_default_stat_vector
from app.engine.multipliers import (
    duration_multiplier,
    continuity_multiplier,
    timing_multiplier,
    intensity_multiplier,
)
from app.engine.scoring import score_activity, PER_ACTIVITY_CAP
from app.engine.workload import (
    calculate_daily_workload,
    calculate_weekly_workload,
    calculate_peak_penalty,
    calculate_compression_penalty,
    calculate_recovery_deficit,
)
from app.engine.simulator import simulate_commitment
from app.engine.rebalancer import find_rebalance_proposals

__all__ = [
    "get_default_stat_vector",
    "duration_multiplier",
    "continuity_multiplier",
    "timing_multiplier",
    "intensity_multiplier",
    "score_activity",
    "PER_ACTIVITY_CAP",
    "calculate_daily_workload",
    "calculate_weekly_workload",
    "calculate_peak_penalty",
    "calculate_compression_penalty",
    "calculate_recovery_deficit",
    "simulate_commitment",
    "find_rebalance_proposals",
]
