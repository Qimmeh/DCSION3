"""
Flask REST API Package (/api/v1)
================================
Provides versioned JSON endpoints for frontend widgets, mobile apps,
and dashboard capacity visualizations.
"""
from functools import wraps
from flask import Blueprint, jsonify, request, g
from flask_login import current_user
from app.models import User

api_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


def require_user(f):
    """
    Decorator that resolves the current user:
      1. Flask-Login current_user if authenticated via session.
      2. 'X-User-Id' header for token/headless API testing.
      3. Fallback to first existing user or demo account so endpoints can be tested easily.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = None
        if current_user and current_user.is_authenticated:
            user = current_user
        else:
            # Check X-User-Id header
            user_id = request.headers.get("X-User-Id")
            if user_id:
                user = User.query.get(user_id)

            # Fallback to demo user for testing
            if not user:
                user = User.query.first()
                if not user:
                    from app.extensions import db
                    user = User(username="demo_student", email="demo@university.edu")
                    user.set_password("demo123")
                    db.session.add(user)
                    db.session.commit()

        g.current_api_user = user
        return f(*args, **kwargs)

    return decorated_function


@api_bp.errorhandler(400)
def bad_request(e):
    return jsonify({"error": "Bad request", "message": str(e)}), 400


@api_bp.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Resource not found"}), 404


@api_bp.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500

@api_bp.route("/health", methods=["GET"])
def health():
    from app.extensions import db
    from sqlalchemy import inspect
    db_status = "unknown"
    tables = []
    error = None
    try:
        db.create_all()
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        db_status = "connected"
    except Exception as e:
        db_status = "error"
        error = str(e)

    return jsonify({
        "status": "online",
        "database": db_status,
        "table_count": len(tables),
        "tables": tables,
        "error": error
    })


# Import and attach route handlers
from app.api import workload_api, activities_api, simulation_api, ghost_api, recovery_api

