# SecIncident API

MVP REST API untuk **pelaporan dan pelacakan insiden keamanan siber** (domain *cybersecurity*).
Dibuat untuk UTS Pemrograman Web Lanjut (TK070), Universitas AMIKOM Yogyakarta, TA 2026/2027.

- Stack: Python 3.12, Flask, Flask-SQLAlchemy (ORM), Flask-Migrate (Alembic), Marshmallow, SQLite (lokal) / MySQL-MariaDB (opsional), pytest
- Arsitektur: **MVC** (Model = `app/models`, View = `app/schemas`, Controller = `app/controllers`)

## 1. Masalah, Pengguna, Fitur, Batasan

**Masalah.** Insiden keamanan di organisasi kecil/kampus sering dilaporkan lewat chat atau email tanpa catatan terpusat: tingkat keparahan tidak seragam, aset terdampak tidak jelas, status penanganan tidak terlacak, dan tidak ada jejak audit.

**Pengguna.** `reporter` (staf/mahasiswa pelapor), `analyst` (tim keamanan yang menangani), `admin` (pengelola sistem).

**Fitur utama.** Pelaporan insiden dengan kategori dan severity; inventaris aset beserta tingkat kekritisan; penautan aset terdampak ke insiden; workflow status tervalidasi (`open -> investigating -> contained -> resolved -> closed`); pencarian, filter, sorting, paginasi; audit log otomatis; ringkasan statistik.

**Batasan.** Autentikasi memakai satu API key (header `X-API-Key`), JWT per-user direncanakan untuk UAS; tidak ada scanning/eksploitasi sistem apa pun; seluruh data bersifat sintetis; tanpa upload file; tanpa notifikasi.

**Aset, aktor, risiko, jenis insiden.** Aset: aplikasi, server, workstation, jaringan, perangkat IoT. Aktor: reporter, analyst, admin (pelaku ancaman tidak dimodelkan, hanya dampaknya). Jenis insiden (kategori seed): Phishing, Malware, Brute Force, Data Leak, Misconfiguration. Risiko = kombinasi `severity` insiden dan `criticality` aset.

## 2. ERD

![ERD](docs/erd.png)

```mermaid
erDiagram
    users ||--o{ assets : "memiliki (owner_id)"
    users ||--o{ incidents : "melaporkan (reporter_id)"
    users ||--o{ incidents : "ditugaskan (assignee_id)"
    users ||--o{ audit_logs : "aktor (user_id)"
    incident_categories ||--o{ incidents : "category_id"
    incidents ||--o{ incident_assets : "incident_id"
    assets ||--o{ incident_assets : "asset_id"
```

Enam tabel: `users`, `incident_categories`, `assets`, `incidents`, `incident_assets` (tabel asosiasi M:N dengan atribut `impact_note`), `audit_logs`. Foreign key ditegakkan (`PRAGMA foreign_keys=ON` untuk SQLite).

## 3. Instalasi dan Menjalankan

```bash
git clone <URL-REPO-ANDA> && cd secincident-api
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # lalu isi API_KEY (Windows: copy)
```

Konfigurasi lewat environment variable: `API_KEY` (wajib diganti), `DATABASE_URL` (default `sqlite:///secincident.db`; MySQL: `mysql+pymysql://user:pass@host/db`, install `pymysql`).

**Membuat database (migrasi) dan seed data sintetis:**

```bash
export FLASK_APP=wsgi.py        # Windows PowerShell: $env:FLASK_APP="wsgi.py"
flask db upgrade                # menjalankan migrasi di migrations/
flask seed                      # 4 user, 5 kategori, 5 aset, 8 insiden (password seed: Password123!)
# alternatif tanpa Alembic: flask init-db
```

**Menjalankan aplikasi:**

```bash
export API_KEY=dev-secret-key
flask run                       # http://127.0.0.1:5000
```

**Menjalankan test:** `python -m pytest -v` (20 test, memakai SQLite in-memory).

## 4. Autentikasi dan Keamanan Dasar

- Semua endpoint `/api/v1/*` memerlukan header `X-API-Key` (dibandingkan dengan `hmac.compare_digest`). `GET /health` terbuka.
- Header opsional `X-Actor-Id: <user_id>` mencatat pelaku pada audit log.
- Password di-hash (`werkzeug`), tidak pernah dikembalikan di response.
- Semua query lewat ORM (parameterized, tahan SQL injection); field tak dikenal ditolak; batas ukuran body 1 MB; whitelist field `sort`; `per_page` maksimum 100.
- Header keamanan: `X-Content-Type-Options`, `X-Frame-Options`, `Cache-Control: no-store`, `Content-Security-Policy`.
- Error 500 tidak membocorkan detail internal; audit log hanya bisa dibaca.

## 5. Format Response

Sukses daftar: `{"data": [...], "meta": {"page", "per_page", "total", "pages"}}`

Error (konsisten di semua endpoint):

```json
{"error": {"code": "VALIDATION_ERROR", "message": "Input tidak valid.", "details": {"severity": ["Must be one of: low, medium, high, critical."]}}}
```

| Status | Arti |
|---|---|
| 200 / 201 / 204 | Berhasil / dibuat / dihapus tanpa isi |
| 400 | JSON rusak atau parameter query tidak valid |
| 401 | API key tidak ada atau salah |
| 404 | Data tidak ditemukan |
| 409 | Duplikat, data masih direferensikan, atau transisi status tidak valid |
| 422 | Validasi input gagal |

## 6. Daftar Endpoint

Rincian lengkap request/response: [`docs/openapi.yaml`](docs/openapi.yaml). Koleksi Postman: [`docs/postman_collection.json`](docs/postman_collection.json) (import, variabel `base_url` dan `api_key`).

| Method | Path | Fungsi | Sukses |
|---|---|---|---|
| GET | `/health` | Cek layanan | 200 |
| POST/GET | `/api/v1/users` | Buat / daftar user (filter `role`, `q`) | 201 / 200 |
| GET/PUT/PATCH/DELETE | `/api/v1/users/{id}` | Detail / ganti / ubah sebagian / hapus | 200 / 204 |
| POST/GET | `/api/v1/categories` | Buat / daftar kategori | 201 / 200 |
| GET/PUT/PATCH/DELETE | `/api/v1/categories/{id}` | CRUD kategori | 200 / 204 |
| POST/GET | `/api/v1/assets` | Buat / daftar aset (filter `asset_type`, `criticality`, `owner_id`, `q`) | 201 / 200 |
| GET/PUT/PATCH/DELETE | `/api/v1/assets/{id}` | CRUD aset | 200 / 204 |
| POST/GET | `/api/v1/incidents` | Lapor / daftar insiden | 201 / 200 |
| GET/PUT/PATCH/DELETE | `/api/v1/incidents/{id}` | CRUD insiden | 200 / 204 |
| PATCH | `/api/v1/incidents/{id}/status` | Ubah status sesuai workflow | 200 |
| POST | `/api/v1/incidents/{id}/assets` | Tautkan aset terdampak | 201 |
| DELETE | `/api/v1/incidents/{id}/assets/{asset_id}` | Lepas tautan | 204 |
| GET | `/api/v1/audit-logs` | Audit log (read-only) | 200 |
| GET | `/api/v1/stats/summary` | Statistik per severity/status | 200 |

**Pencarian, filter, sorting, paginasi** pada `GET /api/v1/incidents`: `?status=open&severity=high&category_id=1&q=phishing&sort=-detected_at,title&page=1&per_page=10`

## 7. Contoh Request dan Response

```bash
# Membuat insiden
curl -X POST http://127.0.0.1:5000/api/v1/incidents \
  -H "X-API-Key: dev-secret-key" -H "X-Actor-Id: 4" -H "Content-Type: application/json" \
  -d '{"title":"Email phishing menyasar staf","description":"Beberapa staf menerima email palsu.","severity":"high","category_id":1,"reporter_id":4,"asset_ids":[3]}'
```
```json
{"id": 9, "title": "Email phishing menyasar staf", "severity": "high", "status": "open",
 "category": {"id": 1, "name": "Phishing"}, "reporter_id": 4, "assignee_id": null,
 "assets": [{"id": 3, "name": "Laptop Staf Keuangan", "asset_type": "workstation", "impact_note": null}],
 "detected_at": "2026-11-16T08:00:00", "resolved_at": null, "created_at": "...", "updated_at": "..."}
```

```bash
# Transisi status tidak valid -> 409
curl -X PATCH http://127.0.0.1:5000/api/v1/incidents/9/status \
  -H "X-API-Key: dev-secret-key" -H "Content-Type: application/json" -d '{"status":"resolved"}'
```
```json
{"error": {"code": "INVALID_TRANSITION", "message": "Transisi status open -> resolved tidak diizinkan.", "details": {"allowed": ["closed", "investigating"]}}}
```

## 8. Struktur Proyek

```
app/models/        # Model (ORM)
app/schemas/       # View: validasi input & serialisasi output
app/controllers/   # Controller: blueprint & logika endpoint
app/utils/         # error handler, helper auth/paginasi/audit
migrations/        # Alembic
tests/             # pytest
docs/              # ERD, OpenAPI, Postman, rencana UAS
tools/gen_docs.py  # generator OpenAPI + Postman
```

## 9. Sumber, Library, dan Bantuan AI

Library: Flask 3.1.3, Flask-SQLAlchemy 3.1.1, Flask-Migrate 4.1.0, SQLAlchemy 2.1.8, Marshmallow 4.4.0, pytest 9.2.0 (dokumentasi resmi masing-masing). Graphviz dipakai untuk membuat gambar ERD.

**Bantuan AI:** kerangka kode, test, dokumentasi, dan generator OpenAPI/Postman disusun dengan bantuan Claude (Anthropic), kemudian dijalankan, diuji, dan dipelajari oleh penulis. Sesuai ketentuan soal, penggunaan ini dicatat di sini.

## 10. Rencana UAS

Lihat [`docs/RENCANA_UAS.md`](docs/RENCANA_UAS.md).

## Lisensi / Tautan

- Repository: `<ISI URL GITHUB>`
- Demo: `<ISI URL DEMO>`
- Release: `v1.0`
