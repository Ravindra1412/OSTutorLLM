"""
app/models/mentor_interaction.py

`mentor_interactions` table (Part 3.13, `mentor_memory` — Sections 13-14).
Every question asked to the Student or Faculty AI Assistant, and the
answer actually given, is logged here — this is what "mentor memory" means
concretely: a real, queryable record of past Q&A, not a conversational
LLM context window (the Tutor Engine's `ChatSession.state_json`, Part 3.6,
already owns that concept for tutoring conversations specifically; this
table is for the Mentor Assistant's distinct, stateless-per-question Q&A
pattern — see `mentor_assistant.py`'s own docstring for why these are kept
separate rather than merged).
"""

from app.extensions import db
from app.models.mixins import TimestampMixin

ROLE_STUDENT = "student"
ROLE_FACULTY = "faculty"
VALID_ROLES = (ROLE_STUDENT, ROLE_FACULTY)


class MentorInteraction(TimestampMixin, db.Model):
    __tablename__ = "mentor_interactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = db.Column(db.String(10), nullable=False)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    intent = db.Column(db.String(50), nullable=True)  # which rule/handler answered this, for explainability

    __table_args__ = (
        db.CheckConstraint("role IN ('student','faculty')", name="ck_mentor_interaction_role"),
    )

    user = db.relationship("User")

    def to_dict(self) -> dict:
        return {
            "id": self.id, "question": self.question, "answer": self.answer,
            "intent": self.intent, "asked_at": self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<MentorInteraction user_id={self.user_id} intent={self.intent}>"
