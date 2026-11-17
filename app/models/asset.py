from app.extensions import db
from app.models.user import utcnow


class Asset(db.Model):
    __tablename__ = "assets"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    asset_type = db.Column(db.String(20), nullable=False)  # server|workstation|network|application|iot
    ip_address = db.Column(db.String(45))
    criticality = db.Column(db.String(10), nullable=False, default="medium")
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    owner = db.relationship("User")
