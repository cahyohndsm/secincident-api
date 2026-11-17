from flask import Blueprint, jsonify
from sqlalchemy import func, select

from app.extensions import db
from app.models import Incident
from app.utils.http import require_api_key

bp = Blueprint("stats", __name__, url_prefix="/api/v1/stats")
bp.before_request(require_api_key)


@bp.get("/summary")
def summary():
    def count_by(col):
        rows = db.session.execute(select(col, func.count()).group_by(col)).all()
        return {k: v for k, v in rows}

    total = db.session.scalar(select(func.count()).select_from(Incident))
    return jsonify({"total_incidents": total, "by_severity": count_by(Incident.severity), "by_status": count_by(Incident.status)})
