"""
Utility functions for capacity calculation and dashboard helpers.
"""
from datetime import date, datetime, timedelta

def capacity_summary(user):
    """Calculate or retrieve capacity summary for the dashboard."""
    # Check if a recent snapshot exists
    from app.models import WorkloadSnapshot
    today = date.today()
    snap = WorkloadSnapshot.query.filter_by(user_id=user.id, date=today, snapshot_type='daily').first()
    if snap:
        return {
            "academic": snap.academic_load,
            "work": snap.work_load,
            "social": snap.social_load,
            "health": snap.health_load,
            "errands": snap.errands_load,
            "overall": snap.overall_score,
            "status": snap.status_level,
            "limiting_factor": snap.limiting_factor or "None"
        }
    return {
        "academic": 0.0,
        "work": 0.0,
        "social": 0.0,
        "health": 0.0,
        "errands": 0.0,
        "overall": 0.0,
        "status": "normal",
        "limiting_factor": "None"
    }

def record_weekly_snapshot(user, summary):
    pass

def active_tasks_for_week(user):
    from app.models import Task, Activity
    # Return active tasks/activities
    tasks = user.tasks.filter(Task.status != 'done').all() if hasattr(user, 'tasks') else []
    return tasks

def prioritise(tasks):
    return {
        "urgent": [t for t in tasks if getattr(t, 'importance', 1) >= 3],
        "medium": [t for t in tasks if getattr(t, 'importance', 1) == 2],
        "flexible": [t for t in tasks if getattr(t, 'importance', 1) <= 1]
    }

def overload_suggestions(user, summary):
    suggestions = []
    if summary.get("overall", 0) > 85:
        suggestions.append("Consider postponing non-essential flexible errands to the weekend.")
    return suggestions

def core_tasks_today_message(user):
    return "Focus on your primary high-priority commitments today."

def get_nudge(user, summary):
    if summary.get("overall", 0) > 90:
        return "Critical workload detected! Take a 15-minute recovery walk."
    return "Your workload is within manageable capacity limits."

def trend_data(user):
    return [0, 10, 20, 15, 30, 25, 20]
