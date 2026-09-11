"""
app/models/notification.py

`notifications` table (Part 3.4, Section 5). Backs the notification
bell dropdown from Part 3.2's navbar (base.html). Pure data storage in
this phase — no notification-sending logic (email/push) is implemented,
only the persisted record and read/unread state.
"""

from app.extensions import db
from app.models.mixins import TimestampMixin

TYPE_ACHIEVEMENT = "achievement"
TYPE_PROGRESS = "progress"
TYPE_SYSTEM = "system"
TYPE_FACULTY = "faculty"

VALID_NOTIFICATION_TYPES = (TYPE_ACHIEVEMENT, TYPE_PROGRESS, TYPE_SYSTEM, TYPE_FACULTY)


class Notification(TimestampMixin, db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    message = db.Column(db.String(255), nullable=False)
    notification_type = db.Column(db.String(20), nullable=False, default=TYPE_SYSTEM)
    is_read = db.Column(db.Boolean, nullable=False, default=False, index=True)

    __table_args__ = (
        db.CheckConstraint(
            "notification_type IN ('achievement','progress','system','faculty')",
            name="ck_notifications_type",
        ),
    )

    user = db.relationship("User", back_populates="notifications")

    def __repr__(self) -> str:
        return f"<Notification id={self.id} user_id={self.user_id} read={self.is_read}>"
