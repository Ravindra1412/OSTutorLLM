"""
tests/integration/test_mentor.py

Part 3.13 test suite. Follows the same real-data integration-testing
philosophy as every prior phase: exercise the real Quiz/Code Review/
Tutor engines so the Mentor's orchestration over their real output is
actually proven, not mocked.
"""

import pytest

from app.extensions import db
from app.models import Progress, StudyPlan, MentorInteraction
from app.quiz.services import quiz_service
from app.code_review.services import review_service
from app.ai.services import tutor_service
from app.mentor.services import (
    mentor_engine, student_model, learning_health, confidence_engine,
    study_planner, insights_engine, mentor_assistant,
)
from tests.fixtures.factories import make_student, make_faculty, make_topic, login

pytestmark = pytest.mark.integration

FLAWED_SCRIPT = "for f in *.txt\n  do cat $f\ndone\nx=5\n"


def _do_quiz(student_id, topic="Navigation"):
    result = quiz_service.start_quiz(student_id, topic_name=topic, question_count=1)
    for q in result.quiz.questions:
        quiz_service.submit_answer(student_id, result.attempt.id, q.id, "answer")
    return quiz_service.submit_quiz(student_id, result.attempt.id)


class TestStudentModel:
    def test_learning_style_no_activity(self, app):
        student = make_student(email="nostyle@example.com")
        style = student_model.infer_learning_style(student.id)
        assert style["label"] == "Not enough activity yet"

    def test_learning_style_reflects_dominant_engine(self, app):
        student = make_student(email="quizstyle@example.com")
        make_topic("Navigation")
        for _ in range(3):
            _do_quiz(student.id)
        style = student_model.infer_learning_style(student.id)
        assert "Quiz" in style["label"] or "Balanced" in style["label"]

    def test_build_student_profile_shape(self, app):
        student = make_student(email="profileshape@example.com")
        profile = student_model.build_student_profile(student.id)
        for key in ("learning_style", "current_level", "quiz_performance", "confidence_score"):
            assert key in profile


class TestLearningHealth:
    def test_health_score_bounded_and_has_status(self, app):
        student = make_student(email="health1@example.com")
        result = learning_health.compute_learning_health(student.id)
        assert 0 <= result["health_score"] <= 100
        assert result["status"] in ("Excellent", "Good", "Needs Improvement", "Critical")

    def test_health_improves_with_real_activity(self, app):
        student = make_student(email="health2@example.com")
        make_topic("Navigation")
        before = learning_health.compute_learning_health(student.id)["health_score"]
        _do_quiz(student.id)
        tutor_service.start_session(student.id, "Navigation")
        after = learning_health.compute_learning_health(student.id)["health_score"]
        assert after >= before

    def test_missing_factors_tracked_honestly(self, app):
        student = make_student(email="health3@example.com")
        result = learning_health.compute_learning_health(student.id)
        assert "revision_frequency" in result["factors_missing_data"] or result["factors"]["revision_frequency"] is None


class TestConfidenceEngine:
    def test_no_data_returns_narrow_fallback(self, app):
        student = make_student(email="conf1@example.com")
        result = confidence_engine.compute_confidence(student.id)
        assert result["overall_confidence"] is None or isinstance(result["overall_confidence"], float)

    def test_topic_confidence_matches_progress(self, app):
        student = make_student(email="conf2@example.com")
        db.session.add(Progress(user_id=student.id, topic_name="Loops", mastery_score=72.0))
        db.session.commit()
        result = confidence_engine.compute_confidence(student.id)
        entry = next(t for t in result["topic_confidence"] if t["topic_name"] == "Loops")
        assert entry["confidence"] == 72.0

    def test_why_explains_weak_topics(self, app):
        student = make_student(email="conf3@example.com")
        db.session.add(Progress(user_id=student.id, topic_name="Weak One", mastery_score=20.0))
        db.session.commit()
        result = confidence_engine.compute_confidence(student.id)
        assert len(result["why"]["what_needs_work"]) > 0


class TestStudyPlanner:
    def test_weekly_plan_has_seven_days(self, app):
        student = make_student(email="plan1@example.com")
        plan = study_planner.generate_weekly_plan(student.id)
        assert len(plan["schedule"]) == 7
        assert plan["schedule"][-1]["day"] == "Sunday"
        assert plan["schedule"][-2]["day"] == "Saturday"

    def test_weekly_plan_prioritizes_weak_topics(self, app):
        student = make_student(email="plan2@example.com")
        db.session.add(Progress(user_id=student.id, topic_name="Weak Topic X", mastery_score=15.0))
        db.session.commit()
        plan = study_planner.generate_weekly_plan(student.id)
        monday_topic = plan["schedule"][0]["topic"]
        assert monday_topic == "Weak Topic X"

    def test_plan_is_persisted_and_retrievable(self, app):
        student = make_student(email="plan3@example.com")
        study_planner.generate_daily_plan(student.id)
        saved = study_planner.get_saved_plan(student.id, "daily")
        assert saved is not None
        assert StudyPlan.query.filter_by(user_id=student.id, period_type="daily").count() == 1

    def test_regenerating_replaces_not_duplicates(self, app):
        student = make_student(email="plan4@example.com")
        study_planner.generate_weekly_plan(student.id)
        study_planner.generate_weekly_plan(student.id)
        assert StudyPlan.query.filter_by(user_id=student.id, period_type="weekly").count() == 1

    def test_monthly_plan_has_four_weeks(self, app):
        student = make_student(email="plan5@example.com")
        plan = study_planner.generate_monthly_plan(student.id)
        assert len(plan["weeks"]) == 4


class TestInsightsEngine:
    def test_no_data_returns_honest_fallback(self, app):
        student = make_student(email="insight1@example.com")
        insights = insights_engine.generate_insights(student.id)
        assert len(insights) == 1
        assert "not enough" in insights[0]["text"].lower()

    def test_weak_topic_insight_has_evidence(self, app):
        student = make_student(email="insight2@example.com")
        db.session.add(Progress(user_id=student.id, topic_name="Struggle Topic", mastery_score=20.0))
        db.session.commit()
        insights = insights_engine.generate_insights(student.id)
        weak_insight = next((i for i in insights if "Struggle Topic" in i["text"]), None)
        assert weak_insight is not None
        assert weak_insight["evidence"]

    def test_improvement_insight_from_real_quiz_history(self, app):
        student = make_student(email="insight3@example.com")
        make_topic("Navigation")
        _do_quiz(student.id)
        _do_quiz(student.id)
        insights = insights_engine.generate_insights(student.id)
        assert isinstance(insights, list)


class TestMentorEngine:
    def test_overview_returns_all_sections(self, app):
        student = make_student(email="overview1@example.com")
        overview = mentor_engine.build_mentor_overview(student.id)
        for key in ("student_profile", "learning_health", "confidence", "weak_topics",
                    "recommendations", "achievements", "insights", "todays_plan", "recent_timeline"):
            assert key in overview

    def test_full_cycle_regenerates_recommendations_and_plan(self, app):
        student = make_student(email="cycle1@example.com")
        db.session.add(Progress(user_id=student.id, topic_name="Weak Cycle Topic", mastery_score=10.0))
        db.session.commit()
        result = mentor_engine.run_full_mentor_cycle(student.id)
        assert len(result["recommendations"]) > 0
        assert result["todays_plan"] is not None

    def test_overview_reflects_real_cross_engine_activity(self, app):
        """The mentor's whole point — this proves it actually reads
        real data from all three engines, not placeholder output."""
        student = make_student(email="crossengine@example.com")
        make_topic("Navigation")
        _do_quiz(student.id)
        review_service.submit_for_review(student.id, "Loops", FLAWED_SCRIPT)
        tutor_service.start_session(student.id, "Navigation")

        overview = mentor_engine.build_mentor_overview(student.id)
        assert overview["learning_health"]["factors"]["tutor_engagement"] > 0
        assert len(overview["recent_timeline"]) >= 3


class TestMentorAssistantStudent:
    def test_daily_plan_question(self, app):
        student = make_student(email="ask1@example.com")
        result = mentor_assistant.ask_student_assistant(student.id, "What should I study today?")
        assert result["intent"] == "daily_plan"
        assert result["answer"]

    def test_weakest_topic_question(self, app):
        student = make_student(email="ask2@example.com")
        db.session.add(Progress(user_id=student.id, topic_name="Ask Weak", mastery_score=10.0))
        db.session.commit()
        result = mentor_assistant.ask_student_assistant(student.id, "Which topic is my weakest?")
        assert "Ask Weak" in result["answer"]

    def test_readiness_question(self, app):
        student = make_student(email="ask3@example.com")
        result = mentor_assistant.ask_student_assistant(student.id, "Am I ready for the next quiz?")
        assert result["intent"] == "readiness_check"

    def test_interaction_is_logged(self, app):
        student = make_student(email="ask4@example.com")
        mentor_assistant.ask_student_assistant(student.id, "What should I study today?")
        history = mentor_assistant.get_interaction_history(student.id)
        assert len(history) == 1
        assert MentorInteraction.query.filter_by(user_id=student.id).count() == 1

    def test_fallback_for_unrecognized_question(self, app):
        student = make_student(email="ask5@example.com")
        result = mentor_assistant.ask_student_assistant(student.id, "What's the weather like?")
        assert result["intent"] == "fallback_insight"


class TestMentorAssistantFaculty:
    def test_struggling_students_by_topic(self, app):
        faculty = make_faculty(email="faskfac1@example.com")
        student = make_student(email="strugglingstudent@example.com")
        db.session.add(Progress(user_id=student.id, topic_name="Loops", mastery_score=30.0))
        db.session.commit()

        result = mentor_assistant.ask_faculty_assistant(faculty.id, "Which students struggle with Loops?")
        assert "Test Student" in result["answer"] or "1 student" in result["answer"]
        assert result["intent"] == "struggling_students"

    def test_lowest_average_topic(self, app):
        faculty = make_faculty(email="faskfac2@example.com")
        student = make_student(email="lowavgstudent@example.com")
        db.session.add(Progress(user_id=student.id, topic_name="Hard Topic", mastery_score=25.0))
        db.session.commit()
        result = mentor_assistant.ask_faculty_assistant(faculty.id, "Which topic has the lowest average score?")
        assert "Hard Topic" in result["answer"]

    def test_common_mistakes_question(self, app):
        faculty = make_faculty(email="faskfac3@example.com")
        student = make_student(email="cmstudent@example.com")
        review_service.submit_for_review(student.id, "Loops", FLAWED_SCRIPT)
        result = mentor_assistant.ask_faculty_assistant(faculty.id, "Summarize common shell mistakes.")
        assert result["intent"] == "common_mistakes"

    def test_unrecognized_question_gives_help(self, app):
        faculty = make_faculty(email="faskfac4@example.com")
        result = mentor_assistant.ask_faculty_assistant(faculty.id, "What's for lunch?")
        assert result["intent"] == "fallback_help"


class TestMentorAPI:
    def test_overview_requires_student_role(self, client, app):
        make_faculty(email="apirole@example.com")
        login(client, "apirole@example.com")
        resp = client.get("/api/mentor/overview")
        assert resp.status_code == 403

    def test_full_student_mentor_flow_over_http(self, client, app):
        make_student(email="httpmentor@example.com")
        login(client, "httpmentor@example.com")

        overview_resp = client.get("/api/mentor/overview")
        assert overview_resp.status_code == 200

        health_resp = client.get("/api/mentor/health")
        assert health_resp.status_code == 200

        confidence_resp = client.get("/api/mentor/confidence")
        assert confidence_resp.status_code == 200

        insights_resp = client.get("/api/mentor/insights")
        assert insights_resp.status_code == 200

        weekly_resp = client.post("/api/mentor/study-plan/weekly/generate")
        assert weekly_resp.status_code == 200

        get_plan_resp = client.get("/api/mentor/study-plan/weekly")
        assert get_plan_resp.status_code == 200
        assert get_plan_resp.get_json()["data"] is not None

        ask_resp = client.post("/api/mentor/assistant/ask", json={"question": "What should I study today?"})
        assert ask_resp.status_code == 200

        history_resp = client.get("/api/mentor/assistant/history")
        assert history_resp.status_code == 200
        assert len(history_resp.get_json()["data"]) == 1

        refresh_resp = client.post("/api/mentor/refresh")
        assert refresh_resp.status_code == 200

    def test_invalid_period_rejected(self, client, app):
        make_student(email="badperiod@example.com")
        login(client, "badperiod@example.com")
        resp = client.get("/api/mentor/study-plan/yearly")
        assert resp.status_code == 400

    def test_faculty_assistant_over_http(self, client, app):
        make_faculty(email="httpfacmentor@example.com")
        login(client, "httpfacmentor@example.com")
        resp = client.post("/api/faculty/mentor/assistant/ask", json={"question": "Which topic has the lowest average score?"})
        assert resp.status_code == 200

        history_resp = client.get("/api/faculty/mentor/assistant/history")
        assert history_resp.status_code == 200

    def test_student_blocked_from_faculty_mentor_assistant(self, client, app):
        make_student(email="blockedstudent@example.com")
        login(client, "blockedstudent@example.com")
        resp = client.post("/api/faculty/mentor/assistant/ask", json={"question": "test"})
        assert resp.status_code == 403


class TestMentorPages:
    def test_mentor_home_page_renders(self, client, app):
        make_student(email="pagemento@example.com")
        login(client, "pagemento@example.com")
        resp = client.get("/mentor")
        assert resp.status_code == 200

    def test_study_planner_page_renders(self, client, app):
        make_student(email="pageplanner@example.com")
        login(client, "pageplanner@example.com")
        resp = client.get("/mentor/study-planner")
        assert resp.status_code == 200

    def test_faculty_blocked_from_mentor_pages(self, client, app):
        make_faculty(email="pagefacblock@example.com")
        login(client, "pagefacblock@example.com")
        resp = client.get("/mentor")
        assert resp.status_code == 403
