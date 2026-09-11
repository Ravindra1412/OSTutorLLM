"""
app/models/code_review_session.py

`code_review_sessions` table (Part 3.8, Section 13). One row per
"code review conversation" a student has on a topic — mirrors the
ChatSession pattern from Part 3.6 exactly (a session groups multiple
submissions the way a ChatSession groups multiple tutor messages),
so a student can submit, get feedback, revise, and resubmit multiple
times (Section 3's workflow) within one continuous review thread.
"""

from app.extensions import db
from app.models.mixins import TimestampMixin

STATUS_ACTIVE = "active"
STATUS_COMPLETED = "completed"


class CodeReviewSession(TimestampMixin, db.Model):
    __tablename__ = "code_review_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_name = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=STATUS_ACTIVE)

    __table_args__ = (
        db.CheckConstraint("status IN ('active','completed')", name="ck_code_review_sessions_status"),
    )

    user = db.relationship("User", back_populates="code_review_sessions")
    submissions = db.relationship(
        "CodeSubmission", back_populates="session", cascade="all, delete-orphan",
        order_by="CodeSubmission.submission_number",
    )

    def __repr__(self) -> str:
        return f"<CodeReviewSession id={self.id} user_id={self.user_id} topic={self.topic_name}>"
