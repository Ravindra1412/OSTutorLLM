"""
app/models/assignment.py

`assignments` table (Part 3.10, Section 10). Faculty-authored coursework
tied to a Topic, distinct from a Quiz (auto-graded, structured
questions) or a Code Review submission (ad-hoc, student-initiated) —
an Assignment is instructor-defined work with a due date that students
submit free-text/code against and a faculty member grades manually.
"""

from app.extensions import db
from app.models.mixins import TimestampMixin


class Assignment(TimestampMixin, db.Model):
    __tablename__ = "assignments"

    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    due_at = db.Column(db.DateTime, nullable=False)
    allow_late_submission = db.Column(db.Boolean, nullable=False, default=True)
    is_published = db.Column(db.Boolean, nullable=False, default=False, index=True)
    max_score = db.Column(db.Float, nullable=False, default=100.0)

    __table_args__ = (
        db.CheckConstraint("max_score > 0", name="ck_assignments_max_score_positive"),
    )

    topic = db.relationship("Topic")
    created_by = db.relationship("User", foreign_keys=[created_by_user_id])
    submissions = db.relationship("AssignmentSubmission", back_populates="assignment", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Assignment id={self.id} title={self.title}>"
