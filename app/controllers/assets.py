from flask import Blueprint, jsonify, request
from sqlalchemy import or_, select

from app.extensions import db
from app.models import Asset, User
from app.schemas import AssetIn, AssetOut
from app.utils.http import (apply_sort, ensure_exists, get_or_404, load_body,
                            paginated, record_audit, require_api_key)

bp = Blueprint("assets", __name__, url_prefix="/api/v1/assets")
bp.before_request(require_api_key)
_out = AssetOut()


@bp.post("")
def create_asset():
    data = load_body(AssetIn())
    ensure_exists(User, data["owner_id"], "owner_id", "User")
    asset = Asset(**data)
    db.session.add(asset)
    db.session.flush()
    record_audit("CREATE", "asset", asset.id, asset.name)
    db.session.commit()
    return jsonify(_out.dump(asset)), 201


@bp.get("")
def list_assets():
    stmt = select(Asset)
    for f in ("asset_type", "criticality", "owner_id"):
        if (v := request.args.get(f)) is not None:
            stmt = stmt.where(getattr(Asset, f) == v)
    if q := request.args.get("q"):
        like = f"%{q}%"
        stmt = stmt.where(or_(Asset.name.ilike(like), Asset.ip_address.ilike(like)))
    stmt = apply_sort(stmt, Asset, {"id", "name", "criticality", "created_at"}, "id")
    return jsonify(paginated(stmt, _out))


@bp.get("/<int:asset_id>")
def get_asset(asset_id):
    return jsonify(_out.dump(get_or_404(Asset, asset_id, "Aset")))


@bp.route("/<int:asset_id>", methods=["PUT", "PATCH"])
def update_asset(asset_id):
    asset = get_or_404(Asset, asset_id, "Aset")
    data = load_body(AssetIn(), partial=request.method == "PATCH")
    if "owner_id" in data:
        ensure_exists(User, data["owner_id"], "owner_id", "User")
    for k, v in data.items():
        setattr(asset, k, v)
    record_audit("UPDATE", "asset", asset.id)
    db.session.commit()
    return jsonify(_out.dump(asset))


@bp.delete("/<int:asset_id>")
def delete_asset(asset_id):
    asset = get_or_404(Asset, asset_id, "Aset")
    db.session.delete(asset)  # 409 jika masih tertaut ke insiden
    record_audit("DELETE", "asset", asset_id)
    db.session.commit()
    return "", 204
