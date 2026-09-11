"""
tests/unit/test_code_review_monitoring.py

Comprehensive tests for app/faculty/services/code_review_monitoring.py.
Exercises all aggregation functions, corrupt JSON error resilience, daily/weekly
bucketing modes, score calculations, and dashboard summaries.
"""

import json
from datetime import datetime, timezone
import pytest

from app.extensions import db
from app.models import CodeSubmission, CodeReviewSession
from tests.fixtures.factories import make_student
from app.faculty.services.code_review_monitoring import (
    common_mistakes,
    most_frequent_errors_by_topic,
    improvement_timeline,
    review_history,
    build_monitoring_summary,
)


@pytest.fixture
def monitoring_data(app):
    """Seed student, sessions, and submissions with clean and edge-case data."""
    with app.app_context():
        student = make_student(email="monitor_student@example.com")

        # Session 1: Multithreading
        session1 = CodeReviewSession(
            user_id=student.id,
            topic_name="Multithreading",
        )
        db.session.add(session1)
        db.session.flush()

        # Session 2: Virtual Memory
        session2 = CodeReviewSession(
            user_id=student.id,
            topic_name="Virtual Memory",
        )
        db.session.add(session2)
        db.session.flush()

        # Submission 1: Valid findings and scores
        sub1 = CodeSubmission(
            session_id=session1.id,
            submission_number=1,
            code_text="pthread_mutex_lock(&m);",
            static_analysis_json=json.dumps([
                {"category": "concurrency", "message": "Missing unlock"},
                {"category": "syntax", "message": "Missing return"}
            ]),
            scores_json=json.dumps({"overall": 80}),
            hints_used_count=1,
            created_at=datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc),
        )

        # Submission 2: Valid findings with unknown category fallback
        sub2 = CodeSubmission(
            session_id=session2.id,
            submission_number=1,
            code_text="char *buf = malloc(10);",
            static_analysis_json=json.dumps([
                {"category": "memory", "message": "Memory leak"},
                {"message": "Unknown issue without category key"}
            ]),
            scores_json=json.dumps({"overall": 90}),
            hints_used_count=0,
            created_at=datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc),
        )

        # Submission 3: Corrupted JSON strings to test try-except branches
        sub3 = CodeSubmission(
            session_id=session1.id,
            submission_number=2,
            code_text="invalid_code()",
            static_analysis_json="INVALID_JSON_CONTENT",
            scores_json="INVALID_SCORES_JSON",
            hints_used_count=2,
            created_at=datetime(2026, 9, 8, 10, 0, 0, tzinfo=timezone.utc),
        )

        # Submission 4: Score without overall key
        sub4 = CodeSubmission(
            session_id=session1.id,
            submission_number=3,
            code_text="valid_code()",
            static_analysis_json=json.dumps([
                {"category": "concurrency", "message": "Deadlock potential"}
            ]),
            scores_json=json.dumps({"style": 50}),
            hints_used_count=0,
            created_at=datetime(2026, 9, 8, 11, 0, 0, tzinfo=timezone.utc),
        )

        db.session.add_all([sub1, sub2, sub3, sub4])
        db.session.commit()

        yield


def test_common_mistakes_aggregates_properly(app, monitoring_data):
    with app.app_context():
        results = common_mistakes(top_n=5)
        assert len(results) > 0
        categories = {r["category"]: r["occurrences"] for r in results}
        assert categories.get("concurrency") == 2
        assert categories.get("syntax") == 1
        assert categories.get("memory") == 1
        assert categories.get("unknown") == 1


def test_most_frequent_errors_by_topic(app, monitoring_data):
    with app.app_context():
        results = most_frequent_errors_by_topic(top_n=5)
        assert len(results) > 0
        topics = {r["topic_name"] for r in results}
        assert "Multithreading" in topics
        assert "Virtual Memory" in topics

        concurrency_err = next(
            r for r in results if r["topic_name"] == "Multithreading" and r["category"] == "concurrency"
        )
        assert concurrency_err["occurrences"] == 2


def test_improvement_timeline_weekly_and_daily(app, monitoring_data):
    with app.app_context():
        weekly = improvement_timeline(bucket="week")
        assert len(weekly) == 1
        assert weekly[0]["average_score"] == 85.0
        assert weekly[0]["submission_count"] == 2

        daily = improvement_timeline(bucket="day")
        assert len(daily) == 1
        assert daily[0]["period"] == "2026-09-01"
        assert daily[0]["average_score"] == 85.0


def test_review_history_listing(app, monitoring_data):
    with app.app_context():
        history = review_history(limit=10)
        assert len(history) == 4
        assert history[0]["submission_id"] is not None
        assert history[0]["student_name"] is not None
        corrupted_sub = next(h for h in history if h["hints_used"] == 2)
        assert corrupted_sub["overall_score"] is None


def test_build_monitoring_summary_structure(app, monitoring_data):
    with app.app_context():
        summary = build_monitoring_summary()
        assert "common_mistakes" in summary
        assert "most_frequent_errors_by_topic" in summary
        assert "improvement_timeline" in summary
        assert "review_history" in summary