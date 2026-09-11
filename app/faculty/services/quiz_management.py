"""
app/faculty/services/quiz_management.py

Quiz Management (Section 8) — FACULTY-AUTHORED quizzes.

Important architectural note (see app/faculty/__init__.py's scope
note for the general pattern, and docs/project-report-part3.10.md
Section 8 for the full rationale): the existing Quiz Engine
(app/quiz/services/quiz_service.py, Part 3.7) generates a brand-new
Quiz + QuizQuestion row set on every `start_quiz()` call — there is no
concept there of "one quiz definition, taken by many students." That
is working, tested (240 passing tests) behavior this phase does NOT
touch or restructure.

Faculty-authored quizzes are therefore a parallel, additive concept:
a Quiz row with `created_by_user_id` set (a column that already
existed since Part 3.4, previously always null) and `is_published`/
`scheduled_at` (added this phase). A small, separate student-facing
entry point — `quiz_service.start_authored_quiz()`, added this phase —
lets a student attempt THIS SPECIFIC Quiz by id instead of generating
a new one, reusing the exact same QuizAttempt/timer/evaluation
pipeline for everything after that point. Zero changes to
`start_quiz()` itself.
"""

from datetime import datetime, timezone
import json

from app.extensions import db
from app.models import Topic, Quiz, QuizQuestion, QuizAttempt, QuizResult, User
from app.quiz.question_types import VALID_QUESTION_TYPES


class QuizManagementError(Exception):
    pass


def create_quiz(
    created_by_user_id: int, topic_id: int, title: str, difficulty_level: int,
    questions: list[dict], time_limit_seconds: int | None = None,
    negative_marking_enabled: bool = False, is_published: bool = False, scheduled_at=None,
) -> Quiz:
    if db.session.get(Topic, topic_id) is None:
        raise QuizManagementError("Topic not found.")
    if not questions:
        raise QuizManagementError("A quiz needs at least one question.")

    quiz = Quiz(
        topic_id=topic_id, title=title.strip(), difficulty_level=difficulty_level,
        created_by_user_id=created_by_user_id, time_limit_seconds=time_limit_seconds,
        negative_marking_enabled=negative_marking_enabled, adaptive=False,
        is_published=is_published, scheduled_at=scheduled_at,
    )
    db.session.add(quiz)
    db.session.flush()

    for i, q in enumerate(questions):
        q_type = q.get("question_type", "mcq")
        if q_type not in VALID_QUESTION_TYPES:
            raise QuizManagementError(f"Invalid question_type '{q_type}'.")
        options = q.get("options")
        db.session.add(QuizQuestion(
            quiz_id=quiz.id, question_text=q["question_text"], question_type=q_type,
            options_json=json.dumps(options) if options is not None else None,
            correct_answer=json.dumps(q["correct_answer"]),
            explanation=q.get("explanation"), difficulty_level=q.get("difficulty_level", difficulty_level),
            points=q.get("points", 1.0), sequence_order=i,
        ))
    db.session.commit()
    return quiz


def update_quiz(quiz_id: int, **fields) -> Quiz:
    quiz = db.session.get(Quiz, quiz_id)
    if quiz is None:
        raise QuizManagementError("Quiz not found.")
    for key in ("title", "difficulty_level", "time_limit_seconds", "negative_marking_enabled",
                "is_published", "scheduled_at"):
        if key in fields and fields[key] is not None:
            setattr(quiz, key, fields[key])
    db.session.commit()
    return quiz


def delete_quiz(quiz_id: int) -> bool:
    quiz = db.session.get(Quiz, quiz_id)
    if quiz is None:
        return False
    db.session.delete(quiz)
    db.session.commit()
    return True


def list_faculty_quizzes(created_by_user_id: int | None = None) -> list[dict]:
    query = Quiz.query.filter(Quiz.created_by_user_id.isnot(None))
    if created_by_user_id:
        query = query.filter_by(created_by_user_id=created_by_user_id)
    quizzes = query.order_by(Quiz.created_at.desc()).all()
    return [
        {
            "id": q.id, "title": q.title, "topic_name": q.topic.name, "difficulty_level": q.difficulty_level,
            "question_count": len(q.questions), "is_published": q.is_published,
            "scheduled_at": q.scheduled_at.isoformat() if q.scheduled_at else None,
            "attempt_count": len(q.attempts), "created_at": q.created_at.isoformat(),
        }
        for q in quizzes
    ]


def get_quiz_results(quiz_id: int) -> dict | None:
    """Section 8 — View Results. Every submitted attempt against this
    specific authored quiz, with per-student scores."""
    quiz = db.session.get(Quiz, quiz_id)
    if quiz is None:
        return None

    attempts = QuizAttempt.query.filter_by(quiz_id=quiz_id, is_submitted=True).order_by(QuizAttempt.completed_at.desc()).all()
    rows = []
    for a in attempts:
        student = db.session.get(User, a.user_id)
        rows.append({
            "attempt_id": a.id, "student_name": student.name if student else "Unknown",
            "student_email": student.email if student else "",
            "score_percent": a.score, "completed_at": a.completed_at.isoformat() if a.completed_at else None,
        })
    return {"quiz_title": quiz.title, "topic_name": quiz.topic.name, "results": rows}
