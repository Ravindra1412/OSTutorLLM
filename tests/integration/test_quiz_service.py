"""
tests/test_quiz_service.py

Section 22 — API/Adaptive Learning/Timer/Randomization tests for the
quiz engine's orchestration layer. Uses the real database and the real
Mock LLM provider — the same pipeline proven live in
docs/project-report-part3.7.md's verification log, captured here as
repeatable automated tests.
"""

from datetime import datetime, timezone, timedelta

import pytest

from app.extensions import db
from app.models import User, StudentProfile, Progress
from app.quiz.services import quiz_service, difficulty_manager, timer_service, security


@pytest.fixture()
def student(app):
    user = User(name="Quiz Student", email="quizstudent@example.com", role="student")
    user.set_password("password123")
    db.session.add(user)
    db.session.flush()
    db.session.add(StudentProfile(user_id=user.id))
    db.session.commit()
    return user


class TestQuizWorkflow:
    def test_start_quiz_creates_questions_and_attempt(self, app, student):
        result = quiz_service.start_quiz(student.id, topic_name="File Permissions", question_count=3)
        assert result.attempt.id is not None
        assert len(result.quiz.questions) == 3
        assert result.attempt.is_submitted is False

    def test_full_workflow_answer_and_submit(self, app, student):
        result = quiz_service.start_quiz(student.id, topic_name="Loops", question_count=2)
        for q in result.quiz.questions:
            quiz_service.submit_answer(student.id, result.attempt.id, q.id, "some answer")

        outcome = quiz_service.submit_quiz(student.id, result.attempt.id)
        assert outcome["score_percent"] is not None
        assert outcome["summary"]["total_questions"] == 2
        assert outcome["feedback"] is not None

    def test_unanswered_questions_graded_as_blank(self, app, student):
        result = quiz_service.start_quiz(student.id, topic_name="Loops", question_count=2)
        outcome = quiz_service.submit_quiz(student.id, result.attempt.id)
        assert outcome["summary"]["total_questions"] == 2

    def test_progress_updated_after_quiz(self, app, student):
        result = quiz_service.start_quiz(student.id, topic_name="Navigation", question_count=2)
        quiz_service.submit_quiz(student.id, result.attempt.id)

        entry = Progress.query.filter_by(user_id=student.id, topic_name="Navigation").first()
        assert entry is not None
        assert entry.mastery_score is not None


class TestSecurity:
    def test_cannot_submit_answer_for_another_users_attempt(self, app, student):
        other = User(name="Other", email="other@example.com", role="student")
        other.set_password("password123")
        db.session.add(other)
        db.session.flush()
        db.session.add(StudentProfile(user_id=other.id))
        db.session.commit()

        result = quiz_service.start_quiz(student.id, topic_name="Loops", question_count=1)
        q = result.quiz.questions[0]

        with pytest.raises(security.QuizSecurityError):
            quiz_service.submit_answer(other.id, result.attempt.id, q.id, "x")

    def test_cannot_double_submit(self, app, student):
        result = quiz_service.start_quiz(student.id, topic_name="Loops", question_count=1)
        quiz_service.submit_quiz(student.id, result.attempt.id)
        with pytest.raises(security.QuizSecurityError):
            quiz_service.submit_quiz(student.id, result.attempt.id)

    def test_cannot_start_second_active_attempt_on_same_quiz(self, app, student):
        result = quiz_service.start_quiz(student.id, topic_name="Loops", question_count=1)
        with pytest.raises(security.QuizSecurityError):
            security.assert_no_other_active_attempt(student.id, result.quiz.id)

    def test_cannot_answer_after_time_expired(self, app, student):
        result = quiz_service.start_quiz(student.id, topic_name="Loops", question_count=1, time_limit_seconds=60)
        result.attempt.expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)
        db.session.commit()

        with pytest.raises(security.QuizSecurityError):
            quiz_service.submit_answer(student.id, result.attempt.id, result.quiz.questions[0].id, "x")


class TestTimer:
    def test_untimed_quiz_never_expires(self, app, student):
        result = quiz_service.start_quiz(student.id, topic_name="Loops", question_count=1, time_limit_seconds=None)
        assert timer_service.is_expired(result.attempt) is False
        assert timer_service.remaining_seconds(result.attempt) is None

    def test_pause_and_resume_preserves_remaining_time(self, app, student):
        result = quiz_service.start_quiz(student.id, topic_name="Loops", question_count=1, time_limit_seconds=100)
        remaining_before = timer_service.remaining_seconds(result.attempt)

        timer_service.pause_timer(result.attempt)
        assert result.attempt.paused_at is not None

        timer_service.resume_timer(result.attempt)
        remaining_after = timer_service.remaining_seconds(result.attempt)
        assert abs(remaining_before - remaining_after) <= 2

    def test_auto_submit_when_expired(self, app, student):
        result = quiz_service.start_quiz(student.id, topic_name="Loops", question_count=1, time_limit_seconds=60)
        result.attempt.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.session.commit()

        was_auto_submitted = quiz_service.auto_submit_if_expired(student.id, result.attempt.id)
        assert was_auto_submitted is True

        db.session.refresh(result.attempt)
        assert result.attempt.is_submitted is True
        assert result.attempt.auto_submitted is True


class TestAdaptiveDifficulty:
    def test_new_topic_defaults_to_easy_ish(self, app, student):
        level = difficulty_manager.determine_adaptive_difficulty(student.id, "Deadlocks")
        assert level == 2

    def test_high_mastery_maps_to_hard(self, app, student):
        db.session.add(Progress(user_id=student.id, topic_name="Loops", mastery_score=90))
        db.session.commit()
        level = difficulty_manager.determine_adaptive_difficulty(student.id, "Loops")
        assert level == 5

    def test_low_mastery_maps_to_easy(self, app, student):
        db.session.add(Progress(user_id=student.id, topic_name="Loops", mastery_score=15))
        db.session.commit()
        level = difficulty_manager.determine_adaptive_difficulty(student.id, "Loops")
        assert level == 1

    def test_label_and_level_conversion_roundtrip(self):
        assert difficulty_manager.label_for_level(1) == difficulty_manager.EASY
        assert difficulty_manager.label_for_level(3) == difficulty_manager.MEDIUM
        assert difficulty_manager.label_for_level(5) == difficulty_manager.HARD
        assert difficulty_manager.level_for_label(difficulty_manager.EASY) in (1, 2)


class TestRandomization:
    def test_question_set_avoids_recent_repeats_when_possible(self, app, student):
        from app.quiz.services import question_generator

        result1 = quiz_service.start_quiz(student.id, topic_name="File Permissions", question_count=2)
        quiz_service.submit_quiz(student.id, result1.attempt.id)

        first_texts = {q.question_text for q in result1.quiz.questions}
        second_questions = question_generator.generate_question_set(student.id, "File Permissions", 2, count=2)
        second_texts = {q["question_text"] for q in second_questions}

        assert first_texts != second_texts


class TestScoringEngine:
    def test_negative_marking_reduces_score_when_enabled(self, app, student):
        result = quiz_service.start_quiz(
            student.id, topic_name="Loops", question_count=2, negative_marking_enabled=True
        )
        for q in result.quiz.questions:
            quiz_service.submit_answer(student.id, result.attempt.id, q.id, "definitely wrong answer xyz")
        outcome = quiz_service.submit_quiz(student.id, result.attempt.id)

        assert outcome["score_percent"] == 0.0
