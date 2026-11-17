import pytest

from app import create_app
from app.extensions import db
from config import TestConfig

H = {"X-API-Key": "test-key"}


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def base(client):
    """Siapkan user, kategori, dan aset dasar; kembalikan id-nya."""
    u = client.post("/api/v1/users", json={"username": "rina", "email": "rina@example.test", "password": "Password123!", "role": "analyst"}, headers=H).get_json()
    c = client.post("/api/v1/categories", json={"name": "Phishing", "default_severity": "high"}, headers=H).get_json()
    a = client.post("/api/v1/assets", json={"name": "Web Portal", "asset_type": "application", "ip_address": "10.0.0.5", "criticality": "high", "owner_id": u["id"]}, headers=H).get_json()
    return {"user": u["id"], "cat": c["id"], "asset": a["id"]}


def incident_payload(base, **over):
    p = {"title": "Percobaan phishing", "description": "Email palsu menyasar staf keuangan.", "severity": "high",
         "category_id": base["cat"], "reporter_id": base["user"]}
    p.update(over)
    return p
