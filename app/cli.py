import click
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import (Asset, AuditLog, Incident, IncidentAsset,
                        IncidentCategory, User)
from app.models.user import utcnow
from datetime import timedelta


def seed_data():
    """Data sintetis (bukan data nyata) untuk demo dan pengujian."""
    if db.session.query(User).count():
        return False
    pw = generate_password_hash("Password123!")
    users = [User(username=n, email=f"{n}@example.test", password_hash=pw, role=r) for n, r in
             [("admin", "admin"), ("analyst1", "analyst"), ("analyst2", "analyst"), ("reporter1", "reporter")]]
    cats = [IncidentCategory(name=n, description=d, default_severity=s) for n, d, s in [
        ("Phishing", "Email/pesan penipuan untuk mencuri kredensial", "high"),
        ("Malware", "Perangkat lunak berbahaya termasuk ransomware", "critical"),
        ("Brute Force", "Percobaan login berulang", "medium"),
        ("Data Leak", "Kebocoran data sensitif", "critical"),
        ("Misconfiguration", "Konfigurasi layanan tidak aman", "medium")]]
    db.session.add_all(users + cats)
    db.session.flush()
    admin, a1, a2, rep = users
    assets = [
        Asset(name="Web Portal Akademik", asset_type="application", ip_address="10.0.0.10", criticality="critical", owner_id=admin.id),
        Asset(name="Server Database Utama", asset_type="server", ip_address="10.0.0.20", criticality="critical", owner_id=admin.id),
        Asset(name="Laptop Staf Keuangan", asset_type="workstation", ip_address="10.0.1.15", criticality="high", owner_id=rep.id),
        Asset(name="Router Gedung A", asset_type="network", ip_address="10.0.2.1", criticality="medium", owner_id=a1.id),
        Asset(name="Sensor Suhu Lab IoT", asset_type="iot", ip_address="10.0.3.7", criticality="low", owner_id=a2.id),
    ]
    db.session.add_all(assets)
    db.session.flush()
    now = utcnow()
    specs = [
        ("Email phishing menyasar staf keuangan", "Beberapa staf menerima email palsu meminta reset password.", "high", "investigating", 0, rep, a1, [2]),
        ("Ransomware terdeteksi pada laptop", "Antivirus mendeteksi enkripsi file mencurigakan pada laptop staf.", "critical", "contained", 1, rep, a1, [2]),
        ("Brute force SSH ke server database", "Ratusan percobaan login gagal dari satu IP simulasi.", "medium", "open", 2, a2, a2, [1]),
        ("Dump data mahasiswa terekspos", "Berkas ekspor data tersimpan di folder publik.", "critical", "open", 3, rep, a1, [0, 1]),
        ("Panel admin router memakai password bawaan", "Ditemukan saat audit internal konfigurasi.", "medium", "resolved", 4, a1, a2, [3]),
        ("Sensor IoT mengirim telemetri tanpa enkripsi", "Data suhu dikirim lewat HTTP biasa.", "low", "investigating", 4, a2, a2, [4]),
        ("Percobaan login admin dari lokasi tak biasa", "Notifikasi login gagal beruntun di portal akademik.", "high", "closed", 2, a1, a1, [0]),
        ("Phishing berkedok pengumuman beasiswa", "Tautan palsu menyebar lewat grup pesan.", "medium", "open", 0, rep, None, []),
    ]
    for i, (t, d, sev, st, ci, rp, asg, aids) in enumerate(specs):
        inc = Incident(title=t, description=d, severity=sev, status=st, category_id=cats[ci].id, reporter_id=rp.id,
                       assignee_id=asg.id if asg else None, detected_at=now - timedelta(days=len(specs) - i),
                       resolved_at=now if st in ("resolved", "closed") else None)
        inc.asset_links = [IncidentAsset(asset_id=assets[a].id, impact_note="Terdampak") for a in aids]
        db.session.add(inc)
    db.session.flush()
    db.session.add(AuditLog(user_id=admin.id, action="CREATE", entity="seed", detail="Data sintetis awal dimuat"))
    db.session.commit()
    return True


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        """Buat semua tabel (alternatif cepat dari `flask db upgrade`)."""
        db.create_all()
        click.echo("Database diinisialisasi.")

    @app.cli.command("seed")
    def seed():
        """Isi data sintetis."""
        click.echo("Seed berhasil." if seed_data() else "Data sudah ada, seed dilewati.")
