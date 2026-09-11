"""
app/routes/progress_routes.py

Progress blueprint (Section 4). Unlike Tutor/Quiz, a basic read
endpoint is implemented here because the `progress` table (Part 3.1
Section 8.4) already exists in this phase's schema — this is plain
data retrieval, not tutoring/quiz business logic, so it stays in scope.
Write access (mastery score updates) is deferred until an actual
learning event producer (Tutor/Quiz Engine) exists to call it.
"""

from flask import Blueprint
from flask_login import login_required, current_user

from app.models import Progress
from app.utils.constants import ROLE_STUDENT
from app.utils.formatters import success_response
from app.utils.helpers import role_required

progress_bp = Blueprint("progress_bp", __name__, url_prefix="/api/progress")


@progress_bp.route("", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def get_progress():
    entries = Progress.query.filter_by(user_id=current_user.id).all()
    data = [
        {"topic_name": e.topic_name, "mastery_score": e.mastery_score, "last_updated": e.last_updated.isoformat()}
        for e in entries
    ]
    return success_response(data, message=f"Found {len(data)} tracked topic(s).")


@progress_bp.route("/summary", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def get_progress_summary():
    """Part 3.9, Section 4/16 — Progress Tracker rollup: completed
    topics/lessons and time-spent breakdown, on top of the raw
    per-topic list already served by GET /api/progress above."""
    from app.analytics.services import progress_tracker

    data = {
        "tracked_topic_count": progress_tracker.get_tracked_topic_count(current_user.id),
        "completed_topics": progress_tracker.get_completed_topics(current_user.id),
        "completed_lessons": progress_tracker.get_completed_lessons(current_user.id),
        "quiz_scores": progress_tracker.get_quiz_scores(current_user.id),
        "code_review_scores": progress_tracker.get_code_review_scores(current_user.id),
        "time_spent": progress_tracker.get_time_spent_summary(current_user.id),
    }
    return success_response(data, message="Progress summary computed.")
