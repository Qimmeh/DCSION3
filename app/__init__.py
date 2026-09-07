from flask import Flask
from flask_login import current_user

from config import Config
from app.extensions import db, login_manager, csrf


def create_app(config_class=Config):
    app = Flask(__name__, template_folder="../frontend", static_folder="../frontend")
    app.config.from_object(config_class)


    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app import models as app_models
    from app.models import User


    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.auth import bp as auth_bp
    from app.main import bp as main_bp
    from app.tasks import bp as tasks_bp
    from app.wellbeing import bp as wellbeing_bp
    from app.api import api_bp

    csrf.exempt(api_bp)

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(wellbeing_bp)
    app.register_blueprint(api_bp)

    @app.context_processor
    def inject_globals():
        return {"current_user": current_user}

    with app.app_context():
        try:
            table_count = len(db.Model.metadata.tables)
            print(f"Connecting to database and creating {table_count} tables via db.create_all()...", flush=True)
            db.create_all()
            print("db.create_all() finished successfully! All tables verified.", flush=True)
        except Exception as err:
            print(f"FAILED to run db.create_all(): {err}", flush=True)


    return app