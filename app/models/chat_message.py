"""
app/models/chat_message.py

`chat_messages` table (Part 3.4, Section 5/9 — Tutor Session Models).
Individual conversation turns within a ChatSession (Part 3.3). This is
purely a data-storage model in this phase — NO hint-ladder logic, no
LLM calls, no Prompt Engine wiring (explicitly out of scope per this
phase's instructions). `hint_stage` is stored per message so that once
the Tutor Engine phase exists, the exact same table already supports
its policy-compliance auditing needs (Part 2, Section 27 acceptance
criteria) without a schema change.
"""

from app.extensions import db
from app.models.mixins import TimestampMixin

ROLE_STUDENT = "student"
ROLE_TUTOR = "tutor"


class ChatMessage(TimestampMixin, db.Model):
    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer, db.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role = db.Column(db.String(10), nullable=False)  # 'student' | 'tutor'
    message_text = db.Column(db.Text, nullable=False)
    hint_stage = db.Column(db.Integer, nullable=True)  # 0=diagnostic, 1-3=hint level, null=n/a (student turn)

    __table_args__ = (
        db.CheckConstraint("role IN ('student','tutor')", name="ck_chat_messages_role"),
        db.CheckConstraint(
            "hint_stage IS NULL OR hint_stage BETWEEN 0 AND 4", name="ck_chat_messages_hint_stage_range"
        ),
    )

    session = db.relationship("ChatSession", back_populates="messages")

    def __repr__(self) -> str:
        return f"<ChatMessage id={self.id} session_id={self.session_id} role={self.role}>"
