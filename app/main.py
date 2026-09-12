from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

# from app.utils import (
#     capacity_summary, prioritise, active_tasks_for_week, overload_suggestions,
#     core_tasks_today_message, record_weekly_snapshot, trend_data, get_nudge,
# )

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("index.html")


@bp.route("/dashboard")
@login_required
def dashboard():
    summary = capacity_summary(current_user)
    record_weekly_snapshot(current_user, summary)

    tasks = active_tasks_for_week(current_user)
    buckets = prioritise(tasks)
    suggestions = overload_suggestions(current_user, summary)
    today_msg = core_tasks_today_message(current_user)
    nudge = get_nudge(current_user, summary)
    trend = trend_data(current_user)

    return render_template(
        "dashboard.html",
        summary=summary,
        buckets=buckets,
        suggestions=suggestions,
        today_msg=today_msg,
        nudge=nudge,
        trend=trend,
    )