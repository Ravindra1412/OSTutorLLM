"""
app/analytics/services/predictive_engine.py

Predictive Learning (Section 13). Per the phase brief: "Use simple,
explainable heuristics rather than unsupported predictive claims."
Nothing in this module is a trained model or a statistically validated
probability — every number is a direct, documented transformation of
already-tracked data, and every response says so in its own field
names (e.g. `estimated_mastery_likelihood`, never `probability`, to
avoid implying statistical rigor that doesn't exist).

  estimated_mastery_likelihood - Progress.mastery_score / 100 for a
                                topic, directly. A 72% mastery score
                                becomes a 0.72 "likelihood" — this is a
                                relabeling for the dashboard's benefit,
                                not a new computation.
  readiness_for_next_lesson     - True if the student's overall quiz
                                average (last 5 attempts) is >= 70 AND
                                they have learned on at least 1 of the
                                last 3 days. Both are simple, visible
                                thresholds, not a hidden model.
  topics_needing_revision         - delegates directly to
                                weak_topic_detector.detect_weak_topics()
                                — no separate logic duplicated.
  risk_of_falling_behind           - "elevated" if the student's streak
                                is 0 (no activity yesterday/today) AND
                                engagement_score < 20; "watch" if only
                                one of those is true; else "low". A
                                3-bucket label, not a numeric score, to
                                avoid implying false precision.
"""

from app.models import QuizHistory
from app.analytics.services.weak_topic_detector import detect_weak_topics
from app.analytics.services.progress_tracker import get_learning_streak_days
from app.analytics.services.performance_scorer import engagement_score
from app.models import Progress


def estimated_mastery_likelihood(user_id: int) -> list[dict]:
    entries = Progress.query.filter_by(user_id=user_id).all()
    return [
        {"topic_name": e.topic_name, "estimated_mastery_likelihood": round(e.mastery_score / 100.0, 2)}
        for e in entries
    ]


def readiness_for_next_lesson(user_id: int) -> dict:
    recent_scores = [
        r.score for r in
        QuizHistory.query.filter_by(user_id=user_id).order_by(QuizHistory.taken_at.desc()).limit(5).all()
        if r.score is not None
    ]
    avg_recent = round(sum(recent_scores) / len(recent_scores), 2) if recent_scores else None
    recently_active = get_learning_streak_days(user_id) >= 1

    ready = bool(avg_recent is not None and avg_recent >= 70 and recently_active)
    return {
        "ready": ready,
        "recent_quiz_average": avg_recent,
        "recently_active": recently_active,
        "reason": (
            "Recent quiz average is 70%+ and activity is recent." if ready else
            "Not enough recent quiz data yet." if avg_recent is None else
            "Recent quiz average is below 70%." if avg_recent < 70 else
            "No recent learning activity."
        ),
    }


def topics_needing_revision(user_id: int) -> list[dict]:
    return detect_weak_topics(user_id, limit=5)


def risk_of_falling_behind(user_id: int) -> dict:
    streak = get_learning_streak_days(user_id)
    engagement = engagement_score(user_id)

    inactive = streak == 0
    low_engagement = engagement < 20

    if inactive and low_engagement:
        level = "elevated"
    elif inactive or low_engagement:
        level = "watch"
    else:
        level = "low"

    return {
        "level": level,
        "current_streak_days": streak,
        "engagement_score": engagement,
        "note": "Heuristic based on activity streak and 30-day engagement volume — not a statistical prediction.",
    }


def build_predictive_summary(user_id: int) -> dict:
    return {
        "estimated_mastery_likelihood": estimated_mastery_likelihood(user_id),
        "readiness_for_next_lesson": readiness_for_next_lesson(user_id),
        "topics_needing_revision": topics_needing_revision(user_id),
        "risk_of_falling_behind": risk_of_falling_behind(user_id),
    }
