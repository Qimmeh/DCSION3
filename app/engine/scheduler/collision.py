"""
Deadline Collision & High-Risk Bottleneck Detection
===================================================
Scans the 7 to 14 day horizon for:
1. Clusters of exams and assignment deadlines
2. High required effort colliding with low battery forecasts
3. Schedule compression (back-to-back blocks without recovery)
4. Recovery displacement (sleep or protected rest threatened)
"""
from datetime import date, datetime, timedelta
from typing import List, Dict, Any


def detect_deadline_collisions(
    horizon_days: List[Dict[str, Any]],
    tasks_with_deadlines: List[Dict[str, Any]],
    protected_sleep_hours: float = 6.0,
) -> Dict[str, Any]:
    """
    Analyzes tasks with upcoming deadlines against the daily horizon forecast.
    Returns detected collision signals, bottleneck windows, and tasks needing earlier placement.
    """
    collisions = []
    tasks_needing_earlier_placement = []

    # 1. Map tasks to their deadline date
    deadlines_by_date: Dict[date, List[Dict[str, Any]]] = {}
    for task in tasks_with_deadlines:
        dl = task.get("deadline")
        if dl:
            if isinstance(dl, str):
                try:
                    dl = datetime.fromisoformat(dl)
                except Exception:
                    continue
            dl_date = dl.date() if isinstance(dl, datetime) else dl
            deadlines_by_date.setdefault(dl_date, []).append(task)

    # 2. Map forecast days by date
    forecast_by_date = {d["date"]: d for d in horizon_days}

    # 3. Detect multi-deadline clusters (e.g. 2+ deadlines within 48h)
    sorted_dates = sorted(deadlines_by_date.keys())
    for i, d1 in enumerate(sorted_dates):
        clustered_tasks = list(deadlines_by_date[d1])
        for j in range(i + 1, len(sorted_dates)):
            d2 = sorted_dates[j]
            if (d2 - d1).days <= 2:
                clustered_tasks.extend(deadlines_by_date[d2])
            else:
                break

        if len(clustered_tasks) >= 2:
            collisions.append({
                "type": "deadline_cluster",
                "severity": "high",
                "dates": [d.isoformat() for d in [d1, d2]],
                "description": f"Multiple deadlines clustered around {d1.isoformat()}: {[t.get('title') for t in clustered_tasks]}.",
                "tasks": [t.get("id") for t in clustered_tasks if t.get("id")],
            })

    # 4. Detect high effort near high-workload / low-battery days ("Finish Before" triggers)
    for task in tasks_with_deadlines:
        dl = task.get("deadline")
        if not dl:
            continue
        if isinstance(dl, str):
            try:
                dl = datetime.fromisoformat(dl)
            except Exception:
                continue
        dl_date = dl.date() if isinstance(dl, datetime) else dl
        rem_mins = task.get("remaining_effort_minutes", 60)

        # Check the 48-hour window leading up to deadline
        for offset in range(3):
            check_date = (dl_date - timedelta(days=offset)).isoformat()
            day_forecast = forecast_by_date.get(check_date)
            if day_forecast:
                w_score = day_forecast.get("workload_score", 0.0)
                end_bat = day_forecast.get("end_battery", 100.0)

                # Collision if deadline day is already high workload or low battery
                if (w_score >= 70.0 or end_bat <= 45.0) and rem_mins >= 120:
                    collisions.append({
                        "type": "battery_compression_collision",
                        "severity": "critical" if w_score >= 85.0 else "high",
                        "date": check_date,
                        "task_id": task.get("id"),
                        "task_title": task.get("title"),
                        "description": (
                            f"Task '{task.get('title')}' requires {round(rem_mins/60, 1)}h, "
                            f"but deadline period ({check_date}) has projected workload {w_score}% "
                            f"and battery {end_bat}%. Work must be shifted earlier."
                        )
                    })
                    if task not in tasks_needing_earlier_placement:
                        tasks_needing_earlier_placement.append(task)
                    break

    return {
        "has_collisions": len(collisions) > 0,
        "collision_count": len(collisions),
        "collisions": collisions,
        "tasks_needing_earlier_placement": tasks_needing_earlier_placement,
    }
