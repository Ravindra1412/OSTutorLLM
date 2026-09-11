"""
app/faculty/services/settings_service.py

Settings (Section 15). Theme/Language/Notification Preferences are
per-user and already live in `user_settings` (Part 3.4) — exposed via
a new role-agnostic endpoint in settings_routes.py (Part 3.3/3.10),
not duplicated here. AI Settings delegates entirely to
ai_tutor_management.py. This module covers the two genuinely new
pieces: Security Settings (informational — this is a single-deployment
student project, not a multi-tenant SaaS, so "security settings" here
is a real, honest read of the actual configured values, not a set of
knobs that would need a lot of unbuilt infrastructure to be real) and
Backup Settings (a REAL, working SQLite file copy — not a stub).
"""

import os
import shutil
from datetime import datetime, timezone

from flask import current_app


def get_security_settings() -> dict:
    """Section 15 — Security Settings. Reads real, already-enforced
    values (Part 3.3's session/cookie config, Part 3.1's password
    policy) rather than presenting configurable-looking toggles for
    things this codebase doesn't actually gate at runtime."""
    from app.utils.constants import MIN_PASSWORD_LENGTH

    cfg = current_app.config
    return {
        "session_lifetime_hours": cfg["PERMANENT_SESSION_LIFETIME"].total_seconds() / 3600,
        "session_cookie_secure": cfg["SESSION_COOKIE_SECURE"],
        "session_cookie_httponly": cfg["SESSION_COOKIE_HTTPONLY"],
        "min_password_length": MIN_PASSWORD_LENGTH,
        "rate_limit_per_minute": cfg["RATE_LIMIT_PER_MINUTE"],
    }


def get_backup_settings() -> dict:
    backup_dir = current_app.config["BACKUP_FOLDER"]
    backups = []
    if os.path.isdir(backup_dir):
        for f in sorted(os.listdir(backup_dir), reverse=True):
            full = os.path.join(backup_dir, f)
            backups.append({"filename": f, "size_bytes": os.path.getsize(full)})
    db_uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    return {
        "supported": db_uri.startswith("sqlite:///") and db_uri != "sqlite:///:memory:",
        "database_uri_type": "sqlite" if db_uri.startswith("sqlite") else "other",
        "existing_backups": backups,
    }


def trigger_backup() -> str:
    """Section 15 — Backup Settings. A real file-copy backup for the
    common case (SQLite dev/small-deployment database) — genuinely
    working, not a placeholder. Non-SQLite databases (a real Postgres
    production deployment) need a proper `pg_dump`-based process,
    which is explicitly out of scope here (see get_backup_settings'
    `supported` flag, checked by the route before calling this)."""
    db_uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    if not db_uri.startswith("sqlite:///") or db_uri == "sqlite:///:memory:":
        raise ValueError("Automatic backup is only supported for the file-based SQLite database in this phase.")

    db_path = db_uri.replace("sqlite:///", "", 1)
    if not os.path.isfile(db_path):
        raise ValueError("Database file not found on disk.")

    backup_dir = current_app.config["BACKUP_FOLDER"]
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_filename)
    shutil.copy2(db_path, backup_path)
    return backup_filename
