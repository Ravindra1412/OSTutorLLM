"""
app/models/topic.py

`topics` table (Part 3.4, Section 5/7). The formal curriculum taxonomy
deferred from Part 3.1 (Section 8.10) is implemented here. Every other
table that previously stored a free-text `topic_name` string
(Progress, ChatSession, QuizHistory — all from Part 3.3) is LEFT AS-IS
in this phase to avoid a breaking data-migration of existing rows;
new Part 3.4 tables (Quiz, Lesson, Command, ShellProgram) reference
`topics.id` properly via foreign key. Backfilling the older string
columns to real foreign keys is noted as a follow-up in Section 21.
"""

from app.extensions import db
from app.models.mixins import TimestampMixin


class Topic(TimestampMixin, db.Model):
    __tablename__ = "topics"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False, index=True)
    category = db.Column(db.String(100), nullable=False)  # e.g. "Linux Commands" | "Shell Scripting"
    description = db.Column(db.Text, nullable=True)
    difficulty_level = db.Column(db.Integer, nullable=False, default=1)  # 1 (beginner) .. 5 (advanced)

    __table_args__ = (
        db.CheckConstraint("difficulty_level BETWEEN 1 AND 5", name="ck_topics_difficulty_range"),
    )

    lessons = db.relationship(
        "Lesson", back_populates="topic", cascade="all, delete-orphan", order_by="Lesson.sequence_order"
    )
    commands = db.relationship("Command", back_populates="topic")
    shell_programs = db.relationship("ShellProgram", back_populates="topic")
    quizzes = db.relationship("Quiz", back_populates="topic")

    def __repr__(self) -> str:
        return f"<Topic id={self.id} name={self.name}>"
