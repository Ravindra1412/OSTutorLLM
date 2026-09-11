"""
app/mentor/services/mentor_engine.py

The Learning Mentor Engine (Section 3) — the central orchestrator.
Loads a student's complete cross-engine picture and drives the
workflow described in Section 4, by calling existing, real services in
the right order — this file contains almost no computation of its own,
by design (see app/mentor/__init__.py's architecture note).
"""

from app.analytics.services import (
    dashboard_service, recommendation_engine, achievement_manager, timeline_service,
)
from app.analytics.services.weak_topic_detector import detect_weak_topics
from app.mentor.services import student_model, learning_health, confidence_engine, study_planner, insights_engine


def build_mentor_overview(user_id: int) -> dict:
    """Section 3's core responsibility list, one function call each,
    assembled into a single payload — the Mentor Dashboard's one-call
    data source (mirrors Part 3.9's dashboard_service.build_dashboard
    pattern, one level up)."""
    profile = student_model.build_student_profile(user_id)
    health = learning_health.compute_learning_health(user_id)
    confidence = confidence_engine.compute_confidence(user_id)
    weak_topics = detect_weak_topics(user_id, limit=5)
    recommendations = recommendation_engine.get_active_recommendations(user_id)
    achievements = achievement_manager.get_achievements_summary(user_id)
    insights = insights_engine.generate_insights(user_id)
    daily_plan = study_planner.get_saved_plan(user_id, "daily") or study_planner.generate_daily_plan(user_id)
    recent_timeline = timeline_service.get_timeline(user_id, limit=10)

    return {
        "student_profile": profile,
        "learning_health": health,
        "confidence": confidence,
        "weak_topics": weak_topics,
        "recommendations": recommendations,
        "achievements": achievements,
        "insights": insights,
        "todays_plan": daily_plan,
        "recent_timeline": recent_timeline,
    }


def run_full_mentor_cycle(user_id: int) -> dict:
    """Section 4's complete workflow, executed as one call: refresh
    recommendations + re-check achievements (Part 3.9's own
    refresh_and_build_dashboard does exactly this pair), regenerate
    the study plan against current data, then return the full
    overview. This is the function a 'Refresh my mentor' button calls
    — the read-only build_mentor_overview() above stays cheap for
    ordinary page loads."""
    recommendation_engine.sync_recommendations(user_id)
    achievement_manager.check_and_award_platform_achievements(user_id)
    study_planner.generate_weekly_plan(user_id)
    study_planner.generate_daily_plan(user_id)
    return build_mentor_overview(user_id)
