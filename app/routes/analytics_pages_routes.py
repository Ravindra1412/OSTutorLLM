"""
app/routes/analytics_pages_routes.py

Dashboard/Analytics page routes (Part 3.9, Section 15). Mirrors the
exact pattern established for quiz_pages_bp (Part 3.7) and
code_review_pages_bp (Part 3.8): server-rendered HTML shells that
drive themselves via static/js/analytics_dashboard.js calling the real
JSON API in app/routes/analytics_routes.py.
"""

from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

from app.utils.constants import ROLE_STUDENT

analytics_pages_bp = Blueprint("analytics_pages_bp", __name__, url_prefix="/dashboard")


def _require_student():
    if not current_user.is_authenticated or current_user.role != ROLE_STUDENT:
        abort(403)


@analytics_pages_bp.route("", methods=["GET"])
@login_required
def dashboard_page():
    """Section 9 — Student Dashboard: overview, progress cards, level/
    XP, daily goal, recommended activities."""
    _require_student()
    return render_template("analytics/dashboard.html")


@analytics_pages_bp.route("/progress", methods=["GET"])
@login_required
def progress_page():
    """Section 15 — Progress Page: topic completion, learning calendar,
    time-spent breakdown, quiz/code review score history."""
    _require_student()
    return render_template("analytics/progress.html")


@analytics_pages_bp.route("/achievements", methods=["GET"])
@login_required
def achievements_page():
    """Section 15 — Achievement Page: badges, XP, level, streak, daily/
    weekly goals."""
    _require_student()
    return render_template("analytics/achievements.html")


@analytics_pages_bp.route("/timeline", methods=["GET"])
@login_required
def timeline_page():
    """Section 15 — Timeline: chronological learning history."""
    _require_student()
    return render_template("analytics/timeline.html")


@analytics_pages_bp.route("/recommendations", methods=["GET"])
@login_required
def recommendations_page():
    """Section 15 — Recommendation Page."""
    _require_student()
    return render_template("analytics/recommendations.html")
