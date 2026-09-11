"""
app/models/system_configuration.py

`system_configuration` table (Part 3.4, Section 5). A global, admin-level
key-value store for platform-wide settings that are not tied to any
single user — e.g. maintenance-mode flags, default hint-stage count,
feature toggles for in-progress modules. Distinct from `user_settings`
(per-user) and `.env` (deployment-time secrets/config, Part 3.1 Section
7.4) — this table is for values an admin may want to change *at runtime*
without a redeploy.
"""

from app.extensions import db
from app.models.mixins import TimestampMixin


class SystemConfiguration(TimestampMixin, db.Model):
    __tablename__ = "system_configuration"

    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    config_value = db.Column(db.Text, nullable=True)
    description = db.Column(db.String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<SystemConfiguration {self.config_key}={self.config_value!r}>"
