"""
app/models/bookmark.py

`bookmarks` table (Part 3.1, Section 8.8) — lets a student flag a
tutor session for later revision, with an optional note.
"""

from app.extensions import db


class Bookmark(db.Model):
    __tablename__ = "bookmarks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = db.Column(db.Integer, db.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    note = db.Column(db.Text, nullable=True)

    user = db.relationship("User", back_populates="bookmarks")
    session = db.relationship("ChatSession", back_populates="bookmarks")

    def __repr__(self) -> str:
        return f"<Bookmark id={self.id} user_id={self.user_id} session_id={self.session_id}>"
