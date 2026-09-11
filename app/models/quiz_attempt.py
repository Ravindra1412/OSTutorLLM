"""
app/models/quiz_attempt.py

`quiz_attempts` table (Part 3.4, Section 8; extended Part 3.7 Sections
8/19). One row per time a student takes a specific Quiz. Extended this
phase with timer fields (Section 8) and submission-integrity fields
(Section 19 — prevents multiple submissions and supports auto-submit
on time expiry) — question-by-question detail lives in QuizResult
(1 attempt : many results).
"""

from app.extensions import db
from app.models.mixins import TimestampMixin


class QuizAttempt(TimestampMixin, db.Model):
    __tablename__ = "quiz_attempts"

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    score = db.Column(db.Float, nullable=True)  # 0-100, null until graded

    # --- Timer (Section 8) ---
    time_limit_seconds = db.Column(db.Integer, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    paused_at = db.Column(db.DateTime, nullable=True)
    total_paused_seconds = db.Column(db.Integer, nullable=False, default=0)

    # --- Submission integrity (Section 19) ---
    is_submitted = db.Column(db.Boolean, nullable=False, default=False)
    auto_submitted = db.Column(db.Boolean, nullable=False, default=False)

    __table_args__ = (
        db.CheckConstraint("score IS NULL OR (score >= 0 AND score <= 100)", name="ck_quiz_attempts_score_range"),
    )

    quiz = db.relationship("Quiz", back_populates="attempts")
    user = db.relationship("User", back_populates="quiz_attempts")
    results = db.relationship("QuizResult", back_populates="attempt", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<QuizAttempt id={self.id} quiz_id={self.quiz_id} user_id={self.user_id} score={self.score}>"
