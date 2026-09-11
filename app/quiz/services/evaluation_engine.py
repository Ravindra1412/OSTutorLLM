"""
app/quiz/services/evaluation_engine.py

The Evaluation Engine (Section 1/9). Grades one student answer against
one QuizQuestion, dispatching by question_type's evaluation_mode
(app/quiz/question_types.py):
  - "auto"   -> exact/structured comparison here, no LLM call, instant
  - "llm"    -> LLM-assisted comparison against the stored rubric
                (Section 9's "Code Evaluation Placeholder" — implemented
                by reusing Part 3.6's LLM Service rather than left bare)
  - "manual" -> viva only; scored 0 with pending_review=True, a real
                placeholder per Section 9's explicit instruction, since
                genuine human/oral grading is out of scope for this
                phase's automated pipeline

Returns a structured EvaluationResult so the caller (Scoring Engine)
never has to know which path was taken.
"""

import json
from dataclasses import dataclass

from app.models.quiz_question import QuizQuestion
from app.quiz import question_types
from app.ai.prompts import manager as prompt_manager
from app.ai.services.llm_service import generate_reply
from app.utils.logger import get_ai_logger


@dataclass
class EvaluationResult:
    is_correct: bool
    score_fraction: float  # 0.0-1.0, supports partial credit (Section 9)
    feedback: str = ""
    pending_review: bool = False


def evaluate_answer(question: QuizQuestion, student_answer_raw: str, topic_name: str) -> EvaluationResult:
    mode = question_types.evaluation_mode_for(question.question_type)
    if mode == "auto":
        return _evaluate_auto(question, student_answer_raw)
    if mode == "llm":
        return _evaluate_llm(question, student_answer_raw, topic_name)
    return EvaluationResult(is_correct=False, score_fraction=0.0, feedback="Pending manual review.", pending_review=True)


# --------------------------------------------------------------------
# Auto-gradable types
# --------------------------------------------------------------------

def _evaluate_auto(question: QuizQuestion, student_answer_raw: str) -> EvaluationResult:
    qtype = question.question_type
    correct = json.loads(question.correct_answer)

    if qtype in ("mcq", "true_false", "command_prediction", "output_prediction"):
        return _evaluate_single_value(student_answer_raw, correct)
    if qtype == "fill_blank":
        return _evaluate_fill_blank(student_answer_raw, correct)
    if qtype == "multi_select":
        return _evaluate_multi_select(student_answer_raw, correct)
    if qtype == "match_the_following":
        return _evaluate_matching(student_answer_raw, correct)
    if qtype == "drag_and_drop":
        return _evaluate_ordering(student_answer_raw, correct)

    return EvaluationResult(is_correct=False, score_fraction=0.0, feedback="Unsupported auto-grading type.")


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _evaluate_single_value(student_answer_raw: str, correct) -> EvaluationResult:
    is_correct = _normalize(student_answer_raw) == _normalize(str(correct))
    return EvaluationResult(is_correct=is_correct, score_fraction=1.0 if is_correct else 0.0)


def _evaluate_fill_blank(student_answer_raw: str, correct) -> EvaluationResult:
    """`correct` may be a single accepted string OR a list of accepted
    variants (e.g. `["+x", "u+x", "755", "775"]`, per seed_bank.py) —
    matching ANY accepted variant counts as correct."""
    accepted = correct if isinstance(correct, list) else [correct]
    is_correct = any(_normalize(student_answer_raw) == _normalize(str(v)) for v in accepted)
    return EvaluationResult(is_correct=is_correct, score_fraction=1.0 if is_correct else 0.0)


def _evaluate_multi_select(student_answer_raw: str, correct: list) -> EvaluationResult:
    """Partial credit (Section 9): score_fraction = correctly-selected
    minus incorrectly-selected, floored at 0, over the total number of
    correct options — a standard, explainable multi-select scoring
    rule that discourages "select everything" gaming."""
    try:
        selected = json.loads(student_answer_raw) if student_answer_raw else []
    except (ValueError, TypeError):
        selected = []
    selected_set, correct_set = set(selected), set(correct)

    true_positives = len(selected_set & correct_set)
    false_positives = len(selected_set - correct_set)
    fraction = max(0.0, (true_positives - false_positives) / len(correct_set)) if correct_set else 0.0
    is_correct = selected_set == correct_set

    return EvaluationResult(is_correct=is_correct, score_fraction=round(fraction, 2))


def _evaluate_matching(student_answer_raw: str, correct: dict) -> EvaluationResult:
    """Partial credit: fraction of pairs matched correctly."""
    try:
        submitted = json.loads(student_answer_raw) if student_answer_raw else {}
    except (ValueError, TypeError):
        submitted = {}

    total = len(correct)
    if total == 0:
        return EvaluationResult(is_correct=False, score_fraction=0.0)

    matched = sum(1 for k, v in correct.items() if str(submitted.get(k)) == str(v))
    fraction = matched / total
    return EvaluationResult(is_correct=(matched == total), score_fraction=round(fraction, 2))


def _evaluate_ordering(student_answer_raw: str, correct: list) -> EvaluationResult:
    """Drag and Drop Placeholder (Section 3): evaluated as an ordering
    problem — partial credit for each position matching the correct
    order, since a fully-binary right/wrong is harsh for a mostly-
    correct sequence."""
    try:
        submitted = json.loads(student_answer_raw) if student_answer_raw else []
    except (ValueError, TypeError):
        submitted = []

    if not correct or len(submitted) != len(correct):
        return EvaluationResult(is_correct=False, score_fraction=0.0)

    matches = sum(1 for a, b in zip(submitted, correct) if a == b)
    fraction = matches / len(correct)
    return EvaluationResult(is_correct=(fraction == 1.0), score_fraction=round(fraction, 2))


# --------------------------------------------------------------------
# LLM-assisted types (Section 9's "Code Evaluation Placeholder", implemented)
# --------------------------------------------------------------------

def _evaluate_llm(question: QuizQuestion, student_answer_raw: str, topic_name: str) -> EvaluationResult:
    correct = json.loads(question.correct_answer)
    messages = prompt_manager.build_evaluation_messages(
        question_type=question.question_type, topic=topic_name, difficulty_level=question.difficulty_level,
        question_text=question.question_text, correct_answer=str(correct), student_answer=student_answer_raw,
    )
    result = generate_reply(messages)
    if not result.success:
        get_ai_logger().warning("LLM evaluation failed for question_id=%s, marking pending review: %s", question.id, result.text)
        return EvaluationResult(is_correct=False, score_fraction=0.0, feedback=result.text, pending_review=True)

    try:
        raw = result.text.strip()
        if raw.startswith("```"):
            raw = raw.strip("`").lstrip("json").strip()
        parsed = json.loads(raw)
        fraction = max(0.0, min(1.0, float(parsed.get("score_fraction", 0.0))))
        return EvaluationResult(
            is_correct=bool(parsed.get("is_correct", fraction >= 0.6)),
            score_fraction=fraction,
            feedback=parsed.get("feedback", ""),
        )
    except (ValueError, TypeError, KeyError) as exc:
        get_ai_logger().warning("LLM evaluation response unparsable for question_id=%s: %s", question.id, exc)
        return EvaluationResult(is_correct=False, score_fraction=0.0, feedback="Could not auto-grade this response.", pending_review=True)
