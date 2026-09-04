from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Task
from app.forms import TaskForm

bp = Blueprint("tasks", __name__, url_prefix="/tasks")


def _populate_parent_choices(form, exclude_id=None):
    q = current_user.tasks.filter(Task.status != "done")
    if exclude_id:
        q = q.filter(Task.id != exclude_id)
    choices = [(0, "— none —")] + [(t.id, t.title) for t in q.order_by(Task.title)]
    form.parent_id.choices = choices


@bp.route("/")
@login_required
def list_tasks():
    status_filter = request.args.get("status", "open")
    q = current_user.tasks
    if status_filter == "open":
        q = q.filter(Task.status != "done")
    elif status_filter == "done":
        q = q.filter(Task.status == "done")
    all_tasks = q.order_by(Task.deadline.is_(None), Task.deadline.asc()).all()
    top_level = [t for t in all_tasks if t.parent_id is None]
    return render_template("tasks/list.html", tasks=top_level, status_filter=status_filter)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new_task():
    form = TaskForm()
    form.category.choices = [(c, c) for c in current_app_categories()]
    _populate_parent_choices(form)
    parent_id_arg = request.args.get("parent_id", type=int)
    if request.method == "GET" and parent_id_arg:
        form.parent_id.data = parent_id_arg

    if form.validate_on_submit():
        parent_id = form.parent_id.data or None
        task = Task(
            user_id=current_user.id,
            title=form.title.data.strip(),
            description=(form.description.data or "").strip() or None,
            category=form.category.data,
            deadline=form.deadline.data,
            importance=form.importance.data,
            effort_hours=form.effort_hours.data,
            effort_mental=form.effort_mental.data,
            parent_id=parent_id,
        )
        db.session.add(task)
        db.session.commit()
        flash("Task added.", "success")
        if parent_id:
            return redirect(url_for("tasks.view_task", task_id=parent_id))
        return redirect(url_for("tasks.list_tasks"))

    return render_template("tasks/form.html", form=form, task=None)


@bp.route("/<int:task_id>")
@login_required
def view_task(task_id):
    task = _get_owned_task(task_id)
    return render_template("tasks/view.html", task=task)


@bp.route("/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    task = _get_owned_task(task_id)
    form = TaskForm(obj=task)
    form.category.choices = [(c, c) for c in current_app_categories()]
    _populate_parent_choices(form, exclude_id=task.id)
    if request.method == "GET":
        form.parent_id.data = task.parent_id or 0

    if form.validate_on_submit():
        parent_id = form.parent_id.data or None
        if parent_id == task.id:
            parent_id = None
        task.title = form.title.data.strip()
        task.description = (form.description.data or "").strip() or None
        task.category = form.category.data
        task.deadline = form.deadline.data
        task.importance = form.importance.data
        task.effort_hours = form.effort_hours.data
        task.effort_mental = form.effort_mental.data
        task.parent_id = parent_id
        db.session.commit()
        flash("Task updated.", "success")
        return redirect(url_for("tasks.view_task", task_id=task.id))

    return render_template("tasks/form.html", form=form, task=task)


@bp.route("/<int:task_id>/split", methods=["GET", "POST"])
@login_required
def split_task(task_id):
    """Break a big task into smaller steps. Each submitted line becomes a
    leaf subtask inheriting the parent's category and deadline."""
    task = _get_owned_task(task_id)
    if request.method == "POST":
        raw_steps = request.form.get("steps", "")
        lines = [ln.strip() for ln in raw_steps.splitlines() if ln.strip()]
        if not lines:
            flash("Add at least one step.", "error")
        else:
            for line in lines:
                db.session.add(Task(
                    user_id=current_user.id,
                    title=line,
                    category=task.category,
                    deadline=task.deadline,
                    importance=task.importance,
                    effort_hours=max(round(task.effort_hours / len(lines), 2), 0.25),
                    effort_mental=task.effort_mental,
                    parent_id=task.id,
                ))
            db.session.commit()
            flash(f"Split into {len(lines)} steps.", "success")
            return redirect(url_for("tasks.view_task", task_id=task.id))
    return render_template("tasks/split.html", task=task)


@bp.route("/<int:task_id>/status/<string:new_status>", methods=["POST"])
@login_required
def set_status(task_id, new_status):
    if new_status not in ("todo", "in_progress", "done"):
        abort(400)
    task = _get_owned_task(task_id)
    task.status = new_status
    task.completed_at = datetime.utcnow() if new_status == "done" else None
    db.session.commit()
    return redirect(request.referrer or url_for("tasks.list_tasks"))


@bp.route("/<int:task_id>/delete", methods=["POST"])
@login_required
def delete_task(task_id):
    task = _get_owned_task(task_id)
    parent_id = task.parent_id
    db.session.delete(task)
    db.session.commit()
    flash("Task deleted.", "info")
    if parent_id:
        return redirect(url_for("tasks.view_task", task_id=parent_id))
    return redirect(url_for("tasks.list_tasks"))


def _get_owned_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        abort(403)
    return task


def current_app_categories():
    from flask import current_app
    return current_app.config["CATEGORIES"]