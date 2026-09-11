"""
app/routes/quiz_routes.py

Quiz blueprint (Part 3.3 Section 4) — fully implemented in Part 3.7.
Every route is a thin translation layer over app.quiz.services, mirroring
the exact Controller pattern established for the Tutor Engine in Part
3.6's tutor_routes.py. Security (Section 19) is enforced both here
(role/login decorators) and inside the service layer (ownership,
single-submission — app/quiz/services/security.py), matching the
Part 3.6 tutor_routes.py pattern of never trusting a single layer alone.
"""

import json

from flask import Blueprint, request
from flask_login import login_required, current_user

from app.utils.constants import ROLE_STUDENT
from app.utils.formatters import success_response, fail_response
from app.utils.helpers import role_required
from app.utils.validators import require_fields
from app.extensions import db
from app.models import QuizAttempt, QuizHistory
from app.quiz.services import quiz_service, timer_service, security
from app.quiz import question_types

quiz_bp = Blueprint("quiz_bp", __name__, url_prefix="/api/quiz")


# --------------------------------------------------------------------
# Serialization helpers (Section 19 — never leak the correct answer)
# --------------------------------------------------------------------

def _serialize_question_for_student(question) -> dict:
    """CRITICAL security boundary (Section 19 — Answer Tampering):
    `correct_answer` and `explanation` are deliberately EXCLUDED here.
    Only sent to the client after grading, via `_serialize_result`."""
    options = json.loads(question.options_json) if question.options_json else None
    return {
        "id": question.id,
        "question_text": question.question_text,
        "question_type": question.question_type,
        "question_type_label": question_types.display_label_for(question.question_type),
        "options": options,
        "difficulty_level": question.difficulty_level,
        "points": question.points,
        "sequence_order": question.sequence_order,
    }


def _serialize_attempt_start(start_result) -> dict:
    return {
        "attempt_id": start_result.attempt.id,
        "quiz_id": start_result.quiz.id,
        "topic": start_result.topic_name,
        "difficulty_level": start_result.quiz.difficulty_level,
        "time_limit_seconds": start_result.time_limit_seconds,
        "negative_marking_enabled": start_result.quiz.negative_marking_enabled,
        "questions": [_serialize_question_for_student(q) for q in start_result.quiz.questions],
    }


def _serialize_feedback(feedback) -> dict:
    return {
        "mistake_analysis": feedback.mistake_analysis,
        "recommended_videos": feedback.recommended_videos,
        "recommended_notes": feedback.recommended_notes,
        "next_topic_recommendation": feedback.next_topic_recommendation,
        "per_question": [
            {
                "question_id": pq.question_id,
                "question_text": pq.question_text,
                "is_correct": pq.is_correct,
                "student_answer": pq.student_answer,
                "correct_answer": pq.correct_answer_display,
                "explanation": pq.explanation,
                "points_earned": pq.points_earned,
                "points_possible": pq.points_possible,
            }
            for pq in feedback.per_question
        ],
    }


# --------------------------------------------------------------------
# Quiz APIs (Section 20)
# --------------------------------------------------------------------

@quiz_bp.route("/start", methods=["POST"])
@login_required
@role_required(ROLE_STUDENT)
def start():
    data = request.get_json(silent=True) or {}
    mode = data.get("mode", "topic")

    try:
        start_result = quiz_service.start_quiz(
            user_id=current_user.id,
            topic_name=data.get("topic"),
            difficulty_level=data.get("difficulty_level"),
            question_count=int(data.get("question_count", 5)),
            mode=mode,
            time_limit_seconds=data.get("time_limit_seconds", 300),
            negative_marking_enabled=bool(data.get("negative_marking_enabled", False)),
        )
    except security.QuizSecurityError as exc:
        return fail_response(exc.message, status_code=409)
    except ValueError as exc:
        return fail_response(str(exc), status_code=400)

    return success_response(_serialize_attempt_start(start_result), message="Quiz started.", status_code=201)


@quiz_bp.route("/authored/<int:quiz_id>/start", methods=["POST"])
@login_required
@role_required(ROLE_STUDENT)
def start_authored(quiz_id):
    """Part 3.10, Section 8 — attempts a specific faculty-authored Quiz
    by id, as opposed to /start above which always generates a new
    one. See app/faculty/services/quiz_management.py's docstring."""
    try:
        start_result = quiz_service.start_authored_quiz(current_user.id, quiz_id)
    except security.QuizSecurityError as exc:
        return fail_response(exc.message, status_code=409)
    except ValueError as exc:
        return fail_response(str(exc), status_code=400)

    return success_response(_serialize_attempt_start(start_result), message="Quiz started.", status_code=201)


@quiz_bp.route("/<int:attempt_id>", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def get_attempt(attempt_id):
    try:
        quiz_service.auto_submit_if_expired(current_user.id, attempt_id)  # Section 8 — time-expired handling on read
        attempt = security.assert_owns_attempt(db.session.get(QuizAttempt, attempt_id), current_user.id)
    except security.QuizSecurityError as exc:
        return fail_response(exc.message, status_code=404)

    return success_response({
        "attempt_id": attempt.id,
        "is_submitted": attempt.is_submitted,
        "score": attempt.score,
        "remaining_seconds": timer_service.remaining_seconds(attempt),
        "questions": [_serialize_question_for_student(q) for q in attempt.quiz.questions],
    })


@quiz_bp.route("/<int:attempt_id>/answer", methods=["POST"])
@login_required
@role_required(ROLE_STUDENT)
def answer(attempt_id):
    data = request.get_json(silent=True) or {}
    require_fields(data, ["question_id", "answer"])

    answer_value = data["answer"]
    answer_raw = answer_value if isinstance(answer_value, str) else json.dumps(answer_value)

    try:
        quiz_service.submit_answer(current_user.id, attempt_id, data["question_id"], answer_raw)
    except security.QuizSecurityError as exc:
        return fail_response(exc.message, status_code=409)

    return success_response(message="Answer saved.")


@quiz_bp.route("/<int:attempt_id>/pause", methods=["POST"])
@login_required
@role_required(ROLE_STUDENT)
def pause(attempt_id):
    try:
        attempt = security.assert_owns_attempt(db.session.get(QuizAttempt, attempt_id), current_user.id)
    except security.QuizSecurityError as exc:
        return fail_response(exc.message, status_code=404)
    timer_service.pause_timer(attempt)
    return success_response(message="Timer paused.")


@quiz_bp.route("/<int:attempt_id>/resume", methods=["POST"])
@login_required
@role_required(ROLE_STUDENT)
def resume(attempt_id):
    try:
        attempt = security.assert_owns_attempt(db.session.get(QuizAttempt, attempt_id), current_user.id)
    except security.QuizSecurityError as exc:
        return fail_response(exc.message, status_code=404)
    timer_service.resume_timer(attempt)
    return success_response({"remaining_seconds": timer_service.remaining_seconds(attempt)}, message="Timer resumed.")


@quiz_bp.route("/<int:attempt_id>/submit", methods=["POST"])
@login_required
@role_required(ROLE_STUDENT)
def submit(attempt_id):
    try:
        outcome = quiz_service.submit_quiz(current_user.id, attempt_id)
    except security.QuizSecurityError as exc:
        return fail_response(exc.message, status_code=409)

    return success_response({
        "attempt_id": outcome["attempt_id"],
        "score_percent": outcome["score_percent"],
        "summary": outcome["summary"],
        "feedback": _serialize_feedback(outcome["feedback"]),
        "newly_earned_badges": outcome["newly_earned_badges"],
    }, message="Quiz submitted and graded.")


# --------------------------------------------------------------------
# History / Result APIs (Section 20)
# --------------------------------------------------------------------

@quiz_bp.route("/history", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def history():
    entries = QuizHistory.query.filter_by(user_id=current_user.id).order_by(QuizHistory.taken_at.desc()).limit(50).all()
    return success_response([
        {"topic_name": e.topic_name, "score": e.score, "taken_at": e.taken_at.isoformat()} for e in entries
    ])


@quiz_bp.route("/<int:attempt_id>/review", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def review(attempt_id):
    """Section 18 — Review Page backing endpoint. Only available once
    the attempt is submitted (correct answers are only ever revealed
    post-submission, Section 19)."""
    try:
        attempt = security.assert_owns_attempt(db.session.get(QuizAttempt, attempt_id), current_user.id)
    except security.QuizSecurityError as exc:
        return fail_response(exc.message, status_code=404)

    if not attempt.is_submitted:
        return fail_response("This attempt has not been submitted yet.", status_code=403)

    from app.quiz.services.feedback_generator import build_per_question_feedback
    per_question = build_per_question_feedback(attempt)
    return success_response({
        "attempt_id": attempt.id, "score": attempt.score, "topic": attempt.quiz.topic.name,
        "per_question": [
            {
                "question_id": pq.question_id, "question_text": pq.question_text, "is_correct": pq.is_correct,
                "student_answer": pq.student_answer, "correct_answer": pq.correct_answer_display,
                "explanation": pq.explanation, "points_earned": pq.points_earned, "points_possible": pq.points_possible,
            }
            for pq in per_question
        ],
    })


# --------------------------------------------------------------------
# Leaderboard API (Section 13, optional)
# --------------------------------------------------------------------

@quiz_bp.route("/leaderboard", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def leaderboard():
    """Top scores by total XP — a simple, real leaderboard reusing
    StudentProfile.xp_total (Part 3.4), which every quiz completion
    already contributes to via app.quiz.services.achievements."""
    from app.models import StudentProfile, User

    top = (
        StudentProfile.query.join(User, StudentProfile.user_id == User.id)
        .order_by(StudentProfile.xp_total.desc())
        .limit(10)
        .all()
    )
    return success_response([
        {"name": p.user.name, "xp_total": p.xp_total, "level": p.level, "is_you": p.user_id == current_user.id}
        for p in top
    ])


# --------------------------------------------------------------------
# Metadata APIs
# --------------------------------------------------------------------

@quiz_bp.route("/types", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def list_types():
    from app.models.quiz_question import VALID_QUESTION_TYPES
    return success_response([
        {"type": t, "label": question_types.display_label_for(t), "evaluation_mode": question_types.evaluation_mode_for(t)}
        for t in VALID_QUESTION_TYPES
    ])


@quiz_bp.route("/topics", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def list_topics():
    from app.quiz.question_bank.seed_bank import all_covered_topics
    return success_response({"topics": all_covered_topics()})
