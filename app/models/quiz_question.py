"""
app/models/quiz_question.py

`quiz_questions` table (Part 3.4, Section 8; extended Part 3.7 Section
3/6). Supports all 13 question types required by Part 3.7's Quiz
Engine. `options_json` and `correct_answer` are JSON-encoded Text
columns (SQLite has no native array/JSON column type usable portably
with SQLAlchemy's core column types, so this is the standard,
ORM-best-practice approach — see docs/project-report-part3.4.md
Section 16) whose exact shape depends on question_type:

  - mcq:              options_json=["a","b","c","d"], correct_answer="b"
  - multi_select:     options_json=["a","b","c","d"], correct_answer=["a","c"] (JSON list)
  - true_false:        options_json=null,              correct_answer="true"|"false"
  - fill_blank:         options_json=null,              correct_answer="chmod" (or JSON list of accepted variants)
  - command_prediction:  options_json=null,              correct_answer="ls -la"
  - shell_programming:    options_json=null,              correct_answer=<expected script or key output>
  - output_prediction:     options_json=null,              correct_answer=<expected terminal output>
  - error_identification:   options_json=null,              correct_answer=<line/description of the bug>
  - match_the_following:     options_json={"left":[...],"right":[...]}, correct_answer={"0":"2","1":"0",...} (JSON dict, left-index -> right-index)
  - drag_and_drop:             options_json=["step a","step b",...], correct_answer=[1,0,2] (JSON list — correct order, placeholder per Section 3)
  - scenario:                    options_json=null,              correct_answer=<model rubric text> (LLM-assisted evaluation)
  - case_study:                    options_json=null,              correct_answer=<model rubric text> (LLM-assisted evaluation)
  - viva:                            options_json=null,              correct_answer=<model rubric text> (manual/LLM-assisted evaluation placeholder)

See app/quiz/question_types.py for the authoritative constant list and
app/quiz/services/evaluation_engine.py for the per-type grading logic.
"""

from app.extensions import db
from app.models.mixins import TimestampMixin

QUESTION_TYPE_MCQ = "mcq"
QUESTION_TYPE_MULTI_SELECT = "multi_select"
QUESTION_TYPE_TRUE_FALSE = "true_false"
QUESTION_TYPE_FILL_BLANK = "fill_blank"
QUESTION_TYPE_COMMAND_PREDICTION = "command_prediction"
QUESTION_TYPE_SHELL_PROGRAMMING = "shell_programming"
QUESTION_TYPE_OUTPUT_PREDICTION = "output_prediction"
QUESTION_TYPE_ERROR_IDENTIFICATION = "error_identification"
QUESTION_TYPE_MATCH_THE_FOLLOWING = "match_the_following"
QUESTION_TYPE_DRAG_AND_DROP = "drag_and_drop"
QUESTION_TYPE_SCENARIO = "scenario"
QUESTION_TYPE_CASE_STUDY = "case_study"
QUESTION_TYPE_VIVA = "viva"

VALID_QUESTION_TYPES = (
    QUESTION_TYPE_MCQ, QUESTION_TYPE_MULTI_SELECT, QUESTION_TYPE_TRUE_FALSE,
    QUESTION_TYPE_FILL_BLANK, QUESTION_TYPE_COMMAND_PREDICTION, QUESTION_TYPE_SHELL_PROGRAMMING,
    QUESTION_TYPE_OUTPUT_PREDICTION, QUESTION_TYPE_ERROR_IDENTIFICATION,
    QUESTION_TYPE_MATCH_THE_FOLLOWING, QUESTION_TYPE_DRAG_AND_DROP,
    QUESTION_TYPE_SCENARIO, QUESTION_TYPE_CASE_STUDY, QUESTION_TYPE_VIVA,
)

_TYPE_CHECK_SQL = "question_type IN (" + ",".join(f"'{t}'" for t in VALID_QUESTION_TYPES) + ")"


class QuizQuestion(TimestampMixin, db.Model):
    __tablename__ = "quiz_questions"

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(30), nullable=False, default=QUESTION_TYPE_MCQ)
    options_json = db.Column(db.Text, nullable=True)
    correct_answer = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text, nullable=True)  # Section 10 — shown in feedback after grading
    difficulty_level = db.Column(db.Integer, nullable=False, default=1)
    points = db.Column(db.Float, nullable=False, default=1.0)  # Section 9 — supports partial-credit weighting
    sequence_order = db.Column(db.Integer, nullable=False, default=0)  # Section 15 — stable presentation order per quiz

    __table_args__ = (
        db.CheckConstraint(_TYPE_CHECK_SQL, name="ck_quiz_questions_type"),
        db.CheckConstraint("difficulty_level BETWEEN 1 AND 5", name="ck_quiz_questions_difficulty_range"),
        db.CheckConstraint("points >= 0", name="ck_quiz_questions_points_nonnegative"),
    )

    quiz = db.relationship("Quiz", back_populates="questions")
    results = db.relationship("QuizResult", back_populates="question", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<QuizQuestion id={self.id} quiz_id={self.quiz_id} type={self.question_type}>"
