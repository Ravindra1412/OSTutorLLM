"""
app/models/student_profile.py

`student_profiles` table (Part 3.1, Section 8.3) — extends `users`
1:1 with gamification/preference fields, kept separate to keep the
core auth table lean (Part 2, Section 8.9 rationale).

Part 3.4: added created_at/updated_at via TimestampMixin per this
phase's requirement that every model track record mutation time.
"""

from app.extensions import db
from app.models.mixins import TimestampMixin


class StudentProfile(TimestampMixin, db.Model):
    __tablename__ = "student_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    xp_total = db.Column(db.Integer, nullable=False, default=0)
    level = db.Column(db.Integer, nullable=False, default=1)
    streak_days = db.Column(db.Integer, nullable=False, default=0)
    hint_verbosity_pref = db.Column(db.Integer, nullable=False, default=2)  # 1=terse .. 3=detailed

    __table_args__ = (
        db.CheckConstraint("xp_total >= 0", name="ck_student_profiles_xp_nonnegative"),
        db.CheckConstraint("level >= 1", name="ck_student_profiles_level_min1"),
        db.CheckConstraint("streak_days >= 0", name="ck_student_profiles_streak_nonnegative"),
        db.CheckConstraint(
            "hint_verbosity_pref BETWEEN 1 AND 3", name="ck_student_profiles_hint_verbosity_range"
        ),
    )

    user = db.relationship("User", back_populates="student_profile")

    def __repr__(self) -> str:
        return f"<StudentProfile user_id={self.user_id} xp={self.xp_total} level={self.level}>"
