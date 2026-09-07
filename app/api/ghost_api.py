"""
Ghost Schedule API Endpoints
============================
GET  /api/v1/ghost
POST /api/v1/ghost/<id>/confirm
POST /api/v1/ghost/<id>/reject
"""
from datetime import datetime
from flask import jsonify, g
from app.api import api_bp, require_user
from app.extensions import db
from app.models import GhostChange, Activity, AuditLog


@api_bp.route("/ghost", methods=["GET"])
@require_user
def list_ghost_changes():
    """
    List all pending Ghost Schedule proposals.
    """
    user = g.current_api_user
    proposals = GhostChange.query.filter_by(user_id=user.id, status="PENDING").all()
    return jsonify({
        "status": "success",
        "count": len(proposals),
        "proposals": [p.to_dict() for p in proposals]
    })


@api_bp.route("/ghost/<int:ghost_id>/confirm", methods=["POST"])
@require_user
def confirm_ghost_change(ghost_id):
    """
    Section 7.2 - Transactionally applies an unconfirmed Ghost proposal
    to the production schedule once approved by the user.
    """
    user = g.current_api_user
    proposal = GhostChange.query.filter_by(id=ghost_id, user_id=user.id).first_or_404()

    if proposal.status != "PENDING":
        return jsonify({"error": f"Proposal is already {proposal.status}"}), 400

    # Apply atomic items
    for item in proposal.items:
        op = item.operation
        payload = item.payload or {}

        if op == "CREATE":
            act = Activity(
                user_id=user.id,
                title=payload.get("title", "New Event"),
                category=payload.get("category", "Academic"),
                start_time=item.new_start,
                end_time=item.new_end,
                duration_minutes=payload.get("duration_minutes", 60),
                is_fixed=payload.get("is_fixed", True),
                status="planned"
            )
            db.session.add(act)

        elif op == "MOVE":
            if item.source_activity_id:
                act = Activity.query.get(item.source_activity_id)
                if act:
                    act.start_time = item.new_start
                    act.end_time = item.new_end
                    act.status = "rescheduled"

        elif op == "DELETE":
            if item.source_activity_id:
                act = Activity.query.get(item.source_activity_id)
                if act:
                    act.status = "cancelled"

    proposal.status = "CONFIRMED"
    proposal.resolved_at = datetime.utcnow()

    # Log audit trail
    audit = AuditLog(
        user_id=user.id,
        action="confirm_ghost_change",
        entity_type="GhostChange",
        entity_id=proposal.id,
        details={"source_type": proposal.source_type, "items_count": proposal.items.count()}
    )
    db.session.add(audit)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Ghost proposal confirmed and committed to schedule.",
        "proposal_id": proposal.id
    })


@api_bp.route("/ghost/<int:ghost_id>/reject", methods=["POST"])
@require_user
def reject_ghost_change(ghost_id):
    """
    Dismisses a proposal without mutating the calendar.
    """
    user = g.current_api_user
    proposal = GhostChange.query.filter_by(id=ghost_id, user_id=user.id).first_or_404()

    proposal.status = "REJECTED"
    proposal.resolved_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Ghost proposal rejected.",
        "proposal_id": proposal.id
    })
