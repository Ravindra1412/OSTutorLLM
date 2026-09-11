"""
app/quiz/services/quiz_service.py

The Quiz Service / Assessment Manager (Section 1/7) — the central
orchestrator, mirroring Part 3.6's tutor_service.py pattern exactly.
Every route in app/routes/quiz_routes.py is a thin translation layer
calling into this file; every other quiz module (generator, difficulty
manager, evaluation engine, scoring engine, feedback generator,
progress updater, timer, security) exists to be called from here, in
the Section 7 workflow order:

    student starts quiz
        -> select topic (explicit, weak-topic, or revision)
        -> Difficulty Manager determines difficulty (adaptive or explicit)
        -> Question Generator assembles the question set
        -> Timer Service starts the countdown
        -> [student answers, one or many at a time]
        -> Security checks (ownership, not-already-submitted) on submit
        -> Evaluation Engine grades every answer
        -> Scoring Engine computes the overall score
        -> Feedback Generator produces explanations + mistake analysis
        -> Progress Updater writes back into Progress/QuizHistory
        -> Recommend Next Topic (part of Feedback Generator's output)
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from app.extensions import db
from app.models import Topic, Quiz, QuizQuestion, QuizAttempt, QuizResult
from app.models.quiz_question import VALID_QUESTION_TYPES, QUESTION_TYPE_MCQ
from app.quiz.services import (
    question_generator, difficulty_manager, evaluation_engine,
    scoring_engine, feedback_generator, progress_updater, timer_service, security,
)
from app.utils.logger import get_ai_logger


@dataclass
class QuizStartResult:
    attempt: QuizAttempt
    quiz: Quiz
    topic_name: str
    time_limit_seconds: int | None


def _get_or_create_topic(topic_name: str) -> Topic:
    topic = Topic.query.filter_by(name=topic_name).first()
    if topic is None:
        topic = Topic(name=topic_name, category="General", difficulty_level=2)
        db.session.add(topic)
        db.session.commit()
    return topic


def _normalize_question_type(raw_type: str | None) -> str:
    """Normalize raw question_type strings from LLMs/external generators to match

    the database CHECK constraint in app.models.quiz_question.
    """
    if not raw_type:
        return QUESTION_TYPE_MCQ

    cleaned = str(raw_type).strip().lower().replace("-", "_").replace(" ", "_")
    if cleaned in ("multiple_choice", "multiplechoice", "choice"):
        return QUESTION_TYPE_MCQ

    if cleaned in VALID_QUESTION_TYPES:
        return cleaned

    return QUESTION_TYPE_MCQ


def start_quiz(
    user_id: int,
    topic_name: str | None = None,
    difficulty_level: int | None = None,
    question_count: int = 5,
    mode: str = "topic",  # "topic" | "learning_gap" | "revision"
    time_limit_seconds: int | None = 300,
    negative_marking_enabled: bool = False,
) -> QuizStartResult:
    """Section 7, steps 1-5. `mode` implements Section 5's Learning
    Gap / Revision question sourcing as alternates to an explicit
    topic choice."""
    logger = get_ai_logger()

    if mode == "learning_gap":
        topic_name, questions_data = question_generator.generate_learning_gap_quiz(user_id, question_count)
        if topic_name is None:
            raise ValueError("No weak topics found yet — take a few quizzes first so we have data to work with.")
    elif mode == "revision":
        topic_name, questions_data = question_generator.generate_revision_quiz(user_id, question_count)
        if topic_name is None:
            raise ValueError("No tracked progress yet — nothing to revise.")
    else:
        if not topic_name:
            raise ValueError("A topic is required when mode='topic'.")
        resolved_difficulty = difficulty_level if difficulty_level is not None else difficulty_manager.determine_adaptive_difficulty(user_id, topic_name)
        questions_data = question_generator.generate_question_set(user_id, topic_name, resolved_difficulty, question_count)

    if not questions_data:
        raise ValueError(f"Could not generate any questions for '{topic_name}' right now. Please try again shortly.")

    topic = _get_or_create_topic(topic_name)
    avg_difficulty = round(sum(q["difficulty_level"] for q in questions_data) / len(questions_data)) or 1

    quiz = Quiz(
        topic_id=topic.id, title=f"{topic_name} Quiz", difficulty_level=avg_difficulty,
        time_limit_seconds=time_limit_seconds, negative_marking_enabled=negative_marking_enabled,
        adaptive=(difficulty_level is None),
    )
    db.session.add(quiz)
    db.session.flush()

    for i, q in enumerate(questions_data):
        normalized_type = _normalize_question_type(q.get("question_type"))
        db.session.add(QuizQuestion(
            quiz_id=quiz.id,
            question_text=q["question_text"],
            question_type=normalized_type,
            options_json=json.dumps(q["options"]) if q.get("options") is not None else None,
            correct_answer=json.dumps(q["correct_answer"]),
            explanation=q.get("explanation", ""),
            difficulty_level=q["difficulty_level"],
            points=q.get("points", 1.0),
            sequence_order=i,
        ))
    db.session.commit()

    security.assert_no_other_active_attempt(user_id, quiz.id)
    attempt = QuizAttempt(quiz_id=quiz.id, user_id=user_id)
    db.session.add(attempt)
    db.session.commit()

    timer_service.start_timer(attempt, time_limit_seconds)
    logger.info("quiz_started user_id=%s quiz_id=%s topic=%s questions=%s mode=%s", user_id, quiz.id, topic_name, len(questions_data), mode)

    return QuizStartResult(attempt=attempt, quiz=quiz, topic_name=topic_name, time_limit_seconds=time_limit_seconds)


def start_authored_quiz(user_id: int, quiz_id: int) -> QuizStartResult:
    """Part 3.10, Section 8. Attempts an EXISTING faculty-authored Quiz
    (created_by_user_id set) by id, instead of generating a new one —
    see app/faculty/services/quiz_management.py's module docstring for
    why this is a separate function rather than a change to
    start_quiz() above. Everything after this point (submit_answer,
    submit_quiz) is the exact same, unmodified pipeline."""
    logger = get_ai_logger()

    quiz = db.session.get(Quiz, quiz_id)
    if quiz is None or quiz.created_by_user_id is None:
        raise ValueError("Quiz not found.")
    if not quiz.is_published:
        raise ValueError("This quiz has not been published yet.")
    if quiz.scheduled_at:
        scheduled_at = quiz.scheduled_at if quiz.scheduled_at.tzinfo else quiz.scheduled_at.replace(tzinfo=timezone.utc)
        if scheduled_at > datetime.now(timezone.utc):
            raise ValueError(f"This quiz is not available until {scheduled_at.isoformat()}.")

    security.assert_no_other_active_attempt(user_id, quiz.id)
    attempt = QuizAttempt(quiz_id=quiz.id, user_id=user_id)
    db.session.add(attempt)
    db.session.commit()

    timer_service.start_timer(attempt, quiz.time_limit_seconds)
    logger.info("authored_quiz_started user_id=%s quiz_id=%s", user_id, quiz.id)

    return QuizStartResult(
        attempt=attempt, quiz=quiz, topic_name=quiz.topic.name, time_limit_seconds=quiz.time_limit_seconds
    )


def submit_answer(user_id: int, attempt_id: int, question_id: int, student_answer_raw: str) -> None:
    """Stores (but does not grade) one answer — grading happens in bulk
    at final submission (`submit_quiz`), so a student can revise an
    earlier answer before submitting the whole quiz."""
    attempt = security.assert_owns_attempt(db.session.get(QuizAttempt, attempt_id), user_id)
    security.assert_not_already_submitted(attempt)

    if timer_service.is_expired(attempt):
        raise security.QuizSecurityError("Time is up for this quiz — it will be auto-submitted.")

    question = QuizQuestion.query.filter_by(id=question_id, quiz_id=attempt.quiz_id).first()
    if question is None:
        raise security.QuizSecurityError("This question does not belong to the current quiz attempt.")

    existing = QuizResult.query.filter_by(attempt_id=attempt.id, question_id=question_id).first()
    if existing:
        existing.student_answer = student_answer_raw
    else:
        db.session.add(QuizResult(attempt_id=attempt.id, question_id=question_id, student_answer=student_answer_raw))
    db.session.commit()


def submit_quiz(user_id: int, attempt_id: int, auto_submitted: bool = False) -> dict:
    """Section 7, steps: Auto Evaluation -> Generate Feedback -> Store
    Results -> Recommend Next Topic. Returns a full result payload for
    the route layer to serialize (Section 20 — Result API)."""
    attempt = security.assert_owns_attempt(db.session.get(QuizAttempt, attempt_id), user_id)

    if not auto_submitted:
        security.assert_not_already_submitted(attempt)

    topic_name = attempt.quiz.topic.name

    # Grade every question that has a stored (or blank, if skipped) answer.
    for question in attempt.quiz.questions:
        result = QuizResult.query.filter_by(attempt_id=attempt.id, question_id=question.id).first()
        if result is None:
            result = QuizResult(attempt_id=attempt.id, question_id=question.id, student_answer="")
            db.session.add(result)
            db.session.flush()

        evaluation = evaluation_engine.evaluate_answer(question, result.student_answer or "", topic_name)
        result.is_correct = evaluation.is_correct
        result.points_earned = scoring_engine.compute_points_earned(question, evaluation.score_fraction)

    attempt.is_submitted = True
    attempt.auto_submitted = auto_submitted
    attempt.completed_at = datetime.now(timezone.utc)
    db.session.commit()

    score_percent = scoring_engine.compute_attempt_score(attempt)
    attempt.score = score_percent
    db.session.commit()

    progress_updater.update_progress_after_quiz(attempt, topic_name, score_percent)
    feedback = feedback_generator.build_attempt_feedback(attempt, topic_name)

    from app.quiz.services.achievements import check_and_award_quiz_achievements
    newly_earned = check_and_award_quiz_achievements(user_id, attempt)

    # --- Part 3.9: Learning Timeline + cross-engine Achievement Manager ---
    from app.analytics.services import timeline_service, achievement_manager
    from app.models.learning_timeline import EVENT_QUIZ_ATTEMPTED
    timeline_service.log_event(
        user_id, EVENT_QUIZ_ATTEMPTED, title=f"Quiz: {topic_name}",
        topic_name=topic_name, score=score_percent,
    )
    newly_earned.extend(achievement_manager.check_and_award_platform_achievements(user_id))

    get_ai_logger().info(
        "quiz_submitted user_id=%s attempt_id=%s score=%s auto_submitted=%s", user_id, attempt.id, score_percent, auto_submitted
    )

    return {
        "attempt_id": attempt.id,
        "score_percent": score_percent,
        "summary": scoring_engine.summarize_attempt(attempt),
        "feedback": feedback,
        "newly_earned_badges": newly_earned,
    }


def auto_submit_if_expired(user_id: int, attempt_id: int) -> bool:
    """Called on any read of an in-progress attempt (Section 8 — Time
    Expired Handling); if expired, forces a submission of whatever was
    answered so far rather than leaving a dangling attempt."""
    attempt = security.assert_owns_attempt(db.session.get(QuizAttempt, attempt_id), user_id)
    if not attempt.is_submitted and timer_service.is_expired(attempt):
        submit_quiz(user_id, attempt_id, auto_submitted=True)
        return True
    return False