"""
app/models/content_revision.py

`content_revisions` table (Part 3.10, Section 7 — "Version Control for
Content"). Before every Topic/Lesson edit, content_management.py
snapshots the row's current field values as JSON here; `restore()`
writes that snapshot back, giving faculty a real undo path rather than
a read-only audit trail. Deliberately per-row snapshots (not a diff/
patch system) — simple, fully restorable, and easy to reason about for
a small curriculum-sized dataset (a handful of topics/lessons, not a
high-churn wiki that would need diffing for storage efficiency).
"""

from app.extensions import db
from app.models.mixins import TimestampMixin

CONTENT_TYPE_TOPIC = "topic"
CONTENT_TYPE_LESSON = "lesson"
VALID_CONTENT_TYPES = (CONTENT_TYPE_TOPIC, CONTENT_TYPE_LESSON)


class ContentRevision(TimestampMixin, db.Model):
    __tablename__ = "content_revisions"

    id = db.Column(db.Integer, primary_key=True)
    content_type = db.Column(db.String(10), nullable=False, index=True)
    content_id = db.Column(db.Integer, nullable=False, index=True)
    snapshot_json = db.Column(db.Text, nullable=False)  # full field snapshot BEFORE the edit that created this row
    edited_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        db.CheckConstraint("content_type IN ('topic','lesson')", name="ck_content_revisions_type"),
    )

    edited_by = db.relationship("User")

    def __repr__(self) -> str:
        return f"<ContentRevision {self.content_type}:{self.content_id} at {self.created_at}>"
