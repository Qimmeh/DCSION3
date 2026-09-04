from flask import Flask
from flask_login import current_user

from config import Config
from app.extensions import db, login_manager, csrf


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.auth import bp as auth_bp
    from app.main import bp as main_bp
    from app.tasks import bp as tasks_bp
    from app.wellbeing import bp as wellbeing_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(wellbeing_bp)

    @app.context_processor
    def inject_globals():
        return {"current_user": current_user}

    with app.app_context():
        db.create_all()

    return app