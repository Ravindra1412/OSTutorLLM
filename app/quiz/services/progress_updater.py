"""
app/quiz/services/progress_updater.py

The Progress Updater (Section 1). Runs after a quiz is scored, writing
into the SAME `progress` table (Part 3.4) that the Tutor Engine (Part
3.6) and future Faculty Analytics all read — a quiz attempt is just
another mastery-relevant event, not a separate tracking system. Also
writes a `QuizHistory` row (Part 3.3's lightweight summary table) so
the existing `/api/progress` endpoint's fast summary view stays
accurate without modification.
"""

from datetime import datetime, timezone

from app.extensions import db
from app.models import Progress, QuizHistory, QuizAttempt


def update_progress_after_quiz(attempt: QuizAttempt, topic_name: str, score_percent: float) -> Progress:
    """Blends the new quiz score into the topic's running mastery_score
    using a weighted-average toward the new result (70% new / 30% old)
    — recent performance should move the needle more than a single
    stale data point, while still smoothing out one unlucky attempt."""
    entry = Progress.query.filter_by(user_id=attempt.user_id, topic_name=topic_name).first()

    if entry is None:
        entry = Progress(user_id=attempt.user_id, topic_name=topic_name, mastery_score=score_percent)
        db.session.add(entry)
    else:
        entry.mastery_score = round(0.3 * entry.mastery_score + 0.7 * score_percent, 2)
        entry.last_updated = datetime.now(timezone.utc)

    db.session.add(QuizHistory(user_id=attempt.user_id, topic_name=topic_name, score=score_percent))
    db.session.commit()
    return entry
