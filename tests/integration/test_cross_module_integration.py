"""
tests/integration/test_cross_module_integration.py

Part 3.11, Section 5 — Integration Testing. The existing per-engine
test files (tests/integration/test_quiz_service.py etc.) already prove
each engine works correctly in isolation with real DB writes. This
module specifically proves the SEAMS BETWEEN engines named in Section
5 — that data one module writes is what another module actually reads,
not just that each module works alone.
"""

import pytest

from app.extensions import db
from app.models import Progress, LearningTimeline
from app.quiz.services import quiz_service
from app.code_review.services import review_service
from app.ai.services import tutor_service
from app.analytics.services import dashboard_service
from app.faculty.services import class_analytics
from tests.fixtures.factories import make_student, make_faculty, make_topic, login

pytestmark = pytest.mark.integration

FLAWED_SCRIPT = "for f in *.txt\n  do cat $f\ndone\nx=5\n"


class TestAuthenticationGatesAllModules:
    """Section 5 — Authentication <-> All Modules. One sweep across a
    representative route from every engine, unauthenticated."""

    @pytest.mark.parametrize("method,path", [
        ("get", "/api/progress"),
        ("post", "/api/tutor/session"),
        ("post", "/api/quiz/start"),
        ("post", "/api/code-review/submit"),
        ("get", "/api/analytics/dashboard"),
        ("get", "/api/faculty/dashboard"),
    ])
    def test_every_module_rejects_unauthenticated_requests(self, client, method, path):
        resp = getattr(client, method)(path, json={} if method == "post" else None)
        assert resp.status_code in (302, 401)


class TestTutorQuizAnalyticsSharedProgress:
    """Section 5 — Tutor <-> Quiz Engine <-> Analytics <-> Dashboard.
    Confirms these are not four independent systems that happen to
    coexist: a quiz result written by the Quiz Engine is the SAME data
    the Analytics Dashboard reads back, and a tutor session is the
    SAME event visible on the Learning Timeline."""

    def test_quiz_result_flows_into_dashboard(self, app):
        student = make_student(email="flowtest@example.com")
        make_topic("Navigation")

        result = quiz_service.start_quiz(student.id, topic_name="Navigation", question_count=1)
        for q in result.quiz.questions:
            quiz_service.submit_answer(student.id, result.attempt.id, q.id, "some answer")
        quiz_service.submit_quiz(student.id, result.attempt.id)

        dashboard = dashboard_service.build_dashboard(student.id)
        assert dashboard["average_quiz_score"] is not None
        assert any(e["event_type"] == "quiz_attempted" for e in dashboard["recent_timeline"])

    def test_tutor_session_flows_into_timeline_and_dashboard(self, app):
        student = make_student(email="tutorflow@example.com")
        tutor_service.start_session(student.id, "Navigation")

        events = LearningTimeline.query.filter_by(user_id=student.id).all()
        assert any(e.event_type == "tutor_session" for e in events)

        dashboard = dashboard_service.build_dashboard(student.id)
        assert any(e["event_type"] == "tutor_session" for e in dashboard["recent_timeline"])

    def test_code_review_flows_into_class_analytics(self, app):
        """Section 5 — Quiz <-> Analytics generalizes to Code Review
        <-> Analytics too: this confirms the Faculty class-wide view
        reads the exact submission just created, not a stale/cached
        copy."""
        student = make_student(email="crflow@example.com")
        review_service.submit_for_review(student.id, "Loops", FLAWED_SCRIPT)

        stats = class_analytics.code_review_statistics()
        assert stats["submission_count"] == 1


class TestFacultyDashboardReadsRealDatabase:
    """Section 5 — Faculty Dashboard <-> Database. Not mocked — a
    faculty member's dashboard numbers must move when the underlying
    student data actually changes."""

    def test_student_count_updates_when_a_new_student_registers(self, client, app):
        make_faculty(email="countfac@example.com")
        login(client, "countfac@example.com")

        before = client.get("/api/faculty/dashboard").get_json()["data"]["total_students"]

        client.post("/api/auth/register", json={
            "name": "New Student", "email": "newstudent@example.com", "password": "Password123!", "role": "student",
        })

        after = client.get("/api/faculty/dashboard").get_json()["data"]["total_students"]
        assert after == before + 1

    def test_class_analytics_reflects_real_progress_rows(self, app):
        student = make_student(email="progressflow@example.com")
        db.session.add(Progress(user_id=student.id, topic_name="Deadlocks", mastery_score=42.0))
        db.session.commit()

        result = class_analytics.topic_wise_class_performance()
        deadlocks = next((t for t in result if t["topic_name"] == "Deadlocks"), None)
        assert deadlocks is not None
        assert deadlocks["average_mastery"] == 42.0


class TestBackendDatabaseTransactionIntegrity:
    """Section 5 — Backend <-> Database. A failed operation partway
    through must not leave a half-written row behind."""

    def test_quiz_submission_with_invalid_question_id_does_not_corrupt_attempt(self, app):
        from app.quiz.services import security as quiz_security

        student = make_student(email="txntest@example.com")
        make_topic("Navigation")
        result = quiz_service.start_quiz(student.id, topic_name="Navigation", question_count=1)

        with pytest.raises(quiz_security.QuizSecurityError):
            quiz_service.submit_answer(student.id, result.attempt.id, 999999, "answer")

        # The attempt itself must still be intact and attemptable, not
        # left in a broken intermediate state by the rejected sub-operation.
        from app.models import QuizAttempt, QuizResult
        attempt = db.session.get(QuizAttempt, result.attempt.id)
        assert attempt is not None
        assert attempt.is_submitted is False
        assert QuizResult.query.filter_by(attempt_id=attempt.id, question_id=999999).first() is None
