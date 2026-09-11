"""
tests/api/test_api_contract.py

Part 3.11, Section 6 — API Testing. Every existing per-module test
file (tests/api/test_auth.py, tests/api/test_faculty.py, etc.) already
exercises its own endpoints' business logic thoroughly. This module's
job is different and narrower: prove the response CONTRACT documented
in app/utils/formatters.py — {status, message, data?, field?} — is
actually what every blueprint returns, not just the ones already
spot-checked. A frontend built against "every endpoint returns this
one shape" is only as safe as this sweep proves it to be.
"""

import pytest

from tests.fixtures.factories import make_student, make_faculty, make_topic, login

pytestmark = pytest.mark.api

VALID_STATUSES = {"success", "fail", "error"}


def _assert_envelope(body: dict):
    assert "status" in body
    assert body["status"] in VALID_STATUSES
    assert "message" in body
    if body["status"] == "success":
        assert "data" in body
    if body["status"] == "fail" and "field" in body:
        assert isinstance(body["field"], str)


class TestSuccessEnvelopeAcrossBlueprints:
    """One 200-path per blueprint, sampled — not every endpoint (the
    per-module test files already do that), just proof every
    BLUEPRINT'S wiring returns the shared envelope, not a bespoke one."""

    def test_auth_me_envelope(self, client, app):
        make_student(email="envauth@example.com")
        login(client, "envauth@example.com")
        _assert_envelope(client.get("/api/auth/me").get_json())

    def test_progress_envelope(self, client, app):
        make_student(email="envprogress@example.com")
        login(client, "envprogress@example.com")
        _assert_envelope(client.get("/api/progress").get_json())

    def test_analytics_dashboard_envelope(self, client, app):
        make_student(email="envanalytics@example.com")
        login(client, "envanalytics@example.com")
        _assert_envelope(client.get("/api/analytics/dashboard").get_json())

    def test_faculty_dashboard_envelope(self, client, app):
        make_faculty(email="envfaculty@example.com")
        login(client, "envfaculty@example.com")
        _assert_envelope(client.get("/api/faculty/dashboard").get_json())

    def test_faculty_students_envelope(self, client, app):
        make_faculty(email="envfacstudents@example.com")
        login(client, "envfacstudents@example.com")
        _assert_envelope(client.get("/api/faculty/students").get_json())

    def test_quiz_topics_envelope(self, client, app):
        make_student(email="envquiztopics@example.com")
        login(client, "envquiztopics@example.com")
        _assert_envelope(client.get("/api/quiz/topics").get_json())

    def test_code_review_topics_envelope(self, client, app):
        make_student(email="envcrtopics@example.com")
        login(client, "envcrtopics@example.com")
        _assert_envelope(client.get("/api/code-review/topics").get_json())

    def test_settings_account_envelope(self, client, app):
        make_student(email="envsettings@example.com")
        login(client, "envsettings@example.com")
        _assert_envelope(client.get("/api/settings/account").get_json())

    def test_assignments_envelope(self, client, app):
        make_student(email="envassignments@example.com")
        login(client, "envassignments@example.com")
        _assert_envelope(client.get("/api/assignments").get_json())


class TestFailEnvelopeAcrossBlueprints:
    """Deliberately-wrong requests — every one must return the `fail`
    envelope shape with a real 4xx code, never a bare stack trace."""

    def test_missing_required_field_returns_fail_envelope(self, client, app):
        make_student(email="envfail1@example.com")
        login(client, "envfail1@example.com")
        resp = client.post("/api/code-review/submit", json={})
        assert resp.status_code == 400
        body = resp.get_json()
        _assert_envelope(body)
        assert body["status"] == "fail"

    def test_not_found_returns_fail_envelope(self, client, app):
        make_faculty(email="envfail2@example.com")
        login(client, "envfail2@example.com")
        resp = client.get("/api/faculty/students/999999")
        assert resp.status_code == 404
        body = resp.get_json()
        _assert_envelope(body)
        assert body["status"] == "fail"

    def test_bad_login_returns_fail_envelope(self, client, app):
        resp = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "wrong"})
        assert resp.status_code in (400, 401)
        _assert_envelope(resp.get_json())


class TestStatusCodeConventions:
    """Section 6 — Status Codes. Spot-checks the specific codes this
    codebase's own convention promises (201 on create, 404 on
    not-found, 403 on wrong role, 409 on state conflicts)."""

    def test_registration_returns_201(self, client):
        resp = client.post("/api/auth/register", json={
            "name": "Code Test", "email": "codetest@example.com", "password": "Password123!", "role": "student",
        })
        assert resp.status_code == 201

    def test_role_violation_returns_403_not_401(self, client, app):
        """403 (authenticated but not permitted) must be distinct from
        401 (not authenticated at all) — a common REST API mistake."""
        make_student(email="role403@example.com")
        login(client, "role403@example.com")
        resp = client.get("/api/faculty/dashboard")
        assert resp.status_code == 403

    def test_cross_user_resource_returns_404_not_403(self, client, app):
        """Established pattern (Part 3.7 onward): never confirm another
        user's resource exists via a 403 — return 404 either way."""
        make_student(email="crossuser1@example.com")
        make_student(email="crossuser2@example.com")

        login(client, "crossuser1@example.com")
        from app.models import Progress
        import app.extensions as ext
        user1 = client.get("/api/auth/me").get_json()["data"]
        ext.db.session.add(Progress(user_id=user1["id"], topic_name="Weak Topic", mastery_score=10.0))
        ext.db.session.commit()
        sync = client.post("/api/analytics/recommendations/sync")
        rec_id = sync.get_json()["data"][0]["id"]
        client.post("/api/auth/logout")

        login(client, "crossuser2@example.com")
        resp = client.post(f"/api/analytics/recommendations/{rec_id}/dismiss")
        assert resp.status_code == 404

    def test_double_submission_returns_409(self, client, app):
        make_student(email="double409@example.com")
        make_topic("Navigation")
        login(client, "double409@example.com")
        start = client.post("/api/quiz/start", json={"mode": "topic", "topic": "Navigation", "question_count": 1})
        attempt_id = start.get_json()["data"]["attempt_id"]
        client.post(f"/api/quiz/{attempt_id}/submit")
        second = client.post(f"/api/quiz/{attempt_id}/submit")
        assert second.status_code == 409


class TestValidationAcrossBlueprints:
    """Section 6 — Validation. Malformed/missing bodies must be
    rejected with 400, never silently accepted or 500ing."""

    @pytest.mark.parametrize("path,body", [
        ("/api/faculty/content/topics", {}),
        ("/api/faculty/quizzes", {"title": "No Topic"}),
        ("/api/faculty/assignments", {"title": "No Due Date"}),
    ])
    def test_missing_required_fields_rejected(self, client, app, path, body):
        make_faculty(email=f"valfac{hash(path) % 10000}@example.com")
        login(client, f"valfac{hash(path) % 10000}@example.com")
        resp = client.post(path, json=body)
        assert resp.status_code == 400
