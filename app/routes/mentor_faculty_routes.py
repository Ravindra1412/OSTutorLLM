"""
app/routes/mentor_faculty_routes.py

Faculty AI Assistant (Part 3.13, Section 13). Kept separate from
app/routes/mentor_routes.py (student-facing) — same pattern as
Part 3.10's faculty_quiz_bp vs. student quiz_bp: different concerns,
different role gates, different file.
"""

from flask import Blueprint, request
from flask_login import login_required, current_user

from app.utils.constants import ROLE_FACULTY
from app.utils.formatters import success_response
from app.utils.helpers import role_required
from app.utils.validators import require_fields
from app.mentor.services import mentor_assistant

mentor_faculty_bp = Blueprint("mentor_faculty_bp", __name__, url_prefix="/api/faculty/mentor")


@mentor_faculty_bp.route("/assistant/ask", methods=["POST"])
@login_required
@role_required(ROLE_FACULTY)
def ask_faculty_assistant():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["question"])
    result = mentor_assistant.ask_faculty_assistant(current_user.id, data["question"])
    return success_response(result)


@mentor_faculty_bp.route("/assistant/history", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def faculty_assistant_history():
    return success_response(mentor_assistant.get_interaction_history(current_user.id))
