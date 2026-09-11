"""
app/quiz/services/difficulty_manager.py

The Difficulty Manager (Section 1/4). Determines what difficulty level
a student's next quiz on a topic should target. Reuses the real
`progress` table (Part 3.4) and past `QuizAttempt`/`QuizResult` rows
(Part 3.4, extended this phase) — the same personalization data source
already established in Part 3.6's `app/ai/services/personalization.py`
— rather than inventing a second, parallel tracking mechanism.

Three explicit levels (easy/medium/hard, Section 4) map onto the
existing 1-5 integer difficulty_level scale already used by every
content table (Topic, Quiz, QuizQuestion — Part 3.4):
  easy   = 1-2
  medium = 3
  hard   = 4-5
"""

from app.models import Progress, QuizAttempt, Quiz

EASY, MEDIUM, HARD = "easy", "medium", "hard"

_LABEL_TO_LEVEL = {EASY: 2, MEDIUM: 3, HARD: 4}
_LEVEL_TO_LABEL_BOUNDS = [(1, 2, EASY), (3, 3, MEDIUM), (4, 5, HARD)]


def label_for_level(level: int) -> str:
    for lo, hi, label in _LEVEL_TO_LABEL_BOUNDS:
        if lo <= level <= hi:
            return label
    return MEDIUM


def level_for_label(label: str) -> int:
    return _LABEL_TO_LEVEL.get(label, 3)


def determine_adaptive_difficulty(user_id: int, topic_name: str) -> int:
    """Section 4 — Adaptive Mode. Combines two signals:
      1. Long-term topic mastery (Progress.mastery_score, Part 3.4) —
         the primary signal, since it reflects performance across
         tutoring AND quizzes, not just quizzes in isolation.
      2. Recent quiz score trend on this exact topic (last 3 attempts)
         — a secondary adjustment so a student who's IMPROVING quickly
         gets bumped up sooner than mastery_score alone would suggest,
         and one who's REGRESSING gets eased back down.

    Returns an integer 1-5, directly usable as QuizQuestion/Quiz
    difficulty_level — this is the one function every other quiz
    service call site uses to answer "what difficulty right now."
    """
    progress_entry = Progress.query.filter_by(user_id=user_id, topic_name=topic_name).first()
    base_level = _mastery_to_level(progress_entry.mastery_score) if progress_entry else 2  # start slightly easy for a brand-new topic

    recent_attempts = (
        QuizAttempt.query.join(Quiz, QuizAttempt.quiz_id == Quiz.id)
        .filter(QuizAttempt.user_id == user_id, Quiz.topic_id == _topic_id_for_name(topic_name), QuizAttempt.score.isnot(None))
        .order_by(QuizAttempt.completed_at.desc())
        .limit(3)
        .all()
    )
    adjustment = _trend_adjustment([a.score for a in recent_attempts])

    return max(1, min(5, base_level + adjustment))


def _mastery_to_level(mastery_score: float) -> int:
    if mastery_score >= 85:
        return 5
    if mastery_score >= 70:
        return 4
    if mastery_score >= 50:
        return 3
    if mastery_score >= 30:
        return 2
    return 1


def _trend_adjustment(recent_scores: list[float]) -> int:
    """+1 if recent quiz scores are consistently strong (avg >= 85),
    -1 if consistently weak (avg < 40), 0 otherwise. Requires at least
    2 data points so a single lucky/unlucky quiz doesn't swing
    difficulty — Section 11's "Learning Speed" signal, kept simple and
    explainable rather than a black-box formula."""
    if len(recent_scores) < 2:
        return 0
    avg = sum(recent_scores) / len(recent_scores)
    if avg >= 85:
        return 1
    if avg < 40:
        return -1
    return 0


def _topic_id_for_name(topic_name: str):
    from app.models import Topic
    topic = Topic.query.filter_by(name=topic_name).first()
    return topic.id if topic else -1
