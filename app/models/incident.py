from app.extensions import db
from app.models.user import utcnow


class Incident(db.Model):
    __tablename__ = "incidents"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(10), nullable=False)  # low|medium|high|critical
    status = db.Column(db.String(15), nullable=False, default="open")
    category_id = db.Column(db.Integer, db.ForeignKey("incident_categories.id"), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    detected_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    resolved_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    category = db.relationship("IncidentCategory")
    reporter = db.relationship("User", foreign_keys=[reporter_id])
    assignee = db.relationship("User", foreign_keys=[assignee_id])
    asset_links = db.relationship("IncidentAsset", cascade="all, delete-orphan", back_populates="incident")


class IncidentAsset(db.Model):
    """Tabel asosiasi M:N antara incidents dan assets (aset terdampak)."""
    __tablename__ = "incident_assets"

    incident_id = db.Column(db.Integer, db.ForeignKey("incidents.id"), primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("assets.id"), primary_key=True)
    impact_note = db.Column(db.String(255))

    incident = db.relationship("Incident", back_populates="asset_links")
    asset = db.relationship("Asset")
