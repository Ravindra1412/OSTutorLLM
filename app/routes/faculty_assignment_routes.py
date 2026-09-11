"""
app/routes/faculty_assignment_routes.py

Assignment Management (Section 10) — faculty CRUD, submission
tracking, grading, analytics. Student-facing submission is the small
separate blueprint in app/routes/assignment_student_routes.py.
"""

from datetime import datetime

from flask import Blueprint, request
from flask_login import login_required, current_user

from app.utils.constants import ROLE_FACULTY
from app.utils.formatters import success_response, fail_response
from app.utils.helpers import role_required
from app.utils.validators import require_fields, ValidationError
from app.faculty.services import assignment_management as svc
from app.faculty.services.notification_service import send_assignment_reminder

faculty_assignment_bp = Blueprint("faculty_assignment_bp", __name__, url_prefix="/api/faculty/assignments")


def _parse_due_at(value: str):
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        raise ValidationError("due_at must be an ISO-8601 datetime string.", field="due_at")


@faculty_assignment_bp.route("", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def list_assignments():
    return success_response(svc.list_assignments())


@faculty_assignment_bp.route("", methods=["POST"])
@login_required
@role_required(ROLE_FACULTY)
def create_assignment():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["topic_id", "title", "description", "due_at"])
    try:
        assignment = svc.create_assignment(
            created_by_user_id=current_user.id, topic_id=data["topic_id"], title=data["title"],
            description=data["description"], due_at=_parse_due_at(data["due_at"]),
            allow_late_submission=data.get("allow_late_submission", True),
            max_score=data.get("max_score", 100.0), is_published=data.get("is_published", False),
        )
    except svc.AssignmentError as exc:
        return fail_response(str(exc), status_code=400)
    return success_response({"id": assignment.id, "title": assignment.title}, message="Assignment created.", status_code=201)


@faculty_assignment_bp.route("/<int:assignment_id>", methods=["PUT"])
@login_required
@role_required(ROLE_FACULTY)
def update_assignment(assignment_id):
    data = request.get_json(silent=True) or {}
    if "due_at" in data and data["due_at"]:
        data["due_at"] = _parse_due_at(data["due_at"])
    try:
        assignment = svc.update_assignment(assignment_id, **data)
    except svc.AssignmentError as exc:
        return fail_response(str(exc), status_code=404)
    return success_response({"id": assignment.id, "is_published": assignment.is_published}, message="Assignment updated.")


@faculty_assignment_bp.route("/<int:assignment_id>", methods=["DELETE"])
@login_required
@role_required(ROLE_FACULTY)
def delete_assignment(assignment_id):
    if not svc.delete_assignment(assignment_id):
        return fail_response("Assignment not found.", status_code=404)
    return success_response(message="Assignment deleted.")


@faculty_assignment_bp.route("/<int:assignment_id>/submissions", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def get_submissions(assignment_id):
    data = svc.get_submissions(assignment_id)
    if data is None:
        return fail_response("Assignment not found.", status_code=404)
    return success_response(data)


@faculty_assignment_bp.route("/submissions/<int:submission_id>/grade", methods=["POST"])
@login_required
@role_required(ROLE_FACULTY)
def grade_submission(submission_id):
    data = request.get_json(silent=True) or {}
    require_fields(data, ["score"])
    try:
        submission = svc.grade_submission(submission_id, current_user.id, float(data["score"]), data.get("feedback"))
    except svc.AssignmentError as exc:
        return fail_response(str(exc), status_code=404)
    return success_response({"id": submission.id, "score": submission.score}, message="Submission graded.")


@faculty_assignment_bp.route("/<int:assignment_id>/analytics", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def get_analytics(assignment_id):
    data = svc.assignment_analytics(assignment_id)
    if data is None:
        return fail_response("Assignment not found.", status_code=404)
    return success_response(data)


@faculty_assignment_bp.route("/<int:assignment_id>/remind", methods=["POST"])
@login_required
@role_required(ROLE_FACULTY)
def send_reminder(assignment_id):
    try:
        count = send_assignment_reminder(assignment_id)
    except ValueError as exc:
        return fail_response(str(exc), status_code=404)
    return success_response({"reminded_count": count}, message="Reminders sent.")
