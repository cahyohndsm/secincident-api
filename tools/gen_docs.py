"""Menghasilkan docs/openapi.yaml dan docs/postman_collection.json dari satu daftar endpoint."""
import json
import re
from pathlib import Path

import yaml

DOCS = Path(__file__).resolve().parent.parent / "docs"

NEW_INCIDENT = {"title": "Email phishing menyasar staf", "description": "Beberapa staf menerima email palsu meminta reset password.",
                "severity": "high", "category_id": 1, "reporter_id": 4, "assignee_id": 2, "asset_ids": [3]}
# (method, path, ringkasan, body, status sukses, status error, query)
E = [
    ("GET", "/health", "Cek kesehatan layanan (tanpa API key)", None, 200, [], {}),
    ("POST", "/api/v1/users", "Buat user", {"username": "analyst3", "email": "analyst3@example.test", "password": "Password123!", "role": "analyst"}, 201, [401, 409, 422], {}),
    ("GET", "/api/v1/users", "Daftar user (filter role, q; sort; paginasi)", None, 200, [401], {"role": "analyst", "q": "analyst", "sort": "username", "page": "1", "per_page": "10"}),
    ("GET", "/api/v1/users/{id}", "Detail user", None, 200, [401, 404], {}),
    ("PUT", "/api/v1/users/{id}", "Ganti user (lengkap)", {"username": "analyst3", "email": "analyst3@example.test", "password": "Password123!", "role": "analyst"}, 200, [401, 404, 409, 422], {}),
    ("PATCH", "/api/v1/users/{id}", "Ubah sebagian user", {"role": "admin"}, 200, [401, 404, 422], {}),
    ("DELETE", "/api/v1/users/{id}", "Hapus user (409 bila masih direferensikan)", None, 204, [401, 404, 409], {}),
    ("POST", "/api/v1/categories", "Buat kategori insiden", {"name": "Insider Threat", "description": "Ancaman dari orang dalam", "default_severity": "high"}, 201, [401, 409, 422], {}),
    ("GET", "/api/v1/categories", "Daftar kategori", None, 200, [401], {"sort": "name"}),
    ("GET", "/api/v1/categories/{id}", "Detail kategori", None, 200, [401, 404], {}),
    ("PUT", "/api/v1/categories/{id}", "Ganti kategori", {"name": "Insider Threat", "description": "Ancaman orang dalam", "default_severity": "high"}, 200, [401, 404, 409, 422], {}),
    ("PATCH", "/api/v1/categories/{id}", "Ubah sebagian kategori", {"default_severity": "critical"}, 200, [401, 404, 422], {}),
    ("DELETE", "/api/v1/categories/{id}", "Hapus kategori (409 bila dipakai insiden)", None, 204, [401, 404, 409], {}),
    ("POST", "/api/v1/assets", "Buat aset", {"name": "Server File Prodi", "asset_type": "server", "ip_address": "10.0.0.30", "criticality": "high", "owner_id": 1}, 201, [401, 422], {}),
    ("GET", "/api/v1/assets", "Daftar aset (filter asset_type, criticality, owner_id, q)", None, 200, [401], {"asset_type": "server", "criticality": "high", "q": "server", "sort": "-criticality"}),
    ("GET", "/api/v1/assets/{id}", "Detail aset", None, 200, [401, 404], {}),
    ("PUT", "/api/v1/assets/{id}", "Ganti aset", {"name": "Server File Prodi", "asset_type": "server", "ip_address": "10.0.0.31", "criticality": "high", "owner_id": 1}, 200, [401, 404, 422], {}),
    ("PATCH", "/api/v1/assets/{id}", "Ubah sebagian aset", {"criticality": "critical"}, 200, [401, 404, 422], {}),
    ("DELETE", "/api/v1/assets/{id}", "Hapus aset (409 bila tertaut insiden)", None, 204, [401, 404, 409], {}),
    ("POST", "/api/v1/incidents", "Laporkan insiden baru", NEW_INCIDENT, 201, [401, 422], {}),
    ("GET", "/api/v1/incidents", "Daftar insiden (filter status, severity, category_id, assignee_id, reporter_id, asset_id, q; sort; paginasi)", None, 200, [400, 401], {"status": "open", "severity": "high", "q": "phishing", "sort": "-detected_at", "page": "1", "per_page": "10"}),
    ("GET", "/api/v1/incidents/{id}", "Detail insiden beserta aset terdampak", None, 200, [401, 404], {}),
    ("PUT", "/api/v1/incidents/{id}", "Ganti insiden (lengkap)", {k: v for k, v in NEW_INCIDENT.items() if k != "asset_ids"}, 200, [401, 404, 422], {}),
    ("PATCH", "/api/v1/incidents/{id}", "Ubah sebagian insiden", {"severity": "critical"}, 200, [401, 404, 422], {}),
    ("PATCH", "/api/v1/incidents/{id}/status", "Ubah status (workflow tervalidasi)", {"status": "investigating"}, 200, [401, 404, 409, 422], {}),
    ("DELETE", "/api/v1/incidents/{id}", "Hapus insiden", None, 204, [401, 404], {}),
    ("POST", "/api/v1/incidents/{id}/assets", "Tautkan aset terdampak", {"asset_id": 2, "impact_note": "Server diisolasi"}, 201, [401, 404, 409, 422], {}),
    ("DELETE", "/api/v1/incidents/{id}/assets/{asset_id}", "Lepas tautan aset", None, 204, [401, 404], {}),
    ("GET", "/api/v1/audit-logs", "Daftar audit log (read-only; filter entity, action, user_id, entity_id)", None, 200, [401], {"entity": "incident", "action": "STATUS_CHANGE", "sort": "-id"}),
    ("GET", "/api/v1/stats/summary", "Ringkasan jumlah insiden per severity dan status", None, 200, [401], {}),
]
ERR = {400: "Request/parameter tidak valid", 401: "API key salah/tidak ada", 404: "Data tidak ditemukan",
       409: "Konflik (duplikat/referensi/transisi tidak valid)", 422: "Validasi input gagal"}


def openapi():
    paths = {}
    for m, p, s, body, ok, errs, q in E:
        op = {"summary": s, "tags": [p.split("/")[3] if p.startswith("/api") else "system"], "responses": {str(ok): {"description": "Berhasil"}}}
        if p != "/health":
            op["security"] = [{"ApiKeyAuth": []}]
        params = [{"name": n, "in": "path", "required": True, "schema": {"type": "integer"}} for n in re.findall(r"{(\w+)}", p)]
        params += [{"name": k, "in": "query", "schema": {"type": "string"}, "example": v} for k, v in q.items()]
        if params:
            op["parameters"] = params
        if body is not None:
            op["requestBody"] = {"required": True, "content": {"application/json": {"example": body}}}
        for c in errs:
            op["responses"][str(c)] = {"description": ERR[c], "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}}
        paths.setdefault(p, {})[m.lower()] = op
    return {
        "openapi": "3.0.3",
        "info": {"title": "SecIncident API", "version": "1.0.0", "description": "MVP REST API pelaporan & pelacakan insiden keamanan siber (UTS Pemrograman Web Lanjut)."},
        "servers": [{"url": "http://localhost:5000"}],
        "components": {
            "securitySchemes": {"ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"}},
            "schemas": {"Error": {"type": "object", "properties": {"error": {"type": "object", "properties": {
                "code": {"type": "string", "example": "VALIDATION_ERROR"}, "message": {"type": "string"}, "details": {"type": "object"}}}}}},
        },
        "paths": paths,
    }


def postman():
    folders = {}
    for m, p, s, body, ok, errs, q in E:
        url_path = re.sub(r"{(\w+)}", r":\1", p)
        item = {"name": f"{m} {p}", "request": {
            "method": m, "header": [{"key": "Content-Type", "value": "application/json"}] if body is not None else [],
            "url": {"raw": "{{base_url}}" + url_path, "host": ["{{base_url}}"], "path": [x for x in url_path.strip("/").split("/")]},
            "description": s}}
        if p != "/health":
            item["request"]["auth"] = {"type": "apikey", "apikey": [{"key": "key", "value": "X-API-Key"}, {"key": "value", "value": "{{api_key}}"}, {"key": "in", "value": "header"}]}
        if q:
            item["request"]["url"]["query"] = [{"key": k, "value": v} for k, v in q.items()]
        vars_ = re.findall(r"{(\w+)}", p)
        if vars_:
            item["request"]["url"]["variable"] = [{"key": v, "value": "1"} for v in vars_]
        if body is not None:
            item["request"]["body"] = {"mode": "raw", "raw": json.dumps(body, indent=2, ensure_ascii=False), "options": {"raw": {"language": "json"}}}
        item["event"] = [{"listen": "test", "script": {"type": "text/javascript", "exec": [f"pm.test('Status {ok}', () => pm.response.to.have.status({ok}));"]}}]
        folder = p.split("/")[3] if p.startswith("/api") else "system"
        folders.setdefault(folder, []).append(item)
    return {"info": {"name": "SecIncident API v1.0", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
            "variable": [{"key": "base_url", "value": "http://localhost:5000"}, {"key": "api_key", "value": "dev-secret-key"}],
            "item": [{"name": k, "item": v} for k, v in folders.items()]}


if __name__ == "__main__":
    (DOCS / "openapi.yaml").write_text(yaml.safe_dump(openapi(), sort_keys=False, allow_unicode=True), encoding="utf-8")
    (DOCS / "postman_collection.json").write_text(json.dumps(postman(), indent=2, ensure_ascii=False), encoding="utf-8")
    print("OK", len(E), "endpoint")
