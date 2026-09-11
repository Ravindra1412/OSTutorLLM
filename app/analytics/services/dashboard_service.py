"""
app/analytics/services/dashboard_service.py

Dashboard Service (Section 9). The single aggregation point that the
Dashboard API (Section 16) and Dashboard page call — every other
analytics module stays independently usable (and independently
testable) via its own function, while this module's only job is
composing their outputs into one response shape for the frontend so
the dashboard page needs exactly one fetch() call, not six.
"""

from app.models import Progress
from app.analytics.services import (
    progress_tracker, analytics_engine, weak_topic_detector,
    recommendation_engine, achievement_manager, performance_scorer,
    timeline_service,
)


def build_dashboard(user_id: int) -> dict:
    return {
        "progress": {
            "tracked_topic_count": progress_tracker.get_tracked_topic_count(user_id),
            "completed_topics": progress_tracker.get_completed_topics(user_id),
            "time_spent": progress_tracker.get_time_spent_summary(user_id),
        },
        "performance_scores": performance_scorer.compute_all_scores(user_id),
        "weak_topics": weak_topic_detector.detect_weak_topics(user_id, limit=3),
        "recommendations": recommendation_engine.get_active_recommendations(user_id),
        "achievements": achievement_manager.get_achievements_summary(user_id),
        "recent_timeline": timeline_service.get_timeline(user_id, limit=8),
        "average_quiz_score": analytics_engine.average_quiz_score(user_id),
    }


def refresh_and_build_dashboard(user_id: int) -> dict:
    """Regenerates recommendations and re-checks platform achievements
    before building the payload — used by the explicit dashboard
    refresh endpoint, as opposed to build_dashboard()'s cheap read-only
    path used for quick page loads."""
    recommendation_engine.sync_recommendations(user_id)
    achievement_manager.check_and_award_platform_achievements(user_id)
    return build_dashboard(user_id)
