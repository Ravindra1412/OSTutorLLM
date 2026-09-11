"""
app/analytics/services/progress_tracker.py

Progress Tracker (Section 4). Pure aggregation over existing tables —
no new source-of-truth data is invented here. Tracks:

  - Completed Lessons / Completed Topics
  - Quiz Scores (from QuizHistory, Part 3.3's lightweight summary table
    — chosen over QuizAttempt because it already exists specifically
    as the fast-read summary view; see progress_updater.py, Part 3.7)
  - Code Review Scores (from CodeSubmission.scores_json, Part 3.8)
  - Hint Usage (CodeSubmission.hints_used_count, Part 3.8; the Tutor
    Engine's hint stage isn't separately counted per-turn in any table,
    so tutor hint usage is out of scope here — an honest limitation,
    not an oversight)
  - Time Spent Learning, bucketed Daily / Weekly / Monthly / Total

Time-spent methodology (Section 4, explained once here rather than at
every call site):
  - Quiz time: (completed_at - started_at) for attempts where both
    timestamps exist — a real, measured duration (Part 3.7's
    server-authoritative timer already guarantees this is accurate).
  - Tutor time: (ended_at - started_at) for ChatSessions with ended_at
    set. Sessions never explicitly ended are NOT counted — no reliable
    end timestamp exists for those, and estimating one would be a
    fabricated number presented as fact. This is a deliberate,
    documented heuristic boundary (Part 3.9, Section 13 requires
    "simple, explainable heuristics rather than unsupported predictive
    claims" — the same principle applies to measurement, not just
    prediction).
  - Code review time: no timer exists in the Code Review Engine (Part
    3.8 has no start/end timestamps for a review session, only
    created_at per submission). A fixed CODE_REVIEW_MINUTES_ESTIMATE
    per submission is used as an explicit, labeled estimate — never
    presented as measured fact in the API response (the dashboard
    surfaces this as "code_review_minutes_estimated").
  - Lesson time: CompletedLesson.time_spent_minutes directly (Part 3.4
    field, populated by a future lesson-completion producer — no
    student route writes CompletedLesson rows yet in this codebase, so
    this will correctly read as zero until that producer exists; not
    rebuilt here since it is out of this phase's scope).
"""

from collections import defaultdict
from datetime import datetime, timezone, timedelta

from app.models import (
    Progress, QuizHistory, QuizAttempt, CompletedLesson,
    ChatSession, CodeReviewSession, CodeSubmission,
)

CODE_REVIEW_MINUTES_ESTIMATE = 8  # documented estimate, see module docstring
MASTERY_COMPLETE_THRESHOLD = 75.0  # a topic counts as "completed" at 75%+ mastery


def get_completed_topics(user_id: int) -> list[dict]:
    """Topics at or above MASTERY_COMPLETE_THRESHOLD, from the shared
    Progress table (Part 3.4) every engine already writes into."""
    entries = Progress.query.filter_by(user_id=user_id).all()
    return [
        {"topic_name": e.topic_name, "mastery_score": e.mastery_score}
        for e in entries if e.mastery_score >= MASTERY_COMPLETE_THRESHOLD
    ]


def get_tracked_topic_count(user_id: int) -> int:
    return Progress.query.filter_by(user_id=user_id).count()


def get_completed_lessons(user_id: int) -> list[dict]:
    rows = CompletedLesson.query.filter_by(user_id=user_id).all()
    return [{"lesson_id": r.lesson_id, "time_spent_minutes": r.time_spent_minutes} for r in rows]


def get_quiz_scores(user_id: int) -> list[dict]:
    rows = QuizHistory.query.filter_by(user_id=user_id).order_by(QuizHistory.taken_at.asc()).all()
    return [{"topic_name": r.topic_name, "score": r.score, "taken_at": r.taken_at.isoformat()} for r in rows]


def get_code_review_scores(user_id: int) -> list[dict]:
    """Joins CodeSubmission -> CodeReviewSession to scope to this
    user (CodeSubmission itself has no user_id — it belongs to a
    session, Part 3.8's design)."""
    import json

    rows = (
        CodeSubmission.query.join(CodeReviewSession)
        .filter(CodeReviewSession.user_id == user_id)
        .order_by(CodeSubmission.created_at.asc())
        .all()
    )
    out = []
    for r in rows:
        overall = None
        if r.scores_json:
            try:
                overall = json.loads(r.scores_json).get("overall")
            except (ValueError, TypeError):
                overall = None
        out.append({
            "topic_name": r.session.topic_name, "overall_score": overall,
            "hints_used": r.hints_used_count, "created_at": r.created_at.isoformat(),
        })
    return out


def _bucket_key(dt: datetime, granularity: str) -> str:
    if granularity == "day":
        return dt.strftime("%Y-%m-%d")
    if granularity == "week":
        iso = dt.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    return dt.strftime("%Y-%m")  # month


def get_time_spent_summary(user_id: int) -> dict:
    """Section 4 — Time Spent Learning, bucketed daily/weekly/monthly
    plus a running total. Returns minute totals per bucket for each
    granularity, plus grand totals split by measured vs. estimated
    source (see module docstring)."""
    minutes_by_day: dict[str, float] = defaultdict(float)
    minutes_by_week: dict[str, float] = defaultdict(float)
    minutes_by_month: dict[str, float] = defaultdict(float)

    def _add(dt: datetime, minutes: float):
        if minutes <= 0:
            return
        minutes_by_day[_bucket_key(dt, "day")] += minutes
        minutes_by_week[_bucket_key(dt, "week")] += minutes
        minutes_by_month[_bucket_key(dt, "month")] += minutes

    measured_minutes = 0.0
    estimated_minutes = 0.0

    quiz_attempts = QuizAttempt.query.filter_by(user_id=user_id).filter(
        QuizAttempt.started_at.isnot(None), QuizAttempt.completed_at.isnot(None)
    ).all()
    for a in quiz_attempts:
        mins = max(0.0, (a.completed_at - a.started_at).total_seconds() / 60.0)
        _add(a.completed_at, mins)
        measured_minutes += mins

    sessions = ChatSession.query.filter_by(user_id=user_id).filter(ChatSession.ended_at.isnot(None)).all()
    for s in sessions:
        mins = max(0.0, (s.ended_at - s.started_at).total_seconds() / 60.0)
        _add(s.ended_at, mins)
        measured_minutes += mins

    submissions = (
        CodeSubmission.query.join(CodeReviewSession)
        .filter(CodeReviewSession.user_id == user_id).all()
    )
    for sub in submissions:
        _add(sub.created_at, CODE_REVIEW_MINUTES_ESTIMATE)
        estimated_minutes += CODE_REVIEW_MINUTES_ESTIMATE

    lessons = CompletedLesson.query.filter_by(user_id=user_id).all()
    for lesson in lessons:
        mins = lesson.time_spent_minutes or 0.0
        _add(lesson.created_at, mins)
        measured_minutes += mins

    today_key = _bucket_key(datetime.now(timezone.utc), "day")
    week_key = _bucket_key(datetime.now(timezone.utc), "week")
    month_key = _bucket_key(datetime.now(timezone.utc), "month")

    return {
        "today_minutes": round(minutes_by_day.get(today_key, 0.0), 1),
        "this_week_minutes": round(minutes_by_week.get(week_key, 0.0), 1),
        "this_month_minutes": round(minutes_by_month.get(month_key, 0.0), 1),
        "total_minutes": round(measured_minutes + estimated_minutes, 1),
        "total_measured_minutes": round(measured_minutes, 1),
        "total_estimated_minutes": round(estimated_minutes, 1),
        "daily_breakdown": dict(sorted(minutes_by_day.items())[-14:]),  # last 14 tracked days
    }


def get_learning_streak_days(user_id: int) -> int:
    """Consecutive days (up to and including today or yesterday) with
    at least one learning event in LearningTimeline. Kept separate from
    StudentProfile.streak_days (Part 3.1) which is not currently
    incremented by any engine — this computes the real value from
    actual event data rather than relying on that unmaintained field."""
    from app.models import LearningTimeline

    rows = (
        LearningTimeline.query.filter_by(user_id=user_id)
        .order_by(LearningTimeline.created_at.desc())
        .limit(400)
        .all()
    )
    if not rows:
        return 0

    days = sorted({r.created_at.date() for r in rows}, reverse=True)
    today = datetime.now(timezone.utc).date()

    if days[0] not in (today, today - timedelta(days=1)):
        return 0  # streak broken — most recent activity wasn't today or yesterday

    streak = 1
    for i in range(1, len(days)):
        if (days[i - 1] - days[i]).days == 1:
            streak += 1
        else:
            break
    return streak
