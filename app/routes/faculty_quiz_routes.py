"""
app/routes/faculty_quiz_routes.py

Quiz Management (Section 8) — faculty-authored quizzes. See
app/faculty/services/quiz_management.py's module docstring for how
this relates to (and stays fully separate from) the Quiz Engine's
existing per-attempt generation (Part 3.7).
"""

from flask import Blueprint, request, send_file
from flask_login import login_required, current_user

from app.utils.constants import ROLE_FACULTY
from app.utils.formatters import success_response, fail_response
from app.utils.helpers import role_required
from app.utils.validators import require_fields
from app.faculty.services import quiz_management as svc
from app.faculty.services import reports_service
from app.faculty.services.notification_service import notify_quiz_published

faculty_quiz_bp = Blueprint("faculty_quiz_bp", __name__, url_prefix="/api/faculty/quizzes")


@faculty_quiz_bp.route("", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def list_quizzes():
    mine_only = request.args.get("mine_only", "false").lower() == "true"
    created_by = current_user.id if mine_only else None
    return success_response(svc.list_faculty_quizzes(created_by))


@faculty_quiz_bp.route("", methods=["POST"])
@login_required
@role_required(ROLE_FACULTY)
def create_quiz():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["topic_id", "title", "questions"])
    try:
        quiz = svc.create_quiz(
            created_by_user_id=current_user.id, topic_id=data["topic_id"], title=data["title"],
            difficulty_level=data.get("difficulty_level", 1), questions=data["questions"],
            time_limit_seconds=data.get("time_limit_seconds"),
            negative_marking_enabled=data.get("negative_marking_enabled", False),
            is_published=data.get("is_published", False), scheduled_at=data.get("scheduled_at"),
        )
    except svc.QuizManagementError as exc:
        return fail_response(str(exc), status_code=400)
    return success_response({"id": quiz.id, "title": quiz.title}, message="Quiz created.", status_code=201)


@faculty_quiz_bp.route("/<int:quiz_id>", methods=["PUT"])
@login_required
@role_required(ROLE_FACULTY)
def update_quiz(quiz_id):
    data = request.get_json(silent=True) or {}
    was_publishing = data.get("is_published") is True
    try:
        quiz = svc.update_quiz(quiz_id, **data)
    except svc.QuizManagementError as exc:
        return fail_response(str(exc), status_code=404)

    if was_publishing:
        notify_quiz_published(quiz.id)  # Section 13 — Quiz Notifications

    return success_response({"id": quiz.id, "title": quiz.title, "is_published": quiz.is_published}, message="Quiz updated.")


@faculty_quiz_bp.route("/<int:quiz_id>", methods=["DELETE"])
@login_required
@role_required(ROLE_FACULTY)
def delete_quiz(quiz_id):
    if not svc.delete_quiz(quiz_id):
        return fail_response("Quiz not found.", status_code=404)
    return success_response(message="Quiz deleted.")


@faculty_quiz_bp.route("/<int:quiz_id>/results", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def get_results(quiz_id):
    results = svc.get_quiz_results(quiz_id)
    if results is None:
        return fail_response("Quiz not found.", status_code=404)
    return success_response(results)


@faculty_quiz_bp.route("/<int:quiz_id>/results/download", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def download_results(quiz_id):
    fmt = request.args.get("format", "csv").lower()
    try:
        report = reports_service.generate_quiz_report(quiz_id)
    except ValueError as exc:
        return fail_response(str(exc), status_code=404)

    exporters = {"csv": (reports_service.to_csv, "csv", "text/csv"),
                 "excel": (reports_service.to_excel, "xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                 "pdf": (reports_service.to_pdf, "pdf", "application/pdf")}
    if fmt not in exporters:
        return fail_response("format must be one of: csv, excel, pdf.", status_code=400)
    exporter, ext, mimetype = exporters[fmt]
    buf = exporter(report)
    return send_file(buf, mimetype=mimetype, as_attachment=True, download_name=f"quiz_{quiz_id}_results.{ext}")
