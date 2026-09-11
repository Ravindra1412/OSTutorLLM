"""
app/quiz/question_types.py

Section 3 — Quiz Types. The authoritative registry of all 13 required
question types, re-exported from app.models.quiz_question (the single
source of truth for the valid-values list, so the database CHECK
constraint and this application-level registry can never drift out of
sync — both read from the same tuple).

Each type is tagged with an `evaluation_mode`:
  - "auto"    : exact/structured comparison, gradable instantly (Section 9)
  - "llm"     : LLM-assisted comparison against a rubric (Section 9's
                "Manual Evaluation Placeholder" / "Code Evaluation
                Placeholder" — implemented here via the LLM Service
                from Part 3.6 rather than left fully unimplemented,
                since that infrastructure already exists and reusing
                it is more valuable than a bare TODO)
  - "manual"  : reserved for a real human-grading placeholder (viva),
                auto-scored 0 for now with an explicit "pending_review"
                flag rather than silently guessing a score
"""

from app.models.quiz_question import (
    QUESTION_TYPE_MCQ, QUESTION_TYPE_MULTI_SELECT, QUESTION_TYPE_TRUE_FALSE,
    QUESTION_TYPE_FILL_BLANK, QUESTION_TYPE_COMMAND_PREDICTION, QUESTION_TYPE_SHELL_PROGRAMMING,
    QUESTION_TYPE_OUTPUT_PREDICTION, QUESTION_TYPE_ERROR_IDENTIFICATION,
    QUESTION_TYPE_MATCH_THE_FOLLOWING, QUESTION_TYPE_DRAG_AND_DROP,
    QUESTION_TYPE_SCENARIO, QUESTION_TYPE_CASE_STUDY, QUESTION_TYPE_VIVA,
    VALID_QUESTION_TYPES,
)

EVALUATION_MODE = {
    QUESTION_TYPE_MCQ: "auto",
    QUESTION_TYPE_MULTI_SELECT: "auto",
    QUESTION_TYPE_TRUE_FALSE: "auto",
    QUESTION_TYPE_FILL_BLANK: "auto",
    QUESTION_TYPE_COMMAND_PREDICTION: "auto",
    QUESTION_TYPE_OUTPUT_PREDICTION: "auto",
    QUESTION_TYPE_MATCH_THE_FOLLOWING: "auto",
    QUESTION_TYPE_DRAG_AND_DROP: "auto",
    QUESTION_TYPE_ERROR_IDENTIFICATION: "llm",
    QUESTION_TYPE_SHELL_PROGRAMMING: "llm",
    QUESTION_TYPE_SCENARIO: "llm",
    QUESTION_TYPE_CASE_STUDY: "llm",
    QUESTION_TYPE_VIVA: "manual",
}

DISPLAY_LABEL = {
    QUESTION_TYPE_MCQ: "Multiple Choice",
    QUESTION_TYPE_MULTI_SELECT: "Multiple Select",
    QUESTION_TYPE_TRUE_FALSE: "True / False",
    QUESTION_TYPE_FILL_BLANK: "Fill in the Blank",
    QUESTION_TYPE_COMMAND_PREDICTION: "Linux Command Prediction",
    QUESTION_TYPE_SHELL_PROGRAMMING: "Shell Programming",
    QUESTION_TYPE_OUTPUT_PREDICTION: "Code Output Prediction",
    QUESTION_TYPE_ERROR_IDENTIFICATION: "Error Identification",
    QUESTION_TYPE_MATCH_THE_FOLLOWING: "Match the Following",
    QUESTION_TYPE_DRAG_AND_DROP: "Drag and Drop (ordering)",
    QUESTION_TYPE_SCENARIO: "Scenario-Based",
    QUESTION_TYPE_CASE_STUDY: "Case Study",
    QUESTION_TYPE_VIVA: "Viva",
}


def is_valid_type(question_type: str) -> bool:
    return question_type in VALID_QUESTION_TYPES


def evaluation_mode_for(question_type: str) -> str:
    return EVALUATION_MODE.get(question_type, "manual")


def display_label_for(question_type: str) -> str:
    return DISPLAY_LABEL.get(question_type, question_type)
