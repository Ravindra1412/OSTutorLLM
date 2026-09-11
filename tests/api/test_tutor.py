"""
tests/api/test_tutor.py

API integration tests for app/routes/tutor_routes.py.
Exercises all route handlers, authentication/role guards, session ownership checks,
hint progression, full solution reveals, history, and teaching modes.
"""

import pytest
from app.extensions import db
from app.models import ChatSession, ChatMessage
from app.ai import config as ai_config
from tests.fixtures.factories import make_student, make_faculty, make_topic


@pytest.fixture
def student_client(app):
    """Clean test client logged in as student 1."""
    with app.app_context():
        make_student(email="student_tutor@example.com")
        make_topic("Process Synchronization")

    client = app.test_client()
    client.post("/api/auth/login", json={
        "email": "student_tutor@example.com",
        "password": "Password123!"
    })
    return client


@pytest.fixture
def faculty_client(app):
    """Faculty client to verify role-based access denial."""
    with app.app_context():
        make_faculty(email="faculty_tutor@example.com")

    client = app.test_client()
    client.post("/api/auth/login", json={
        "email": "faculty_tutor@example.com",
        "password": "Password123!"
    })
    return client


# ----------------------------------------------------------------------
# 1. Authorization & Role Checks
# ----------------------------------------------------------------------

def test_unauthenticated_request_rejected(app):
    client = app.test_client()
    res = client.get("/api/tutor/modes")
    assert res.status_code in (401, 302)


def test_faculty_cannot_access_student_tutor(faculty_client):
    res = faculty_client.get("/api/tutor/modes")
    assert res.status_code == 403


# ----------------------------------------------------------------------
# 2. GET /api/tutor/modes & /api/tutor/recommendation
# ----------------------------------------------------------------------

def test_list_teaching_modes(student_client):
    res = student_client.get("/api/tutor/modes")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert "modes" in data
    assert "intermediate" in data["modes"]
    assert data["default"] == "intermediate"


def test_get_recommendation(student_client):
    res = student_client.get("/api/tutor/recommendation")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert "recommended_topic" in data
    assert "weak_topics" in data


# ----------------------------------------------------------------------
# 3. POST /api/tutor/session (Start Session)
# ----------------------------------------------------------------------

def test_start_session_validation_error(student_client):
    res = student_client.post("/api/tutor/session", json={})
    assert res.status_code == 400


def test_start_session_success(student_client):
    res = student_client.post("/api/tutor/session", json={
        "topic": "Process Synchronization",
        "teaching_mode": "intermediate"
    })
    assert res.status_code == 201
    body = res.get_json()
    assert body["status"] == "success"
    data = body["data"]
    assert "session_id" in data
    assert data["topic"] == "Process Synchronization"
    assert "reply" in data


# ----------------------------------------------------------------------
# 4. Session Ownership & Cross-Student Isolation (_get_owned_session_or_404)
# ----------------------------------------------------------------------

def test_session_not_found_raises_error(student_client):
    res = student_client.get("/api/tutor/session/999999/history")
    assert res.status_code == 400


def test_student_cannot_access_another_students_session(student_client, app):
    # Student 1 creates a session
    start_res = student_client.post("/api/tutor/session", json={
        "topic": "Process Synchronization"
    })
    session_id = start_res.get_json()["data"]["session_id"]

    # Create Student 2 with distinct credentials
    with app.app_context():
        make_student(email="other_student_isolation@example.com")

    other_client = app.test_client()
    other_client.post("/api/auth/login", json={
        "email": "other_student_isolation@example.com",
        "password": "Password123!"
    })

    # Student 2 tries to access Student 1's session
    res = other_client.get(f"/api/tutor/session/{session_id}/history")
    assert res.status_code == 400
    assert "Tutor session not found." in res.get_json()["message"]


# ----------------------------------------------------------------------
# 5. POST /api/tutor/message & GET /history & POST /reset
# ----------------------------------------------------------------------

def test_send_message_validation(student_client):
    res = student_client.post("/api/tutor/message", json={"session_id": 1})
    assert res.status_code == 400


def test_send_message_and_get_history(student_client):
    start_res = student_client.post("/api/tutor/session", json={
        "topic": "Process Synchronization"
    })
    session_id = start_res.get_json()["data"]["session_id"]

    msg_res = student_client.post("/api/tutor/message", json={
        "session_id": session_id,
        "message": "Can you give me an example of a race condition?"
    })
    assert msg_res.status_code == 200
    assert "reply" in msg_res.get_json()["data"]

    hist_res = student_client.get(f"/api/tutor/session/{session_id}/history")
    assert hist_res.status_code == 200
    messages = hist_res.get_json()["data"]["messages"]
    assert len(messages) >= 2


def test_reset_session(student_client):
    start_res = student_client.post("/api/tutor/session", json={
        "topic": "Process Synchronization"
    })
    session_id = start_res.get_json()["data"]["session_id"]

    reset_res = student_client.post(f"/api/tutor/session/{session_id}/reset")
    assert reset_res.status_code == 200
    assert reset_res.get_json()["status"] == "success"


# ----------------------------------------------------------------------
# 6. POST /api/tutor/reveal (Hint ladder enforcement)
# ----------------------------------------------------------------------

def test_reveal_blocked_when_hints_not_exhausted(student_client):
    start_res = student_client.post("/api/tutor/session", json={
        "topic": "Process Synchronization"
    })
    session_id = start_res.get_json()["data"]["session_id"]

    reveal_res = student_client.post("/api/tutor/reveal", json={
        "session_id": session_id
    })
    assert reveal_res.status_code == 403
    assert "Hints haven't been exhausted yet" in reveal_res.get_json()["message"]


def test_reveal_success_when_hints_exhausted(student_client, app):
    start_res = student_client.post("/api/tutor/session", json={
        "topic": "Process Synchronization"
    })
    session_id = start_res.get_json()["data"]["session_id"]

    with app.app_context():
        session = db.session.get(ChatSession, session_id)
        msg = ChatMessage(
            session_id=session.id,
            role="tutor",
            message_text="Here is hint 3.",
            hint_stage=ai_config.MAX_HINT_STAGE
        )
        db.session.add(msg)
        db.session.commit()

    reveal_res = student_client.post("/api/tutor/reveal", json={
        "session_id": session_id
    })
    assert reveal_res.status_code == 200
    data = reveal_res.get_json()["data"]
    assert data["is_final_solution"] is True