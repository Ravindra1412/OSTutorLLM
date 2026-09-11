"""
app/quiz/services/timer_service.py

The Timer Service (Section 1/8). Server-authoritative timing — the
frontend's countdown display (Part 3.2's quiz.js) is cosmetic; THIS
module is what actually enforces the time limit, since a client-side
timer alone is trivially bypassable (Section 19 — anti-tampering).
`QuizAttempt.expires_at` (Part 3.7 model extension) is the single
source of truth checked on every submit.
"""

from datetime import datetime, timezone, timedelta

from app.extensions import db
from app.models import QuizAttempt


def start_timer(attempt: QuizAttempt, time_limit_seconds: int | None) -> None:
    attempt.started_at = datetime.now(timezone.utc)
    attempt.time_limit_seconds = time_limit_seconds
    if time_limit_seconds:
        attempt.expires_at = attempt.started_at + timedelta(seconds=time_limit_seconds)
    db.session.commit()


def pause_timer(attempt: QuizAttempt) -> None:
    if attempt.paused_at is None and attempt.expires_at is not None:
        attempt.paused_at = datetime.now(timezone.utc)
        db.session.commit()


def resume_timer(attempt: QuizAttempt) -> None:
    """Extends expires_at by exactly the paused duration, so pausing
    never costs the student any of their allotted time (Section 8 —
    Pause/Resume)."""
    if attempt.paused_at is not None:
        paused_duration = (datetime.now(timezone.utc) - attempt.paused_at.replace(tzinfo=timezone.utc)).total_seconds()
        attempt.total_paused_seconds += int(paused_duration)
        if attempt.expires_at is not None:
            attempt.expires_at = attempt.expires_at.replace(tzinfo=timezone.utc) + timedelta(seconds=paused_duration)
        attempt.paused_at = None
        db.session.commit()


def is_expired(attempt: QuizAttempt) -> bool:
    if attempt.expires_at is None:
        return False  # untimed quiz
    now = datetime.now(timezone.utc)
    expires_at = attempt.expires_at if attempt.expires_at.tzinfo else attempt.expires_at.replace(tzinfo=timezone.utc)
    return now >= expires_at


def remaining_seconds(attempt: QuizAttempt) -> int | None:
    if attempt.expires_at is None:
        return None
    expires_at = attempt.expires_at if attempt.expires_at.tzinfo else attempt.expires_at.replace(tzinfo=timezone.utc)
    remaining = (expires_at - datetime.now(timezone.utc)).total_seconds()
    return max(0, int(remaining))
