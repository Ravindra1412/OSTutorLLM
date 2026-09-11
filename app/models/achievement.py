"""
app/models/achievement.py

`achievements` table (Part 3.1, Section 8.7; redesigned Part 3.4,
Section 10). Originally a simple free-text `title` column in Part 3.3;
redesigned here as a proper join between User and the new Badge catalog
table, which is the correct normalized shape once a real Badge catalog
exists (avoids duplicating/misspelling badge names as free text across
every earned row). No route logic in Part 3.3 depended on the old
`title` field beyond the ORM relationship, so this change is safe.
"""

from datetime import datetime, timezone

from app.extensions import db
from app.models.mixins import TimestampMixin


class Achievement(TimestampMixin, db.Model):
    __tablename__ = "achievements"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    badge_id = db.Column(db.Integer, db.ForeignKey("badges.id", ondelete="CASCADE"), nullable=False, index=True)
    earned_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint("user_id", "badge_id", name="uq_achievements_user_badge"),
    )

    user = db.relationship("User", back_populates="achievements")
    badge = db.relationship("Badge", back_populates="achievements")

    def __repr__(self) -> str:
        return f"<Achievement user_id={self.user_id} badge_id={self.badge_id}>"
