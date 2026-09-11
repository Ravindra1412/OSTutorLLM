"""
app/analytics/services/timeline_service.py

Learning Timeline (Section 11). Two responsibilities:

1. `log_event()` — the single write path every engine hook calls
   (quiz_service.submit_quiz, review_service.submit_for_review,
   tutor_service.start_session, achievement_manager award paths).
   Kept deliberately tiny and defensive (never raises into the
   caller's transaction) so instrumenting an engine with a timeline
   entry is always a safe, one-line addition.

2. `get_timeline()` — chronological read for the Timeline page/API,
   newest-first, optionally filtered by event_type.
"""

from app.extensions import db
from app.models import LearningTimeline
from app.models.learning_timeline import VALID_EVENT_TYPES
from app.utils.logger import get_ai_logger


def log_event(
    user_id: int,
    event_type: str,
    title: str,
    topic_name: str | None = None,
    score: float | None = None,
    xp_earned: int = 0,
) -> LearningTimeline | None:
    """Appends one row to the timeline. Returns the created row, or
    None if the write failed — deliberately swallows errors (logging
    them) rather than propagating, because a timeline-logging failure
    must never roll back or block the real learning event (quiz
    submission, code review, tutor turn) it's describing."""
    if event_type not in VALID_EVENT_TYPES:
        get_ai_logger().warning("timeline_log_invalid_event_type type=%s", event_type)
        return None
    try:
        entry = LearningTimeline(
            user_id=user_id,
            event_type=event_type,
            topic_name=topic_name,
            title=title,
            score=score,
            xp_earned=xp_earned,
        )
        db.session.add(entry)
        db.session.commit()
        return entry
    except Exception as exc:  # pragma: no cover - defensive path
        db.session.rollback()
        get_ai_logger().error("timeline_log_failed user_id=%s event_type=%s error=%s", user_id, event_type, exc)
        return None


def get_timeline(user_id: int, event_type: str | None = None, limit: int = 50) -> list[dict]:
    """Newest-first chronological history (Section 11 — "Display
    chronological learning history")."""
    query = LearningTimeline.query.filter_by(user_id=user_id)
    if event_type:
        query = query.filter_by(event_type=event_type)
    rows = query.order_by(LearningTimeline.created_at.desc()).limit(limit).all()
    return [row.to_dict() for row in rows]
