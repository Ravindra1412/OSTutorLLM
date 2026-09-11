"""
app/models/completed_lesson.py

`completed_lessons` table (Part 3.4, Section 7 — Learning Models).
A many-to-many join between User and Lesson (a student can complete
many lessons; a lesson is completed by many students), enriched with
per-completion metadata (when, how long). This is what "Completed
Lessons" and part of "Learning Time" tracking (Section 7) is built on;
"Topic Mastery" and "Weak Topics" continue to be derived from the
existing `progress` table (Part 3.1 Section 8.4), since mastery is a
computed rollup rather than a raw event log.
"""

from app.extensions import db
from app.models.mixins import TimestampMixin


class CompletedLesson(TimestampMixin, db.Model):
    __tablename__ = "completed_lessons"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    time_spent_minutes = db.Column(db.Float, nullable=True)

    __table_args__ = (
        db.UniqueConstraint("user_id", "lesson_id", name="uq_completed_lessons_user_lesson"),
        db.CheckConstraint(
            "time_spent_minutes IS NULL OR time_spent_minutes >= 0",
            name="ck_completed_lessons_time_nonnegative",
        ),
    )

    user = db.relationship("User", back_populates="completed_lessons")
    lesson = db.relationship("Lesson", back_populates="completions")

    def __repr__(self) -> str:
        return f"<CompletedLesson user_id={self.user_id} lesson_id={self.lesson_id}>"
