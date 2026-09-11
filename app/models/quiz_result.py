"""
app/models/quiz_result.py

`quiz_results` table (Part 3.4, Section 8; extended Part 3.7 Section
9). Per-question outcome within a single QuizAttempt — the
finest-grained record in the quiz schema. Extended this phase with
`points_earned` (supports partial credit, e.g. a multi-select question
where the student got 2 of 3 correct options) and `student_answer_raw`
kept as `student_answer` (Text, JSON-encoded for multi-select/matching/
drag-and-drop answers) so this one column works across every question
type without a schema branch per type.
"""

from app.extensions import db
from app.models.mixins import TimestampMixin


class QuizResult(TimestampMixin, db.Model):
    __tablename__ = "quiz_results"

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(
        db.Integer, db.ForeignKey("quiz_attempts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id = db.Column(
        db.Integer, db.ForeignKey("quiz_questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_answer = db.Column(db.Text, nullable=True)
    is_correct = db.Column(db.Boolean, nullable=True)  # null until graded
    points_earned = db.Column(db.Float, nullable=False, default=0.0)  # Section 9 — partial credit support

    __table_args__ = (
        db.UniqueConstraint("attempt_id", "question_id", name="uq_quiz_results_attempt_question"),
        db.CheckConstraint("points_earned >= 0", name="ck_quiz_results_points_nonnegative"),
    )

    attempt = db.relationship("QuizAttempt", back_populates="results")
    question = db.relationship("QuizQuestion", back_populates="results")

    def __repr__(self) -> str:
        return f"<QuizResult attempt_id={self.attempt_id} question_id={self.question_id} correct={self.is_correct}>"
