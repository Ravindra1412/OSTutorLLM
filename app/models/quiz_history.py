"""
app/models/quiz_history.py

`quiz_history` table (Part 3.1, Section 8.6). Per-attempt quiz record;
individual question-level detail (`quiz_questions`, Part 2 Section 8)
is introduced once the Quiz Engine is implemented.
"""

from datetime import datetime, timezone

from app.extensions import db


class QuizHistory(db.Model):
    __tablename__ = "quiz_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_name = db.Column(db.String(150), nullable=False)
    score = db.Column(db.Float, nullable=True)
    taken_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", back_populates="quiz_history")

    def __repr__(self) -> str:
        return f"<QuizHistory id={self.id} user_id={self.user_id} score={self.score}>"
