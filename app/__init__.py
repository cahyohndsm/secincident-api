from flask import Flask, jsonify
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.extensions import db, migrate
from config import Config


@event.listens_for(Engine, "connect")
def _sqlite_fk(dbapi_conn, _):
    """SQLite tidak menegakkan foreign key secara default."""
    if dbapi_conn.__class__.__module__.startswith("sqlite3"):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    from app import models  # noqa: F401  (daftarkan model untuk migrasi)
    migrate.init_app(app, db)

    from app.controllers import ALL_BLUEPRINTS
    for bp in ALL_BLUEPRINTS:
        app.register_blueprint(bp)

    from app.utils.errors import register_error_handlers
    register_error_handlers(app)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "service": "secincident-api", "version": "1.0.0"})

    @app.after_request
    def security_headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["Content-Security-Policy"] = "default-src 'none'"
        return resp

    from app.cli import register_cli
    register_cli(app)
    return app
