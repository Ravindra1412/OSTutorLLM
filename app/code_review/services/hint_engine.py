"""
app/code_review/services/hint_engine.py

The Hint Engine (Section 1/7). Mirrors the exact hint-ladder pattern
established in Part 3.6 (Tutor Engine) and Part 3.7 (Quiz Engine), now
applied to ONE static/LLM-flagged issue at a time in a code review,
per Part 2 Section 15's original Code Review design: "identify one
issue at a time... guiding question... don't reveal fix until asked."

Stage meaning (why each hint is given — Section 7's explicit request):
  0 = Issue flagged, no hint yet — student sees WHAT was found, not
      WHY or HOW to fix it, forcing them to think first.
  1 = Conceptual nudge — points at the general category of problem
      without naming the specific fix.
  2 = Structural hint — narrows to the specific construct/command
      involved, still without the exact corrected line.
  3 = Near-complete scaffold — shows the shape of the fix with a
      placeholder, leaving only the final detail for the student.
  4 = Final guidance — the full explanation AND the corrected
      construct, only after the ladder is exhausted or explicitly
      requested (same policy as Tutor/Quiz Engines' reveal stage).
"""

HINT_STAGE_FLAGGED = 0
HINT_STAGE_1 = 1
HINT_STAGE_2 = 2
HINT_STAGE_3 = 3
HINT_STAGE_FINAL = 4
MAX_HINT_STAGE = HINT_STAGE_3

STAGE_RATIONALE = {
    HINT_STAGE_FLAGGED: "The issue is named, but not explained yet — the student engages with what was found before being told why.",
    HINT_STAGE_1: "A conceptual nudge toward the general category of the problem, without naming the specific fix.",
    HINT_STAGE_2: "Narrows to the specific command/construct involved, still withholding the exact corrected line.",
    HINT_STAGE_3: "A near-complete scaffold — the shape of the fix, with the final specific detail left for the student.",
    HINT_STAGE_FINAL: "Full explanation and the corrected construct, since all prior hints have been engaged with.",
}


def next_stage(current_stage: int, requested_final: bool = False) -> int:
    """Advances exactly one stage per request, EXCEPT an explicit
    'just show me' request (same student-respecting override as
    Part 3.6/3.7's hint engines) or reaching the ladder's end, both of
    which jump straight to HINT_STAGE_FINAL."""
    if requested_final or current_stage >= MAX_HINT_STAGE:
        return HINT_STAGE_FINAL
    return current_stage + 1


def is_exhausted(current_stage: int) -> bool:
    return current_stage >= MAX_HINT_STAGE


def rationale_for_stage(stage: int) -> str:
    return STAGE_RATIONALE.get(stage, "")
