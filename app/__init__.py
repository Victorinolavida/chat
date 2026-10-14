from flask import Flask, jsonify

from app.config import Config
from app.extensions import db, jwt, migrate, socketio


def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    socketio.init_app(
        app,
        cors_allowed_origins="*",
        path=app.config["SOCKETIO_PATH"],
    )

    from app import models  # noqa: F401  (register models with Alembic)
    from app.routes import auth_bp, conversations_bp, messages_bp, users_bp
    from app.sockets import register_chat_events

    app.register_blueprint(auth_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(conversations_bp)
    app.register_blueprint(users_bp)
    register_chat_events(socketio)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    return app
