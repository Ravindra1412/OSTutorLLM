"""
app/models/badge.py

`badges` table (Part 3.4, Section 10) — the catalog of unlockable
badges (name, description, tier, XP reward), matching Part 2 Section 14
(Gamification Design). A specific student's *earned* badges are
recorded in the (redesigned) Achievement table — Badge is the catalog,
Achievement is the join of "this student earned this badge, at this time."
"""

from app.extensions import db
from app.models.mixins import TimestampMixin

TIER_BRONZE = "bronze"
TIER_SILVER = "silver"
TIER_GOLD = "gold"


class Badge(TimestampMixin, db.Model):
    __tablename__ = "badges"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=False)
    icon = db.Column(db.String(50), nullable=True)  # icon identifier, e.g. a Bootstrap Icons class
    tier = db.Column(db.String(10), nullable=False, default=TIER_BRONZE)
    xp_reward = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        db.CheckConstraint("tier IN ('bronze','silver','gold')", name="ck_badges_tier"),
        db.CheckConstraint("xp_reward >= 0", name="ck_badges_xp_nonnegative"),
    )

    achievements = db.relationship("Achievement", back_populates="badge", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Badge id={self.id} name={self.name} tier={self.tier}>"
