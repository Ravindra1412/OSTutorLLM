"""
app/routes/quiz_pages_routes.py

Quiz page routes (Section 18 — Frontend). Mirrors the exact pattern
established in Part 3.5 for auth_pages_bp: this blueprint renders HTML
pages (server-rendered shells that then drive themselves via
static/js/quiz_engine.js calling the real JSON API in
app/routes/quiz_routes.py), kept separate from that JSON API blueprint
so each stays a clean single responsibility — one returns JSON, one
returns HTML, and neither has to branch behavior based on what the
caller wants.
"""

from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import QuizAttempt, Quiz
from app.models.quiz_question import VALID_QUESTION_TYPES
from app.utils.constants import ROLE_STUDENT
from app.quiz.question_bank.seed_bank import all_covered_topics
from app.quiz import question_types

quiz_pages_bp = Blueprint("quiz_pages_bp", __name__, url_prefix="/quiz")


def _require_student():
    if not current_user.is_authenticated or current_user.role != ROLE_STUDENT:
        abort(403)


@quiz_pages_bp.route("", methods=["GET"])
@login_required
def dashboard():
    """Section 18 — Quiz Dashboard: topic/mode/difficulty selection and authored quizzes."""
    _require_student()
    published_quizzes = Quiz.query.filter_by(is_published=True).order_by(Quiz.id.desc()).all()
    return render_template(
        "quiz/dashboard.html",
        topics=all_covered_topics(),
        question_types=[{"type": t, "label": question_types.display_label_for(t)} for t in VALID_QUESTION_TYPES],
        authored_quizzes=published_quizzes,
    )


@quiz_pages_bp.route("/attempt/<int:attempt_id>", methods=["GET"])
@login_required
def take_quiz(attempt_id):
    """Section 18 — Question Page + Timer. Ownership is enforced again
    here at the page level (not just the API), consistent with Part
    3.7 Section 19's defense-in-depth pattern — a student cannot even
    load another student's quiz-taking page by guessing the URL."""
    _require_student()
    attempt = db.session.get(QuizAttempt, attempt_id)
    if attempt is None or attempt.user_id != current_user.id:
        abort(404)
    if attempt.is_submitted:
        return render_template("quiz/result.html", attempt_id=attempt_id)
    
    # Handle safe topic retrieval whether attached via relation or raw string
    topic_name = "General"
    if attempt.quiz and hasattr(attempt.quiz, 'topic'):
        topic_name = getattr(attempt.quiz.topic, 'name', str(attempt.quiz.topic))
    elif hasattr(attempt, 'topic'):
        topic_name = attempt.topic

    return render_template("quiz/question.html", attempt_id=attempt_id, topic=topic_name)


@quiz_pages_bp.route("/attempt/<int:attempt_id>/result", methods=["GET"])
@login_required
def result(attempt_id):
    """Section 18 — Result Page."""
    _require_student()
    attempt = db.session.get(QuizAttempt, attempt_id)
    if attempt is None or attempt.user_id != current_user.id:
        abort(404)
    return render_template("quiz/result.html", attempt_id=attempt_id)


@quiz_pages_bp.route("/attempt/<int:attempt_id>/review", methods=["GET"])
@login_required
def review(attempt_id):
    """Section 18 — Review Page."""
    _require_student()
    attempt = db.session.get(QuizAttempt, attempt_id)
    if attempt is None or attempt.user_id != current_user.id:
        abort(404)
    if not attempt.is_submitted:
        abort(403)
    return render_template("quiz/review.html", attempt_id=attempt_id)


@quiz_pages_bp.route("/leaderboard", methods=["GET"])
@login_required
def leaderboard_page():
    _require_student()
    return render_template("quiz/leaderboard.html")