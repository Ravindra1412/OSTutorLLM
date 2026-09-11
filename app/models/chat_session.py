"""
app/models/chat_session.py

`chat_sessions` table (Part 3.1, Section 8.5). Holds Tutor session
metadata. Message-by-message content lives in ChatMessage (Part 3.4).

Part 3.6 addition: `state_json` — a single TEXT column storing the
Memory Manager's structured session state (teaching_mode,
understanding_estimate, completed_steps, current_lesson, difficulty
adjustments) as JSON. A dedicated multi-table schema for this was
considered and rejected: this state is read/written as one atomic unit
every single turn (never queried by individual field), so a JSON blob
is both simpler and avoids a join on the hottest code path in the
whole AI Tutor Engine. See app/ai/memory/manager.py for the read/write
logic and the exact JSON shape.
"""

from datetime import datetime, timezone

from app.extensions import db


class ChatSession(db.Model):
    __tablename__ = "chat_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_name = db.Column(db.String(150), nullable=False)
    started_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    ended_at = db.Column(db.DateTime, nullable=True)
    state_json = db.Column(db.Text, nullable=True)

    user = db.relationship("User", back_populates="chat_sessions")
    bookmarks = db.relationship("Bookmark", back_populates="session", cascade="all, delete-orphan")
    messages = db.relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.id"
    )

    def __repr__(self) -> str:
        return f"<ChatSession id={self.id} user_id={self.user_id} topic={self.topic_name}>"
