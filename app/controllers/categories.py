from flask import Blueprint, jsonify, request
from sqlalchemy import select

from app.extensions import db
from app.models import IncidentCategory
from app.schemas import CategoryIn, CategoryOut
from app.utils.http import (apply_sort, get_or_404, load_body, paginated,
                            record_audit, require_api_key)

bp = Blueprint("categories", __name__, url_prefix="/api/v1/categories")
bp.before_request(require_api_key)
_out = CategoryOut()


@bp.post("")
def create_category():
    cat = IncidentCategory(**load_body(CategoryIn()))
    db.session.add(cat)
    db.session.flush()
    record_audit("CREATE", "category", cat.id, cat.name)
    db.session.commit()
    return jsonify(_out.dump(cat)), 201


@bp.get("")
def list_categories():
    stmt = apply_sort(select(IncidentCategory), IncidentCategory, {"id", "name"}, "name")
    return jsonify(paginated(stmt, _out))


@bp.get("/<int:cat_id>")
def get_category(cat_id):
    return jsonify(_out.dump(get_or_404(IncidentCategory, cat_id, "Kategori")))


@bp.route("/<int:cat_id>", methods=["PUT", "PATCH"])
def update_category(cat_id):
    cat = get_or_404(IncidentCategory, cat_id, "Kategori")
    for k, v in load_body(CategoryIn(), partial=request.method == "PATCH").items():
        setattr(cat, k, v)
    record_audit("UPDATE", "category", cat.id)
    db.session.commit()
    return jsonify(_out.dump(cat))


@bp.delete("/<int:cat_id>")
def delete_category(cat_id):
    cat = get_or_404(IncidentCategory, cat_id, "Kategori")
    db.session.delete(cat)
    record_audit("DELETE", "category", cat_id)
    db.session.commit()
    return "", 204
