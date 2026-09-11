"""
app/models/progress.py

`progress` table (Part 3.1, Section 8.4) — per-topic mastery tracking.
The formal `topics` table is deferred to the Tutor/Quiz Engine phase
(Part 3.1, Section 8.10); topic_name is a plain string for now.
"""

from datetime import datetime, timezone

from app.extensions import db


class Progress(db.Model):
    __tablename__ = "progress"
    __table_args__ = (
        db.UniqueConstraint("user_id", "topic_name", name="uq_progress_user_topic"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_name = db.Column(db.String(150), nullable=False)
    mastery_score = db.Column(db.Float, nullable=False, default=0.0)
    last_updated = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship("User", back_populates="progress_entries")

    def __repr__(self) -> str:
        return f"<Progress user_id={self.user_id} topic={self.topic_name} score={self.mastery_score}>"
