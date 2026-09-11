"""
app/models/command.py

`commands` table (Part 3.4, Section 5). A reference catalog of Linux
commands (e.g. `ls`, `chmod`, `grep`) that the Tutor/Quiz Engines will
draw on in later phases for generating questions and hints grounded in
real command syntax, rather than the LLM inventing syntax details from
memory (reduces hallucination risk — Part 2, Section 11).
"""

from app.extensions import db
from app.models.mixins import TimestampMixin


class Command(TimestampMixin, db.Model):
    __tablename__ = "commands"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, index=True)  # e.g. "chmod"
    syntax = db.Column(db.String(255), nullable=False)  # e.g. "chmod [OPTIONS] MODE FILE"
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=True)  # e.g. "File Permissions"
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id", ondelete="SET NULL"), nullable=True, index=True)

    __table_args__ = (
        db.UniqueConstraint("name", "syntax", name="uq_commands_name_syntax"),
    )

    topic = db.relationship("Topic", back_populates="commands")

    def __repr__(self) -> str:
        return f"<Command id={self.id} name={self.name}>"
