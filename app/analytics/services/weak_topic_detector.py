"""
app/analytics/services/weak_topic_detector.py

Weak Topic Detection (Section 6). Combines four independent signals
into one explainable per-topic weakness score, so "why is this topic
flagged" is always answerable from the returned `signals` list rather
than a single opaque number:

  1. Low mastery       - Progress.mastery_score below WEAK_THRESHOLD.
  2. Low quiz scores    - average QuizHistory.score for the topic below
                         WEAK_THRESHOLD.
  3. Frequent hints      - CodeSubmission.hints_used_count summed per
                         topic above HIGH_HINT_USAGE.
  4. Repeated errors      - a topic's Code Review submissions carrying
                         3+ static-analysis findings on average.

Each signal contributes a fixed weight to a 0-100 `weakness_score`;
higher = weaker. This is intentionally simple arithmetic (not a
trained model) per Part 3.9 Section 13's explainability requirement —
every point in the score traces back to a named, visible signal.
"""

import json
import statistics

from app.models import Progress, QuizHistory, CodeSubmission, CodeReviewSession

WEAK_THRESHOLD = 60.0
HIGH_HINT_USAGE = 3
SIGNAL_WEIGHT = 25  # each of up to 4 signals contributes up to 25 points


def _topic_quiz_averages(user_id: int) -> dict[str, float]:
    rows = QuizHistory.query.filter_by(user_id=user_id).all()
    by_topic: dict[str, list] = {}
    for r in rows:
        if r.score is not None:
            by_topic.setdefault(r.topic_name, []).append(r.score)
    return {topic: statistics.fmean(scores) for topic, scores in by_topic.items()}


def _topic_hint_totals(user_id: int) -> dict[str, int]:
    submissions = (
        CodeSubmission.query.join(CodeReviewSession)
        .filter(CodeReviewSession.user_id == user_id).all()
    )
    totals: dict[str, int] = {}
    for sub in submissions:
        topic = sub.session.topic_name
        totals[topic] = totals.get(topic, 0) + (sub.hints_used_count or 0)
    return totals


def _topic_avg_finding_count(user_id: int) -> dict[str, float]:
    submissions = (
        CodeSubmission.query.join(CodeReviewSession)
        .filter(CodeReviewSession.user_id == user_id, CodeSubmission.static_analysis_json.isnot(None))
        .all()
    )
    by_topic: dict[str, list] = {}
    for sub in submissions:
        try:
            count = len(json.loads(sub.static_analysis_json))
        except (ValueError, TypeError):
            continue
        by_topic.setdefault(sub.session.topic_name, []).append(count)
    return {topic: statistics.fmean(counts) for topic, counts in by_topic.items()}


def detect_weak_topics(user_id: int, limit: int = 5) -> list[dict]:
    mastery_by_topic = {p.topic_name: p.mastery_score for p in Progress.query.filter_by(user_id=user_id).all()}
    quiz_avg_by_topic = _topic_quiz_averages(user_id)
    hints_by_topic = _topic_hint_totals(user_id)
    findings_by_topic = _topic_avg_finding_count(user_id)

    all_topics = set(mastery_by_topic) | set(quiz_avg_by_topic) | set(hints_by_topic) | set(findings_by_topic)

    ranked = []
    for topic in all_topics:
        signals = []
        score = 0

        mastery = mastery_by_topic.get(topic)
        if mastery is not None and mastery < WEAK_THRESHOLD:
            score += SIGNAL_WEIGHT
            signals.append(f"Mastery score is {mastery:.1f}% (below {WEAK_THRESHOLD:.0f}% target).")

        quiz_avg = quiz_avg_by_topic.get(topic)
        if quiz_avg is not None and quiz_avg < WEAK_THRESHOLD:
            score += SIGNAL_WEIGHT
            signals.append(f"Average quiz score is {quiz_avg:.1f}%.")

        hints = hints_by_topic.get(topic, 0)
        if hints >= HIGH_HINT_USAGE:
            score += SIGNAL_WEIGHT
            signals.append(f"Requested {hints} hint(s) during code review on this topic.")

        avg_findings = findings_by_topic.get(topic)
        if avg_findings is not None and avg_findings >= 3:
            score += SIGNAL_WEIGHT
            signals.append(f"Code review submissions average {avg_findings:.1f} issues found.")

        if score > 0:
            ranked.append({
                "topic_name": topic,
                "weakness_score": score,
                "mastery_score": mastery,
                "signals": signals,
            })

    ranked.sort(key=lambda t: t["weakness_score"], reverse=True)
    return ranked[:limit]
