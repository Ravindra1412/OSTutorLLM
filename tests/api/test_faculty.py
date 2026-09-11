"""
tests/test_faculty.py

Part 3.10 test suite. Follows the same integration-testing philosophy
as test_analytics.py (Part 3.9): exercises the real service functions
and the real Flask test client against real HTTP routes, rather than
mocking the layers underneath.
"""

import pytest
from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models import (
    User, StudentProfile, FacultyProfile, Topic, Lesson, Quiz, Assignment,
    AssignmentSubmission, ContentResource, SystemConfiguration,
)
from app.utils.constants import ROLE_STUDENT, ROLE_FACULTY
from app.quiz.services import quiz_service
from app.code_review.services import review_service
from app.ai.services import tutor_service
from app.faculty.services import (
    dashboard_overview, student_management, class_analytics, content_management,
    quiz_management, assignment_management, ai_tutor_management, code_review_monitoring,
    reports_service, notification_service, settings_service, faculty_profile_service,
)

FLAWED_SCRIPT = "for f in *.txt\n  do cat $f\ndone\nx=5\n"


@pytest.fixture()
def student(app):
    user = User(name="Faculty-Test Student", email="fstudent@example.com", role=ROLE_STUDENT)
    user.set_password("password123")
    db.session.add(user)
    db.session.flush()
    db.session.add(StudentProfile(user_id=user.id))
    db.session.commit()
    return user


@pytest.fixture()
def faculty(app):
    user = User(name="Dr. Faculty", email="faculty@example.com", role=ROLE_FACULTY)
    user.set_password("password123")
    db.session.add(user)
    db.session.flush()
    db.session.add(FacultyProfile(user_id=user.id, department="CS"))
    db.session.commit()
    return user


@pytest.fixture()
def topic(app):
    t = Topic(name="Loops", category="Shell Programming", description="For/while loops", difficulty_level=2)
    db.session.add(t)
    db.session.commit()
    return t


class TestDashboardOverview:
    def test_overview_empty_platform(self, app, faculty):
        overview = dashboard_overview.get_overview(faculty.id)
        assert overview["total_students"] == 0
        assert overview["system_health"]["database"] == "connected"

    def test_overview_counts_students(self, app, faculty, student):
        overview = dashboard_overview.get_overview(faculty.id)
        assert overview["total_students"] == 1


class TestStudentManagement:
    def test_list_students_search(self, app, student):
        result = student_management.list_students(search="Faculty-Test")
        assert result["total"] == 1
        result_none = student_management.list_students(search="Nonexistent")
        assert result_none["total"] == 0

    def test_get_student_detail_reuses_part39_services(self, app, student):
        detail = student_management.get_student_detail(student.id)
        assert detail is not None
        assert "performance_scores" in detail
        assert "analytics" in detail

    def test_get_student_detail_unknown_returns_none(self, app):
        assert student_management.get_student_detail(999999) is None


class TestClassAnalytics:
    def test_weak_and_strong_topics(self, app, student):
        from app.models import Progress
        db.session.add(Progress(user_id=student.id, topic_name="Weak Topic", mastery_score=30.0))
        db.session.add(Progress(user_id=student.id, topic_name="Strong Topic", mastery_score=90.0))
        db.session.commit()

        result = class_analytics.weak_and_strong_topics()
        weak_names = {t["topic_name"] for t in result["weak_topics"]}
        strong_names = {t["topic_name"] for t in result["strong_topics"]}
        assert "Weak Topic" in weak_names
        assert "Strong Topic" in strong_names

    def test_quiz_statistics_empty(self, app):
        stats = class_analytics.quiz_statistics()
        assert stats["attempt_count"] == 0
        assert stats["average"] is None


class TestContentManagement:
    def test_create_and_list_topics(self, app):
        content_management.create_topic("New Topic", "OS", "desc", 1)
        topics = content_management.list_topics()
        assert any(t.name == "New Topic" for t in topics)

    def test_duplicate_topic_name_rejected(self, app, topic):
        with pytest.raises(content_management.ContentError):
            content_management.create_topic("Loops", "X", "desc", 1)

    def test_update_topic_creates_revision_and_restore_works(self, app, faculty, topic):
        original_name = topic.name
        content_management.update_topic(topic.id, faculty.id, name="Renamed Loops")
        assert db.session.get(Topic, topic.id).name == "Renamed Loops"

        revisions = content_management.get_revisions("topic", topic.id)
        assert len(revisions) == 1
        assert revisions[0]["snapshot"]["name"] == original_name

        ok = content_management.restore_revision(revisions[0]["id"])
        assert ok is True
        assert db.session.get(Topic, topic.id).name == original_name

    def test_delete_topic(self, app, topic):
        assert content_management.delete_topic(topic.id) is True
        assert content_management.delete_topic(topic.id) is False  # already gone

    def test_create_lesson_requires_valid_topic(self, app):
        with pytest.raises(content_management.ContentError):
            content_management.create_lesson(999999, "Title", "Summary", 0)

    def test_lesson_crud_and_revision(self, app, faculty, topic):
        lesson = content_management.create_lesson(topic.id, "Intro", "Summary text", 0)
        content_management.update_lesson(lesson.id, faculty.id, title="Intro Updated")
        revisions = content_management.get_revisions("lesson", lesson.id)
        assert len(revisions) == 1
        assert content_management.delete_lesson(lesson.id) is True

    def test_command_and_shell_program_crud(self, app, topic):
        cmd = content_management.create_command("ls", "ls [options]", "List files", "navigation", topic.id)
        assert content_management.delete_command(cmd.id) is True

        program = content_management.create_shell_program(topic.id, "Loop Example", "desc", "for i in 1 2 3; do echo $i; done", 1)
        assert content_management.delete_shell_program(program.id) is True


class TestQuizManagement:
    def test_create_quiz_with_questions(self, app, faculty, topic):
        quiz = quiz_management.create_quiz(
            created_by_user_id=faculty.id, topic_id=topic.id, title="Faculty Quiz",
            difficulty_level=1,
            questions=[{"question_text": "2+2?", "question_type": "mcq", "options": ["3", "4"], "correct_answer": "4"}],
            is_published=True,
        )
        assert quiz.id is not None
        assert quiz.is_published is True
        assert len(quiz.questions) == 1

    def test_create_quiz_no_questions_rejected(self, app, faculty, topic):
        with pytest.raises(quiz_management.QuizManagementError):
            quiz_management.create_quiz(faculty.id, topic.id, "Empty Quiz", 1, questions=[])

    def test_create_quiz_invalid_question_type_rejected(self, app, faculty, topic):
        with pytest.raises(quiz_management.QuizManagementError):
            quiz_management.create_quiz(
                faculty.id, topic.id, "Bad Quiz", 1,
                questions=[{"question_text": "?", "question_type": "not_a_type", "correct_answer": "x"}],
            )

    def test_student_can_attempt_authored_quiz_end_to_end(self, app, faculty, topic, student):
        """Real end-to-end: faculty authors a quiz with a known correct
        answer, publishes it, student attempts it via the NEW
        start_authored_quiz path, answers correctly, and the existing
        (unmodified) submit_quiz/evaluation pipeline grades it."""
        quiz = quiz_management.create_quiz(
            created_by_user_id=faculty.id, topic_id=topic.id, title="Authored Quiz", difficulty_level=1,
            questions=[{"question_text": "2+2?", "question_type": "mcq", "options": ["3", "4"], "correct_answer": "4"}],
            is_published=True,
        )
        start_result = quiz_service.start_authored_quiz(student.id, quiz.id)
        assert start_result.quiz.id == quiz.id

        question = start_result.quiz.questions[0]
        quiz_service.submit_answer(student.id, start_result.attempt.id, question.id, "4")
        result = quiz_service.submit_quiz(student.id, start_result.attempt.id)
        assert result["score_percent"] == 100.0

    def test_unpublished_quiz_cannot_be_attempted(self, app, faculty, topic, student):
        quiz = quiz_management.create_quiz(
            faculty.id, topic.id, "Draft Quiz", 1,
            questions=[{"question_text": "?", "question_type": "mcq", "options": ["a"], "correct_answer": "a"}],
            is_published=False,
        )
        with pytest.raises(ValueError):
            quiz_service.start_authored_quiz(student.id, quiz.id)

    def test_scheduled_future_quiz_cannot_be_attempted_yet(self, app, faculty, topic, student):
        future = datetime.now(timezone.utc) + timedelta(days=1)
        quiz = quiz_management.create_quiz(
            faculty.id, topic.id, "Scheduled Quiz", 1,
            questions=[{"question_text": "?", "question_type": "mcq", "options": ["a"], "correct_answer": "a"}],
            is_published=True, scheduled_at=future,
        )
        with pytest.raises(ValueError):
            quiz_service.start_authored_quiz(student.id, quiz.id)

    def test_get_quiz_results(self, app, faculty, topic, student):
        quiz = quiz_management.create_quiz(
            faculty.id, topic.id, "Results Quiz", 1,
            questions=[{"question_text": "2+2?", "question_type": "mcq", "options": ["3", "4"], "correct_answer": "4"}],
            is_published=True,
        )
        start_result = quiz_service.start_authored_quiz(student.id, quiz.id)
        quiz_service.submit_answer(student.id, start_result.attempt.id, start_result.quiz.questions[0].id, "4")
        quiz_service.submit_quiz(student.id, start_result.attempt.id)

        results = quiz_management.get_quiz_results(quiz.id)
        assert len(results["results"]) == 1
        assert results["results"][0]["score_percent"] == 100.0

    def test_dynamically_generated_quizzes_unaffected(self, app, student, topic):
        """Regression guard: the existing per-attempt Quiz Engine
        (Part 3.7) must work completely unchanged."""
        result = quiz_service.start_quiz(student.id, topic_name="Loops", question_count=1)
        assert result.quiz.created_by_user_id is None
        assert result.quiz.is_published is True  # model default, doesn't break dynamic quizzes


class TestAssignmentManagement:
    def test_create_and_list_assignments(self, app, faculty, topic):
        due = datetime.now(timezone.utc) + timedelta(days=7)
        assignment_management.create_assignment(faculty.id, topic.id, "HW1", "Do the thing", due, is_published=True)
        assignments = assignment_management.list_assignments(published_only=True)
        assert len(assignments) == 1

    def test_grade_submission_and_analytics(self, app, faculty, student, topic):
        due = datetime.now(timezone.utc) + timedelta(days=1)
        assignment = assignment_management.create_assignment(faculty.id, topic.id, "HW2", "desc", due, is_published=True)
        db.session.add(AssignmentSubmission(
            assignment_id=assignment.id, user_id=student.id, submission_text="my answer",
            submitted_at=datetime.now(timezone.utc), is_late=False,
        ))
        db.session.commit()

        submissions = assignment_management.get_submissions(assignment.id)
        assert len(submissions["submissions"]) == 1

        sub_id = submissions["submissions"][0]["id"]
        graded = assignment_management.grade_submission(sub_id, faculty.id, 95.0, "Great work")
        assert graded.score == 95.0

        analytics = assignment_management.assignment_analytics(assignment.id)
        assert analytics["submission_count"] == 1
        assert analytics["average_score"] == 95.0

    def test_delete_assignment(self, app, faculty, topic):
        due = datetime.now(timezone.utc) + timedelta(days=1)
        assignment = assignment_management.create_assignment(faculty.id, topic.id, "HW3", "desc", due)
        assert assignment_management.delete_assignment(assignment.id) is True


class TestAssignmentStudentFlow:
    def test_late_submission_flagged_correctly(self, app, faculty, student, topic, client):
        past_due = datetime.now(timezone.utc) - timedelta(hours=1)
        assignment = assignment_management.create_assignment(
            faculty.id, topic.id, "Overdue HW", "desc", past_due, allow_late_submission=True, is_published=True,
        )
        client.post("/api/auth/login", json={"email": student.email, "password": "password123"})
        resp = client.post(f"/api/assignments/{assignment.id}/submit", json={"submission_text": "late answer"})
        assert resp.status_code == 201

        submission = AssignmentSubmission.query.filter_by(assignment_id=assignment.id, user_id=student.id).first()
        assert submission.is_late is True

    def test_late_submission_blocked_when_not_allowed(self, app, faculty, student, topic, client):
        past_due = datetime.now(timezone.utc) - timedelta(hours=1)
        assignment = assignment_management.create_assignment(
            faculty.id, topic.id, "Strict HW", "desc", past_due, allow_late_submission=False, is_published=True,
        )
        client.post("/api/auth/login", json={"email": student.email, "password": "password123"})
        resp = client.post(f"/api/assignments/{assignment.id}/submit", json={"submission_text": "too late"})
        assert resp.status_code == 400


class TestAITutorManagement:
    def test_default_teaching_mode_is_valid(self, app):
        from app.ai.services.teaching_modes import is_valid_mode
        settings = ai_tutor_management.get_ai_settings()
        assert is_valid_mode(settings["default_teaching_mode"])

    def test_invalid_teaching_mode_rejected(self, app):
        with pytest.raises(ValueError):
            ai_tutor_management.update_ai_settings(default_teaching_mode="not_a_real_mode")

    def test_disabling_ai_tutor_blocks_new_sessions(self, app, student):
        ai_tutor_management.update_ai_settings(ai_tutor_enabled=False)
        with pytest.raises(ValueError):
            tutor_service.start_session(student.id, "Navigation")

        ai_tutor_management.update_ai_settings(ai_tutor_enabled=True)
        session, _ = tutor_service.start_session(student.id, "Navigation")
        assert session.id is not None

    def test_prompt_template_view_and_edit_roundtrip(self, app, tmp_path, monkeypatch):
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "test_prompt.txt").write_text("original content")
        monkeypatch.setattr(ai_tutor_management, "TEMPLATES_DIR", str(template_dir))

        assert "test_prompt.txt" in ai_tutor_management.list_prompt_templates()
        assert ai_tutor_management.get_prompt_template("test_prompt.txt") == "original content"

        ai_tutor_management.update_prompt_template("test_prompt.txt", "new content")
        assert ai_tutor_management.get_prompt_template("test_prompt.txt") == "new content"
        backups = [f for f in template_dir.iterdir() if f.name.endswith(".bak")]
        assert len(backups) == 1

    def test_path_traversal_blocked(self, app):
        with pytest.raises(ValueError):
            ai_tutor_management.get_prompt_template("../../etc/passwd")


class TestCodeReviewMonitoring:
    def test_common_mistakes_from_real_submission(self, app, student):
        review_service.submit_for_review(student.id, "Loops", FLAWED_SCRIPT)
        mistakes = code_review_monitoring.common_mistakes()
        assert isinstance(mistakes, list)

    def test_review_history(self, app, student):
        review_service.submit_for_review(student.id, "Loops", FLAWED_SCRIPT)
        history = code_review_monitoring.review_history()
        assert len(history) == 1
        assert history[0]["student_name"] == student.name


class TestReportsService:
    def test_class_performance_report_shape(self, app, student):
        from app.models import Progress
        db.session.add(Progress(user_id=student.id, topic_name="Loops", mastery_score=70.0))
        db.session.commit()
        report = reports_service.generate_class_performance_report()
        assert report["columns"] == ["Topic", "Average Mastery %", "Students Tracking"]
        assert len(report["rows"]) == 1

    def test_csv_export_roundtrip(self, app):
        report = {"title": "Test", "columns": ["A", "B"], "rows": [[1, 2], [3, 4]]}
        buf = reports_service.to_csv(report)
        content = buf.read().decode("utf-8")
        assert "Test" in content and "A,B" in content

    def test_excel_export_produces_valid_file(self, app):
        report = {"title": "Test", "columns": ["A", "B"], "rows": [[1, 2]]}
        buf = reports_service.to_excel(report)
        assert buf.read(2) == b"PK"  # xlsx is a zip archive

    def test_pdf_export_produces_valid_file(self, app):
        report = {"title": "Test", "columns": ["A", "B"], "rows": [[1, 2]]}
        buf = reports_service.to_pdf(report)
        assert buf.read(4) == b"%PDF"

    def test_student_progress_report_unknown_student_raises(self, app):
        with pytest.raises(ValueError):
            reports_service.generate_student_progress_report(999999)


class TestNotificationService:
    def test_announcement_reaches_all_students(self, app, student):
        count = notification_service.send_announcement("Test announcement")
        assert count == 1
        from app.models import Notification
        notif = Notification.query.filter_by(user_id=student.id).first()
        assert notif is not None
        assert notif.message == "Test announcement"

    def test_student_alert_unknown_student_raises(self, app):
        with pytest.raises(ValueError):
            notification_service.send_student_alert(999999, "hi")

    def test_assignment_reminder_only_pending(self, app, faculty, student, topic):
        due = datetime.now(timezone.utc) + timedelta(days=1)
        assignment = assignment_management.create_assignment(faculty.id, topic.id, "HW", "desc", due, is_published=True)
        count = notification_service.send_assignment_reminder(assignment.id)
        assert count == 1  # student hasn't submitted

        db.session.add(AssignmentSubmission(
            assignment_id=assignment.id, user_id=student.id, submission_text="done",
            submitted_at=datetime.now(timezone.utc), is_late=False,
        ))
        db.session.commit()
        count_after = notification_service.send_assignment_reminder(assignment.id)
        assert count_after == 0  # now submitted, no longer pending


class TestSettingsService:
    def test_backup_unsupported_for_in_memory_db(self, app):
        settings = settings_service.get_backup_settings()
        assert settings["supported"] is False

    def test_trigger_backup_raises_for_in_memory_db(self, app):
        with pytest.raises(ValueError):
            settings_service.trigger_backup()

    def test_security_settings_shape(self, app):
        settings = settings_service.get_security_settings()
        assert "min_password_length" in settings


class TestFacultyProfileService:
    def test_update_and_get_profile(self, app, faculty):
        faculty_profile_service.update_profile(faculty.id, department="Mathematics", title="Professor")
        profile = faculty_profile_service.get_profile(faculty.id)
        assert profile["department"] == "Mathematics"
        assert profile["title"] == "Professor"

    def test_get_profile_rejects_student(self, app, student):
        assert faculty_profile_service.get_profile(student.id) is None


class TestFacultyAPIPermissions:
    def _login(self, client, email):
        return client.post("/api/auth/login", json={"email": email, "password": "password123"})

    def test_student_blocked_from_faculty_dashboard(self, app, client, student):
        self._login(client, student.email)
        resp = client.get("/api/faculty/dashboard")
        assert resp.status_code == 403

    def test_faculty_can_access_dashboard(self, app, client, faculty):
        self._login(client, faculty.email)
        resp = client.get("/api/faculty/dashboard")
        assert resp.status_code == 200

    def test_unauthenticated_blocked(self, client):
        resp = client.get("/api/faculty/dashboard")
        assert resp.status_code in (302, 401)


class TestFacultyFullHTTPFlow:
    def _login(self, client, email):
        return client.post("/api/auth/login", json={"email": email, "password": "password123"})

    def test_end_to_end_faculty_workflow(self, app, client, faculty, student):
        self._login(client, faculty.email)

        topic_resp = client.post("/api/faculty/content/topics", json={
            "name": "Http Topic", "category": "OS", "description": "d", "difficulty_level": 1,
        })
        assert topic_resp.status_code == 201
        topic_id = topic_resp.get_json()["data"]["id"]

        quiz_resp = client.post("/api/faculty/quizzes", json={
            "topic_id": topic_id, "title": "Http Quiz", "difficulty_level": 1, "is_published": True,
            "questions": [{"question_text": "2+2?", "question_type": "mcq", "options": ["3", "4"], "correct_answer": "4"}],
        })
        assert quiz_resp.status_code == 201
        quiz_id = quiz_resp.get_json()["data"]["id"]

        assignment_resp = client.post("/api/faculty/assignments", json={
            "topic_id": topic_id, "title": "Http HW", "description": "d",
            "due_at": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(), "is_published": True,
        })
        assert assignment_resp.status_code == 201

        analytics_resp = client.get("/api/faculty/analytics/class")
        assert analytics_resp.status_code == 200

        students_resp = client.get("/api/faculty/students")
        assert students_resp.status_code == 200
        assert students_resp.get_json()["data"]["total"] == 1

        report_resp = client.get("/api/faculty/reports/class-performance?format=csv")
        assert report_resp.status_code == 200
        assert report_resp.mimetype == "text/csv"

        client.post("/api/auth/logout")

        # Student attempts the authored quiz
        self._login(client, student.email)
        start_resp = client.post(f"/api/quiz/authored/{quiz_id}/start")
        assert start_resp.status_code == 201

        assignments_resp = client.get("/api/assignments")
        assert assignments_resp.status_code == 200
        assert len(assignments_resp.get_json()["data"]) == 1


class TestFacultyPageRoutes:
    def _login(self, client, email):
        return client.post("/api/auth/login", json={"email": email, "password": "password123"})

    @pytest.mark.parametrize("path", [
        "/faculty", "/faculty/students", "/faculty/analytics", "/faculty/content",
        "/faculty/quizzes", "/faculty/assignments", "/faculty/reports",
        "/faculty/notifications", "/faculty/profile", "/faculty/settings",
    ])
    def test_pages_render_for_faculty(self, app, client, faculty, path):
        self._login(client, faculty.email)
        resp = client.get(path)
        assert resp.status_code == 200

    def test_student_blocked_from_faculty_pages(self, app, client, student):
        self._login(client, student.email)
        resp = client.get("/faculty")
        assert resp.status_code == 403
