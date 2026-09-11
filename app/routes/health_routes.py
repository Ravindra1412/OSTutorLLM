"""
app/routes/health_routes.py

Health Check blueprint (Section 9). Used by deployment orchestration
(Docker/Gunicorn health checks, future CI/CD readiness probes — Part 3.1
Section 24) to verify the app process is alive and the database is
reachable, without requiring authentication.
"""

from datetime import datetime, timezone

from flask import Blueprint
from sqlalchemy import text

from app.extensions import db
from app.utils.formatters import success_response

health_bp = Blueprint("health_bp", __name__)


@health_bp.route("/health", methods=["GET"])
def health():
    """Lightweight liveness check — does not touch the database.
    Suitable for a container orchestrator's fast, frequent health probe."""
    return success_response({"status": "alive"}, message="OSTutorLLM backend is running.")


@health_bp.route("/status", methods=["GET"])
def status():
    """Deeper readiness check — verifies the database connection is
    actually usable, not just that the process is running."""
    db_ok = True
    db_error = None
    try:
        db.session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — intentionally broad for a health probe
        db_ok = False
        db_error = str(exc)

    payload = {
        "app": "OSTutorLLM",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": "connected" if db_ok else "unreachable",
    }

    if not db_ok:
        payload["database_error"] = db_error
        return success_response(payload, message="Service degraded.", status_code=503)

    return success_response(payload, message="All systems operational.")
