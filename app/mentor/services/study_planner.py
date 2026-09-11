"""
app/mentor/services/study_planner.py

AI Study Planner (Section 9). Builds real schedules from the student's
actual weak topics (`weak_topic_detector`, Part 3.9) and unstarted
curriculum topics (`Topic`/`Progress`, Part 3.4) — never a generic
template. Persisted to `StudyPlan` (one row per user+period, replaced
on regeneration) so "today's plan" is stable across page loads rather
than reshuffling every time the student checks it.
"""

import json
from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models import Topic, Progress, StudyPlan
from app.models.study_plan import PERIOD_DAILY, PERIOD_WEEKLY, PERIOD_MONTHLY
from app.analytics.services.weak_topic_detector import detect_weak_topics

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _unstarted_topics(user_id: int, limit: int) -> list[str]:
    tracked = {p.topic_name for p in Progress.query.filter_by(user_id=user_id).all()}
    topics = Topic.query.order_by(Topic.difficulty_level.asc()).all()
    return [t.name for t in topics if t.name not in tracked][:limit]


def _save_plan(user_id: int, period_type: str, plan: dict) -> StudyPlan:
    row = StudyPlan.query.filter_by(user_id=user_id, period_type=period_type).first()
    if row is None:
        row = StudyPlan(user_id=user_id, period_type=period_type, plan_json=json.dumps(plan))
        db.session.add(row)
    else:
        row.plan_json = json.dumps(plan)
    db.session.commit()
    return row


def generate_weekly_plan(user_id: int) -> dict:
    """Section 9's own worked example, but populated with the
    student's REAL weak topics rather than the illustrative sample
    content — weak topics get the earlier weekdays (highest priority,
    freshest attention), a new/unstarted topic fills any remaining
    slot, Saturday is always a quiz on the week's most-covered topic,
    Sunday is always revision."""
    weak = [w["topic_name"] for w in detect_weak_topics(user_id, limit=4)]
    fresh = _unstarted_topics(user_id, limit=5 - len(weak) if len(weak) < 5 else 0)
    weekday_topics = (weak + fresh)[:5]
    while len(weekday_topics) < 5:
        weekday_topics.append("Free practice — revisit any topic")

    schedule = []
    for i, day in enumerate(WEEKDAYS[:5]):
        topic = weekday_topics[i]
        reason = "Flagged as a weak topic — prioritized early in the week." if topic in weak else \
                 "Unstarted curriculum topic — a good time to begin it." if topic in fresh else \
                 "No specific gap detected — use this slot for whatever feels least solid."
        schedule.append({"day": day, "activity": f"Study: {topic}", "topic": topic, "reason": reason})

    quiz_topic = weekday_topics[0] if weekday_topics else None
    schedule.append({
        "day": "Saturday", "activity": f"Quiz: {quiz_topic}" if quiz_topic else "Quiz: any tracked topic",
        "topic": quiz_topic, "reason": "Checks retention of this week's main focus topic.",
    })
    schedule.append({
        "day": "Sunday", "activity": "Revision — review this week's weak topics",
        "topic": None, "reason": "Spaced revision improves retention (Section 12's retention-signal principle).",
    })

    plan = {"period": "weekly", "schedule": schedule, "generated_at": datetime.now(timezone.utc).isoformat()}
    _save_plan(user_id, PERIOD_WEEKLY, plan)
    return plan


def generate_daily_plan(user_id: int) -> dict:
    """Today's specific slot from the (regenerated) weekly plan — so
    daily and weekly are always consistent with each other, not two
    independently-randomized plans."""
    weekly = generate_weekly_plan(user_id)
    today_name = datetime.now(timezone.utc).strftime("%A")
    todays_slot = next((s for s in weekly["schedule"] if s["day"] == today_name), weekly["schedule"][0])

    plan = {
        "period": "daily", "day": today_name, "focus": todays_slot,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_plan(user_id, PERIOD_DAILY, plan)
    return plan


def generate_monthly_plan(user_id: int) -> dict:
    """4 weekly themes — week 1-2 close current weak topics, week 3
    introduces new curriculum topics, week 4 is exam-prep-style
    cumulative revision."""
    weak = [w["topic_name"] for w in detect_weak_topics(user_id, limit=6)]
    fresh = _unstarted_topics(user_id, limit=6)

    weeks = [
        {"week": 1, "theme": "Close current gaps", "topics": weak[:3] or ["General revision"]},
        {"week": 2, "theme": "Reinforce and quiz", "topics": weak[3:6] or fresh[:2] or ["General practice"]},
        {"week": 3, "theme": "New topics", "topics": fresh[:3] or ["Advanced practice on tracked topics"]},
        {"week": 4, "theme": "Cumulative revision + exam prep", "topics": (weak + fresh)[:4] or ["Full review"]},
    ]

    plan = {"period": "monthly", "weeks": weeks, "generated_at": datetime.now(timezone.utc).isoformat()}
    _save_plan(user_id, PERIOD_MONTHLY, plan)
    return plan


def get_saved_plan(user_id: int, period_type: str) -> dict | None:
    row = StudyPlan.query.filter_by(user_id=user_id, period_type=period_type).first()
    return json.loads(row.plan_json) if row else None
