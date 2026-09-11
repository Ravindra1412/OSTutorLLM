"""
app/analytics/services/analytics_engine.py

Learning Analytics (Section 5). Every metric here is computed
deterministically from existing tables (QuizHistory, QuizResult/
QuizAttempt, Progress, CodeSubmission) — no LLM call, no external
service, so this is free, fast, and fully explainable (Part 3.9's own
Section 13 principle: "simple, explainable heuristics rather than
unsupported predictive claims" is applied throughout this module too,
not just the dedicated predictive_engine.py).

Metric definitions (documented once, here, rather than scattered):

  average_quiz_score   - mean of QuizHistory.score across all attempts.
  topic_wise_performance - Progress.mastery_score per topic (the one
                         blended, cross-engine number every engine
                         already maintains — Section 5 doesn't need a
                         second competing performance number).
  improvement_rate     - mean score of the most recent 5 quiz attempts
                         minus mean score of the 5 before that,
                         expressed in percentage points. None if fewer
                         than 2 attempts exist (not enough data for a
                         trend — returned as None, never guessed).
  accuracy             - correct QuizResult rows / total graded
                         QuizResult rows, across all submitted attempts.
  learning_speed        - average days between consecutive learning
                         events (LearningTimeline) over the last 30
                         events. Lower = more frequent/faster-paced
                         learning. None if fewer than 2 events.
  consistency_score     - 100 minus the coefficient of variation (as a
                         percentage) of quiz scores, clamped to [0,100].
                         High = scores cluster tightly around the mean;
                         low = scores swing widely attempt to attempt.
  retention_signal       - for topics with 2+ quiz attempts, the score
                         delta between the first and most recent
                         attempt on that topic. Positive = retained/
                         improved since first learning it.
  mistake_patterns        - most frequent static-analysis finding
                         categories across Code Review submissions
                         (Part 3.8's `category` field) — the closest
                         real, structured signal this codebase has for
                         "repeated errors."
"""

import json
import statistics
from collections import Counter

from app.models import QuizHistory, QuizAttempt, QuizResult, Progress, CodeSubmission, CodeReviewSession, LearningTimeline


def average_quiz_score(user_id: int) -> float | None:
    scores = [r.score for r in QuizHistory.query.filter_by(user_id=user_id).all() if r.score is not None]
    return round(statistics.fmean(scores), 2) if scores else None


def topic_wise_performance(user_id: int) -> list[dict]:
    entries = Progress.query.filter_by(user_id=user_id).order_by(Progress.mastery_score.desc()).all()
    return [{"topic_name": e.topic_name, "mastery_score": e.mastery_score} for e in entries]


def improvement_rate(user_id: int) -> float | None:
    scores = [
        r.score for r in QuizHistory.query.filter_by(user_id=user_id).order_by(QuizHistory.taken_at.asc()).all()
        if r.score is not None
    ]
    if len(scores) < 2:
        return None
    recent = scores[-5:]
    prior = scores[-10:-5] if len(scores) > 5 else scores[:-5]
    if not prior:
        return None
    return round(statistics.fmean(recent) - statistics.fmean(prior), 2)


def accuracy(user_id: int) -> float | None:
    results = (
        QuizResult.query.join(QuizAttempt)
        .filter(QuizAttempt.user_id == user_id, QuizAttempt.is_submitted.is_(True))
        .all()
    )
    graded = [r for r in results if r.is_correct is not None]
    if not graded:
        return None
    correct = sum(1 for r in graded if r.is_correct)
    return round(100.0 * correct / len(graded), 2)


def learning_speed_days_between_sessions(user_id: int) -> float | None:
    events = (
        LearningTimeline.query.filter_by(user_id=user_id)
        .order_by(LearningTimeline.created_at.desc())
        .limit(30)
        .all()
    )
    if len(events) < 2:
        return None
    timestamps = sorted(e.created_at for e in events)
    gaps = [(timestamps[i] - timestamps[i - 1]).total_seconds() / 86400.0 for i in range(1, len(timestamps))]
    return round(statistics.fmean(gaps), 2)


def consistency_score(user_id: int) -> float | None:
    scores = [r.score for r in QuizHistory.query.filter_by(user_id=user_id).all() if r.score is not None]
    if len(scores) < 2:
        return None
    mean = statistics.fmean(scores)
    if mean == 0:
        return None
    stdev = statistics.pstdev(scores)
    coefficient_of_variation_pct = (stdev / mean) * 100
    return round(max(0.0, min(100.0, 100.0 - coefficient_of_variation_pct)), 2)


def retention_signal(user_id: int) -> list[dict]:
    rows = QuizHistory.query.filter_by(user_id=user_id).order_by(QuizHistory.taken_at.asc()).all()
    by_topic: dict[str, list] = {}
    for r in rows:
        if r.score is not None:
            by_topic.setdefault(r.topic_name, []).append(r.score)

    out = []
    for topic, scores in by_topic.items():
        if len(scores) >= 2:
            out.append({
                "topic_name": topic,
                "first_score": scores[0],
                "latest_score": scores[-1],
                "retention_delta": round(scores[-1] - scores[0], 2),
            })
    return out


def mistake_patterns(user_id: int, top_n: int = 5) -> list[dict]:
    """Section 5 — Mistake Patterns / Repeated Errors, drawn from Code
    Review static-analysis finding categories (Part 3.8)."""
    submissions = (
        CodeSubmission.query.join(CodeReviewSession)
        .filter(CodeReviewSession.user_id == user_id, CodeSubmission.static_analysis_json.isnot(None))
        .all()
    )
    categories: Counter = Counter()
    for sub in submissions:
        try:
            findings = json.loads(sub.static_analysis_json)
        except (ValueError, TypeError):
            continue
        for f in findings:
            categories[f.get("category", "unknown")] += 1

    return [{"category": cat, "occurrences": count} for cat, count in categories.most_common(top_n)]


def build_full_analytics(user_id: int) -> dict:
    """Section 5 — assembles every metric above into one payload for
    the Analytics API / Dashboard."""
    return {
        "average_quiz_score": average_quiz_score(user_id),
        "topic_wise_performance": topic_wise_performance(user_id),
        "improvement_rate": improvement_rate(user_id),
        "accuracy": accuracy(user_id),
        "learning_speed_days_between_sessions": learning_speed_days_between_sessions(user_id),
        "consistency_score": consistency_score(user_id),
        "retention_signal": retention_signal(user_id),
        "mistake_patterns": mistake_patterns(user_id),
    }
