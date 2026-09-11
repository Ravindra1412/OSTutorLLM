"""
app/models/activity_log.py

`activity_log` table (Part 3.4, Section 5). A generic, append-only
record of significant user actions across the whole platform (login,
topic started, quiz submitted, achievement earned, etc.) — the
database-backed counterpart to the file-based `logs/activity.log`
from Part 3.3 (app/utils/logger.py). The file log is for ops/debugging
tail -f visibility; this table is for querying activity data (e.g. the
Faculty Analytics engagement trend chart, Part 2 Section 18) from SQL.

`user_id` is nullable to allow logging system-level events (e.g. a
future scheduled job) that aren't tied to a specific user.
"""

from app.extensions import db
from app.models.mixins import TimestampMixin


class ActivityLog(TimestampMixin, db.Model):
    __tablename__ = "activity_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False, index=True)  # e.g. "login", "quiz_submitted"
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)

    user = db.relationship("User", back_populates="activity_logs")

    def __repr__(self) -> str:
        return f"<ActivityLog id={self.id} user_id={self.user_id} action={self.action}>"
