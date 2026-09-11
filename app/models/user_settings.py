"""
app/models/user_settings.py

`user_settings` table (Part 3.4, Section 5 — "Settings"). Generic,
role-agnostic application preferences (theme, language, notification
toggles) as seen on the Settings page in Part 3.2. Deliberately kept
separate from `student_profiles.hint_verbosity_pref`, which is a
learning-specific preference only students have — Settings applies to
both students and faculty.
"""

from app.extensions import db
from app.models.mixins import TimestampMixin

THEME_LIGHT = "light"
THEME_DARK = "dark"


class UserSettings(TimestampMixin, db.Model):
    __tablename__ = "user_settings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    theme = db.Column(db.String(10), nullable=False, default=THEME_DARK)
    language = db.Column(db.String(10), nullable=False, default="en")
    email_notifications_enabled = db.Column(db.Boolean, nullable=False, default=True)
    achievement_notifications_enabled = db.Column(db.Boolean, nullable=False, default=True)
    streak_reminders_enabled = db.Column(db.Boolean, nullable=False, default=False)
    high_contrast_enabled = db.Column(db.Boolean, nullable=False, default=False)
    reduce_motion_enabled = db.Column(db.Boolean, nullable=False, default=False)

    __table_args__ = (
        db.CheckConstraint("theme IN ('light','dark')", name="ck_user_settings_theme"),
    )

    user = db.relationship("User", back_populates="settings")

    def __repr__(self) -> str:
        return f"<UserSettings user_id={self.user_id} theme={self.theme}>"
