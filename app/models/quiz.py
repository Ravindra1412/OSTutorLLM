"""
app/models/quiz.py

`quizzes` table (Part 3.4, Section 5/8; extended Part 3.7 Section
1/4/8/9) — the normalized quiz schema.

Relationship to Part 3.3's `QuizHistory` table: QuizHistory remains in
the schema unchanged as a lightweight per-attempt summary row (score +
topic + timestamp) that the existing Part 3.3 `/api/progress` and
future dashboard summaries read from cheaply. Quiz/QuizQuestion/
QuizAttempt/QuizResult introduced here are the full normalized model
the Quiz Engine reads/writes question-by-question detail into.

Part 3.7 additions: `time_limit_seconds` (Section 8 — Timer),
`negative_marking_enabled` (Section 9 — optional negative marking),
`adaptive` (Section 4 — flags whether this quiz's difficulty was
chosen by the Difficulty Manager rather than requested explicitly).
"""

from app.extensions import db
from app.models.mixins import TimestampMixin


class Quiz(TimestampMixin, db.Model):
    __tablename__ = "quizzes"

    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    difficulty_level = db.Column(db.Integer, nullable=False, default=1)
    # Nullable: a system/AI-generated quiz has no human author.
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    time_limit_seconds = db.Column(db.Integer, nullable=True)  # null = untimed
    negative_marking_enabled = db.Column(db.Boolean, nullable=False, default=False)
    adaptive = db.Column(db.Boolean, nullable=False, default=False)
    # Part 3.10, Section 8: only meaningful for faculty-authored quizzes
    # (created_by_user_id set). Dynamically-generated per-attempt quizzes
    # from the Quiz Engine (Part 3.7) default True/None so their existing
    # behavior is completely unaffected by this addition.
    is_published = db.Column(db.Boolean, nullable=False, default=True)
    scheduled_at = db.Column(db.DateTime, nullable=True)  # null = available immediately once published

    __table_args__ = (
        db.CheckConstraint("difficulty_level BETWEEN 1 AND 5", name="ck_quizzes_difficulty_range"),
    )

    topic = db.relationship("Topic", back_populates="quizzes")
    created_by = db.relationship("User", foreign_keys=[created_by_user_id])
    questions = db.relationship(
        "QuizQuestion", back_populates="quiz", cascade="all, delete-orphan",
        order_by="QuizQuestion.sequence_order",
    )
    attempts = db.relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Quiz id={self.id} title={self.title}>"
