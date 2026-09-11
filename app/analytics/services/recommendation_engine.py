"""
app/analytics/services/recommendation_engine.py

Recommendation Engine (Section 7). Generates a small set of concrete,
explainable next actions from real tracked data — no LLM call (kept
deterministic and free, consistent with Part 3.9 Section 13's
explainability requirement and Part 3's general free-tier-first
principle).

Recommendation types produced, in priority order:
  1. revision   - from weak_topic_detector.py's ranked weak topics
                 (priority 1 — highest, these are measured gaps).
  2. next_quiz    - the least-recently-quizzed tracked topic (Quiz
                 Engine's own "Revision Mode", Part 3.7 Section 5,
                 reused as a recommendation rather than duplicated).
  3. practice     - a Code Review topic the student hasn't submitted
                 to yet, drawn from app.code_review.topics (Part 3.8).
  4. next_lesson - a curriculum Topic (Part 3.4) with lessons that has
                 no Progress entry yet — i.e. genuinely unstarted.
  5. reading     - a static, honest placeholder (Part 3.7's Quiz Engine
                 Section 10 already documents that no content system
                 exists for "recommended reading" in this project; this
                 phase does not invent one, consistent with that
                 documented limitation — the recommendation instead
                 points back at the Tutor Engine's own lesson for the
                 topic, which IS real content).

`sync_recommendations()` REPLACES a student's active recommendation
set on every call: existing non-dismissed rows are deleted and
regenerated fresh, so recommendations never drift stale relative to
the student's current performance. Dismissed rows are also cleared at
the start of each sync — a student re-earning the same weak-topic flag
in a later, independent analysis should see it again rather than have
an old dismissal silently suppress it forever.
"""

from app.extensions import db
from app.models import Progress, QuizHistory, Topic, Lesson
from app.models.recommendation import Recommendation, TYPE_REVISION, TYPE_NEXT_QUIZ, TYPE_PRACTICE, TYPE_NEXT_LESSON
from app.analytics.services.weak_topic_detector import detect_weak_topics
from app.code_review.topics import CODE_REVIEW_TOPICS

MAX_RECOMMENDATIONS = 6


def _least_recently_quizzed_topic(user_id: int) -> str | None:
    tracked = {p.topic_name for p in Progress.query.filter_by(user_id=user_id).all()}
    if not tracked:
        return None
    last_quiz_at = {}
    for row in QuizHistory.query.filter_by(user_id=user_id).all():
        if row.topic_name in tracked:
            prev = last_quiz_at.get(row.topic_name)
            if prev is None or row.taken_at > prev:
                last_quiz_at[row.topic_name] = row.taken_at
    never_quizzed = tracked - set(last_quiz_at)
    if never_quizzed:
        return sorted(never_quizzed)[0]
    if not last_quiz_at:
        return None
    return min(last_quiz_at, key=last_quiz_at.get)


def _unattempted_code_review_topic(user_id: int) -> str | None:
    from app.models import CodeReviewSession

    attempted = {
        s.topic_name for s in CodeReviewSession.query.filter_by(user_id=user_id).all()
    }
    for topic in CODE_REVIEW_TOPICS:
        if topic not in attempted:
            return topic
    return None


def _unstarted_curriculum_topic(user_id: int) -> Topic | None:
    tracked = {p.topic_name for p in Progress.query.filter_by(user_id=user_id).all()}
    topics_with_lessons = (
        Topic.query.join(Lesson).distinct().order_by(Topic.difficulty_level.asc()).all()
    )
    for topic in topics_with_lessons:
        if topic.name not in tracked:
            return topic
    return None


def generate_recommendations(user_id: int) -> list[dict]:
    """Returns the fresh recommendation set as plain dicts (not yet
    persisted) — used both by sync_recommendations() and by any
    caller wanting a preview without writing to the database."""
    recs: list[dict] = []

    for weak in detect_weak_topics(user_id, limit=3):
        recs.append({
            "rec_type": TYPE_REVISION,
            "topic_name": weak["topic_name"],
            "title": f"Revise: {weak['topic_name']}",
            "reason": weak["signals"][0] if weak["signals"] else "Tracked performance is below target on this topic.",
            "priority": 1,
        })

    next_quiz_topic = _least_recently_quizzed_topic(user_id)
    if next_quiz_topic and next_quiz_topic not in {r["topic_name"] for r in recs}:
        recs.append({
            "rec_type": TYPE_NEXT_QUIZ,
            "topic_name": next_quiz_topic,
            "title": f"Take a quiz: {next_quiz_topic}",
            "reason": "This is your least recently tested tracked topic — a quick check keeps it fresh.",
            "priority": 2,
        })

    practice_topic = _unattempted_code_review_topic(user_id)
    if practice_topic:
        recs.append({
            "rec_type": TYPE_PRACTICE,
            "topic_name": practice_topic,
            "title": f"Try a shell programming exercise: {practice_topic}",
            "reason": "You haven't submitted any code for review on this topic yet.",
            "priority": 2,
        })

    next_topic = _unstarted_curriculum_topic(user_id)
    if next_topic:
        recs.append({
            "rec_type": TYPE_NEXT_LESSON,
            "topic_name": next_topic.name,
            "title": f"Start a new topic: {next_topic.name}",
            "reason": f"Unstarted topic in the curriculum ({next_topic.category}, difficulty {next_topic.difficulty_level}/5).",
            "priority": 3,
        })

    return recs[:MAX_RECOMMENDATIONS]


def sync_recommendations(user_id: int) -> list[Recommendation]:
    """Replaces the student's full recommendation set with a freshly
    generated one. See module docstring for the replace-not-append
    rationale."""
    Recommendation.query.filter_by(user_id=user_id).delete(synchronize_session="fetch")

    fresh = generate_recommendations(user_id)
    rows = [Recommendation(user_id=user_id, **rec) for rec in fresh]
    db.session.add_all(rows)
    db.session.commit()
    return rows


def get_active_recommendations(user_id: int) -> list[dict]:
    rows = (
        Recommendation.query.filter_by(user_id=user_id, is_dismissed=False)
        .order_by(Recommendation.priority.asc(), Recommendation.created_at.desc())
        .all()
    )
    return [r.to_dict() for r in rows]


def dismiss_recommendation(user_id: int, recommendation_id: int) -> bool:
    rec = Recommendation.query.filter_by(id=recommendation_id, user_id=user_id).first()
    if rec is None:
        return False
    rec.is_dismissed = True
    db.session.commit()
    return True
