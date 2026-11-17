"""Helper request: auth API key, parsing JSON, paginasi, sorting, audit log."""
import hmac

from flask import current_app, request
from marshmallow import ValidationError

from app.extensions import db
from app.models.audit import AuditLog
from app.models.user import User
from app.utils.errors import ApiError


def require_api_key():
    supplied = request.headers.get("X-API-Key", "")
    expected = current_app.config["API_KEY"]
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise ApiError(401, "UNAUTHORIZED", "API key tidak ada atau tidak valid (header X-API-Key).")


def load_body(schema, partial=False):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "INVALID_JSON", "Body harus berupa JSON object (Content-Type: application/json).")
    try:
        return schema.load(data, partial=partial)
    except ValidationError as e:
        raise ApiError(422, "VALIDATION_ERROR", "Input tidak valid.", e.messages)


def get_or_404(model, pk, label):
    obj = db.session.get(model, pk)
    if obj is None:
        raise ApiError(404, "NOT_FOUND", f"{label} dengan id {pk} tidak ditemukan.")
    return obj


def ensure_exists(model, pk, field, label):
    """Validasi foreign key sebelum insert/update."""
    if pk is not None and db.session.get(model, pk) is None:
        raise ApiError(422, "VALIDATION_ERROR", "Referensi tidak valid.", {field: [f"{label} dengan id {pk} tidak ditemukan."]})


def _int_arg(name, default, minimum=1, maximum=None):
    raw = request.args.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ApiError(400, "INVALID_QUERY", f"Parameter '{name}' harus bilangan bulat.")
    if value < minimum or (maximum and value > maximum):
        raise ApiError(400, "INVALID_QUERY", f"Parameter '{name}' di luar rentang yang diizinkan.")
    return value


def apply_sort(stmt, model, allowed, default):
    for part in request.args.get("sort", default).split(","):
        part = part.strip()
        if not part:
            continue
        name = part.lstrip("-")
        if name not in allowed:
            raise ApiError(400, "INVALID_SORT", f"Field sort '{name}' tidak didukung.", {"allowed": sorted(allowed)})
        col = getattr(model, name)
        stmt = stmt.order_by(col.desc() if part.startswith("-") else col.asc())
    return stmt


def paginated(stmt, schema):
    page = _int_arg("page", 1)
    per_page = _int_arg("per_page", 10, maximum=100)
    p = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    return {
        "data": schema.dump(p.items, many=True),
        "meta": {"page": p.page, "per_page": p.per_page, "total": p.total, "pages": p.pages},
    }


def record_audit(action, entity, entity_id, detail=None):
    """Catat audit log; actor opsional lewat header X-Actor-Id. Ikut di transaksi yang sama."""
    actor_id = None
    raw = request.headers.get("X-Actor-Id")
    if raw:
        try:
            actor_id = int(raw)
        except ValueError:
            raise ApiError(400, "INVALID_HEADER", "X-Actor-Id harus bilangan bulat.")
        ensure_exists(User, actor_id, "X-Actor-Id", "User")
    db.session.add(AuditLog(user_id=actor_id, action=action, entity=entity, entity_id=entity_id, detail=detail))
