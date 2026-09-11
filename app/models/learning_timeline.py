"""
app/models/learning_timeline.py

`learning_timeline` table (Part 3.9, Section 11 — Learning Timeline).
An append-only, per-student event log distinct from ActivityLog (Part
3.4): ActivityLog is a generic platform-wide audit trail (login,
system events); LearningTimeline is specifically the chronological
record of *learning* events (lesson completed, quiz attempted, code
reviewed, tutor session started, achievement earned) that the
Timeline/Dashboard/Analytics pages read from directly, so those pages
never have to fan out and join five different engine tables just to
render "what did this student do, in order."

Written by each engine's own hook point (quiz_service.submit_quiz,
review_service.submit_for_review, tutor_service.start_session,
achievement award paths) — the same "each engine writes into one
shared table" pattern already established by Progress (Part 3.4) being
updated by the Tutor (3.6), Quiz (3.7), and Code Review (3.8) engines.

`created_at` (from TimestampMixin) IS the event's occurred-at
timestamp — no separate column, consistent with ActivityLog's design.
"""

from app.extensions import db
from app.models.mixins import TimestampMixin

EVENT_LESSON_COMPLETED = "lesson_completed"
EVENT_QUIZ_ATTEMPTED = "quiz_attempted"
EVENT_CODE_REVIEW_SUBMITTED = "code_review_submitted"
EVENT_TUTOR_SESSION = "tutor_session"
EVENT_ACHIEVEMENT_EARNED = "achievement_earned"

VALID_EVENT_TYPES = (
    EVENT_LESSON_COMPLETED,
    EVENT_QUIZ_ATTEMPTED,
    EVENT_CODE_REVIEW_SUBMITTED,
    EVENT_TUTOR_SESSION,
    EVENT_ACHIEVEMENT_EARNED,
)


class LearningTimeline(TimestampMixin, db.Model):
    __tablename__ = "learning_timeline"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = db.Column(db.String(30), nullable=False, index=True)
    topic_name = db.Column(db.String(150), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    score = db.Column(db.Float, nullable=True)  # 0-100 where applicable (quiz/code review score)
    xp_earned = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        db.CheckConstraint(
            "event_type IN ('lesson_completed','quiz_attempted','code_review_submitted',"
            "'tutor_session','achievement_earned')",
            name="ck_learning_timeline_event_type",
        ),
        db.CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 100)", name="ck_learning_timeline_score_range"
        ),
    )

    user = db.relationship("User", back_populates="timeline_events")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "topic_name": self.topic_name,
            "title": self.title,
            "score": self.score,
            "xp_earned": self.xp_earned,
            "occurred_at": self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<LearningTimeline user_id={self.user_id} type={self.event_type} topic={self.topic_name}>"
