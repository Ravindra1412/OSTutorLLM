"""
app/models/login_history.py

Authentication audit trail (Part 3.4, Section 6). Records every login
attempt — successful or failed — separately from `User.last_login_at`
(which only ever holds the single most recent successful login for
fast dashboard access). This table is what a security review or a
"new device" alert feature would query.

Part 3.5 fix: user_id is nullable with ondelete="SET NULL", not the
original NOT NULL. A failed login attempt against an email that does
not correspond to any account (e.g. a credential-stuffing attempt, or
simply a typo) is exactly the kind of event this audit table exists to
capture — it must be representable with no user to attribute it to.
This mirrors the same nullable-FK pattern already used by
ActivityLog.user_id for the same reason.
"""

from app.extensions import db
from app.models.mixins import TimestampMixin


class LoginHistory(TimestampMixin, db.Model):
    __tablename__ = "login_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    ip_address = db.Column(db.String(45), nullable=True)  # 45 chars fits IPv6
    user_agent = db.Column(db.String(255), nullable=True)
    success = db.Column(db.Boolean, nullable=False, default=True)

    user = db.relationship("User", back_populates="login_history")

    def __repr__(self) -> str:
        return f"<LoginHistory user_id={self.user_id} success={self.success} at={self.created_at}>"
