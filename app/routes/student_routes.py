"""
app/routes/student_routes.py

Student blueprint (Section 4). Foundation phase scope: authenticated,
role-protected placeholder endpoints only — real dashboard aggregation
logic is deferred to the Student Dashboard implementation phase
(Part 3.1, Section 15, Step 8-9) once Progress/Quiz/Tutor data exists
to aggregate.
"""

from flask import Blueprint
from flask_login import login_required, current_user

from app.utils.constants import ROLE_STUDENT
from app.utils.formatters import success_response
from app.utils.helpers import role_required

student_bp = Blueprint("student_bp", __name__, url_prefix="/api/student")


@student_bp.route("/dashboard", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def dashboard():
    """Placeholder response — real payload (mastery summary, recommended
    topic, recent activity per Part 2 Section 18.2) is wired up once the
    Progress Tracker and Learning Recommendation Engine exist."""
    return success_response(
        {"user_id": current_user.id, "note": "Dashboard aggregation not yet implemented."},
        message="Student dashboard endpoint reachable.",
    )


@student_bp.route("/profile", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def profile():
    return success_response(current_user.to_dict())
