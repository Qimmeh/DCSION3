"""
Capacity Simulator & Domino Rebalancer API Endpoints
===================================================
POST /api/v1/capacity/simulate
POST /api/v1/domino/rebalance
"""
from datetime import datetime, date, timedelta
from flask import jsonify, request, g
from app.api import api_bp, require_user
from app.models import Activity, Commitment, WorkloadSnapshot
from app.extensions import db
from app.engine import simulate_commitment, find_rebalance_proposals


@api_bp.route("/capacity/simulate", methods=["POST"])
@require_user
def run_capacity_simulation():
    """
    Section 21 - Tests a proposed commitment against current schedule.
    Payload:
    {
      "title": "5-hour Saturday shift",
      "category": "Work",
      "duration_minutes": 300,
      "intensity": "High"
    }
    """
    user = g.current_api_user
    data = request.get_json() or {}

    title = data.get("title", "Proposed Commitment")
    duration_minutes = int(data.get("duration_minutes", 120))
    intensity = data.get("intensity", "Medium")
    category = data.get("category", "Work")

    # Get user's current activities for today
    today = date.today()
    start_dt = datetime.combine(today, datetime.min.time())
    end_dt = datetime.combine(today, datetime.max.time())

    activities = Activity.query.filter(
        Activity.user_id == user.id,
        Activity.start_time >= start_dt,
        Activity.start_time <= end_dt,
        Activity.status != "cancelled"
    ).all()

    # Get recent daily snapshot scores for weekly burn rate projection
    seven_days_ago = today - timedelta(days=6)
    snaps = WorkloadSnapshot.query.filter(
        WorkloadSnapshot.user_id == user.id,
        WorkloadSnapshot.date >= seven_days_ago,
        WorkloadSnapshot.date <= today,
        WorkloadSnapshot.snapshot_type == "daily"
    ).all()
    recent_scores = [s.overall_score for s in snaps] or [35.0] * 6

    proposed = {
        "title": title,
        "category": category,
        "duration_minutes": duration_minutes,
        "continuous_minutes": duration_minutes,
        "intensity": intensity,
    }

    sim_result = simulate_commitment(activities, proposed, recent_daily_scores=recent_scores)

    # Record proposal in commitments table for audit
    commitment = Commitment(
        user_id=user.id,
        title=title,
        category=category,
        estimated_hours=duration_minutes / 60.0,
        intensity=intensity,
        simulated_weekly_load_before=sim_result["weekly"]["before"],
        simulated_weekly_load_after=sim_result["weekly"]["after"],
        simulation_verdict=sim_result["verdict"],
        displaced_summary={"tradeoffs": sim_result["displaced_tradeoffs"]},
        status="simulating"
    )
    db.session.add(commitment)
    db.session.commit()

    return jsonify({
        "status": "success",
        "simulation": sim_result,
        "commitment_id": commitment.id
    })


@api_bp.route("/domino/rebalance", methods=["POST"])
@require_user
def run_domino_rebalance():
    """
    Section 22 - Domino Rebalancer:
    Scans today's schedule and suggests moving flexible low-priority tasks/errands
    to relieve schedule congestion while protecting fixed commitments and sleep.
    """
    user = g.current_api_user
    today = date.today()
    start_dt = datetime.combine(today, datetime.min.time())
    end_dt = datetime.combine(today, datetime.max.time())

    activities = Activity.query.filter(
        Activity.user_id == user.id,
        Activity.start_time >= start_dt,
        Activity.start_time <= end_dt,
        Activity.status != "cancelled"
    ).all()

    proposals = find_rebalance_proposals(activities)

    return jsonify({
        "status": "success",
        "proposals_count": len(proposals),
        "proposals": proposals,
        "guidance": "Fixed timetable blocks and protected recovery windows were automatically preserved."
    })
