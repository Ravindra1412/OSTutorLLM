"""
app/mentor/services/insights_engine.py

AI Learning Insights (Section 12). Every sentence returned here is
built from a real, retrievable number — never phrased from a template
with no underlying data. Each insight dict carries an `evidence` field
naming exactly which number/service produced it, so the "why" is never
just implied.
"""

from app.models import Topic, Progress
from app.analytics.services.weak_topic_detector import detect_weak_topics
from app.analytics.services.analytics_engine import retention_signal
from app.analytics.services.predictive_engine import readiness_for_next_lesson


def _weak_topic_insights(user_id: int) -> list[dict]:
    insights = []
    for w in detect_weak_topics(user_id, limit=3):
        insights.append({
            "text": f"You struggle with {w['topic_name']}.",
            "evidence": w["signals"][0] if w["signals"] else f"weakness_score={w['weakness_score']}",
        })
    return insights


def _improvement_insights(user_id: int) -> list[dict]:
    insights = []
    for r in retention_signal(user_id):
        if r["retention_delta"] > 0 and r["first_score"] > 0:
            pct = round(100.0 * r["retention_delta"] / r["first_score"], 0)
            insights.append({
                "text": f"You improved {r['topic_name']} by {pct:.0f}% (from {r['first_score']:.0f}% to {r['latest_score']:.0f}%).",
                "evidence": f"first_score={r['first_score']}, latest_score={r['latest_score']}",
            })
    return insights


def _readiness_insight(user_id: int) -> dict | None:
    readiness = readiness_for_next_lesson(user_id)
    tracked = {p.topic_name for p in Progress.query.filter_by(user_id=user_id).all()}
    next_topic = Topic.query.filter(~Topic.name.in_(tracked)).order_by(Topic.difficulty_level.asc()).first() if tracked else None

    if readiness["ready"] and next_topic:
        return {
            "text": f"You are ready for {next_topic.name}.",
            "evidence": readiness["reason"],
        }
    return None


def _prerequisite_insight(user_id: int) -> dict | None:
    """Heuristic, not a real prerequisite graph (none exists in the
    curriculum schema): within the same Topic.category, if the student
    has attempted a HIGHER-difficulty topic while a LOWER-difficulty
    one in the same category still has low mastery, suggest revising
    the easier one first — a reasonable proxy for 'foundations before
    advanced material,' explicitly labeled as such."""
    entries = Progress.query.filter_by(user_id=user_id).all()
    if len(entries) < 2:
        return None

    by_name = {e.topic_name: e.mastery_score for e in entries}
    topics = {t.name: t for t in Topic.query.filter(Topic.name.in_(by_name.keys())).all()}

    for name, mastery in by_name.items():
        topic = topics.get(name)
        if topic is None or mastery >= 60:
            continue
        for other_name, other_topic in topics.items():
            if other_name == name or other_topic.category != topic.category:
                continue
            if other_topic.difficulty_level > topic.difficulty_level and by_name.get(other_name, 0) > 0:
                return {
                    "text": f"You should revise {name} before {other_name}.",
                    "evidence": f"{name} mastery is {mastery:.0f}% (below 60%) and is a lower-difficulty prerequisite-like topic in the same category ({topic.category}) as {other_name}.",
                }
    return None


def generate_insights(user_id: int) -> list[dict]:
    insights = _weak_topic_insights(user_id) + _improvement_insights(user_id)

    readiness = _readiness_insight(user_id)
    if readiness:
        insights.append(readiness)

    prerequisite = _prerequisite_insight(user_id)
    if prerequisite:
        insights.append(prerequisite)

    if not insights:
        insights.append({
            "text": "Not enough learning activity yet to generate personalized insights.",
            "evidence": "No quiz/tutor/code-review data recorded for this student.",
        })
    return insights
