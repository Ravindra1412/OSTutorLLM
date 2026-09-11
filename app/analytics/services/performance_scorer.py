"""
app/analytics/services/performance_scorer.py

Performance Scoring (Section 12). Every score is 0-100 and every
formula is documented here rather than buried in code, per this
phase's explainability requirement.

  topic_mastery_score - mean Progress.mastery_score across every
                       tracked topic. The platform's single blended
                       mastery number (Part 3.4), averaged.
  quiz_score           - mean QuizHistory.score (analytics_engine's
                       average_quiz_score, reused rather than
                       recomputed).
  coding_score          - mean overall score across Code Review
                       submissions (CodeSubmission.scores_json.overall,
                       Part 3.8).
  consistency_score      - analytics_engine.consistency_score, reused
                       (100 minus the coefficient of variation of quiz
                       scores).
  engagement_score        - min(100, learning_events_last_30_days * 4).
                       25 learning events in the last 30 days (roughly
                       one every 1.2 days) reaches the 100 cap. A
                       simple, explainable frequency measure — NOT a
                       claim about depth or quality of engagement.
  confidence_score          - 100 minus (average hints used per code
                       review submission * 20, capped). A student who
                       needs 0 hints on average scores 100; one needing
                       5+ hints per submission on average scores 0.
                       Deliberately simple: hint reliance is the one
                       real, measured proxy for confidence this
                       codebase has.
  overall_learning_score      - a weighted average of the five scores
                       above (weights below), skipping any component
                       with no data yet (re-normalizing the remaining
                       weights) rather than treating missing data as
                       zero, which would unfairly punish a student who
                       simply hasn't used one engine yet.

Weights (must sum to 1.0): mastery 0.30, quiz 0.25, coding 0.20,
consistency 0.15, engagement 0.10 — mastery and quiz score weighted
highest because they are the most direct measures of actual learning
outcome; engagement weighted lowest because activity volume alone
doesn't prove understanding.
"""

import json
import statistics

from app.models import CodeSubmission, CodeReviewSession, LearningTimeline
from app.analytics.services.analytics_engine import average_quiz_score, consistency_score
from app.analytics.services.progress_tracker import get_completed_topics
from app.models import Progress

_WEIGHTS = {
    "topic_mastery_score": 0.30,
    "quiz_score": 0.25,
    "coding_score": 0.20,
    "consistency_score": 0.15,
    "engagement_score": 0.10,
}


def topic_mastery_score(user_id: int) -> float | None:
    entries = Progress.query.filter_by(user_id=user_id).all()
    if not entries:
        return None
    return round(statistics.fmean(e.mastery_score for e in entries), 2)


def coding_score(user_id: int) -> float | None:
    submissions = (
        CodeSubmission.query.join(CodeReviewSession)
        .filter(CodeReviewSession.user_id == user_id, CodeSubmission.scores_json.isnot(None))
        .all()
    )
    overalls = []
    for sub in submissions:
        try:
            overall = json.loads(sub.scores_json).get("overall")
        except (ValueError, TypeError):
            overall = None
        if overall is not None:
            overalls.append(overall)
    return round(statistics.fmean(overalls), 2) if overalls else None


def engagement_score(user_id: int) -> float:
    from datetime import datetime, timezone, timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    count = LearningTimeline.query.filter(
        LearningTimeline.user_id == user_id, LearningTimeline.created_at >= cutoff
    ).count()
    return round(min(100.0, count * 4), 2)


def confidence_score(user_id: int) -> float | None:
    submissions = (
        CodeSubmission.query.join(CodeReviewSession)
        .filter(CodeReviewSession.user_id == user_id).all()
    )
    if not submissions:
        return None
    avg_hints = statistics.fmean(s.hints_used_count or 0 for s in submissions)
    return round(max(0.0, 100.0 - avg_hints * 20), 2)


def compute_all_scores(user_id: int) -> dict:
    scores = {
        "topic_mastery_score": topic_mastery_score(user_id),
        "quiz_score": average_quiz_score(user_id),
        "coding_score": coding_score(user_id),
        "consistency_score": consistency_score(user_id),
        "engagement_score": engagement_score(user_id),  # always defined (0 if no activity)
    }

    available = {k: v for k, v in scores.items() if v is not None}
    if not available:
        overall = None
    else:
        total_weight = sum(_WEIGHTS[k] for k in available)
        overall = round(sum(_WEIGHTS[k] * v for k, v in available.items()) / total_weight, 2)

    scores["overall_learning_score"] = overall
    scores["completed_topic_count"] = len(get_completed_topics(user_id))
    return scores
