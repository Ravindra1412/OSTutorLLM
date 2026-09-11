"""
app/code_review/topics.py

Section 4 — Supported Topics. Distinct from the general `Topic` table
(Part 3.4), which spans the whole platform (Tutor + Quiz + Code
Review). This is a scoped list specifically for what the Code Review
Engine is prepared to give shell-programming-specific feedback on —
used to populate the frontend Topic Selector (Section 14) and to give
the LLM Review Engine an explicit scope hint in its prompt (Section
12), so review quality doesn't degrade by trying to be equally
expert about every possible submission.
"""

CODE_REVIEW_TOPICS = [
    "Linux Commands",
    "Shell Variables",
    "Conditional Statements",
    "Loops",
    "Functions",
    "Arrays",
    "File Handling",
    "Text Processing",
    "Process Management",
    "Permissions",
    "Redirection",
    "Pipes",
    "grep",
    "sed",
    "awk",
    "System Utilities",
]


def is_supported_topic(topic_name: str) -> bool:
    return topic_name in CODE_REVIEW_TOPICS
