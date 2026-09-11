"""
app/ai/services/personalization.py

Learning Personalization (Section 1/11). Reads the real `progress`
table (Part 3.4) — the same table the future Progress Dashboard and
Faculty Analytics will read — rather than inventing a parallel
tracking mechanism. This keeps the AI Tutor Engine's personalization
consistent with every other part of the platform's mastery model
(Part 2, Section 13.1).
"""

from app.models import Progress

WEAK_TOPIC_THRESHOLD = 50.0  # Part 2, Section 13.3


def get_competency_summary(user_id: int, topic_name: str) -> str:
    """A short natural-language summary injected into the developer
    prompt (Section 4) so the LLM implicitly personalizes its hints
    without needing to re-derive the student's history itself."""
    entry = Progress.query.filter_by(user_id=user_id, topic_name=topic_name).first()
    if entry is None:
        return f"This is the student's first tracked interaction with '{topic_name}'."

    if entry.mastery_score >= 80:
        band = "strong"
    elif entry.mastery_score >= WEAK_TOPIC_THRESHOLD:
        band = "developing"
    else:
        band = "weak"

    return f"Student's current mastery of '{topic_name}' is {entry.mastery_score:.0f}/100 ({band})."


def detect_difficulty_level(understanding_estimate: int) -> str:
    """Section 11 — Difficulty Detection. Maps the Memory Manager's
    running understanding_estimate (0-100, Section 6) to a teaching
    mode suggestion. This is a suggestion the Tutor Service may apply
    automatically or leave to an explicit student/faculty choice — kept
    as a pure function so it's independently testable."""
    if understanding_estimate < 30:
        return "beginner"
    if understanding_estimate < 70:
        return "intermediate"
    return "advanced"


def get_weak_topics(user_id: int, limit: int = 5) -> list[dict]:
    """Section 11 — Weak Topic Detection."""
    entries = (
        Progress.query.filter(Progress.user_id == user_id, Progress.mastery_score < WEAK_TOPIC_THRESHOLD)
        .order_by(Progress.mastery_score.asc())
        .limit(limit)
        .all()
    )
    return [{"topic_name": e.topic_name, "mastery_score": e.mastery_score} for e in entries]


def recommend_next_topic(user_id: int, available_topics: list[str]) -> str | None:
    """Section 11 — Recommended Next Topic / Learning Path Tracking.
    Recommends the lowest-mastery topic among `available_topics` that
    the student has any tracked progress on; falls back to the first
    topic with no progress at all (encouraging breadth before depth
    keeps a brand-new student from being sent to a topic ranked
    'weakest' purely because it has zero data)."""
    entries = {
        e.topic_name: e.mastery_score
        for e in Progress.query.filter_by(user_id=user_id).all()
        if e.topic_name in available_topics
    }

    untouched = [t for t in available_topics if t not in entries]
    if untouched:
        return untouched[0]

    if not entries:
        return available_topics[0] if available_topics else None

    return min(entries, key=entries.get)
