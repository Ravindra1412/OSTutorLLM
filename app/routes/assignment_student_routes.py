"""
app/routes/assignment_student_routes.py

Student-facing half of Assignment Management (Part 3.10, Section 10).
Kept as its own small blueprint (not inside student_routes.py) so
Assignment-related routes are easy to find in one place regardless of
which side (faculty or student) is using them.
"""

from datetime import datetime, timezone

from flask import Blueprint, request
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Assignment, AssignmentSubmission
from app.utils.constants import ROLE_STUDENT
from app.utils.formatters import success_response, fail_response
from app.utils.helpers import role_required
from app.utils.validators import require_fields

assignment_student_bp = Blueprint("assignment_student_bp", __name__, url_prefix="/api/assignments")


@assignment_student_bp.route("", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def list_published_assignments():
    assignments = Assignment.query.filter_by(is_published=True).order_by(Assignment.due_at.asc()).all()
    my_submissions = {
        s.assignment_id: s for s in AssignmentSubmission.query.filter_by(user_id=current_user.id).all()
    }
    return success_response([
        {
            "id": a.id, "title": a.title, "description": a.description, "topic_name": a.topic.name,
            "due_at": a.due_at.isoformat(), "max_score": a.max_score,
            "submitted": a.id in my_submissions,
            "score": my_submissions[a.id].score if a.id in my_submissions else None,
        }
        for a in assignments
    ])


@assignment_student_bp.route("/<int:assignment_id>/submit", methods=["POST"])
@login_required
@role_required(ROLE_STUDENT)
def submit_assignment(assignment_id):
    assignment = db.session.get(Assignment, assignment_id)
    if assignment is None or not assignment.is_published:
        return fail_response("Assignment not found.", status_code=404)

    data = request.get_json(silent=True) or {}
    require_fields(data, ["submission_text"])

    now = datetime.now(timezone.utc)
    due_at = assignment.due_at if assignment.due_at.tzinfo else assignment.due_at.replace(tzinfo=timezone.utc)
    is_late = now > due_at
    if is_late and not assignment.allow_late_submission:
        return fail_response("The deadline for this assignment has passed.", status_code=400)

    existing = AssignmentSubmission.query.filter_by(assignment_id=assignment_id, user_id=current_user.id).first()
    if existing:
        existing.submission_text = data["submission_text"]
        existing.submitted_at = now
        existing.is_late = is_late
        existing.score = None
        existing.feedback = None
        existing.graded_at = None
    else:
        db.session.add(AssignmentSubmission(
            assignment_id=assignment_id, user_id=current_user.id, submission_text=data["submission_text"],
            submitted_at=now, is_late=is_late,
        ))
    db.session.commit()
    return success_response(message="Assignment submitted.", status_code=201)
