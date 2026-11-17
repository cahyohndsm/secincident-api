from flask import Blueprint, jsonify, request
from sqlalchemy import or_, select

from app.extensions import db
from app.models import Asset, Incident, IncidentAsset, IncidentCategory, User
from app.models.user import utcnow
from app.schemas import IncidentIn, IncidentOut, LinkAssetIn, StatusIn
from app.utils.errors import ApiError
from app.utils.http import (apply_sort, ensure_exists, get_or_404, load_body,
                            paginated, record_audit, require_api_key)

bp = Blueprint("incidents", __name__, url_prefix="/api/v1/incidents")
bp.before_request(require_api_key)
_out = IncidentOut()

# Alur status yang diizinkan (state machine sederhana)
TRANSITIONS = {
    "open": {"investigating", "closed"},
    "investigating": {"contained", "resolved"},
    "contained": {"investigating", "resolved"},
    "resolved": {"closed", "investigating"},  # investigating = reopen
    "closed": set(),
}


def _check_refs(data):
    ensure_exists(IncidentCategory, data.get("category_id"), "category_id", "Kategori")
    ensure_exists(User, data.get("reporter_id"), "reporter_id", "User")
    ensure_exists(User, data.get("assignee_id"), "assignee_id", "User")


@bp.post("")
def create_incident():
    data = load_body(IncidentIn())
    _check_refs(data)
    asset_ids = list(dict.fromkeys(data.pop("asset_ids")))
    for aid in asset_ids:
        ensure_exists(Asset, aid, "asset_ids", "Aset")
    if data["detected_at"] is None:
        data["detected_at"] = utcnow()
    else:
        data["detected_at"] = data["detected_at"].replace(tzinfo=None)
    incident = Incident(**data)
    incident.asset_links = [IncidentAsset(asset_id=a) for a in asset_ids]
    db.session.add(incident)
    db.session.flush()
    record_audit("CREATE", "incident", incident.id, f"severity={incident.severity}")
    db.session.commit()
    return jsonify(_out.dump(incident)), 201


@bp.get("")
def list_incidents():
    stmt = select(Incident)
    for f in ("status", "severity", "category_id", "assignee_id", "reporter_id"):
        if (v := request.args.get(f)) is not None:
            stmt = stmt.where(getattr(Incident, f) == v)
    if q := request.args.get("q"):
        like = f"%{q}%"
        stmt = stmt.where(or_(Incident.title.ilike(like), Incident.description.ilike(like)))
    if asset_id := request.args.get("asset_id"):
        stmt = stmt.join(IncidentAsset).where(IncidentAsset.asset_id == asset_id)
    stmt = apply_sort(stmt, Incident, {"id", "title", "severity", "status", "detected_at", "created_at"}, "-detected_at")
    return jsonify(paginated(stmt, _out))


@bp.get("/<int:incident_id>")
def get_incident(incident_id):
    return jsonify(_out.dump(get_or_404(Incident, incident_id, "Insiden")))


@bp.route("/<int:incident_id>", methods=["PUT", "PATCH"])
def update_incident(incident_id):
    incident = get_or_404(Incident, incident_id, "Insiden")
    data = load_body(IncidentIn(), partial=request.method == "PATCH")
    if "asset_ids" in data:
        raise ApiError(422, "VALIDATION_ERROR", "Input tidak valid.", {"asset_ids": ["Gunakan endpoint /incidents/{id}/assets."]})
    _check_refs(data)
    if data.get("detected_at"):
        data["detected_at"] = data["detected_at"].replace(tzinfo=None)
    for k, v in data.items():
        setattr(incident, k, v)
    record_audit("UPDATE", "incident", incident.id)
    db.session.commit()
    return jsonify(_out.dump(incident))


@bp.patch("/<int:incident_id>/status")
def change_status(incident_id):
    incident = get_or_404(Incident, incident_id, "Insiden")
    new = load_body(StatusIn())["status"]
    if new not in TRANSITIONS[incident.status]:
        raise ApiError(409, "INVALID_TRANSITION", f"Transisi status {incident.status} -> {new} tidak diizinkan.",
                       {"allowed": sorted(TRANSITIONS[incident.status])})
    old = incident.status
    incident.status = new
    incident.resolved_at = utcnow() if new == "resolved" else (None if new == "investigating" else incident.resolved_at)
    record_audit("STATUS_CHANGE", "incident", incident.id, f"{old} -> {new}")
    db.session.commit()
    return jsonify(_out.dump(incident))


@bp.delete("/<int:incident_id>")
def delete_incident(incident_id):
    incident = get_or_404(Incident, incident_id, "Insiden")
    db.session.delete(incident)
    record_audit("DELETE", "incident", incident_id)
    db.session.commit()
    return "", 204


@bp.post("/<int:incident_id>/assets")
def link_asset(incident_id):
    incident = get_or_404(Incident, incident_id, "Insiden")
    data = load_body(LinkAssetIn())
    ensure_exists(Asset, data["asset_id"], "asset_id", "Aset")
    if db.session.get(IncidentAsset, (incident_id, data["asset_id"])):
        raise ApiError(409, "CONFLICT", "Aset sudah tertaut pada insiden ini.")
    incident.asset_links.append(IncidentAsset(asset_id=data["asset_id"], impact_note=data["impact_note"]))
    record_audit("LINK_ASSET", "incident", incident_id, f"asset_id={data['asset_id']}")
    db.session.commit()
    return jsonify(_out.dump(incident)), 201


@bp.delete("/<int:incident_id>/assets/<int:asset_id>")
def unlink_asset(incident_id, asset_id):
    link = db.session.get(IncidentAsset, (incident_id, asset_id))
    if link is None:
        raise ApiError(404, "NOT_FOUND", "Tautan aset-insiden tidak ditemukan.")
    db.session.delete(link)
    record_audit("UNLINK_ASSET", "incident", incident_id, f"asset_id={asset_id}")
    db.session.commit()
    return "", 204
