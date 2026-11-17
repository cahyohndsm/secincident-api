"""Lapisan View: validasi input (load) dan representasi JSON output (dump)."""
import ipaddress

from marshmallow import Schema, ValidationError, fields, validate

SEVERITIES = ["low", "medium", "high", "critical"]
STATUSES = ["open", "investigating", "contained", "resolved", "closed"]
ASSET_TYPES = ["server", "workstation", "network", "application", "iot"]
ROLES = ["admin", "analyst", "reporter"]


def _valid_ip(value):
    try:
        ipaddress.ip_address(value)
    except ValueError:
        raise ValidationError("Alamat IP tidak valid.")



# ---------- User ----------
class UserIn(Schema):
    username = fields.String(required=True, validate=validate.Regexp(r"^[A-Za-z0-9_.-]{3,50}$", error="3-50 karakter: huruf, angka, _ . -"))
    email = fields.Email(required=True, validate=validate.Length(max=120))
    password = fields.String(required=True, load_only=True, validate=validate.Length(min=8, max=128))
    role = fields.String(load_default="reporter", validate=validate.OneOf(ROLES))


class UserOut(Schema):
    id = fields.Int()
    username = fields.Str()
    email = fields.Str()
    role = fields.Str()
    created_at = fields.DateTime()


# ---------- Category ----------
class CategoryIn(Schema):
    name = fields.String(required=True, validate=validate.Length(min=3, max=80))
    description = fields.String(load_default=None, validate=validate.Length(max=255))
    default_severity = fields.String(load_default="medium", validate=validate.OneOf(SEVERITIES))


class CategoryOut(Schema):
    id = fields.Int()
    name = fields.Str()
    description = fields.Str()
    default_severity = fields.Str()


# ---------- Asset ----------
class AssetIn(Schema):
    name = fields.String(required=True, validate=validate.Length(min=2, max=100))
    asset_type = fields.String(required=True, validate=validate.OneOf(ASSET_TYPES))
    ip_address = fields.String(load_default=None, allow_none=True, validate=_valid_ip)
    criticality = fields.String(load_default="medium", validate=validate.OneOf(SEVERITIES))
    owner_id = fields.Int(required=True, strict=True)


class AssetOut(Schema):
    id = fields.Int()
    name = fields.Str()
    asset_type = fields.Str()
    ip_address = fields.Str()
    criticality = fields.Str()
    owner_id = fields.Int()
    created_at = fields.DateTime()


# ---------- Incident ----------
class IncidentIn(Schema):
    title = fields.String(required=True, validate=validate.Length(min=5, max=150))
    description = fields.String(required=True, validate=validate.Length(min=10, max=5000))
    severity = fields.String(required=True, validate=validate.OneOf(SEVERITIES))
    category_id = fields.Int(required=True, strict=True)
    reporter_id = fields.Int(required=True, strict=True)
    assignee_id = fields.Int(load_default=None, allow_none=True, strict=True)
    detected_at = fields.DateTime(load_default=None, allow_none=True)
    asset_ids = fields.List(fields.Int(strict=True), load_default=list, validate=validate.Length(max=50))


class StatusIn(Schema):
    status = fields.String(required=True, validate=validate.OneOf(STATUSES))


class LinkAssetIn(Schema):
    asset_id = fields.Int(required=True, strict=True)
    impact_note = fields.String(load_default=None, validate=validate.Length(max=255))


class IncidentOut(Schema):
    id = fields.Int()
    title = fields.Str()
    description = fields.Str()
    severity = fields.Str()
    status = fields.Str()
    category = fields.Method("get_category")
    reporter_id = fields.Int()
    assignee_id = fields.Int(allow_none=True)
    detected_at = fields.DateTime()
    resolved_at = fields.DateTime(allow_none=True)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
    assets = fields.Method("get_assets")

    def get_category(self, obj):
        return {"id": obj.category.id, "name": obj.category.name}

    def get_assets(self, obj):
        return [
            {"id": l.asset.id, "name": l.asset.name, "asset_type": l.asset.asset_type, "impact_note": l.impact_note}
            for l in obj.asset_links
        ]


class AuditOut(Schema):
    id = fields.Int()
    user_id = fields.Int(allow_none=True)
    action = fields.Str()
    entity = fields.Str()
    entity_id = fields.Int(allow_none=True)
    detail = fields.Str(allow_none=True)
    created_at = fields.DateTime()
