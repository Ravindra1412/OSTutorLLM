"""
app/models/study_plan.py

`study_plans` table (Part 3.13, Section 9 — AI Study Planner). One row per
(user, period_type) — regenerating overwrites in place rather than
accumulating history, since a study plan is meant to reflect the student's
CURRENT weak/strong topics, not a historical record (the Learning Timeline,
Part 3.9, already owns historical record-keeping).

`plan_json` stores a structured schedule (see study_planner.py for the
exact shape) rather than a fixed set of columns — the schedule's shape
differs meaningfully between daily/weekly/monthly, and a JSON blob avoids
three near-duplicate table schemas for what is fundamentally the same
concept at different granularities.
"""

from app.extensions import db
from app.models.mixins import TimestampMixin

PERIOD_DAILY = "daily"
PERIOD_WEEKLY = "weekly"
PERIOD_MONTHLY = "monthly"
VALID_PERIODS = (PERIOD_DAILY, PERIOD_WEEKLY, PERIOD_MONTHLY)


class StudyPlan(TimestampMixin, db.Model):
    __tablename__ = "study_plans"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    period_type = db.Column(db.String(10), nullable=False)
    plan_json = db.Column(db.Text, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "period_type", name="uq_study_plan_per_user_period"),
        db.CheckConstraint("period_type IN ('daily','weekly','monthly')", name="ck_study_plan_period_type"),
    )

    user = db.relationship("User")

    def __repr__(self) -> str:
        return f"<StudyPlan user_id={self.user_id} period={self.period_type}>"
