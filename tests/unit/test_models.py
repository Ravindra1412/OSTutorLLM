"""
tests/test_models.py

Database layer test suite (Part 3.4, Section 19): CRUD, relationships,
constraint/validation enforcement, and db_helpers behavior. Runs against
the in-memory SQLite TestingConfig database (see tests/conftest.py) —
fully isolated from any developer's local dev.db.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    User, StudentProfile, FacultyProfile, Topic, Lesson, Command,
    Quiz, QuizQuestion, QuizAttempt, QuizResult, ChatSession, ChatMessage,
    Progress, CompletedLesson, Bookmark, Badge, Achievement,
    Notification, ActivityLog, SystemConfiguration, UserSettings, LoginHistory,
)
from app.utils.db_helpers import create_record, DuplicateRecordError, paginate, search_by_field


# --------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------

@pytest.fixture()
def student_user(app):
    user = User(name="Jordan Smith", email="jordan@example.com", role="student")
    user.set_password("supersecret123")
    db.session.add(user)
    db.session.flush()
    db.session.add(StudentProfile(user_id=user.id))
    db.session.commit()
    return user


@pytest.fixture()
def faculty_user(app):
    user = User(name="Dr. Ruiz", email="ruiz@example.com", role="faculty")
    user.set_password("supersecret123")
    db.session.add(user)
    db.session.flush()
    db.session.add(FacultyProfile(user_id=user.id, department="CS"))
    db.session.commit()
    return user


@pytest.fixture()
def topic(app):
    t = Topic(name="Loops", category="Shell Scripting", difficulty_level=3)
    db.session.add(t)
    db.session.commit()
    return t


# --------------------------------------------------------------------
# CRUD tests
# --------------------------------------------------------------------

class TestCRUD:
    def test_create_and_read_user(self, app, student_user):
        fetched = User.query.filter_by(email="jordan@example.com").first()
        assert fetched is not None
        assert fetched.check_password("supersecret123")
        assert not fetched.check_password("wrong-password")

    def test_update_record(self, app, student_user):
        student_user.name = "Jordan A. Smith"
        db.session.commit()
        fetched = db.session.get(User, student_user.id)
        assert fetched.name == "Jordan A. Smith"

    def test_delete_record(self, app, student_user):
        user_id = student_user.id
        db.session.delete(student_user)
        db.session.commit()
        assert db.session.get(User, user_id) is None

    def test_create_record_helper_success(self, app):
        topic = create_record(Topic(name="Piping", category="Linux Commands", difficulty_level=2))
        assert topic.id is not None

    def test_create_record_helper_duplicate_raises(self, app, topic):
        with pytest.raises(DuplicateRecordError):
            create_record(Topic(name="Loops", category="Shell Scripting", difficulty_level=1))


# --------------------------------------------------------------------
# Relationship tests
# --------------------------------------------------------------------

class TestRelationships:
    def test_user_student_profile_one_to_one(self, app, student_user):
        assert student_user.student_profile is not None
        assert student_user.student_profile.user_id == student_user.id

    def test_cascade_delete_user_removes_student_profile(self, app, student_user):
        profile_id = student_user.student_profile.id
        db.session.delete(student_user)
        db.session.commit()
        assert db.session.get(StudentProfile, profile_id) is None

    def test_topic_to_lessons_one_to_many(self, app, topic):
        db.session.add(Lesson(topic_id=topic.id, title="Intro to for loops", content_summary="...", sequence_order=1))
        db.session.add(Lesson(topic_id=topic.id, title="while loops", content_summary="...", sequence_order=2))
        db.session.commit()
        assert len(topic.lessons) == 2
        assert topic.lessons[0].sequence_order == 1  # ordered by sequence_order per relationship config

    def test_quiz_question_attempt_result_chain(self, app, student_user, topic):
        quiz = Quiz(topic_id=topic.id, title="Loops Quiz", difficulty_level=2)
        db.session.add(quiz)
        db.session.flush()
        question = QuizQuestion(
            quiz_id=quiz.id, question_text="What does a for loop do?",
            question_type="mcq", correct_answer="Iterates", difficulty_level=1,
        )
        db.session.add(question)
        db.session.flush()

        attempt = QuizAttempt(quiz_id=quiz.id, user_id=student_user.id, score=100.0)
        db.session.add(attempt)
        db.session.flush()

        result = QuizResult(attempt_id=attempt.id, question_id=question.id, student_answer="Iterates", is_correct=True)
        db.session.add(result)
        db.session.commit()

        assert quiz.questions[0].id == question.id
        assert attempt.results[0].is_correct is True
        assert student_user.quiz_attempts[0].id == attempt.id

    def test_chat_session_to_messages_one_to_many(self, app, student_user):
        session = ChatSession(user_id=student_user.id, topic_name="File Permissions")
        db.session.add(session)
        db.session.flush()
        db.session.add(ChatMessage(session_id=session.id, role="tutor", message_text="What does chmod do?", hint_stage=0))
        db.session.add(ChatMessage(session_id=session.id, role="student", message_text="Not sure"))
        db.session.commit()

        assert len(session.messages) == 2
        assert session.messages[0].role == "tutor"

    def test_badge_achievement_many_to_many_via_join(self, app, student_user):
        badge = Badge(name="First Steps", description="...", tier="gold", xp_reward=50)
        db.session.add(badge)
        db.session.flush()
        db.session.add(Achievement(user_id=student_user.id, badge_id=badge.id))
        db.session.commit()

        assert student_user.achievements[0].badge.name == "First Steps"
        assert badge.achievements[0].user_id == student_user.id

    def test_completed_lesson_junction(self, app, student_user, topic):
        lesson = Lesson(topic_id=topic.id, title="Intro", content_summary="...", sequence_order=1)
        db.session.add(lesson)
        db.session.flush()
        db.session.add(CompletedLesson(user_id=student_user.id, lesson_id=lesson.id, time_spent_minutes=12.5))
        db.session.commit()

        assert student_user.completed_lessons[0].lesson.title == "Intro"


# --------------------------------------------------------------------
# Constraint / validation tests
# --------------------------------------------------------------------

class TestConstraints:
    def test_topic_name_unique_constraint(self, app, topic):
        with pytest.raises(IntegrityError):
            db.session.add(Topic(name="Loops", category="x", difficulty_level=1))
            db.session.commit()
        db.session.rollback()

    def test_topic_difficulty_check_constraint(self, app):
        with pytest.raises(IntegrityError):
            db.session.add(Topic(name="Bad", category="x", difficulty_level=99))
            db.session.commit()
        db.session.rollback()

    def test_user_role_check_constraint(self, app):
        bad_user = User(name="Bad", email="bad@example.com", role="superadmin")
        bad_user.set_password("whatever123")
        with pytest.raises(IntegrityError):
            db.session.add(bad_user)
            db.session.commit()
        db.session.rollback()

    def test_achievement_unique_user_badge_constraint(self, app, student_user):
        badge = Badge(name="Streaker", description="...", tier="bronze", xp_reward=10)
        db.session.add(badge)
        db.session.flush()
        db.session.add(Achievement(user_id=student_user.id, badge_id=badge.id))
        db.session.commit()

        with pytest.raises(IntegrityError):
            db.session.add(Achievement(user_id=student_user.id, badge_id=badge.id))
            db.session.commit()
        db.session.rollback()

    def test_quiz_attempt_score_range_check_constraint(self, app, student_user, topic):
        quiz = Quiz(topic_id=topic.id, title="Range Test Quiz", difficulty_level=1)
        db.session.add(quiz)
        db.session.flush()
        with pytest.raises(IntegrityError):
            db.session.add(QuizAttempt(quiz_id=quiz.id, user_id=student_user.id, score=150))
            db.session.commit()
        db.session.rollback()


# --------------------------------------------------------------------
# Pagination / search tests
# --------------------------------------------------------------------

class TestDbHelpers:
    def test_pagination(self, app):
        for i in range(5):
            db.session.add(Topic(name=f"Topic {i}", category="Test", difficulty_level=1))
        db.session.commit()

        result = paginate(Topic.query.order_by(Topic.id), page=1, per_page=2)
        assert result["total"] == 5
        assert len(result["items"]) == 2
        assert result["total_pages"] == 3

    def test_search_by_field(self, app, topic):
        db.session.add(Topic(name="File Permissions", category="Linux Commands", difficulty_level=2))
        db.session.commit()

        results = search_by_field(Topic, "name", "perm")
        assert len(results) == 1
        assert results[0].name == "File Permissions"


# --------------------------------------------------------------------
# Platform-model smoke tests (Notification, ActivityLog, SystemConfiguration, Settings, LoginHistory)
# --------------------------------------------------------------------

class TestPlatformModels:
    def test_notification_created_unread_by_default(self, app, student_user):
        n = Notification(user_id=student_user.id, message="Achievement unlocked!", notification_type="achievement")
        db.session.add(n)
        db.session.commit()
        assert n.is_read is False

    def test_activity_log_records_action(self, app, student_user):
        log = ActivityLog(user_id=student_user.id, action="login", ip_address="127.0.0.1")
        db.session.add(log)
        db.session.commit()
        assert student_user.activity_logs[0].action == "login"

    def test_system_configuration_key_value(self, app):
        db.session.add(SystemConfiguration(config_key="maintenance_mode", config_value="false"))
        db.session.commit()
        fetched = SystemConfiguration.query.filter_by(config_key="maintenance_mode").first()
        assert fetched.config_value == "false"

    def test_user_settings_defaults(self, app, student_user):
        settings = UserSettings(user_id=student_user.id)
        db.session.add(settings)
        db.session.commit()
        assert settings.theme == "dark"
        assert settings.email_notifications_enabled is True

    def test_login_history_records_attempt(self, app, student_user):
        db.session.add(LoginHistory(user_id=student_user.id, ip_address="10.0.0.1", success=True))
        db.session.commit()
        assert student_user.login_history[0].success is True
