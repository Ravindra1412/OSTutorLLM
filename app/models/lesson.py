"""
app/models/lesson.py

`lessons` table (Part 3.1, Section 8.7 deferred; implemented Part 3.4).
Reference/summary content within a Topic, ordered by sequence_order.
Actual completion tracking per student lives in CompletedLesson
(many-to-many join table, Part 3.4 Section 7).
"""

from app.extensions import db
from app.models.mixins import TimestampMixin


class Lesson(TimestampMixin, db.Model):
    __tablename__ = "lessons"

    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    content_summary = db.Column(db.Text, nullable=False)
    sequence_order = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint("topic_id", "sequence_order", name="uq_lessons_topic_sequence"),
    )

    topic = db.relationship("Topic", back_populates="lessons")
    completions = db.relationship("CompletedLesson", back_populates="lesson", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Lesson id={self.id} topic_id={self.topic_id} title={self.title}>"
