from datetime import date

from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, request
from flask_login import login_required, current_user

from app.extensions import db, csrf
from app.models import CheckIn, TimerSession
from app.forms import CheckInForm

bp = Blueprint("wellbeing", __name__, url_prefix="/wellbeing")


@bp.route("/checkin", methods=["GET", "POST"])
@login_required
def checkin():
    today = date.today()
    existing = current_user.checkins.filter_by(date=today).first()
    form = CheckInForm(obj=existing)

    if form.validate_on_submit():
        if existing:
            existing.mood = form.mood.data
            existing.stress = form.stress.data
            existing.note = form.note.data
        else:
            db.session.add(CheckIn(
                user_id=current_user.id,
                date=today,
                mood=form.mood.data,
                stress=form.stress.data,
                note=form.note.data,
            ))
        db.session.commit()
        
        # ALGORITHM: If stress is high, push today's moveable tasks to tomorrow
        if form.stress.data > 7:
            from app.models import Task
            from datetime import timedelta
            
            today = date.today()
            moveable_tasks = current_user.tasks.filter(
                Task.deadline == today,
                Task.is_moveable == True,
                Task.status != 'done'
            ).all()
            
            if moveable_tasks:
                for t in moveable_tasks:
                    t.deadline = today + timedelta(days=1)
                db.session.commit()
                flash(f"Algorithm detected high stress! Automatically pushed {len(moveable_tasks)} moveable task(s) to tomorrow.", "info")
            else:
                flash("Check-in saved. Note: High stress detected, but no moveable tasks found to reschedule today.", "warning")
        else:
            flash("Check-in saved.", "success")
            
        return redirect(url_for("main.dashboard"))

    history = current_user.checkins.order_by(CheckIn.date.desc()).limit(14).all()
    return render_template("wellbeing/checkin.html", form=form, existing=existing, history=history)


@bp.route("/timer")
@login_required
def timer():
    return render_template("wellbeing/timer.html")


@bp.route("/timer/log", methods=["POST"])
@login_required
@csrf.exempt
def log_timer_session():
    data = request.get_json(silent=True) or {}
    mode = data.get("mode")
    minutes = data.get("minutes")
    if mode not in ("focus", "rest") or not isinstance(minutes, (int, float)) or minutes <= 0:
        return jsonify({"ok": False}), 400
    db.session.add(TimerSession(
        user_id=current_user.id, mode=mode, duration_minutes=round(minutes)
    ))
    db.session.commit()
    focus_today = sum(
        s.duration_minutes for s in current_user.timer_sessions
        if s.mode == "focus" and s.completed_at.date() == date.today()
    )
    return jsonify({"ok": True, "focus_minutes_today": focus_today})


@bp.route("/boundaries")
@login_required
def boundaries():
    return render_template("wellbeing/boundaries.html")