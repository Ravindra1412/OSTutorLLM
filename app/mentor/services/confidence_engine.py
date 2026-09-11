"""
app/mentor/services/confidence_engine.py

Confidence Engine (Section 7). Distinct from
`performance_scorer.confidence_score()` (Part 3.9), which is a single,
narrow number (100 minus average code-review hint reliance). This
module builds the richer, multi-dimensional breakdown the brief asks
for — topic/command/programming/overall — reusing that narrow score as
one input rather than replacing it, plus a real "why" grounded in
`analytics_engine.retention_signal()` (score deltas over repeated
attempts) and `weak_topic_detector` (current gaps).
"""

from app.models import Topic, Progress
from app.analytics.services import performance_scorer, analytics_engine
from app.analytics.services.weak_topic_detector import detect_weak_topics


def _topic_confidence(user_id: int) -> list[dict]:
    """Direct reframing of Progress.mastery_score as a confidence
    percentage per topic — the mastery score already IS the most
    direct measure of how well-grounded a student is in a topic."""
    entries = Progress.query.filter_by(user_id=user_id).all()
    return [{"topic_name": e.topic_name, "confidence": round(e.mastery_score, 1)} for e in entries]


def _category_confidence(user_id: int, category_keyword: str) -> float | None:
    """Average mastery across topics whose curriculum Category contains
    the given keyword — used to separate 'Linux command' confidence
    from 'shell programming' confidence, since the curriculum's own
    Topic.category field (Part 3.4) already carries this distinction."""
    rows = (
        Progress.query.join(Topic, Progress.topic_name == Topic.name)
        .filter(Progress.user_id == user_id, Topic.category.ilike(f"%{category_keyword}%"))
        .all()
    )
    if not rows:
        return None
    return round(sum(r.mastery_score for r in rows) / len(rows), 1)


def compute_confidence(user_id: int) -> dict:
    topic_confidence = _topic_confidence(user_id)
    command_confidence = _category_confidence(user_id, "command") or _category_confidence(user_id, "linux")
    programming_confidence = _category_confidence(user_id, "shell") or _category_confidence(user_id, "programming")

    dimension_values = [v for v in (command_confidence, programming_confidence) if v is not None]
    if dimension_values:
        overall = round(sum(dimension_values) / len(dimension_values), 1)
    else:
        # Fall back to the narrower, always-available hint-reliance-based
        # score (Part 3.9) if there's no category-tagged topic data yet.
        overall = performance_scorer.confidence_score(user_id)

    retention = analytics_engine.retention_signal(user_id)
    improved = sorted([r for r in retention if r["retention_delta"] > 0], key=lambda r: -r["retention_delta"])
    declined = sorted([r for r in retention if r["retention_delta"] < 0], key=lambda r: r["retention_delta"])
    weak = detect_weak_topics(user_id, limit=3)

    why = {
        "what_improved": [
            f"{r['topic_name']} improved by {r['retention_delta']:.1f} points since you first attempted it."
            for r in improved[:3]
        ],
        "what_needs_work": [
            f"{w['topic_name']}: {w['signals'][0]}" if w["signals"] else w["topic_name"]
            for w in weak
        ],
        "what_declined": [
            f"{r['topic_name']} dropped by {abs(r['retention_delta']):.1f} points — consider a quick revision."
            for r in declined[:3]
        ],
    }

    return {
        "topic_confidence": topic_confidence,
        "command_confidence": command_confidence,
        "programming_confidence": programming_confidence,
        "overall_confidence": overall,
        "why": why,
    }
