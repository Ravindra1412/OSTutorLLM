"""
app/routes/code_review_pages_routes.py

Code Review page routes (Section 14 — Frontend). Mirrors the exact
pattern established for quiz_pages_bp (Part 3.7) and auth_pages_bp
(Part 3.5): renders HTML shells driven by static/js/code_review_engine.js
calling the real JSON API (app/routes/code_review_routes.py).
"""

from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import CodeReviewSession
from app.utils.constants import ROLE_STUDENT
from app.code_review.topics import CODE_REVIEW_TOPICS

code_review_pages_bp = Blueprint("code_review_pages_bp", __name__, url_prefix="/code-review")


def _require_student():
    if not current_user.is_authenticated or current_user.role != ROLE_STUDENT:
        abort(403)


@code_review_pages_bp.route("", methods=["GET"])
@login_required
def editor():
    """Section 14 — Code Editor + Topic Selector + Review Button."""
    _require_student()
    return render_template("code_review/editor.html", topics=CODE_REVIEW_TOPICS)


@code_review_pages_bp.route("/session/<int:session_id>", methods=["GET"])
@login_required
def session_view(session_id):
    """Section 14 — Feedback Panel + Score Card + Hint Panel +
    Improvement Timeline, all for an existing session (used both right
    after a fresh submission and when resuming/resubmitting)."""
    _require_student()
    session = db.session.get(CodeReviewSession, session_id)
    if session is None or session.user_id != current_user.id:
        abort(404)
    return render_template("code_review/editor.html", topics=CODE_REVIEW_TOPICS, session_id=session_id, topic=session.topic_name)


@code_review_pages_bp.route("/history", methods=["GET"])
@login_required
def history_page():
    _require_student()
    return render_template("code_review/history.html")
