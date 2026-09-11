"""
app/code_review/services/progress_integration.py

Progress Integration (Section 1). Writes each code review's overall
score back into the SAME `progress` table (Part 3.4) that the Tutor
Engine (Part 3.6) and Quiz Engine (Part 3.7) both update — a code
review is just another mastery-relevant event on a topic, not a
separate tracking system. Uses the identical weighted-average blend
(70% new / 30% old) as Part 3.7's progress_updater.py for consistency
across every engine that touches Progress.
"""

from datetime import datetime, timezone

from app.extensions import db
from app.models import Progress


def update_progress_after_review(user_id: int, topic_name: str, overall_score: float) -> Progress:
    entry = Progress.query.filter_by(user_id=user_id, topic_name=topic_name).first()

    if entry is None:
        entry = Progress(user_id=user_id, topic_name=topic_name, mastery_score=overall_score)
        db.session.add(entry)
    else:
        entry.mastery_score = round(0.3 * entry.mastery_score + 0.7 * overall_score, 2)
        entry.last_updated = datetime.now(timezone.utc)

    db.session.commit()
    return entry
