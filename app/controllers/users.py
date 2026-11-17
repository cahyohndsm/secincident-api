from flask import Blueprint, jsonify, request
from sqlalchemy import or_, select
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import User
from app.schemas import UserIn, UserOut
from app.utils.http import (apply_sort, get_or_404, load_body, paginated,
                            record_audit, require_api_key)

bp = Blueprint("users", __name__, url_prefix="/api/v1/users")
bp.before_request(require_api_key)
_out = UserOut()


@bp.post("")
def create_user():
    data = load_body(UserIn())
    data["password_hash"] = generate_password_hash(data.pop("password"))
    user = User(**data)
    db.session.add(user)
    db.session.flush()
    record_audit("CREATE", "user", user.id, f"username={user.username}")
    db.session.commit()
    return jsonify(_out.dump(user)), 201


@bp.get("")
def list_users():
    stmt = select(User)
    if role := request.args.get("role"):
        stmt = stmt.where(User.role == role)
    if q := request.args.get("q"):
        like = f"%{q}%"
        stmt = stmt.where(or_(User.username.ilike(like), User.email.ilike(like)))
    stmt = apply_sort(stmt, User, {"id", "username", "created_at"}, "id")
    return jsonify(paginated(stmt, _out))


@bp.get("/<int:user_id>")
def get_user(user_id):
    return jsonify(_out.dump(get_or_404(User, user_id, "User")))


@bp.route("/<int:user_id>", methods=["PUT", "PATCH"])
def update_user(user_id):
    user = get_or_404(User, user_id, "User")
    data = load_body(UserIn(), partial=request.method == "PATCH")
    if "password" in data:
        user.password_hash = generate_password_hash(data.pop("password"))
    for k, v in data.items():
        setattr(user, k, v)
    record_audit("UPDATE", "user", user.id)
    db.session.commit()
    return jsonify(_out.dump(user))


@bp.delete("/<int:user_id>")
def delete_user(user_id):
    user = get_or_404(User, user_id, "User")
    db.session.delete(user)  # gagal 409 bila masih direferensikan (FK)
    record_audit("DELETE", "user", user_id)
    db.session.commit()
    return "", 204
