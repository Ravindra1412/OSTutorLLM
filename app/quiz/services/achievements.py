"""
app/quiz/services/achievements.py

Section 14 — Achievements. Awards Badge/Achievement rows (Part 3.4
models) and XP (StudentProfile.xp_total, Part 3.4) based on quiz
outcomes. Uses get-or-create for badges so this module has no hard
dependency on seed-data ordering (Part 3.4's `flask seed-db` already
seeds a "Quiz Master" badge, for example, but this module works even
if that hasn't been run).
"""

from datetime import datetime, timezone

from app.extensions import db
from app.models import Badge, Achievement, QuizAttempt, User

PERFECT_SCORE_BADGE = ("Perfectionist", "Score 100% on any quiz.", "gold", 50)
FAST_LEARNER_BADGE = ("Fast Learner", "Complete a quiz in under half the allotted time with 80%+ score.", "silver", 30)
QUIZ_MASTER_BADGE = ("Quiz Master", "Score 90%+ on any quiz.", "silver", 40)

XP_PER_CORRECT_ANSWER = 5
XP_PERFECT_SCORE_BONUS = 25


def _get_or_create_badge(name: str, description: str, tier: str, xp_reward: int) -> Badge:
    badge = Badge.query.filter_by(name=name).first()
    if badge is None:
        badge = Badge(name=name, description=description, tier=tier, xp_reward=xp_reward)
        db.session.add(badge)
        db.session.commit()
    return badge


def _award_badge_if_not_earned(user_id: int, badge: Badge) -> bool:
    """Returns True if newly awarded (False if the student already had
    it — Achievement's unique(user_id, badge_id) constraint, Part 3.4,
    makes this safe to call idempotently)."""
    already_earned = Achievement.query.filter_by(user_id=user_id, badge_id=badge.id).first()
    if already_earned:
        return False
    db.session.add(Achievement(user_id=user_id, badge_id=badge.id, earned_at=datetime.now(timezone.utc)))
    _grant_xp(user_id, badge.xp_reward)
    db.session.commit()

    # Part 3.9: Learning Timeline entry, consistent with achievement_manager.py's badges
    from app.analytics.services import timeline_service
    from app.models.learning_timeline import EVENT_ACHIEVEMENT_EARNED
    timeline_service.log_event(
        user_id, EVENT_ACHIEVEMENT_EARNED, title=f"Badge earned: {badge.name}", xp_earned=badge.xp_reward,
    )
    return True


def _grant_xp(user_id: int, amount: int) -> None:
    user = db.session.get(User, user_id)
    if user and user.student_profile:
        user.student_profile.xp_total += amount
        user.student_profile.level = 1 + user.student_profile.xp_total // 500  # Part 3.2's leveling formula


def check_and_award_quiz_achievements(user_id: int, attempt: QuizAttempt) -> list:
    """Section 14. Returns the list of badge names newly earned from
    THIS attempt, so the route/frontend can show a celebratory toast
    (Part 3.2's achievement-toast pattern) for exactly what was earned."""
    newly_earned = []

    correct_count = sum(1 for r in attempt.results if r.is_correct)
    _grant_xp(user_id, correct_count * XP_PER_CORRECT_ANSWER)

    if attempt.score == 100.0:
        badge = _get_or_create_badge(*PERFECT_SCORE_BADGE)
        _grant_xp(user_id, XP_PERFECT_SCORE_BONUS)
        if _award_badge_if_not_earned(user_id, badge):
            newly_earned.append(badge.name)

    elif attempt.score is not None and attempt.score >= 90:
        badge = _get_or_create_badge(*QUIZ_MASTER_BADGE)
        if _award_badge_if_not_earned(user_id, badge):
            newly_earned.append(badge.name)

    if (
        attempt.time_limit_seconds and attempt.started_at and attempt.completed_at
        and attempt.score is not None and attempt.score >= 80
    ):
        elapsed = (attempt.completed_at - attempt.started_at).total_seconds()
        if elapsed <= attempt.time_limit_seconds / 2:
            badge = _get_or_create_badge(*FAST_LEARNER_BADGE)
            if _award_badge_if_not_earned(user_id, badge):
                newly_earned.append(badge.name)

    db.session.commit()
    return newly_earned
