"""
app/models/assignment_submission.py

`assignment_submissions` table (Part 3.10, Section 10). One row per
student per assignment (a resubmission overwrites in place — simpler
and sufficient for a single-instructor course; a resubmission-history
model is a reasonable future enhancement, not built here). `is_late`
is computed and stored at submission time (comparing against
`Assignment.due_at`) rather than recomputed on every read, so a
due-date edit after the fact never silently changes a past
submission's lateness status.
"""

from app.extensions import db
from app.models.mixins import TimestampMixin


class AssignmentSubmission(TimestampMixin, db.Model):
    __tablename__ = "assignment_submissions"

    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(
        db.Integer, db.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    submission_text = db.Column(db.Text, nullable=False)
    submitted_at = db.Column(db.DateTime, nullable=False)
    is_late = db.Column(db.Boolean, nullable=False, default=False)
    score = db.Column(db.Float, nullable=True)
    feedback = db.Column(db.Text, nullable=True)
    graded_at = db.Column(db.DateTime, nullable=True)
    graded_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        db.UniqueConstraint("assignment_id", "user_id", name="uq_assignment_submission_per_student"),
        db.CheckConstraint("score IS NULL OR (score >= 0)", name="ck_assignment_submission_score_nonnegative"),
    )

    assignment = db.relationship("Assignment", back_populates="submissions")
    user = db.relationship("User", foreign_keys=[user_id])
    graded_by = db.relationship("User", foreign_keys=[graded_by_user_id])

    def __repr__(self) -> str:
        return f"<AssignmentSubmission assignment_id={self.assignment_id} user_id={self.user_id}>"
