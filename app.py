"""
app.py
Application factory for the Flask Patient Manager.
"""
import os
from flask import Flask
from config import config_map
from extensions import db, login_manager, csrf, migrate


def create_app(config_name: str | None = None) -> Flask:
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__, instance_relative_config=True)

    # Load config
    cfg = config_map.get(config_name, config_map["default"])
    app.config.from_object(cfg)

    # Ensure instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)

    # Fix SQLite path to use instance folder
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:///instance/"):
        db_path = os.path.join(app.instance_path, "patients.db")
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    # Initialise extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.patients import patients_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(patients_bp)

    # Shell context for `flask shell`
    @app.shell_context_processor
    def make_shell_context():
        from models import User, Patient
        return {"db": db, "User": User, "Patient": Patient}

    return app


# Allow `flask run` to find the app
app = create_app()
