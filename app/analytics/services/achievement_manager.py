"""
app/analytics/services/achievement_manager.py

Achievement System (Section 8). Extends — does not replace —
app/quiz/services/achievements.py (Part 3.7), which already covers
quiz-specific badges (Perfectionist, Quiz Master, Fast Learner) and is
left untouched. This module adds the badges that only make sense once
data exists ACROSS engines: streaks, cross-engine diversity, and
volume milestones for the Code Review and Tutor engines, which had no
achievement logic at all before this phase.

XP/leveling reuses the exact formula already established in Part 3.2/
3.7 (level = 1 + xp_total // 500) via StudentProfile — one leveling
system for the whole platform, not a competing one for this module.

Daily Goal (Section 8) is a fixed, simple target (DAILY_GOAL_MINUTES)
rather than a per-student configurable one — configurability is a
reasonable future enhancement (Section 22) but out of this phase's
scope; a fixed goal is fully functional and honestly labeled as such.

Certificates (Section 8) are an explicit, honest placeholder — no
certificate-generation/PDF system exists in this codebase (would
compose with the `pdf` capability at a future phase); this module
returns `available: False` rather than fabricating one.
"""

from datetime import datetime, timezone

from app.extensions import db
from app.models import Badge, Achievement, User, ChatSession, CodeReviewSession
from app.analytics.services.progress_tracker import get_learning_streak_days, get_time_spent_summary

DAILY_GOAL_MINUTES = 15

STREAK_BADGES = [
    (3, "3-Day Streak", "Learn on 3 consecutive days.", "bronze", 15),
    (7, "7-Day Streak", "Learn on 7 consecutive days.", "silver", 40),
    (30, "30-Day Streak", "Learn on 30 consecutive days.", "gold", 150),
]
WELL_ROUNDED_BADGE = ("Well-Rounded Learner", "Use the Tutor, Quiz, and Code Review engines at least once each.", "silver", 35)
CODE_REVIEWER_BADGE = ("Dedicated Reviewer", "Submit 5 code reviews.", "bronze", 20)
CONVERSATIONALIST_BADGE = ("Conversationalist", "Complete 5 Tutor sessions.", "bronze", 20)


def _get_or_create_badge(name: str, description: str, tier: str, xp_reward: int) -> Badge:
    badge = Badge.query.filter_by(name=name).first()
    if badge is None:
        badge = Badge(name=name, description=description, tier=tier, xp_reward=xp_reward)
        db.session.add(badge)
        db.session.commit()
    return badge


def _award_if_not_earned(user_id: int, badge: Badge) -> bool:
    if Achievement.query.filter_by(user_id=user_id, badge_id=badge.id).first():
        return False
    db.session.add(Achievement(user_id=user_id, badge_id=badge.id, earned_at=datetime.now(timezone.utc)))
    user = db.session.get(User, user_id)
    if user and user.student_profile:
        user.student_profile.xp_total += badge.xp_reward
        user.student_profile.level = 1 + user.student_profile.xp_total // 500
    db.session.commit()

    from app.analytics.services import timeline_service
    from app.models.learning_timeline import EVENT_ACHIEVEMENT_EARNED
    timeline_service.log_event(
        user_id, EVENT_ACHIEVEMENT_EARNED, title=f"Badge earned: {badge.name}", xp_earned=badge.xp_reward,
    )
    return True


def check_and_award_platform_achievements(user_id: int) -> list[str]:
    """Section 8. Called from each engine's hook point (alongside the
    existing quiz-only check_and_award_quiz_achievements) — safe to
    call idempotently and cheaply from any engine's submit path."""
    newly_earned = []

    streak = get_learning_streak_days(user_id)
    for threshold, name, desc, tier, xp in STREAK_BADGES:
        if streak >= threshold:
            badge = _get_or_create_badge(name, desc, tier, xp)
            if _award_if_not_earned(user_id, badge):
                newly_earned.append(badge.name)

    from app.models import QuizAttempt

    used_tutor = ChatSession.query.filter_by(user_id=user_id).count() > 0
    used_quiz = QuizAttempt.query.filter_by(user_id=user_id).count() > 0
    used_code_review = CodeReviewSession.query.filter_by(user_id=user_id).count() > 0
    if used_tutor and used_quiz and used_code_review:
        badge = _get_or_create_badge(*WELL_ROUNDED_BADGE)
        if _award_if_not_earned(user_id, badge):
            newly_earned.append(badge.name)

    if CodeReviewSession.query.filter_by(user_id=user_id).count() >= 5:
        badge = _get_or_create_badge(*CODE_REVIEWER_BADGE)
        if _award_if_not_earned(user_id, badge):
            newly_earned.append(badge.name)

    if ChatSession.query.filter_by(user_id=user_id).count() >= 5:
        badge = _get_or_create_badge(*CONVERSATIONALIST_BADGE)
        if _award_if_not_earned(user_id, badge):
            newly_earned.append(badge.name)

    return newly_earned


def get_daily_goal_status(user_id: int) -> dict:
    today_minutes = get_time_spent_summary(user_id)["today_minutes"]
    return {
        "goal_minutes": DAILY_GOAL_MINUTES,
        "today_minutes": today_minutes,
        "met": today_minutes >= DAILY_GOAL_MINUTES,
        "percent": round(min(100.0, 100.0 * today_minutes / DAILY_GOAL_MINUTES), 1),
    }


def get_weekly_goal_status(user_id: int) -> dict:
    week_minutes = get_time_spent_summary(user_id)["this_week_minutes"]
    weekly_goal = DAILY_GOAL_MINUTES * 5  # 5 active days/week target
    return {
        "goal_minutes": weekly_goal,
        "this_week_minutes": week_minutes,
        "met": week_minutes >= weekly_goal,
        "percent": round(min(100.0, 100.0 * week_minutes / weekly_goal), 1),
    }


def get_achievements_summary(user_id: int) -> dict:
    earned = (
        Achievement.query.filter_by(user_id=user_id)
        .join(Badge)
        .order_by(Achievement.earned_at.desc())
        .all()
    )
    user = db.session.get(User, user_id)
    profile = user.student_profile if user else None
    return {
        "badges": [
            {
                "name": a.badge.name, "description": a.badge.description, "tier": a.badge.tier,
                "xp_reward": a.badge.xp_reward, "earned_at": a.earned_at.isoformat(),
            }
            for a in earned
        ],
        "xp_total": profile.xp_total if profile else 0,
        "level": profile.level if profile else 1,
        "streak_days": get_learning_streak_days(user_id),
        "daily_goal": get_daily_goal_status(user_id),
        "weekly_goal": get_weekly_goal_status(user_id),
        "certificate": {"available": False, "note": "Certificate generation is not implemented in this phase."},
    }
