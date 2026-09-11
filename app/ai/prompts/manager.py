"""
app/ai/prompts/manager.py

The Prompt Manager (Section 1/4). Loads the text templates from
app/ai/prompts/templates/ and assembles them into the layered
System -> Developer -> History -> Student message structure defined
in Part 2, Section 12.1 — this is the single place in the codebase
that constructs an LLM request, so the hint-ladder policy (Section 7)
is enforced structurally: the Tutor Service tells this module what
hint_stage to use, and this module is what actually tells the LLM
which stage's instructions to follow. A student's message is always
appended LAST, as plain user-role data — never concatenated into the
system/developer instruction layers — which is the core structural
defense against prompt injection (Section 13).
"""

import os

from app.ai.providers.base import LLMMessage
from app.ai import config

_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

_STAGE_HINT_DEPTH = {
    1: ("Conceptual nudge", "Point the student toward the general concept or command family involved, without naming the specific command or flag."),
    2: ("Structural hint", "Name the specific command or construct involved, and describe its general syntax shape, without giving the exact flags/arguments needed for this situation."),
    3: ("Near-complete scaffold", "Give the near-complete structure (e.g. the command with placeholder arguments), leaving only the final specific value(s) for the student to fill in."),
}

TEACHING_MODE_DESCRIPTIONS = {
    "beginner": "Use simple language, avoid jargon, define any term you use, and keep hints very gentle.",
    "intermediate": "Assume basic command-line familiarity; you can use standard terminology without defining it.",
    "advanced": "Be concise and assume strong familiarity; focus hints on edge cases and nuance rather than basics.",
    "exam_prep": "Frame hints and explanations the way they'd be tested in a written or lab exam — precise, definition-focused.",
    "lab_practice": "Focus on practical, hands-on phrasing the student would use while actually working in a terminal.",
}


def _load_template(filename: str) -> str:
    with open(os.path.join(_TEMPLATE_DIR, filename), "r", encoding="utf-8") as f:
        return f.read()


def _stage_instruction(hint_stage: int) -> str:
    if hint_stage == config.HINT_STAGE_DIAGNOSTIC:
        return _load_template("tutor_prompt.txt")
    if hint_stage in (1, 2, 3):
        label, description = _STAGE_HINT_DEPTH[hint_stage]
        return _load_template("hint_prompt.txt").format(
            hint_number=hint_stage, hint_depth_label=label, hint_depth_description=description
        )
    return _load_template("solution_prompt.txt")


def build_tutor_messages(
    topic: str,
    hint_stage: int,
    teaching_mode: str,
    competency_summary: str,
    history: list[LLMMessage],
    student_message: str,
) -> list[LLMMessage]:
    """Assembles the full message list for one Tutor Engine turn.

    Layer order (Part 2, Section 12.2):
      1. System prompt (immutable platform rules)
      2. Developer prompt (this turn's policy: topic, hint stage, mode)
      3. Trimmed conversation history (Section 5 — context window)
      4. The student's current message, appended last, as plain data
    """
    system_text = _load_template("system_prompt.txt")
    stage_instruction = _stage_instruction(hint_stage)
    mode_description = TEACHING_MODE_DESCRIPTIONS.get(teaching_mode, TEACHING_MODE_DESCRIPTIONS["intermediate"])

    developer_text = _load_template("developer_prompt.txt").format(
        topic=topic,
        hint_stage=hint_stage,
        teaching_mode=f"{teaching_mode} ({mode_description})",
        competency_summary=competency_summary or "No prior data for this student on this topic yet.",
        stage_instruction=stage_instruction,
    )

    messages = [
        LLMMessage(role="system", content=system_text),
        LLMMessage(role="system", content=developer_text),
    ]
    messages.extend(history)
    messages.append(LLMMessage(role="user", content=student_message))
    return messages


def build_code_review_messages(topic: str, student_script: str) -> list[LLMMessage]:
    system_text = _load_template("system_prompt.txt")
    review_text = _load_template("code_review_prompt.txt").format(topic=topic, student_script=student_script)
    return [
        LLMMessage(role="system", content=system_text),
        LLMMessage(role="user", content=review_text),
    ]


def build_quiz_messages(topic: str, difficulty_level: int, question_count: int, recent_topics_covered: str) -> list[LLMMessage]:
    system_text = _load_template("system_prompt.txt")
    quiz_text = _load_template("quiz_prompt.txt").format(
        topic=topic, difficulty_level=difficulty_level, question_count=question_count,
        recent_topics_covered=recent_topics_covered or "none",
    )
    return [
        LLMMessage(role="system", content=system_text),
        LLMMessage(role="user", content=quiz_text),
    ]


def build_viva_messages(topic: str, difficulty_level: int, viva_history: str) -> list[LLMMessage]:
    system_text = _load_template("system_prompt.txt")
    viva_text = _load_template("viva_prompt.txt").format(
        topic=topic, difficulty_level=difficulty_level, viva_history=viva_history or "(start of session)"
    )
    return [
        LLMMessage(role="system", content=system_text),
        LLMMessage(role="user", content=viva_text),
    ]


# --------------------------------------------------------------------
# Part 3.7 — Quiz Engine prompts (Section 16)
# --------------------------------------------------------------------

def build_evaluation_messages(
    question_type: str, topic: str, difficulty_level: int,
    question_text: str, correct_answer: str, student_answer: str,
) -> list[LLMMessage]:
    """LLM-assisted grading for open-ended question types (scenario,
    case_study, shell_programming, error_identification — see
    app/quiz/question_types.py's evaluation_mode registry)."""
    system_text = _load_template("system_prompt.txt")
    eval_text = _load_template("evaluation_prompt.txt").format(
        question_type=question_type, topic=topic, difficulty_level=difficulty_level,
        question_text=question_text, correct_answer=correct_answer, student_answer=student_answer,
    )
    return [
        LLMMessage(role="system", content=system_text),
        LLMMessage(role="user", content=eval_text),
    ]


def build_feedback_messages(
    topic: str, score_percent: float, correct_count: int, total_count: int, weak_question_summaries: str
) -> list[LLMMessage]:
    system_text = _load_template("system_prompt.txt")
    feedback_text = _load_template("feedback_prompt.txt").format(
        topic=topic, score_percent=round(score_percent, 1), correct_count=correct_count,
        total_count=total_count, weak_question_summaries=weak_question_summaries or "none in particular",
    )
    return [
        LLMMessage(role="system", content=system_text),
        LLMMessage(role="user", content=feedback_text),
    ]


def build_difficulty_selection_messages(topic: str, performance_history: str) -> list[LLMMessage]:
    system_text = _load_template("system_prompt.txt")
    difficulty_text = _load_template("difficulty_prompt.txt").format(
        topic=topic, performance_history=performance_history or "No prior history available."
    )
    return [
        LLMMessage(role="system", content=system_text),
        LLMMessage(role="user", content=difficulty_text),
    ]


def build_hint_recommendation_messages(question_type: str, topic: str, question_text: str) -> list[LLMMessage]:
    system_text = _load_template("system_prompt.txt")
    hint_text = _load_template("hint_recommendation_prompt.txt").format(
        question_type=question_type, topic=topic, question_text=question_text,
    )
    return [
        LLMMessage(role="system", content=system_text),
        LLMMessage(role="user", content=hint_text),
    ]


# --------------------------------------------------------------------
# Part 3.8 — Code Review Engine prompts (Section 12)
# --------------------------------------------------------------------

def build_code_review_full_messages(topic: str, student_script: str) -> list[LLMMessage]:
    """The main LLM Review Engine call (Section 6) — reuses Part 3.6's
    code_review_prompt.txt, which already implements the staged,
    one-issue-at-a-time, non-solving critique pattern."""
    return build_code_review_messages(topic, student_script)


def build_error_explanation_messages(
    topic: str, category: str, severity: str, line_number, static_message: str
) -> list[LLMMessage]:
    system_text = _load_template("system_prompt.txt")
    text = _load_template("error_explanation_prompt.txt").format(
        topic=topic, category=category, severity=severity,
        line_number=line_number if line_number is not None else "N/A", static_message=static_message,
    )
    return [LLMMessage(role="system", content=system_text), LLMMessage(role="user", content=text)]


def build_improvement_suggestions_messages(topic: str, student_script: str) -> list[LLMMessage]:
    system_text = _load_template("system_prompt.txt")
    text = _load_template("improvement_suggestions_prompt.txt").format(topic=topic, student_script=student_script)
    return [LLMMessage(role="system", content=system_text), LLMMessage(role="user", content=text)]


def build_security_review_messages(topic: str, student_script: str) -> list[LLMMessage]:
    system_text = _load_template("system_prompt.txt")
    text = _load_template("security_review_prompt.txt").format(topic=topic, student_script=student_script)
    return [LLMMessage(role="system", content=system_text), LLMMessage(role="user", content=text)]


def build_best_practices_messages(topic: str) -> list[LLMMessage]:
    system_text = _load_template("system_prompt.txt")
    text = _load_template("best_practices_prompt.txt").format(topic=topic)
    return [LLMMessage(role="system", content=system_text), LLMMessage(role="user", content=text)]


def build_final_guidance_messages(
    topic: str, category: str, line_number, static_message: str
) -> list[LLMMessage]:
    """Section 7 — Final Guidance. Distinct from build_error_explanation_messages:
    that one deliberately withholds the fix (used for hint stages 1-3);
    this one explicitly permits revealing it, used only once the hint
    ladder is exhausted — the same reveal-stage split established by
    the Tutor Engine (Part 3.6) and Quiz Engine (Part 3.7)."""
    system_text = _load_template("system_prompt.txt")
    text = _load_template("final_guidance_prompt.txt").format(
        topic=topic, category=category,
        line_number=line_number if line_number is not None else "N/A", static_message=static_message,
    )
    return [LLMMessage(role="system", content=system_text), LLMMessage(role="user", content=text)]
