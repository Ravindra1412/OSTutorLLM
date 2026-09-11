"""
app/quiz/services/scoring_engine.py

The Scoring Engine (Section 1/9). Aggregates a QuizAttempt's
QuizResult rows into a single 0-100 score. Kept deliberately separate
from the Evaluation Engine (which grades ONE question) — this module's
only job is arithmetic over the results, which makes both independently
testable and lets scoring policy (e.g. negative marking) change without
touching any grading logic.
"""

from app.models import QuizAttempt, QuizQuestion


def compute_attempt_score(attempt: QuizAttempt) -> float:
    """Returns a 0-100 percentage score. If `attempt.quiz.negative_marking_enabled`
    (Section 9, optional), each fully-incorrect (score_fraction==0 AND
    not pending review) auto-graded result subtracts a small penalty
    rather than just contributing zero — capped so total score can never
    go below 0."""
    results = attempt.results
    if not results:
        return 0.0

    total_possible = sum(r.question.points for r in results)
    if total_possible <= 0:
        return 0.0

    earned = sum(r.points_earned for r in results)

    if attempt.quiz.negative_marking_enabled:
        penalty = sum(
            _negative_penalty(r.question) for r in results
            if r.is_correct is False and r.points_earned == 0
        )
        earned = max(0.0, earned - penalty)

    return round((earned / total_possible) * 100, 2)


def _negative_penalty(question: QuizQuestion) -> float:
    """A wrong auto-gradable answer costs 25% of that question's point
    value — deliberately gentler than a full point, since the goal is
    to discourage random guessing on MCQ-style questions without being
    punitive (an explicit configuration choice, not a fixed platform
    default — negative marking itself is opt-in per Section 9)."""
    return question.points * 0.25


def compute_points_earned(question: QuizQuestion, score_fraction: float) -> float:
    return round(question.points * score_fraction, 2)


def summarize_attempt(attempt: QuizAttempt) -> dict:
    results = attempt.results
    correct_count = sum(1 for r in results if r.is_correct)
    return {
        "total_questions": len(results),
        "correct_count": correct_count,
        "incorrect_count": len(results) - correct_count,
        "score_percent": compute_attempt_score(attempt),
    }
