"""
app/faculty/services/code_review_monitoring.py

Code Review Monitoring (Section 11). Class-wide view over the same
CodeSubmission static-analysis findings Part 3.9's per-student
mistake_patterns() already reads — aggregated across everyone instead
of one student, plus a raw review-history listing for browsing.
"""

import json
import statistics
from collections import Counter, defaultdict

from app.models import CodeSubmission


def common_mistakes(top_n: int = 10) -> list[dict]:
    categories: Counter = Counter()
    for sub in CodeSubmission.query.filter(CodeSubmission.static_analysis_json.isnot(None)).all():
        try:
            findings = json.loads(sub.static_analysis_json)
        except (ValueError, TypeError):
            continue
        for f in findings:
            categories[f.get("category", "unknown")] += 1
    return [{"category": cat, "occurrences": count} for cat, count in categories.most_common(top_n)]


def most_frequent_errors_by_topic(top_n: int = 10) -> list[dict]:
    by_topic_category: Counter = Counter()
    for sub in CodeSubmission.query.filter(CodeSubmission.static_analysis_json.isnot(None)).all():
        topic = sub.session.topic_name
        try:
            findings = json.loads(sub.static_analysis_json)
        except (ValueError, TypeError):
            continue
        for f in findings:
            by_topic_category[(topic, f.get("category", "unknown"))] += 1

    return [
        {"topic_name": topic, "category": cat, "occurrences": count}
        for (topic, cat), count in by_topic_category.most_common(top_n)
    ]


def improvement_timeline(bucket: str = "week") -> list[dict]:
    """Section 11 — class-wide average code review score over time,
    bucketed weekly by default, so an instructor can see whether
    scores are trending up or down across the term."""
    buckets: dict[str, list] = defaultdict(list)
    for sub in CodeSubmission.query.filter(CodeSubmission.scores_json.isnot(None)).order_by(CodeSubmission.created_at.asc()).all():
        try:
            overall = json.loads(sub.scores_json).get("overall")
        except (ValueError, TypeError):
            overall = None
        if overall is None:
            continue
        if bucket == "week":
            iso = sub.created_at.isocalendar()
            key = f"{iso[0]}-W{iso[1]:02d}"
        else:
            key = sub.created_at.strftime("%Y-%m-%d")
        buckets[key].append(overall)

    return [
        {"period": key, "average_score": round(statistics.fmean(scores), 2), "submission_count": len(scores)}
        for key, scores in sorted(buckets.items())
    ]


def review_history(limit: int = 50) -> list[dict]:
    subs = CodeSubmission.query.order_by(CodeSubmission.created_at.desc()).limit(limit).all()
    out = []
    for sub in subs:
        student = sub.session.user
        overall = None
        if sub.scores_json:
            try:
                overall = json.loads(sub.scores_json).get("overall")
            except (ValueError, TypeError):
                pass
        out.append({
            "submission_id": sub.id, "student_name": student.name, "student_id": student.id,
            "topic_name": sub.session.topic_name, "overall_score": overall,
            "hints_used": sub.hints_used_count, "submitted_at": sub.created_at.isoformat(),
        })
    return out


def build_monitoring_summary() -> dict:
    return {
        "common_mistakes": common_mistakes(),
        "most_frequent_errors_by_topic": most_frequent_errors_by_topic(),
        "improvement_timeline": improvement_timeline(),
        "review_history": review_history(),
    }
