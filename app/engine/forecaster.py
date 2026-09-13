"""
Multi-Horizon Schedule & Capacity Forecaster
============================================
Projects daily Workload, Battery capacity, Recovery Debt, and Capacity Load
across a 7 to 14 day horizon.
Used by:
- Smart Todo Scheduler (detecting collision periods and deadline bottlenecks)
- Burnout Engine (calculating FutureRisk)
- Dashboard 7-Day Forecast visualization
"""
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional
from app.engine.scoring import score_activity
from app.engine.workload import calculate_daily_workload
from app.engine.battery import (
    calculate_starting_battery,
    calculate_recovery_debt,
    compute_daily_battery_projection,
    calculate_capacity_load,
    evaluate_battery_state,
)


def forecast_horizon(
    start_date: date,
    days: int,
    activities_by_date: Dict[date, List[Dict[str, Any]]],
    initial_battery: float = 85.0,
    initial_debt: float = 0.0,
    target_sleep: float = 8.0,
    assumed_daily_sleep: float = 8.0,
    dimension_weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Simulates forward day-by-day across the horizon:
      Day t:
        - Carries debt and battery from day t-1
        - Calculates starting battery
        - Evaluates activities drain/recovery
        - Calculates 5-stat workload
        - Calculates capacity load
    """
    days = max(1, min(days, 14))
    forecast_days = []
    carried_debt = initial_debt
    carried_battery = initial_battery

    high_load_days = []
    low_battery_days = []
    capacity_loads = []
    workload_scores = []

    for i in range(days):
        current_date = start_date + timedelta(days=i)
        day_activities = activities_by_date.get(current_date, [])

        # Start battery derived from sleep and debt
        if i == 0:
            start_battery = initial_battery
        else:
            debt_calc = calculate_recovery_debt(
                previous_debt=carried_debt,
                target_sleep=target_sleep,
                actual_sleep=assumed_daily_sleep,
            )
            carried_debt = debt_calc["updated_debt"]
            start_battery = calculate_starting_battery(
                actual_sleep=assumed_daily_sleep,
                target_sleep=target_sleep,
                recovery_debt=carried_debt,
            )

        # Calculate daily workload
        if day_activities:
            scored_list = [score_activity(act) for act in day_activities]
            workload_result = calculate_daily_workload(
                activity_scores_list=scored_list,
                activities=day_activities,
                dimension_weights=dimension_weights,
            )
            overall_workload = workload_result["overall_score"]
            dimensions = workload_result["dimension_pressures"]
        else:
            overall_workload = 0.0
            dimensions = {"academic": 0.0, "work": 0.0, "social": 0.0, "health": 0.0, "errands": 0.0}

        # Project battery drain and end of day battery
        battery_result = compute_daily_battery_projection(
            start_battery=start_battery,
            activities=day_activities,
            recovery_debt=carried_debt,
            workload_score=overall_workload,
        )

        projected_end_battery = battery_result["current_battery"]
        cap_load = battery_result["capacity_load"]
        carried_battery = projected_end_battery

        if overall_workload >= 75.0 or cap_load >= 100.0:
            high_load_days.append(current_date.isoformat())
        if projected_end_battery <= 45.0:
            low_battery_days.append(current_date.isoformat())

        capacity_loads.append(cap_load)
        workload_scores.append(overall_workload)

        forecast_days.append({
            "date": current_date.isoformat(),
            "day_of_week": current_date.strftime("%a"),
            "workload_score": overall_workload,
            "dimensions": dimensions,
            "start_battery": start_battery,
            "end_battery": projected_end_battery,
            "total_drain": battery_result["total_drain"],
            "total_recovery": battery_result["total_recovery"],
            "capacity_load": cap_load,
            "battery_state": battery_result["battery_state"],
            "recovery_debt": round(carried_debt, 2),
            "activity_count": len(day_activities),
        })

    avg_workload = round(sum(workload_scores) / len(workload_scores), 1) if workload_scores else 0.0
    avg_capacity_load = round(sum(capacity_loads) / len(capacity_loads), 1) if capacity_loads else 0.0

    return {
        "start_date": start_date.isoformat(),
        "days_count": days,
        "average_workload": avg_workload,
        "average_capacity_load": avg_capacity_load,
        "high_load_dates": high_load_days,
        "low_battery_dates": low_battery_days,
        "has_collision_risk": len(high_load_days) >= 2 or len(low_battery_days) >= 2,
        "daily_forecast": forecast_days,
    }
