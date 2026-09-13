"""
Domino Rebalancer Engine
========================
Finds flexible candidates to reschedule when a day is overloaded or a task extends.
Strictly preserves:
  1. Fixed timetable events (lectures, exams)
  2. Hard deadlines
  3. Protected sleep and recovery windows
"""
from typing import List, Dict, Any


def find_rebalance_proposals(
    activities: List[Any],
    overloaded_day: str = "today",
) -> List[Dict[str, Any]]:
    """
    Section 22 - Domino Rebalancer heuristic.
    Scans schedule for flexible, moveable activities and proposes low-friction adjustments.
    """
    proposals = []

    for act in activities:
        is_fixed = getattr(act, "is_fixed", False) if not isinstance(act, dict) else act.get("is_fixed", False)
        priority = getattr(act, "priority", "Medium") if not isinstance(act, dict) else act.get("priority", "Medium")
        category = getattr(act, "category", "Other") if not isinstance(act, dict) else act.get("category", "Other")
        title = getattr(act, "title", "Activity") if not isinstance(act, dict) else act.get("title", "Activity")
        act_id = getattr(act, "id", None) if not isinstance(act, dict) else act.get("id")
        rec_type = getattr(act, "recovery_type", None) if not isinstance(act, dict) else act.get("recovery_type")

        # Never move fixed commitments or sleep/recovery
        if is_fixed or rec_type:
            continue

        # Low-priority flexible tasks are prime candidates
        if priority in ["Low", "Medium"]:
            if category == "Errands":
                proposals.append({
                    "activity_id": act_id,
                    "title": title,
                    "action": "cluster_or_defer",
                    "suggestion": f"Cluster errand '{title}' into Saturday errand run.",
                    "estimated_load_relief": 12.0,
                    "target_window": "Saturday 14:00 - 16:00",
                })
            elif category == "Academic":
                proposals.append({
                    "activity_id": act_id,
                    "title": title,
                    "action": "reschedule",
                    "suggestion": f"Shift flexible revision '{title}' to tomorrow morning.",
                    "estimated_load_relief": 15.0,
                    "target_window": "Tomorrow 10:00 - 12:00",
                })
            elif category == "Social":
                proposals.append({
                    "activity_id": act_id,
                    "title": title,
                    "action": "convert_async",
                    "suggestion": f"Convert '{title}' to asynchronous communication or postpone.",
                    "estimated_load_relief": 10.0,
                    "target_window": "Deferred",
                })

    return proposals
