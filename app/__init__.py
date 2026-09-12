import os
from flask import Flask, send_from_directory
from flask_login import current_user

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

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.auth import bp as auth_bp
    from app.journal import bp as journal_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(journal_bp)

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

    return app