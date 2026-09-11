"""
app/mentor/services/learning_health.py

Learning Health Engine (Section 6). A single 0-100 score assembled from
8 named factors — every factor is either reused directly from an
existing service (never recomputed twice) or a small, documented
heuristic proxy where no existing metric covers it exactly. Missing
factors are re-normalized across the remaining ones (the same pattern
`performance_scorer.compute_all_scores` already established in Part
3.9) rather than treated as zero, so a student who simply hasn't used
one engine yet isn't unfairly penalized.

Factor sources (documented once, here):
  quiz_performance     - analytics_engine.average_quiz_score (reused)
  code_review          - performance_scorer.coding_score (reused)
  hint_usage           - performance_scorer.confidence_score (reused —
                        it already IS "100 minus hint reliance")
  consistency          - analytics_engine.consistency_score (reused)
  practice_frequency    - performance_scorer.engagement_score (reused —
                        30-day activity volume)
  tutor_engagement       - NEW, simple proxy: session count is the only
                        tutor signal that exists (no per-session quality
                        score) — min(100, session_count * 15), capped at
                        ~7 sessions for full marks.
  attendance               - NEW, simple proxy: learning streak days,
                        min(100, streak_days * 10) — 10 consecutive days
                        reaches the cap.
  revision_frequency         - NEW, simple proxy: how many tracked
                        topics the student has revisited (2+ quiz
                        attempts on the same topic, from
                        analytics_engine.retention_signal), normalized
                        against total tracked topics.

Weights: all 8 factors weighted equally (1/8 each) before re-
normalization — no factor is presumed more important than another,
since unlike performance_scorer's "overall learning score" (which
measures outcome), Learning Health measures the STUDY HABIT pattern
behind the outcome, where no factor obviously dominates.
"""

from app.models import Progress
from app.analytics.services import analytics_engine, performance_scorer, progress_tracker
from app.models import ChatSession

STATUS_EXCELLENT = "Excellent"
STATUS_GOOD = "Good"
STATUS_NEEDS_IMPROVEMENT = "Needs Improvement"
STATUS_CRITICAL = "Critical"


def _tutor_engagement(user_id: int) -> float:
    count = ChatSession.query.filter_by(user_id=user_id).count()
    return round(min(100.0, count * 15), 2)


def _attendance(user_id: int) -> float:
    streak = progress_tracker.get_learning_streak_days(user_id)
    return round(min(100.0, streak * 10), 2)


def _revision_frequency(user_id: int) -> float | None:
    tracked = Progress.query.filter_by(user_id=user_id).count()
    if tracked == 0:
        return None
    revisited = len(analytics_engine.retention_signal(user_id))
    return round(min(100.0, 100.0 * revisited / tracked), 2)


def _status_for_score(score: float) -> str:
    if score >= 85:
        return STATUS_EXCELLENT
    if score >= 65:
        return STATUS_GOOD
    if score >= 40:
        return STATUS_NEEDS_IMPROVEMENT
    return STATUS_CRITICAL


def compute_learning_health(user_id: int) -> dict:
    scores = performance_scorer.compute_all_scores(user_id)

    factors = {
        "quiz_performance": analytics_engine.average_quiz_score(user_id),
        "code_review": scores["coding_score"],
        "hint_usage": performance_scorer.confidence_score(user_id),
        "consistency": scores["consistency_score"],
        "practice_frequency": scores["engagement_score"],  # always defined (0 if no activity)
        "tutor_engagement": _tutor_engagement(user_id),      # always defined
        "attendance": _attendance(user_id),                    # always defined
        "revision_frequency": _revision_frequency(user_id),
    }

    available = {k: v for k, v in factors.items() if v is not None}
    health_score = round(sum(available.values()) / len(available), 2) if available else 0.0

    return {
        "health_score": health_score,
        "status": _status_for_score(health_score),
        "factors": factors,
        "factors_with_data": list(available.keys()),
        "factors_missing_data": [k for k, v in factors.items() if v is None],
    }
