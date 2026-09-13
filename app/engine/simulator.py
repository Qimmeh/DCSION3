"""
Capacity Simulator Engine
=========================
Answers the question: "If I accept this new commitment, what happens to my week?"
Calculates before/after acute daily and rolling weekly workload, detects
displaced recovery or study blocks, and generates actionable verdicts.
"""
from typing import List, Dict, Any
from app.engine.scoring import score_activity
from app.engine.workload import calculate_daily_workload, calculate_weekly_workload


def simulate_commitment(
    current_activities: List[Any],
    proposed_activity: Dict[str, Any],
    recent_daily_scores: List[float] = None,
) -> Dict[str, Any]:
    """
    Section 21 - Capacity Simulator algorithm.
    """
    # 1. Baseline calculation
    current_scored = [score_activity(a) for a in current_activities]
    baseline_daily = calculate_daily_workload(current_scored, current_activities)

    # Baseline weekly estimate
    past_scores = recent_daily_scores or [baseline_daily["overall_score"]] * 6
    baseline_weekly_input = [{"overall_score": sc} for sc in past_scores] + [{"overall_score": baseline_daily["overall_score"]}]
    baseline_weekly = calculate_weekly_workload(baseline_weekly_input)

    # 2. Score proposed activity
    proposed_scored = score_activity(proposed_activity)

    # 3. Simulate new daily schedule
    simulated_activities = list(current_activities) + [proposed_activity]
    simulated_scored = current_scored + [proposed_scored]
    simulated_daily = calculate_daily_workload(simulated_scored, simulated_activities)

    # 4. Simulate new weekly state
    simulated_weekly_input = [{"overall_score": sc} for sc in past_scores] + [{"overall_score": simulated_daily["overall_score"]}]
    simulated_weekly = calculate_weekly_workload(simulated_weekly_input)

    # 5. Check for displaced recovery windows or overlaps
    displaced_tradeoffs = []
    prop_hours = (proposed_activity.get("duration_minutes", 60) or 60) / 60.0

    # Overload checks
    if simulated_weekly["overall_score"] > 90.0:
        displaced_tradeoffs.append("Pushes rolling weekly burn rate into Critical state (>90%).")
    elif simulated_weekly["overall_score"] > 85.0:
        displaced_tradeoffs.append("Elevates sustained weekly workload into High pressure zone (>85%).")

    if simulated_daily["compression_penalty"] > baseline_daily["compression_penalty"]:
        displaced_tradeoffs.append("Significantly reduces available breathing room and transition buffer.")

    if prop_hours >= 4.0:
        displaced_tradeoffs.append(f"Displaces approximately {round(prop_hours * 0.4, 1)} hours of recovery or study buffer.")

    # 6. Recommendation logic: Accept, Decline, or Accept_With_Rebalance
    weekly_diff = simulated_weekly["overall_score"] - baseline_weekly["overall_score"]
    daily_after = simulated_daily["overall_score"]

    if daily_after > 90.0 or simulated_weekly["overall_score"] > 92.0:
        verdict = "Decline"
        recommendation_text = "This commitment removes your protected recovery buffer and pushes workload into critical overload. Consider declining or rebalancing existing commitments first."
    elif daily_after > 80.0 or weekly_diff >= 10.0:
        verdict = "Accept_With_Rebalance"
        recommendation_text = "Commitment can fit if you reschedule non-urgent flexible errands or move low-priority study blocks."
    else:
        verdict = "Accept"
        recommendation_text = "Healthy capacity remaining. This commitment fits comfortably into your schedule."

    return {
        "verdict": verdict,
        "recommendation": recommendation_text,
        "daily": {
            "before": baseline_daily["overall_score"],
            "after": simulated_daily["overall_score"],
            "diff": round(simulated_daily["overall_score"] - baseline_daily["overall_score"], 1),
            "limiting_factor": simulated_daily["limiting_factor"],
        },
        "weekly": {
            "before": baseline_weekly["overall_score"],
            "after": simulated_weekly["overall_score"],
            "diff": round(simulated_weekly["overall_score"] - baseline_weekly["overall_score"], 1),
            "burn_rate_status": simulated_weekly["status_level"],
        },
        "displaced_tradeoffs": displaced_tradeoffs,
        "proposed_activity_impact": proposed_scored["scores"],
    }
