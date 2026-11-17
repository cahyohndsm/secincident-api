# Rencana Pengembangan untuk UAS

| Tahap | Fokus | Keluaran | Alasan / Keputusan Desain |
|---|---|---|---|
| 1 | **Autentikasi & otorisasi JWT** (Flask-JWT-Extended) | Endpoint `POST /auth/login`, access + refresh token, RBAC `admin`/`analyst`/`reporter` | API key UTS hanya satu kunci bersama dan tidak mengenal identitas. JWT memberi identitas per user sehingga `X-Actor-Id` pada audit log diganti klaim token yang tidak bisa dipalsukan. |
| 2 | **Penguatan keamanan** | Rate limiting login (Flask-Limiter), pembatasan CORS, validasi ukuran upload, `bandit` + `pip-audit` pada CI | Mengurangi risiko brute force dan dependensi rentan. |
| 3 | **Optimasi query** | Index pada `incidents(status, severity, detected_at)` dan `audit_logs(entity, entity_id)`; `selectinload` untuk relasi aset; ukur dengan `EXPLAIN QUERY PLAN` | Daftar insiden adalah endpoint paling sering dipakai dan memuat relasi, rawan N+1. |
| 4 | **Synthetic data** | Skrip `Faker` menghasilkan 5.000+ insiden sintetis | Menguji paginasi dan performa tanpa data nyata. |
| 5 | **Dokumentasi & deployment** | Swagger UI pada `/docs`, Dockerfile + Gunicorn, deploy ke PythonAnywhere/Render, MySQL/MariaDB | Dosen dapat menguji langsung; konfigurasi lewat environment variable. |
| 6 | **Frontend/visualisasi** | Dashboard ringkas (Chart.js) memakai `GET /stats/summary`: insiden per severity, status, dan tren harian | Menampilkan nilai praktis bagi analis SOC dan melengkapi demo. |
| 7 | **Otomasi mutu** | GitHub Actions menjalankan `pytest` setiap push; rilis `v2.0` | Menjaga kualitas dan memenuhi kebutuhan commit/release bertahap. |

**Urutan prioritas bila waktu terbatas:** JWT (1), index + query (3), CI (7), Swagger (5), dashboard (6).

**Risiko & mitigasi:** SQLite tidak cocok untuk beban konkuren tinggi, maka siapkan konfigurasi MySQL/MariaDB (`DATABASE_URL`); migrasi Alembic sudah disiapkan sehingga perpindahan database cukup mengganti URL lalu `flask db upgrade`.
