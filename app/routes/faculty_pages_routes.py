"""
app/routes/faculty_pages_routes.py

Faculty Dashboard HTML pages (Part 3.10, Section 21). Mirrors
analytics_pages_routes.py (Part 3.9): server-rendered shells, each
driven by its own static/js/faculty_*.js calling the real JSON APIs.
"""

from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

from app.utils.constants import ROLE_FACULTY

faculty_pages_bp = Blueprint("faculty_pages_bp", __name__, url_prefix="/faculty")


def _require_faculty():
    if not current_user.is_authenticated or current_user.role != ROLE_FACULTY:
        abort(403)


@faculty_pages_bp.route("", methods=["GET"])
@login_required
def dashboard_page():
    _require_faculty()
    return render_template("faculty/dashboard.html")


@faculty_pages_bp.route("/students", methods=["GET"])
@login_required
def students_page():
    _require_faculty()
    return render_template("faculty/students.html")


@faculty_pages_bp.route("/students/<int:student_id>", methods=["GET"])
@login_required
def student_detail_page(student_id):
    _require_faculty()
    return render_template("faculty/student_detail.html", student_id=student_id)


@faculty_pages_bp.route("/analytics", methods=["GET"])
@login_required
def analytics_page():
    _require_faculty()
    return render_template("faculty/analytics.html")


@faculty_pages_bp.route("/content", methods=["GET"])
@login_required
def content_page():
    _require_faculty()
    return render_template("faculty/content.html")


@faculty_pages_bp.route("/quizzes", methods=["GET"])
@login_required
def quizzes_page():
    _require_faculty()
    return render_template("faculty/quizzes.html")


@faculty_pages_bp.route("/quizzes/<int:quiz_id>/results", methods=["GET"])
@login_required
def quiz_results_page(quiz_id):
    _require_faculty()
    return render_template("faculty/quiz_results.html", quiz_id=quiz_id)


@faculty_pages_bp.route("/assignments", methods=["GET"])
@login_required
def assignments_page():
    _require_faculty()
    return render_template("faculty/assignments.html")


@faculty_pages_bp.route("/reports", methods=["GET"])
@login_required
def reports_page():
    _require_faculty()
    return render_template("faculty/reports.html")


@faculty_pages_bp.route("/notifications", methods=["GET"])
@login_required
def notifications_page():
    _require_faculty()
    return render_template("faculty/notifications.html")


@faculty_pages_bp.route("/profile", methods=["GET"])
@login_required
def profile_page():
    _require_faculty()
    return render_template("faculty/profile.html")


@faculty_pages_bp.route("/settings", methods=["GET"])
@login_required
def settings_page():
    _require_faculty()
    return render_template("faculty/settings.html")
