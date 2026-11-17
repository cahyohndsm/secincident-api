from tests.conftest import H, incident_payload


# ---------- Dasar & keamanan ----------
def test_health_tanpa_auth(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.get_json()["status"] == "ok"


def test_tanpa_api_key_ditolak(client):
    r = client.get("/api/v1/incidents")
    assert r.status_code == 401
    assert r.get_json()["error"]["code"] == "UNAUTHORIZED"


def test_security_headers(client):
    r = client.get("/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"


def test_404_format_konsisten(client):
    r = client.get("/api/v1/incidents/999", headers=H)
    assert r.status_code == 404
    assert set(r.get_json()["error"]) >= {"code", "message"}


# ---------- Users ----------
def test_buat_user_berhasil_dan_password_tidak_bocor(client):
    r = client.post("/api/v1/users", json={"username": "budi", "email": "budi@example.test", "password": "Password123!"}, headers=H)
    assert r.status_code == 201
    body = r.get_json()
    assert body["role"] == "reporter" and "password" not in body and "password_hash" not in body


def test_user_validasi_gagal(client):
    r = client.post("/api/v1/users", json={"username": "b", "email": "bukan-email", "password": "123"}, headers=H)
    assert r.status_code == 422
    d = r.get_json()["error"]["details"]
    assert {"username", "email", "password"} <= set(d)


def test_user_duplikat_409(client, base):
    r = client.post("/api/v1/users", json={"username": "rina", "email": "lain@example.test", "password": "Password123!"}, headers=H)
    assert r.status_code == 409


def test_field_tak_dikenal_ditolak(client):
    r = client.post("/api/v1/users", json={"username": "budi", "email": "b@example.test", "password": "Password123!", "is_admin": True}, headers=H)
    assert r.status_code == 422


def test_json_tidak_valid_400(client):
    r = client.post("/api/v1/users", data="bukan json", headers=H)
    assert r.status_code == 400 and r.get_json()["error"]["code"] == "INVALID_JSON"


# ---------- Incidents: CRUD ----------
def test_buat_insiden_berhasil_dengan_aset(client, base):
    r = client.post("/api/v1/incidents", json=incident_payload(base, asset_ids=[base["asset"]]), headers=H)
    assert r.status_code == 201
    b = r.get_json()
    assert b["status"] == "open" and b["category"]["name"] == "Phishing" and b["assets"][0]["id"] == base["asset"]


def test_insiden_validasi_gagal(client, base):
    r = client.post("/api/v1/incidents", json=incident_payload(base, severity="parah", title="x"), headers=H)
    assert r.status_code == 422
    assert {"severity", "title"} <= set(r.get_json()["error"]["details"])


def test_insiden_fk_tidak_valid_422(client, base):
    r = client.post("/api/v1/incidents", json=incident_payload(base, category_id=999), headers=H)
    assert r.status_code == 422 and "category_id" in r.get_json()["error"]["details"]


def test_get_update_patch_delete_insiden(client, base):
    iid = client.post("/api/v1/incidents", json=incident_payload(base), headers=H).get_json()["id"]
    assert client.get(f"/api/v1/incidents/{iid}", headers=H).status_code == 200
    r = client.patch(f"/api/v1/incidents/{iid}", json={"severity": "critical"}, headers=H)
    assert r.status_code == 200 and r.get_json()["severity"] == "critical"
    assert r.get_json()["title"] == "Percobaan phishing"  # PATCH tidak menimpa field lain
    r = client.put(f"/api/v1/incidents/{iid}", json={"severity": "low"}, headers=H)
    assert r.status_code == 422  # PUT wajib lengkap
    assert client.delete(f"/api/v1/incidents/{iid}", headers=H).status_code == 204
    assert client.get(f"/api/v1/incidents/{iid}", headers=H).status_code == 404


# ---------- Status workflow ----------
def test_transisi_status_valid_dan_invalid(client, base):
    iid = client.post("/api/v1/incidents", json=incident_payload(base), headers=H).get_json()["id"]
    r = client.patch(f"/api/v1/incidents/{iid}/status", json={"status": "resolved"}, headers=H)
    assert r.status_code == 409 and r.get_json()["error"]["code"] == "INVALID_TRANSITION"
    assert client.patch(f"/api/v1/incidents/{iid}/status", json={"status": "investigating"}, headers=H).status_code == 200
    r = client.patch(f"/api/v1/incidents/{iid}/status", json={"status": "resolved"}, headers=H)
    assert r.status_code == 200 and r.get_json()["resolved_at"] is not None


# ---------- Filter, sort, pagination ----------
def test_filter_sort_pagination(client, base):
    for i, sev in enumerate(["low", "high", "critical", "high", "medium"]):
        client.post("/api/v1/incidents", json=incident_payload(base, title=f"Insiden nomor {i}", severity=sev), headers=H)
    r = client.get("/api/v1/incidents?severity=high", headers=H).get_json()
    assert r["meta"]["total"] == 2
    r = client.get("/api/v1/incidents?per_page=2&page=2&sort=title", headers=H).get_json()
    assert len(r["data"]) == 2 and r["meta"] == {"page": 2, "per_page": 2, "total": 5, "pages": 3}
    assert [d["title"] for d in r["data"]] == ["Insiden nomor 2", "Insiden nomor 3"]
    assert client.get("/api/v1/incidents?q=nomor 4", headers=H).get_json()["meta"]["total"] == 1
    assert client.get("/api/v1/incidents?sort=password", headers=H).status_code == 400
    assert client.get("/api/v1/incidents?per_page=1000", headers=H).status_code == 400


# ---------- Aset terdampak ----------
def test_link_unlink_aset(client, base):
    iid = client.post("/api/v1/incidents", json=incident_payload(base), headers=H).get_json()["id"]
    r = client.post(f"/api/v1/incidents/{iid}/assets", json={"asset_id": base["asset"], "impact_note": "Terenkripsi"}, headers=H)
    assert r.status_code == 201
    assert client.post(f"/api/v1/incidents/{iid}/assets", json={"asset_id": base["asset"]}, headers=H).status_code == 409
    assert client.delete(f"/api/v1/assets/{base['asset']}", headers=H).status_code == 409  # masih tertaut
    assert client.delete(f"/api/v1/incidents/{iid}/assets/{base['asset']}", headers=H).status_code == 204


# ---------- Integritas ----------
def test_hapus_kategori_yang_dipakai_409(client, base):
    client.post("/api/v1/incidents", json=incident_payload(base), headers=H)
    assert client.delete(f"/api/v1/categories/{base['cat']}", headers=H).status_code == 409


def test_asset_ip_tidak_valid(client, base):
    r = client.post("/api/v1/assets", json={"name": "Srv", "asset_type": "server", "ip_address": "999.1.1.1", "owner_id": base["user"]}, headers=H)
    assert r.status_code == 422


# ---------- Audit & statistik ----------
def test_audit_log_tercatat(client, base):
    h = {**H, "X-Actor-Id": str(base["user"])}
    iid = client.post("/api/v1/incidents", json=incident_payload(base), headers=h).get_json()["id"]
    client.patch(f"/api/v1/incidents/{iid}/status", json={"status": "investigating"}, headers=h)
    logs = client.get(f"/api/v1/audit-logs?entity=incident&entity_id={iid}&sort=id", headers=H).get_json()["data"]
    assert [l["action"] for l in logs] == ["CREATE", "STATUS_CHANGE"]
    assert logs[0]["user_id"] == base["user"]
    assert client.delete("/api/v1/audit-logs", headers=H).status_code == 405  # tidak bisa dihapus


def test_statistik(client, base):
    client.post("/api/v1/incidents", json=incident_payload(base), headers=H)
    s = client.get("/api/v1/stats/summary", headers=H).get_json()
    assert s["total_incidents"] == 1 and s["by_severity"] == {"high": 1}
