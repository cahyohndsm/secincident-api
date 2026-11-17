from app.extensions import db


class IncidentCategory(db.Model):
    __tablename__ = "incident_categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    description = db.Column(db.String(255))
    default_severity = db.Column(db.String(10), nullable=False, default="medium")
