"""
app/models/recommendation.py

`recommendations` table (Part 3.9, Section 7 — Recommendation Engine).
Persisted rather than computed-and-discarded-per-request for two
reasons: (1) so a dismissed recommendation stays dismissed across page
loads without re-deriving and re-showing it, and (2) so the Dashboard
can show "why" a recommendation exists (the `reason` column) as a
fixed explanation rather than a live re-computation that could drift
between the moment it was generated and the moment it's displayed.

`recommendation_engine.py` fully regenerates a student's active
(non-dismissed) recommendation set on each call to
`sync_recommendations()` — this is a replace, not an append, so stale
recommendations from an outdated performance snapshot never linger
alongside fresh ones. Dismissed rows are preserved (not deleted) only
long enough to avoid immediately re-suggesting the same thing; see
recommendation_engine.py's docstring for the exact rule.
"""

from app.extensions import db
from app.models.mixins import TimestampMixin

TYPE_NEXT_LESSON = "next_lesson"
TYPE_NEXT_QUIZ = "next_quiz"
TYPE_REVISION = "revision"
TYPE_PRACTICE = "practice"
TYPE_READING = "reading"

VALID_RECOMMENDATION_TYPES = (
    TYPE_NEXT_LESSON,
    TYPE_NEXT_QUIZ,
    TYPE_REVISION,
    TYPE_PRACTICE,
    TYPE_READING,
)


class Recommendation(TimestampMixin, db.Model):
    __tablename__ = "recommendations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    rec_type = db.Column(db.String(20), nullable=False)
    topic_name = db.Column(db.String(150), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    reason = db.Column(db.String(300), nullable=False)  # explainable: WHY this was recommended
    priority = db.Column(db.Integer, nullable=False, default=2)  # 1=high, 2=medium, 3=low
    is_dismissed = db.Column(db.Boolean, nullable=False, default=False, index=True)

    __table_args__ = (
        db.CheckConstraint(
            "rec_type IN ('next_lesson','next_quiz','revision','practice','reading')",
            name="ck_recommendations_type",
        ),
        db.CheckConstraint("priority BETWEEN 1 AND 3", name="ck_recommendations_priority_range"),
    )

    user = db.relationship("User", back_populates="recommendations")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "rec_type": self.rec_type,
            "topic_name": self.topic_name,
            "title": self.title,
            "reason": self.reason,
            "priority": self.priority,
            "generated_at": self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<Recommendation user_id={self.user_id} type={self.rec_type} topic={self.topic_name}>"
