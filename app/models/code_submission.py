"""
app/models/code_submission.py

`code_submissions` table (Part 3.8, Section 13). One row per submitted
revision within a CodeReviewSession — `submission_number` (1, 2, 3...)
is what makes Section 10's "Code Comparison" possible: comparing
submission N to submission N-1 within the same session shows the
student's actual improvement over time, not just a single grade.

JSON-encoded Text columns (`static_analysis_json`, `llm_feedback_json`,
`scores_json`) follow the exact same pattern established in Part 3.4's
QuizQuestion.options_json — a single flexible column beats a dozen
narrow nullable columns for structured-but-variable-shape data that is
always read/written as one atomic unit, never queried by individual
sub-field in SQL.
"""

from app.extensions import db
from app.models.mixins import TimestampMixin


class CodeSubmission(TimestampMixin, db.Model):
    __tablename__ = "code_submissions"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer, db.ForeignKey("code_review_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    submission_number = db.Column(db.Integer, nullable=False, default=1)
    code_text = db.Column(db.Text, nullable=False)

    static_analysis_json = db.Column(db.Text, nullable=True)   # Section 5 findings
    llm_feedback_json = db.Column(db.Text, nullable=True)       # Section 6/8 structured feedback
    scores_json = db.Column(db.Text, nullable=True)              # Section 9 per-dimension + overall score

    hint_stage = db.Column(db.Integer, nullable=False, default=0)  # Section 7 — 0=none,1-3=hints,4=full guidance
    hints_used_count = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint("session_id", "submission_number", name="uq_code_submissions_session_number"),
        db.CheckConstraint("hint_stage BETWEEN 0 AND 4", name="ck_code_submissions_hint_stage_range"),
    )

    session = db.relationship("CodeReviewSession", back_populates="submissions")

    def __repr__(self) -> str:
        return f"<CodeSubmission id={self.id} session_id={self.session_id} #={self.submission_number}>"
