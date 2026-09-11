"""
app/routes/faculty_student_routes.py

Student Management (Section 5), Learning Analytics (Section 6), and
Code Review Monitoring (Section 11). Grouped in one blueprint because
all three are "faculty looking at student data" views over the same
underlying tables, rather than three unrelated feature domains.
"""

from flask import Blueprint, request

from flask_login import login_required, current_user

from app.utils.constants import ROLE_FACULTY
from app.utils.formatters import success_response, fail_response
from app.utils.helpers import role_required
from app.faculty.services import student_management, class_analytics, code_review_monitoring, reports_service

faculty_student_bp = Blueprint("faculty_student_bp", __name__, url_prefix="/api/faculty")


# --- Student Management (Section 5) ---

@faculty_student_bp.route("/students", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def list_students():
    search = request.args.get("search")
    active_only = request.args.get("active_only", "false").lower() == "true"
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 20)), 100)
    return success_response(student_management.list_students(search, active_only, page, per_page))


@faculty_student_bp.route("/students/<int:student_id>", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def get_student_detail(student_id):
    detail = student_management.get_student_detail(student_id)
    if detail is None:
        return fail_response("Student not found.", status_code=404)
    return success_response(detail)


@faculty_student_bp.route("/students/<int:student_id>/report", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def export_student_report(student_id):
    """Section 5 — Export Student Report. Format via ?format=csv|excel|pdf (default csv)."""
    from flask import send_file

    fmt = request.args.get("format", "csv").lower()
    try:
        report = reports_service.generate_student_progress_report(student_id)
    except ValueError as exc:
        return fail_response(str(exc), status_code=404)

    exporters = {"csv": (reports_service.to_csv, "csv", "text/csv"),
                 "excel": (reports_service.to_excel, "xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                 "pdf": (reports_service.to_pdf, "pdf", "application/pdf")}
    if fmt not in exporters:
        return fail_response("format must be one of: csv, excel, pdf.", status_code=400)

    exporter, ext, mimetype = exporters[fmt]
    buf = exporter(report)
    return send_file(buf, mimetype=mimetype, as_attachment=True, download_name=f"student_{student_id}_progress.{ext}")


# --- Learning Analytics (Section 6) ---

@faculty_student_bp.route("/analytics/class", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def get_class_analytics():
    return success_response(class_analytics.build_class_analytics())


# --- Code Review Monitoring (Section 11) ---

@faculty_student_bp.route("/analytics/code-review", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def get_code_review_monitoring():
    return success_response(code_review_monitoring.build_monitoring_summary())
