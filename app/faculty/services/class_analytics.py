"""
app/faculty/services/class_analytics.py

Class-wide Learning Analytics (Section 6). Aggregates the same
per-student signals Part 3.9 already computes — across every student
— rather than building a second, competing analytics pipeline.
"""

import statistics
from collections import defaultdict

from app.models import User, Progress, QuizHistory, QuizResult, QuizAttempt, CodeSubmission, CodeReviewSession
from app.utils.constants import ROLE_STUDENT

WEAK_THRESHOLD = 60.0
STRONG_THRESHOLD = 80.0


def _all_student_ids() -> list[int]:
    return [u.id for u in User.query.filter_by(role=ROLE_STUDENT).all()]


def topic_wise_class_performance() -> list[dict]:
    """Average Progress.mastery_score per topic, across every student
    tracking that topic — the class-wide counterpart to Part 3.9's
    per-student topic_wise_performance()."""
    by_topic: dict[str, list] = defaultdict(list)
    for p in Progress.query.all():
        by_topic[p.topic_name].append(p.mastery_score)

    return [
        {"topic_name": topic, "average_mastery": round(statistics.fmean(scores), 2), "student_count": len(scores)}
        for topic, scores in by_topic.items()
    ]


def weak_and_strong_topics() -> dict:
    perf = topic_wise_class_performance()
    weak = sorted([t for t in perf if t["average_mastery"] < WEAK_THRESHOLD], key=lambda t: t["average_mastery"])
    strong = sorted(
        [t for t in perf if t["average_mastery"] >= STRONG_THRESHOLD], key=lambda t: -t["average_mastery"]
    )
    return {"weak_topics": weak, "strong_topics": strong}


def quiz_statistics() -> dict:
    scores = [r.score for r in QuizHistory.query.all() if r.score is not None]
    if not scores:
        return {"average": None, "min": None, "max": None, "median": None, "attempt_count": 0}
    return {
        "average": round(statistics.fmean(scores), 2),
        "min": round(min(scores), 2),
        "max": round(max(scores), 2),
        "median": round(statistics.median(scores), 2),
        "attempt_count": len(scores),
    }


def accuracy_class_wide() -> float | None:
    results = QuizResult.query.join(QuizAttempt).filter(QuizAttempt.is_submitted.is_(True)).all()
    graded = [r for r in results if r.is_correct is not None]
    if not graded:
        return None
    correct = sum(1 for r in graded if r.is_correct)
    return round(100.0 * correct / len(graded), 2)


def code_review_statistics() -> dict:
    submissions = CodeSubmission.query.all()
    if not submissions:
        return {"submission_count": 0, "average_score": None, "average_hints_used": None}

    import json
    overalls, hints = [], []
    for sub in submissions:
        hints.append(sub.hints_used_count or 0)
        if sub.scores_json:
            try:
                overall = json.loads(sub.scores_json).get("overall")
                if overall is not None:
                    overalls.append(overall)
            except (ValueError, TypeError):
                pass

    return {
        "submission_count": len(submissions),
        "average_score": round(statistics.fmean(overalls), 2) if overalls else None,
        "average_hints_used": round(statistics.fmean(hints), 2),
    }


def average_learning_time_minutes() -> float:
    from app.analytics.services.progress_tracker import get_time_spent_summary

    ids = _all_student_ids()
    if not ids:
        return 0.0
    total = sum(get_time_spent_summary(sid)["total_minutes"] for sid in ids)
    return round(total / len(ids), 1)


def topic_completion_rates() -> list[dict]:
    """Percentage of tracking students who've reached the 75%+ mastery
    threshold (Part 3.9's MASTERY_COMPLETE_THRESHOLD), per topic."""
    from app.analytics.services.progress_tracker import MASTERY_COMPLETE_THRESHOLD

    by_topic: dict[str, list] = defaultdict(list)
    for p in Progress.query.all():
        by_topic[p.topic_name].append(p.mastery_score)

    return [
        {
            "topic_name": topic,
            "completion_rate_percent": round(
                100.0 * sum(1 for s in scores if s >= MASTERY_COMPLETE_THRESHOLD) / len(scores), 1
            ),
            "tracking_student_count": len(scores),
        }
        for topic, scores in by_topic.items()
    ]


def build_class_analytics() -> dict:
    return {
        "topic_wise_performance": topic_wise_class_performance(),
        **weak_and_strong_topics(),
        "quiz_statistics": quiz_statistics(),
        "accuracy": accuracy_class_wide(),
        "code_review_statistics": code_review_statistics(),
        "average_learning_time_minutes": average_learning_time_minutes(),
        "topic_completion_rates": topic_completion_rates(),
    }
