"""
app/mentor/services/student_model.py

Student Profile Intelligence (Section 5). Assembles the raw signals
every other mentor service reads, from services that already exist —
this module computes exactly one genuinely new thing (`learning_style`,
below) and otherwise composes Parts 3.7-3.9's real data.
"""

import statistics
from collections import Counter

from app.models import StudentProfile, ChatSession, CodeReviewSession, QuizAttempt
from app.analytics.services import progress_tracker, analytics_engine, performance_scorer


def infer_learning_style(user_id: int) -> dict:
    """NOT a psychometric instrument — a simple, explainable heuristic
    over which engine the student actually uses most, framed honestly
    as an activity-pattern label rather than a validated learning-
    style classification (the field's own research disputes whether
    fixed 'learning styles' are even real — this is a light, useful
    signal for recommendation framing, not a scientific claim)."""
    tutor_count = ChatSession.query.filter_by(user_id=user_id).count()
    quiz_count = QuizAttempt.query.filter_by(user_id=user_id).count()
    review_count = CodeReviewSession.query.filter_by(user_id=user_id).count()

    counts = {"Conceptual Learner (Tutor-driven)": tutor_count,
              "Test-Driven Learner (Quiz-driven)": quiz_count,
              "Hands-on Practitioner (Code Review-driven)": review_count}
    total = sum(counts.values())
    if total == 0:
        return {"label": "Not enough activity yet", "basis": "No sessions recorded."}

    top_label, top_count = max(counts.items(), key=lambda kv: kv[1])
    if top_count / total < 0.45:
        return {"label": "Balanced Learner", "basis": f"Activity is spread across all three engines ({tutor_count} tutor, {quiz_count} quiz, {review_count} code review sessions)."}
    return {"label": top_label, "basis": f"{top_count} of {total} learning sessions ({round(100*top_count/total)}%) were in this mode."}


def build_student_profile(user_id: int) -> dict:
    profile = StudentProfile.query.filter_by(user_id=user_id).first()
    scores = performance_scorer.compute_all_scores(user_id)
    confidence = performance_scorer.confidence_score(user_id)
    quiz_scores = [q["score"] for q in progress_tracker.get_quiz_scores(user_id) if q["score"] is not None]

    return {
        "learning_style": infer_learning_style(user_id),
        "current_level": profile.level if profile else 1,
        "xp_total": profile.xp_total if profile else 0,
        "completed_lessons": progress_tracker.get_completed_lessons(user_id),
        "completed_topics": progress_tracker.get_completed_topics(user_id),
        "learning_speed_days_between_sessions": analytics_engine.learning_speed_days_between_sessions(user_id),
        "quiz_performance": {
            "average": round(statistics.fmean(quiz_scores), 1) if quiz_scores else None,
            "attempt_count": len(quiz_scores),
        },
        "code_quality_score": scores["coding_score"],
        "study_frequency_streak_days": progress_tracker.get_learning_streak_days(user_id),
        "retention_signal": analytics_engine.retention_signal(user_id),
        "confidence_score": confidence,
        "overall_learning_health_preview": scores["overall_learning_score"],  # full breakdown lives in learning_health.py
    }
