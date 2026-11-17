from flask import Blueprint, jsonify, request
from sqlalchemy import select

from app.models import AuditLog
from app.schemas import AuditOut
from app.utils.http import apply_sort, paginated, require_api_key

bp = Blueprint("audit", __name__, url_prefix="/api/v1/audit-logs")
bp.before_request(require_api_key)


@bp.get("")
def list_audit_logs():
    """Read-only: audit log tidak boleh diubah/dihapus lewat API."""
    stmt = select(AuditLog)
    for f in ("entity", "action", "user_id", "entity_id"):
        if (v := request.args.get(f)) is not None:
            stmt = stmt.where(getattr(AuditLog, f) == v)
    stmt = apply_sort(stmt, AuditLog, {"id", "created_at"}, "-id")
    return jsonify(paginated(stmt, AuditOut()))
