"""
Deterministic Burnout Risk & Trend Diagnostics Engine
======================================================
Evaluates product-level sustained imbalance between demand and capacity:

    BurnoutRisk = clamp(
        0.30 * CurrentStress +
        0.20 * RecoveryDeficit +
        0.20 * SustainedOverload +
        0.15 * SleepPressure +
        0.15 * FutureRisk,
        0, 100
    )

Provides multi-day trend detection and structured diagnostic output:
    PRIMARY: Academic overload
    SECONDARY: Recovery deficit
    CONTRIBUTING: 3 high-load days, 6h sleep, late-night revision, deadline tomorrow
"""
from typing import Dict, Any, List, Optional
from datetime import date, timedelta

WEIGHT_CURRENT_STRESS = 0.30
WEIGHT_RECOVERY_DEFICIT = 0.20
WEIGHT_SUSTAINED_OVERLOAD = 0.20
WEIGHT_SLEEP_PRESSURE = 0.15
WEIGHT_FUTURE_RISK = 0.15


def calculate_capacity_stress(capacity_load: float) -> float:
    """
    Section 5.6:
      DailyCapacityStress = clamp((CapacityLoad - 80) / 80 * 100, 0, 100)
    Capacity load below 80% represents manageable capacity (stress = 0).
    At 160% capacity load, stress reaches 100%.
    """
    if capacity_load <= 80.0:
        return 0.0
    stress = ((capacity_load - 80.0) / 80.0) * 100.0
    return max(0.0, min(100.0, round(stress, 1)))


def calculate_sustained_overload(capacity_loads_history: List[float]) -> Dict[str, Any]:
    """
    Tracks how many consecutive days capacity load remained elevated (>80%).
    1 day = 25% (mild)
    2 days = 50% (moderate)
    3 days = 75% (high)
    4+ days = 100% (strong/critical)
    """
    consecutive_days = 0
    # Walk backwards from most recent
    for load in reversed(capacity_loads_history):
        if load >= 80.0:
            consecutive_days += 1
        else:
            break

    if consecutive_days == 0:
        score = 0.0
    elif consecutive_days == 1:
        score = 25.0
    elif consecutive_days == 2:
        score = 50.0
    elif consecutive_days == 3:
        score = 75.0
    else:
        score = 100.0

    return {
        "consecutive_high_load_days": consecutive_days,
        "sustained_overload_score": score,
    }


def calculate_risk_trend(current_risk: float, forecast_risk: float) -> Dict[str, Any]:
    """
    Section 5.7:
      RiskTrend = ForecastRisk - CurrentRisk
    Distinguishes rising danger from high but de-escalating periods.
    """
    delta = round(forecast_risk - current_risk, 1)
    if delta > 5.0:
        direction = "rising"
        description = "Risk is rising over the upcoming horizon. Proactive intervention recommended."
    elif delta < -5.0:
        direction = "falling"
        description = "Risk is elevated but decreasing as scheduled recovery approaches."
    else:
        direction = "stable"
        description = "Risk levels are projected to remain steady."

    return {
        "delta": delta,
        "direction": direction,
        "description": description,
    }


def evaluate_risk_state(risk_score: float) -> Dict[str, str]:
    """
    Section 5.8:
      0-24: Low
      25-49: Moderate
      50-69: High
      70-84: Very High
      85-100: Critical
    """
    if risk_score < 25.0:
        return {
            "level": "Low",
            "action": "Normal planning. Capacity is well-balanced."
        }
    elif risk_score < 50.0:
        return {
            "level": "Moderate",
            "action": "Offer recovery windows or workload balancing."
        }
    elif risk_score < 70.0:
        return {
            "level": "High",
            "action": "Recommend rebalance; avoid stacking new high-load tasks."
        }
    elif risk_score < 85.0:
        return {
            "level": "Very High",
            "action": "Proactive survival plan recommended to protect upcoming commitments."
        }
    else:
        return {
            "level": "Critical",
            "action": "Protect recovery and sleep. Surface immediate triage interventions."
        }


def compute_burnout_score(
    current_capacity_load: float,
    recovery_debt_hours: float,
    capacity_loads_history: List[float],
    recent_sleep_deficits: List[float],
    future_capacity_loads: List[float],
    debt_cap_hours: float = 8.0,
) -> Dict[str, Any]:
    """
    Section 5.5:
      BurnoutRisk = clamp(0.30*CurrentStress + 0.20*RecoveryDeficit + 0.20*SustainedOverload + 0.15*SleepPressure + 0.15*FutureRisk, 0, 100)
    """
    current_load = float(current_capacity_load if current_capacity_load is not None else 0.0)
    rec_debt = float(recovery_debt_hours if recovery_debt_hours is not None else 0.0)
    loads_hist = [float(l) for l in (capacity_loads_history or []) if l is not None]
    deficits = [float(d) for d in (recent_sleep_deficits or []) if d is not None]
    future_loads = [float(f) for f in (future_capacity_loads or []) if f is not None]

    # 1. Current Capacity Stress
    current_stress = calculate_capacity_stress(current_load)

    # 2. Recovery Deficit (normalized against debt cap)
    recovery_deficit_score = max(0.0, min(100.0, (rec_debt / max(1.0, debt_cap_hours)) * 100.0))

    # 3. Sustained Overload
    sustained_info = calculate_sustained_overload(loads_hist)
    sustained_score = sustained_info["sustained_overload_score"]
    consecutive_days = sustained_info["consecutive_high_load_days"]

    # 4. Sleep Pressure (avg recent sleep deficit normalized over 3h max)
    avg_deficit = sum(deficits) / max(1, len(deficits)) if deficits else 0.0
    sleep_pressure_score = max(0.0, min(100.0, (avg_deficit / 3.0) * 100.0))

    # 5. Future Risk (projected upcoming capacity stress)
    if future_loads:
        future_stresses = [calculate_capacity_stress(l) for l in future_loads]
        future_risk_score = sum(future_stresses) / len(future_stresses)
    else:
        future_risk_score = current_stress

    # Combined score
    raw_burnout = (
        (WEIGHT_CURRENT_STRESS * current_stress) +
        (WEIGHT_RECOVERY_DEFICIT * recovery_deficit_score) +
        (WEIGHT_SUSTAINED_OVERLOAD * sustained_score) +
        (WEIGHT_SLEEP_PRESSURE * sleep_pressure_score) +
        (WEIGHT_FUTURE_RISK * future_risk_score)
    )
    burnout_risk = max(0.0, min(100.0, round(raw_burnout, 1)))
    state_info = evaluate_risk_state(burnout_risk)
    trend_info = calculate_risk_trend(current_risk=burnout_risk, forecast_risk=future_risk_score)

    # Rank factors for diagnostics
    component_scores = {
        "Capacity Stress": current_stress,
        "Recovery Deficit": recovery_deficit_score,
        "Sustained Overload": sustained_score,
        "Sleep Pressure": sleep_pressure_score,
        "Future Horizon Strain": future_risk_score,
    }
    sorted_factors = sorted(component_scores.items(), key=lambda x: x[1], reverse=True)
    primary_factor = sorted_factors[0][0] if sorted_factors[0][1] > 20.0 else "Balanced Schedule"
    secondary_factor = sorted_factors[1][0] if len(sorted_factors) > 1 and sorted_factors[1][1] > 15.0 else None

    # Contributing factors human-readable list
    contributing = []
    if consecutive_days >= 2:
        contributing.append(f"{consecutive_days} consecutive high-capacity load days")
    if recovery_debt_hours >= 1.5:
        contributing.append(f"{round(recovery_debt_hours, 1)}h accumulated recovery debt")
    if avg_deficit >= 1.0:
        contributing.append(f"{round(avg_deficit, 1)}h average sleep deficit over recent days")
    if current_capacity_load >= 110.0:
        contributing.append(f"Capacity load at {round(current_capacity_load, 1)}% (demand exceeds battery)")
    if trend_info["direction"] == "rising":
        contributing.append("Upcoming commitments projected to increase pressure")

    return {
        "burnout_risk": burnout_risk,
        "risk_level": state_info["level"],
        "recommended_action": state_info["action"],
        "trend": trend_info,
        "components": {
            "current_capacity_stress": current_stress,
            "recovery_deficit": round(recovery_deficit_score, 1),
            "sustained_overload": sustained_score,
            "sleep_pressure": round(sleep_pressure_score, 1),
            "future_risk": round(future_risk_score, 1),
        },
        "diagnosis": {
            "primary_problem": primary_factor,
            "secondary_problem": secondary_factor,
            "contributing_factors": contributing,
        }
    }
