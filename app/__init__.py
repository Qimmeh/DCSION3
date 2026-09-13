import os
from flask import Flask, send_from_directory, request, jsonify
from flask_login import current_user
from flask_cors import CORS

from config import Config
from app.extensions import db, login_manager, csrf


def create_app(config_class=Config):
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
    app = Flask(
        __name__,
        static_folder=frontend_dir,
        template_folder=frontend_dir,
        static_url_path=""
    )
    app.config.from_object(config_class)

    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-User-Id"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        return response

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.auth import bp as auth_bp
    from app.journal import bp as journal_bp
    from app.ai import bp as ai_bp
    from app.api import api_bp

    csrf.exempt(api_bp)

    app.register_blueprint(auth_bp)
    app.register_blueprint(journal_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(api_bp)

    @app.route("/")
    def serve_index():
        return send_from_directory(frontend_dir, "index.html")

    @app.route("/<path:filename>")
    def serve_static_page(filename):
        target_path = os.path.join(frontend_dir, filename)
        if os.path.exists(target_path) and os.path.isfile(target_path):
            return send_from_directory(frontend_dir, filename)
        return "Page not found", 404

    @app.context_processor
    def inject_globals():
        return {"current_user": current_user}

    with app.app_context():
        db.create_all()
        try:
            from app.schema_sync import sync_db_columns
            sync_db_columns(db)
        except Exception as e:
            print("schema_sync warning:", e)

    return app