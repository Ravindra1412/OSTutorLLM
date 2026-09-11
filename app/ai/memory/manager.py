"""
app/ai/memory/manager.py

The Memory Manager (Section 1/6). Reads/writes the structured
per-session learning state stored in ChatSession.state_json. This is
"short-term memory" scoped to a single tutoring session — distinct
from the Progress table (Part 3.4), which is the long-term, cross-
session mastery record. The two are related but serve different
purposes:
  - Memory Manager (this file): "where is the student RIGHT NOW in
    THIS conversation" — completed_steps, current understanding
    estimate, teaching mode.
  - Progress table (Part 3.4): "how good is this student at this
    TOPIC overall, across all sessions" — read by
    app/ai/services/personalization.py (Section 11) to seed a new
    session's starting difficulty.

State shape (JSON):
{
  "teaching_mode": "beginner" | "intermediate" | "advanced" | "exam_prep" | "lab_practice",
  "understanding_estimate": 0-100,
  "completed_steps": ["diagnostic_answered", "hint_1_given", ...],
  "current_lesson": str | null,
  "consecutive_correct": int,
  "consecutive_struggling": int
}
"""

import json

from app.extensions import db
from app.models import ChatSession

DEFAULT_STATE = {
    "teaching_mode": "intermediate",
    "understanding_estimate": 50,
    "completed_steps": [],
    "current_lesson": None,
    "consecutive_correct": 0,
    "consecutive_struggling": 0,
}


def load_state(session: ChatSession) -> dict:
    if not session.state_json:
        return dict(DEFAULT_STATE)
    try:
        state = json.loads(session.state_json)
    except (ValueError, TypeError):
        return dict(DEFAULT_STATE)
    merged = dict(DEFAULT_STATE)
    merged.update(state)
    return merged


def save_state(session: ChatSession, state: dict) -> None:
    session.state_json = json.dumps(state)
    db.session.commit()


def set_teaching_mode(session: ChatSession, mode: str) -> dict:
    state = load_state(session)
    state["teaching_mode"] = mode
    save_state(session, state)
    return state


def mark_step_completed(session: ChatSession, step_name: str) -> dict:
    state = load_state(session)
    if step_name not in state["completed_steps"]:
        state["completed_steps"].append(step_name)
    save_state(session, state)
    return state


def set_current_lesson(session: ChatSession, lesson_title: str | None) -> dict:
    state = load_state(session)
    state["current_lesson"] = lesson_title
    save_state(session, state)
    return state


def record_attempt_outcome(session: ChatSession, was_correct: bool) -> dict:
    """Updates the running understanding estimate and streak counters
    (Section 11 — Difficulty Detection feeds off this). A simple,
    explainable additive adjustment is used rather than an opaque
    formula, so the effect of any single interaction is predictable
    and testable."""
    state = load_state(session)
    if was_correct:
        state["consecutive_correct"] += 1
        state["consecutive_struggling"] = 0
        state["understanding_estimate"] = min(100, state["understanding_estimate"] + 10)
    else:
        state["consecutive_struggling"] += 1
        state["consecutive_correct"] = 0
        state["understanding_estimate"] = max(0, state["understanding_estimate"] - 8)
    save_state(session, state)
    return state


def is_struggling(state: dict, threshold: int = 2) -> bool:
    """True once the student has struggled `threshold` times in a row —
    used by the Hint Engine/Personalization layer to consider dropping
    to an easier explanation style (Section 11 — Difficulty Detection)."""
    return state.get("consecutive_struggling", 0) >= threshold
