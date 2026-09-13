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
from app.engine.battery import (
    calculate_starting_battery,
    calculate_recovery_debt,
    calculate_activity_battery_drain,
    calculate_recovery_restoration,
    calculate_capacity_load,
    compute_daily_battery_projection,
    evaluate_battery_state,
    sleep_recovery_curve,
)
from app.engine.burnout import (
    calculate_capacity_stress,
    calculate_sustained_overload,
    calculate_risk_trend,
    evaluate_risk_state,
    compute_burnout_score,
)

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
    "calculate_starting_battery",
    "calculate_recovery_debt",
    "calculate_activity_battery_drain",
    "calculate_recovery_restoration",
    "calculate_capacity_load",
    "compute_daily_battery_projection",
    "evaluate_battery_state",
    "sleep_recovery_curve",
    "calculate_capacity_stress",
    "calculate_sustained_overload",
    "calculate_risk_trend",
    "evaluate_risk_state",
    "compute_burnout_score",
]
