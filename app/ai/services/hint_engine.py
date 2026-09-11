"""
app/ai/services/hint_engine.py

The Hint Engine (Section 1/8) — the component that structurally
enforces the Tutor Workflow (Section 7). This is deliberately pure
Python logic with NO dependency on the LLM provider: given the current
hint stage and a classification of the student's message intent, it
decides the NEXT stage. This is what makes the workflow "enforced"
rather than "requested via prompt wording" — even if a provider's
output were to misbehave, the stage the Prompt Manager is told to use
next is still decided here, deterministically, and is fully unit-
testable without ever calling an LLM (see tests/test_hint_engine.py).
"""

import re

from app.ai import config

INTENT_ATTEMPT = "attempt"                 # student is answering/trying
INTENT_REQUEST_HINT = "request_hint"       # "give me a hint" / "I don't know"
INTENT_REQUEST_ANSWER = "request_answer"   # "just tell me" / "show the answer"

_HINT_REQUEST_PATTERNS = [
    r"\bhint\b", r"\bi don'?t know\b", r"\bnot sure\b", r"\bstuck\b",
    r"\bany (clue|tip)s?\b", r"\bhelp me\b", r"\bno idea\b",
]
_ANSWER_REQUEST_PATTERNS = [
    r"\bjust (tell|give) me\b", r"\bshow (me )?the answer\b", r"\bfull answer\b",
    r"\bwhat'?s the answer\b", r"\bskip (the )?hints?\b", r"\bi give up\b",
]


def classify_intent(student_message: str) -> str:
    """Lightweight, deterministic keyword classification — sufficient
    for routing hint-stage progression (a wrong classification here
    only ever costs the student one extra hint step, never a policy
    violation), and fully unit-testable without an LLM call. A future
    phase could route ambiguous cases through the LLM for a smarter
    classification without changing this function's interface."""
    text = student_message.lower().strip()

    for pattern in _ANSWER_REQUEST_PATTERNS:
        if re.search(pattern, text):
            return INTENT_REQUEST_ANSWER
    for pattern in _HINT_REQUEST_PATTERNS:
        if re.search(pattern, text):
            return INTENT_REQUEST_HINT
    return INTENT_ATTEMPT


def next_stage(current_stage: int, intent: str) -> int:
    """The core hint-ladder state transition (Section 7's enforced
    workflow, Section 8's adaptive selection):

    - At the diagnostic stage (0): any response (attempt or explicit
      hint request) advances to Hint 1.
    - At hint stages 1-2: an attempt or a hint request both advance to
      the next hint stage (an attempt that's still wrong just earns a
      deeper hint — that IS the pedagogy).
    - At hint stage 3 (the last hint): the next student turn moves to
      the reveal stage regardless of intent, since all hints are
      exhausted (Part 2, Section 27 acceptance criterion — hints must
      be exhausted before reveal, never skipped).
    - An explicit "just give me the answer" at ANY stage skips straight
      to reveal — a deliberate design choice: the platform's philosophy
      is to encourage engagement, not to trap a student who explicitly
      opts out of hints (Part 1, Section 7.3 acknowledges hint policy
      violations are a risk to mitigate, not eliminate at all costs).
    - Once at reveal (4), the stage stays at 4 for the rest of this
      question — asking a NEW question resets to 0 via a fresh
      diagnostic turn, handled by the Tutor Service, not here.
    """
    if intent == INTENT_REQUEST_ANSWER:
        return config.HINT_STAGE_REVEAL

    if current_stage >= config.MAX_HINT_STAGE:
        return config.HINT_STAGE_REVEAL

    return current_stage + 1


def is_hint_ladder_exhausted(current_stage: int) -> bool:
    return current_stage >= config.MAX_HINT_STAGE


def reset_for_new_question() -> int:
    return config.HINT_STAGE_DIAGNOSTIC
