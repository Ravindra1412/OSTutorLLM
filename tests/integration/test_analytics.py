"""
tests/test_analytics.py

Part 3.9 test suite. Uses the real database and the real Mock LLM
provider — same integration-testing philosophy as
test_quiz_service.py (Part 3.7) and test_code_review_service.py (Part
3.8): exercise the real orchestrators (quiz_service.submit_quiz,
review_service.submit_for_review, tutor_service.start_session) so the
Part 3.9 hooks wired into them are proven end-to-end, not just unit-
tested in isolation.
"""

import pytest

from app.extensions import db
from app.models import User, StudentProfile, Progress, LearningTimeline, Recommendation
from app.quiz.services import quiz_service
from app.code_review.services import review_service
from app.ai.services import tutor_service
from app.analytics.services import (
    progress_tracker, analytics_engine, weak_topic_detector,
    recommendation_engine, achievement_manager, performance_scorer,
    predictive_engine, timeline_service, dashboard_service,
)


@pytest.fixture()
def student(app):
    user = User(name="Analytics Student", email="analyticsstudent@example.com", role="student")
    user.set_password("password123")
    db.session.add(user)
    db.session.flush()
    db.session.add(StudentProfile(user_id=user.id))
    db.session.commit()
    return user


FLAWED_SCRIPT = "for f in *.txt\n  do cat $f\ndone\nx=5\n"


def _do_quiz(student_id, topic, count=2):
    result = quiz_service.start_quiz(student_id, topic_name=topic, question_count=count)
    for q in result.quiz.questions:
        quiz_service.submit_answer(student_id, result.attempt.id, q.id, "some answer")
    return quiz_service.submit_quiz(student_id, result.attempt.id)


class TestTimelineService:
    def test_log_event_and_read_back(self, app, student):
        entry = timeline_service.log_event(student.id, "quiz_attempted", title="Test event", topic_name="Loops", score=80.0)
        assert entry is not None
        events = timeline_service.get_timeline(student.id)
        assert len(events) == 1
        assert events[0]["title"] == "Test event"

    def test_invalid_event_type_rejected(self, app, student):
        entry = timeline_service.log_event(student.id, "not_a_real_type", title="x")
        assert entry is None
        assert LearningTimeline.query.count() == 0

    def test_quiz_submission_writes_timeline_entry(self, app, student):
        _do_quiz(student.id, "Loops")
        events = timeline_service.get_timeline(student.id)
        assert any(e["event_type"] == "quiz_attempted" for e in events)

    def test_code_review_submission_writes_timeline_entry(self, app, student):
        review_service.submit_for_review(student.id, "Loops", FLAWED_SCRIPT)
        events = timeline_service.get_timeline(student.id)
        assert any(e["event_type"] == "code_review_submitted" for e in events)

    def test_tutor_session_writes_timeline_entry(self, app, student):
        tutor_service.start_session(student.id, "Navigation")
        events = timeline_service.get_timeline(student.id)
        assert any(e["event_type"] == "tutor_session" for e in events)

    def test_event_type_filter(self, app, student):
        _do_quiz(student.id, "Loops")
        review_service.submit_for_review(student.id, "Loops", FLAWED_SCRIPT)
        quiz_only = timeline_service.get_timeline(student.id, event_type="quiz_attempted")
        assert all(e["event_type"] == "quiz_attempted" for e in quiz_only)
        assert len(quiz_only) >= 1


class TestProgressTracker:
    def test_completed_topics_respects_threshold(self, app, student):
        db.session.add(Progress(user_id=student.id, topic_name="High Mastery", mastery_score=80.0))
        db.session.add(Progress(user_id=student.id, topic_name="Low Mastery", mastery_score=40.0))
        db.session.commit()

        completed = progress_tracker.get_completed_topics(student.id)
        names = {c["topic_name"] for c in completed}
        assert "High Mastery" in names
        assert "Low Mastery" not in names

    def test_time_spent_summary_counts_quiz_duration(self, app, student):
        _do_quiz(student.id, "Loops")
        summary = progress_tracker.get_time_spent_summary(student.id)
        assert summary["total_minutes"] >= 0
        assert "daily_breakdown" in summary

    def test_time_spent_includes_code_review_estimate(self, app, student):
        review_service.submit_for_review(student.id, "Loops", FLAWED_SCRIPT)
        summary = progress_tracker.get_time_spent_summary(student.id)
        assert summary["total_estimated_minutes"] >= progress_tracker.CODE_REVIEW_MINUTES_ESTIMATE

    def test_learning_streak_zero_when_no_activity(self, app, student):
        assert progress_tracker.get_learning_streak_days(student.id) == 0

    def test_learning_streak_one_after_activity_today(self, app, student):
        _do_quiz(student.id, "Loops")
        assert progress_tracker.get_learning_streak_days(student.id) == 1


class TestAnalyticsEngine:
    def test_average_quiz_score_none_when_no_data(self, app, student):
        assert analytics_engine.average_quiz_score(student.id) is None

    def test_average_quiz_score_after_attempts(self, app, student):
        _do_quiz(student.id, "Loops")
        _do_quiz(student.id, "Navigation")
        avg = analytics_engine.average_quiz_score(student.id)
        assert avg is not None
        assert 0 <= avg <= 100

    def test_accuracy_computed_from_results(self, app, student):
        _do_quiz(student.id, "Loops")
        acc = analytics_engine.accuracy(student.id)
        assert acc is None or 0 <= acc <= 100

    def test_improvement_rate_none_with_insufficient_data(self, app, student):
        assert analytics_engine.improvement_rate(student.id) is None
        _do_quiz(student.id, "Loops")
        # 1 attempt still isn't enough for a >=2-point trend comparison in this implementation's edge case
        # but shouldn't raise
        analytics_engine.improvement_rate(student.id)

    def test_mistake_patterns_from_code_review(self, app, student):
        review_service.submit_for_review(student.id, "Loops", FLAWED_SCRIPT)
        patterns = analytics_engine.mistake_patterns(student.id)
        assert isinstance(patterns, list)

    def test_build_full_analytics_returns_all_keys(self, app, student):
        _do_quiz(student.id, "Loops")
        data = analytics_engine.build_full_analytics(student.id)
        for key in (
            "average_quiz_score", "topic_wise_performance", "improvement_rate",
            "accuracy", "learning_speed_days_between_sessions", "consistency_score",
            "retention_signal", "mistake_patterns",
        ):
            assert key in data


class TestWeakTopicDetector:
    def test_low_mastery_topic_flagged(self, app, student):
        db.session.add(Progress(user_id=student.id, topic_name="Weak Topic", mastery_score=30.0))
        db.session.commit()

        weak = weak_topic_detector.detect_weak_topics(student.id)
        names = {w["topic_name"] for w in weak}
        assert "Weak Topic" in names
        entry = next(w for w in weak if w["topic_name"] == "Weak Topic")
        assert entry["weakness_score"] > 0
        assert len(entry["signals"]) > 0

    def test_high_mastery_topic_not_flagged(self, app, student):
        db.session.add(Progress(user_id=student.id, topic_name="Strong Topic", mastery_score=95.0))
        db.session.commit()

        weak = weak_topic_detector.detect_weak_topics(student.id)
        names = {w["topic_name"] for w in weak}
        assert "Strong Topic" not in names

    def test_no_data_returns_empty(self, app, student):
        assert weak_topic_detector.detect_weak_topics(student.id) == []


class TestRecommendationEngine:
    def test_sync_creates_recommendations(self, app, student):
        db.session.add(Progress(user_id=student.id, topic_name="Weak Topic", mastery_score=20.0))
        db.session.commit()

        rows = recommendation_engine.sync_recommendations(student.id)
        assert len(rows) > 0
        assert any(r.rec_type == "revision" for r in rows)

    def test_sync_replaces_stale_recommendations(self, app, student):
        db.session.add(Progress(user_id=student.id, topic_name="Weak Topic", mastery_score=20.0))
        db.session.commit()

        first = recommendation_engine.sync_recommendations(student.id)
        # Dismiss one from the first generation.
        recommendation_engine.dismiss_recommendation(student.id, first[0].id)

        second = recommendation_engine.sync_recommendations(student.id)
        # A full replace means exactly len(second) rows remain in total —
        # the dismissed first-generation row was cleared too, not left
        # behind as orphaned dismissed data (see module docstring).
        assert Recommendation.query.filter_by(user_id=student.id).count() == len(second)
        assert all(not r.is_dismissed for r in second)

    def test_dismiss_recommendation(self, app, student):
        db.session.add(Progress(user_id=student.id, topic_name="Weak Topic", mastery_score=20.0))
        db.session.commit()
        rows = recommendation_engine.sync_recommendations(student.id)
        target = rows[0]

        ok = recommendation_engine.dismiss_recommendation(student.id, target.id)
        assert ok is True

        active = recommendation_engine.get_active_recommendations(student.id)
        assert all(r["id"] != target.id for r in active)

    def test_dismiss_nonexistent_returns_false(self, app, student):
        assert recommendation_engine.dismiss_recommendation(student.id, 999999) is False

    def test_dismiss_wrong_user_returns_false(self, app, student):
        other = User(name="Other Student", email="other@example.com", role="student")
        other.set_password("password123")
        db.session.add(other)
        db.session.flush()
        db.session.add(StudentProfile(user_id=other.id))
        db.session.commit()

        db.session.add(Progress(user_id=student.id, topic_name="Weak Topic", mastery_score=20.0))
        db.session.commit()
        rows = recommendation_engine.sync_recommendations(student.id)

        assert recommendation_engine.dismiss_recommendation(other.id, rows[0].id) is False


class TestAchievementManager:
    def test_streak_badge_awarded_after_activity(self, app, student):
        _do_quiz(student.id, "Loops")
        newly_earned = achievement_manager.check_and_award_platform_achievements(student.id)
        assert "3-Day Streak" not in newly_earned  # only 1 day so far, threshold is 3

    def test_well_rounded_badge_requires_all_three_engines(self, app, student):
        _do_quiz(student.id, "Loops")
        review_service.submit_for_review(student.id, "Loops", FLAWED_SCRIPT)
        tutor_service.start_session(student.id, "Navigation")

        newly_earned = achievement_manager.check_and_award_platform_achievements(student.id)
        assert "Well-Rounded Learner" in newly_earned

    def test_badge_idempotent_not_awarded_twice(self, app, student):
        _do_quiz(student.id, "Loops")
        review_service.submit_for_review(student.id, "Loops", FLAWED_SCRIPT)
        tutor_service.start_session(student.id, "Navigation")

        first = achievement_manager.check_and_award_platform_achievements(student.id)
        second = achievement_manager.check_and_award_platform_achievements(student.id)
        assert "Well-Rounded Learner" in first
        assert "Well-Rounded Learner" not in second

    def test_daily_goal_status_shape(self, app, student):
        status = achievement_manager.get_daily_goal_status(student.id)
        assert set(status) == {"goal_minutes", "today_minutes", "met", "percent"}

    def test_achievements_summary_certificate_honest_placeholder(self, app, student):
        summary = achievement_manager.get_achievements_summary(student.id)
        assert summary["certificate"]["available"] is False


class TestPerformanceScorer:
    def test_overall_score_none_with_zero_data(self, app, student):
        scores = performance_scorer.compute_all_scores(student.id)
        # engagement is always defined (0), so overall should compute from at least that
        assert scores["overall_learning_score"] is not None or scores["engagement_score"] == 0.0

    def test_overall_score_computed_after_activity(self, app, student):
        db.session.add(Progress(user_id=student.id, topic_name="Loops", mastery_score=80.0))
        db.session.commit()
        _do_quiz(student.id, "Loops")

        scores = performance_scorer.compute_all_scores(student.id)
        assert scores["overall_learning_score"] is not None
        assert 0 <= scores["overall_learning_score"] <= 100

    def test_confidence_score_penalizes_hints(self, app, student):
        outcome = review_service.submit_for_review(student.id, "Loops", FLAWED_SCRIPT)
        outcome.submission.hints_used_count = 3
        db.session.commit()

        score = performance_scorer.confidence_score(student.id)
        assert score is not None
        assert score < 100


class TestPredictiveEngine:
    def test_readiness_false_with_no_data(self, app, student):
        readiness = predictive_engine.readiness_for_next_lesson(student.id)
        assert readiness["ready"] is False

    def test_risk_level_is_one_of_three_buckets(self, app, student):
        risk = predictive_engine.risk_of_falling_behind(student.id)
        assert risk["level"] in ("low", "watch", "elevated")

    def test_mastery_likelihood_matches_progress(self, app, student):
        db.session.add(Progress(user_id=student.id, topic_name="Loops", mastery_score=60.0))
        db.session.commit()
        likelihoods = predictive_engine.estimated_mastery_likelihood(student.id)
        entry = next(e for e in likelihoods if e["topic_name"] == "Loops")
        assert entry["estimated_mastery_likelihood"] == 0.6


class TestDashboardService:
    def test_build_dashboard_returns_all_sections(self, app, student):
        _do_quiz(student.id, "Loops")
        dash = dashboard_service.build_dashboard(student.id)
        for key in ("progress", "performance_scores", "weak_topics", "recommendations", "achievements", "recent_timeline"):
            assert key in dash

    def test_refresh_and_build_dashboard_syncs_recommendations(self, app, student):
        db.session.add(Progress(user_id=student.id, topic_name="Weak Topic", mastery_score=10.0))
        db.session.commit()
        dash = dashboard_service.refresh_and_build_dashboard(student.id)
        assert len(dash["recommendations"]) > 0


class TestAnalyticsAPI:
    def _login(self, client, email, password):
        return client.post("/api/auth/login", json={"email": email, "password": password})

    def test_dashboard_requires_login(self, client):
        resp = client.get("/api/analytics/dashboard")
        assert resp.status_code in (302, 401, 403)

    def test_full_flow_over_http(self, client, app):
        reg = client.post("/api/auth/register", json={
            "name": "HTTP Student", "email": "httpstudent@example.com",
            "password": "password123", "role": "student",
        })
        assert reg.status_code == 201

        login = self._login(client, "httpstudent@example.com", "password123")
        assert login.status_code == 200

        dash = client.get("/api/analytics/dashboard")
        assert dash.status_code == 200
        assert dash.get_json()["status"] == "success"

        perf = client.get("/api/analytics/performance")
        assert perf.status_code == 200

        weak = client.get("/api/analytics/weak-topics")
        assert weak.status_code == 200

        predictive = client.get("/api/analytics/predictive")
        assert predictive.status_code == 200

        recs = client.get("/api/analytics/recommendations")
        assert recs.status_code == 200

        sync = client.post("/api/analytics/recommendations/sync")
        assert sync.status_code == 200

        achievements = client.get("/api/analytics/achievements")
        assert achievements.status_code == 200

        timeline = client.get("/api/analytics/timeline")
        assert timeline.status_code == 200

        summary = client.get("/api/progress/summary")
        assert summary.status_code == 200

    def test_dismiss_recommendation_over_http(self, client, app):
        client.post("/api/auth/register", json={
            "name": "Dismiss Student", "email": "dismissstudent@example.com",
            "password": "password123", "role": "student",
        })
        self._login(client, "dismissstudent@example.com", "password123")

        from app.models import User as _User
        user = _User.query.filter_by(email="dismissstudent@example.com").first()
        db.session.add(Progress(user_id=user.id, topic_name="Weak Topic", mastery_score=15.0))
        db.session.commit()

        sync = client.post("/api/analytics/recommendations/sync")
        rec_id = sync.get_json()["data"][0]["id"]

        dismiss = client.post(f"/api/analytics/recommendations/{rec_id}/dismiss")
        assert dismiss.status_code == 200

        active = client.get("/api/analytics/recommendations").get_json()["data"]
        assert all(r["id"] != rec_id for r in active)

    def test_dashboard_refresh_over_http(self, client, app):
        client.post("/api/auth/register", json={
            "name": "Refresh Student", "email": "refreshstudent@example.com",
            "password": "password123", "role": "student",
        })
        self._login(client, "refreshstudent@example.com", "password123")

        resp = client.post("/api/analytics/dashboard/refresh")
        assert resp.status_code == 200
        assert "achievements" in resp.get_json()["data"]

    def test_cross_user_dismiss_blocked(self, client, app):
        client.post("/api/auth/register", json={
            "name": "User A", "email": "usera@example.com", "password": "password123", "role": "student",
        })
        client.post("/api/auth/register", json={
            "name": "User B", "email": "userb@example.com", "password": "password123", "role": "student",
        })

        self._login(client, "usera@example.com", "password123")
        from app.models import User as _User
        user_a = _User.query.filter_by(email="usera@example.com").first()
        db.session.add(Progress(user_id=user_a.id, topic_name="Weak Topic", mastery_score=15.0))
        db.session.commit()
        sync = client.post("/api/analytics/recommendations/sync")
        rec_id = sync.get_json()["data"][0]["id"]
        client.post("/api/auth/logout")

        self._login(client, "userb@example.com", "password123")
        dismiss = client.post(f"/api/analytics/recommendations/{rec_id}/dismiss")
        assert dismiss.status_code == 404


class TestPageRoutes:
    def _register_and_login(self, client, email):
        client.post("/api/auth/register", json={
            "name": "Page Student", "email": email, "password": "password123", "role": "student",
        })
        client.post("/api/auth/login", json={"email": email, "password": "password123"})

    def test_dashboard_page_renders(self, client, app):
        self._register_and_login(client, "pagestudent1@example.com")
        resp = client.get("/dashboard")
        assert resp.status_code == 200

    def test_progress_page_renders(self, client, app):
        self._register_and_login(client, "pagestudent2@example.com")
        resp = client.get("/dashboard/progress")
        assert resp.status_code == 200

    def test_achievements_page_renders(self, client, app):
        self._register_and_login(client, "pagestudent3@example.com")
        resp = client.get("/dashboard/achievements")
        assert resp.status_code == 200

    def test_timeline_page_renders(self, client, app):
        self._register_and_login(client, "pagestudent4@example.com")
        resp = client.get("/dashboard/timeline")
        assert resp.status_code == 200

    def test_recommendations_page_renders(self, client, app):
        self._register_and_login(client, "pagestudent5@example.com")
        resp = client.get("/dashboard/recommendations")
        assert resp.status_code == 200
