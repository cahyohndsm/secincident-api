from app.extensions import db
from app.models.user import utcnow


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(20), nullable=False)  # CREATE|UPDATE|DELETE|STATUS_CHANGE|LINK_ASSET|UNLINK_ASSET
    entity = db.Column(db.String(30), nullable=False)
    entity_id = db.Column(db.Integer)
    detail = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
