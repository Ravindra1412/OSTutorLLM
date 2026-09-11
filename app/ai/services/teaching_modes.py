"""
app/ai/services/teaching_modes.py

Teaching Modes (Section 9). A small, centralized constant set so every
layer (routes, forms, Prompt Manager) validates/references the exact
same five values — avoids the "typo'd mode string silently falls back
to default" class of bug.

The actual behavioral difference per mode is implemented in the Prompt
Manager's TEACHING_MODE_DESCRIPTIONS (app/ai/prompts/manager.py),
which is where mode -> instruction-text mapping belongs; this module
is intentionally just the validated vocabulary.
"""

BEGINNER = "beginner"
INTERMEDIATE = "intermediate"
ADVANCED = "advanced"
EXAM_PREP = "exam_prep"
LAB_PRACTICE = "lab_practice"

ALL_MODES = (BEGINNER, INTERMEDIATE, ADVANCED, EXAM_PREP, LAB_PRACTICE)
DEFAULT_MODE = INTERMEDIATE


def is_valid_mode(mode: str) -> bool:
    return mode in ALL_MODES
