"""
app/models/shell_program.py

`shell_programs` table (Part 3.4, Section 5). Reference/example shell
scripts (as opposed to a student's own submitted script, which will be
handled by the future `code_reviews` table per Part 1 Section 23.10 —
not created in this phase). Used to seed example content and, later,
as grounding material for the Code Review Engine.
"""

from app.extensions import db
from app.models.mixins import TimestampMixin


class ShellProgram(TimestampMixin, db.Model):
    __tablename__ = "shell_programs"

    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id", ondelete="SET NULL"), nullable=True, index=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    sample_code = db.Column(db.Text, nullable=False)
    difficulty_level = db.Column(db.Integer, nullable=False, default=1)

    __table_args__ = (
        db.CheckConstraint("difficulty_level BETWEEN 1 AND 5", name="ck_shell_programs_difficulty_range"),
    )

    topic = db.relationship("Topic", back_populates="shell_programs")

    def __repr__(self) -> str:
        return f"<ShellProgram id={self.id} title={self.title}>"
