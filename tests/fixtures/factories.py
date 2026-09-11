"""
tests/fixtures/factories.py

Part 3.11, Section 3 — reusable test-data factories. Existing test
files (Parts 3.3-3.10) each built their own inline student/faculty/
topic creation helpers, which worked fine and are left untouched
(rewriting 300+ passing tests for cosmetic consistency is explicitly
against this project's own "don't rewrite working code" rule). This
module exists so every NEW test file added in this phase (security/,
performance/, frontend/, the cross-module integration additions) has
one shared, consistent way to stand up test data instead of each
inventing its own — reducing duplication going forward without
touching what already works.
"""

from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models import (
    User, StudentProfile, FacultyProfile, Topic, Lesson, Assignment,
)
from app.utils.constants import ROLE_STUDENT, ROLE_FACULTY

DEFAULT_PASSWORD = "Password123!"


def make_student(email: str = "student@example.com", name: str = "Test Student", password: str = DEFAULT_PASSWORD) -> User:
    user = User(name=name, email=email, role=ROLE_STUDENT)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    db.session.add(StudentProfile(user_id=user.id))
    db.session.commit()
    return user


def make_faculty(email: str = "faculty@example.com", name: str = "Test Faculty", password: str = DEFAULT_PASSWORD) -> User:
    user = User(name=name, email=email, role=ROLE_FACULTY)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    db.session.add(FacultyProfile(user_id=user.id, department="Computer Science"))
    db.session.commit()
    return user


def make_topic(name: str = "Test Topic", category: str = "OS", difficulty_level: int = 2) -> Topic:
    topic = Topic(name=name, category=category, description="A test topic.", difficulty_level=difficulty_level)
    db.session.add(topic)
    db.session.commit()
    return topic


def make_lesson(topic: Topic, title: str = "Test Lesson", sequence_order: int = 0) -> Lesson:
    lesson = Lesson(topic_id=topic.id, title=title, content_summary="Summary.", sequence_order=sequence_order)
    db.session.add(lesson)
    db.session.commit()
    return lesson


def make_assignment(faculty: User, topic: Topic, title: str = "Test Assignment", due_in_days: int = 7, **kwargs) -> Assignment:
    assignment = Assignment(
        topic_id=topic.id, created_by_user_id=faculty.id, title=title, description="Do the work.",
        due_at=datetime.now(timezone.utc) + timedelta(days=due_in_days),
        allow_late_submission=kwargs.get("allow_late_submission", True),
        is_published=kwargs.get("is_published", True),
        max_score=kwargs.get("max_score", 100.0),
    )
    db.session.add(assignment)
    db.session.commit()
    return assignment


def login(client, email: str, password: str = DEFAULT_PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})
