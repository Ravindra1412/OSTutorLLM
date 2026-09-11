"""
app/routes/faculty_report_routes.py

Reports (Section 12) — the 3 report types not already colocated with
their own domain (Student Progress Report is in
faculty_student_routes.py; Quiz Report is in faculty_quiz_routes.py —
each next to the data/route it's exporting, rather than every report
funneled through one generic endpoint).
"""

from flask import Blueprint, request, send_file

from flask_login import login_required
from app.utils.constants import ROLE_FACULTY
from app.utils.formatters import fail_response
from app.utils.helpers import role_required
from app.faculty.services import reports_service

faculty_report_bp = Blueprint("faculty_report_bp", __name__, url_prefix="/api/faculty/reports")

_EXPORTERS = {
    "csv": (reports_service.to_csv, "csv", "text/csv"),
    "excel": (reports_service.to_excel, "xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    "pdf": (reports_service.to_pdf, "pdf", "application/pdf"),
}


def _download(report: dict, base_filename: str):
    fmt = request.args.get("format", "csv").lower()
    if fmt not in _EXPORTERS:
        return fail_response("format must be one of: csv, excel, pdf.", status_code=400)
    exporter, ext, mimetype = _EXPORTERS[fmt]
    buf = exporter(report)
    return send_file(buf, mimetype=mimetype, as_attachment=True, download_name=f"{base_filename}.{ext}")


@faculty_report_bp.route("/class-performance", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def class_performance_report():
    return _download(reports_service.generate_class_performance_report(), "class_performance_report")


@faculty_report_bp.route("/topic-mastery", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def topic_mastery_report():
    return _download(reports_service.generate_topic_mastery_report(), "topic_mastery_report")


@faculty_report_bp.route("/faculty-summary", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def faculty_summary_report():
    return _download(reports_service.generate_faculty_summary_report(), "faculty_summary_report")
