"""
app/models/mixins.py

Shared mixins for SQLAlchemy models. Every model introduced in this
phase (Part 3.4) includes `created_at`/`updated_at` per the phase
requirements by inheriting TimestampMixin instead of redeclaring the
same two columns in twenty different files.

Note on Part 3.3 models: a few (e.g. Progress.last_updated,
QuizHistory.taken_at, Achievement.earned_at) use a single,
domain-meaningful timestamp name instead of generic created_at/updated_at.
This is a deliberate, documented exception (see docs/project-report-part3.4.md,
Section 5) rather than an oversight — "taken_at" is clearer at the call
site than a generic "created_at" for a quiz attempt record, for example.
"""

from datetime import datetime, timezone

from app.extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Adds created_at / updated_at columns to any model that inherits it."""

    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)
