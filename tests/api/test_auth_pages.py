"""
tests/test_auth_pages.py

Part 3.5 auth module test suite (Section 19): registration, login,
logout, password change, forgot/reset password (including token
self-invalidation), profile update, RBAC, and rate limiting — for the
page-based (HTML/session/CSRF) routes in app/routes/auth_pages_routes.py.

Tests disable CSRF via TestingConfig.WTF_CSRF_ENABLED = False (Part
3.3, app/config/config.py) so form posts here focus on business logic
rather than re-deriving a CSRF token per test; CSRF itself is covered
by the live verification log in docs/project-report-part3.5.md, where
a real token was extracted from a real rendered page and a mismatched
token was confirmed to be rejected.
"""

import re

import pytest

from app.extensions import db
from app.models import User
from app.auth.tokens import generate_password_reset_token, generate_email_verification_token
from app.auth.rate_limit import reset_rate_limit_store


@pytest.fixture(autouse=True)
def _clear_rate_limits():
    reset_rate_limit_store()
    yield
    reset_rate_limit_store()


def _extract_next_url(response):
    return response.headers.get("Location")


class TestRegistration:
    def test_register_page_loads(self, client):
        resp = client.get("/register")
        assert resp.status_code == 200
        assert b"Create your account" in resp.data

    def test_register_creates_user_and_logs_in(self, client):
        resp = client.post("/register", data={
            "name": "Jordan Smith", "email": "jordan@example.com", "role": "student",
            "password": "SecurePass123", "confirm_password": "SecurePass123",
        }, follow_redirects=False)
        assert resp.status_code == 302
        assert _extract_next_url(resp).endswith("/profile")

        user = User.query.filter_by(email="jordan@example.com").first()
        assert user is not None
        assert user.role == "student"
        assert user.student_profile is not None
        assert user.email_verified is False

    def test_register_duplicate_email_shows_form_error(self, client, app):
        user = User(name="Existing", email="taken@example.com", role="student")
        user.set_password("whatever123")
        db.session.add(user)
        db.session.commit()

        resp = client.post("/register", data={
            "name": "New Person", "email": "taken@example.com", "role": "student",
            "password": "SecurePass123", "confirm_password": "SecurePass123",
        })
        assert resp.status_code == 200  # re-renders form with error, no redirect
        assert b"already exists" in resp.data

    def test_register_weak_password_rejected(self, client):
        resp = client.post("/register", data={
            "name": "Jordan Smith", "email": "weak@example.com", "role": "student",
            "password": "alllettersnodigits", "confirm_password": "alllettersnodigits",
        })
        assert resp.status_code == 200
        assert b"at least one letter and one number" in resp.data

    def test_register_password_mismatch_rejected(self, client):
        resp = client.post("/register", data={
            "name": "Jordan Smith", "email": "mismatch@example.com", "role": "student",
            "password": "SecurePass123", "confirm_password": "DifferentPass456",
        })
        assert resp.status_code == 200
        assert b"must match" in resp.data


class TestLoginLogout:
    def _register(self, client, email="jordan@example.com", password="SecurePass123"):
        client.post("/register", data={
            "name": "Jordan Smith", "email": email, "role": "student",
            "password": password, "confirm_password": password,
        })
        client.post("/logout")

    def test_login_with_correct_credentials(self, client, app):
        self._register(client)
        resp = client.post("/login", data={"email": "jordan@example.com", "password": "SecurePass123"})
        assert resp.status_code == 302
        assert _extract_next_url(resp).endswith("/profile")

    def test_login_with_wrong_password_shows_error(self, client, app):
        self._register(client)
        resp = client.post("/login", data={"email": "jordan@example.com", "password": "WrongPassword1"})
        assert resp.status_code == 200
        assert b"Invalid email or password" in resp.data

    def test_login_nonexistent_email_same_error_message(self, client):
        resp = client.post("/login", data={"email": "nobody@example.com", "password": "WrongPassword1"})
        assert resp.status_code == 200
        assert b"Invalid email or password" in resp.data

    def test_profile_requires_login_redirects_to_login(self, client):
        resp = client.get("/profile")
        assert resp.status_code == 302
        assert "/login" in _extract_next_url(resp)

    def test_logout_ends_session(self, client, app):
        self._register(client)
        client.post("/login", data={"email": "jordan@example.com", "password": "SecurePass123"})
        assert client.get("/profile").status_code == 200

        client.post("/logout")
        resp = client.get("/profile")
        assert resp.status_code == 302
        assert "/login" in _extract_next_url(resp)


class TestPasswordManagement:
    def _register_and_login(self, client, email="jordan@example.com", password="SecurePass123"):
        client.post("/register", data={
            "name": "Jordan Smith", "email": email, "role": "student",
            "password": password, "confirm_password": password,
        })

    def test_change_password_success(self, client, app):
        self._register_and_login(client)
        resp = client.post("/change-password", data={
            "current_password": "SecurePass123",
            "new_password": "NewSecurePass456",
            "confirm_new_password": "NewSecurePass456",
        })
        assert resp.status_code == 302

        client.post("/logout")
        resp = client.post("/login", data={"email": "jordan@example.com", "password": "NewSecurePass456"})
        assert resp.status_code == 302  # new password works
        client.post("/logout")

        resp2 = client.post("/login", data={"email": "jordan@example.com", "password": "SecurePass123"})
        assert resp2.status_code == 200  # old password no longer works
        assert b"Invalid email or password" in resp2.data

    def test_change_password_wrong_current_password_rejected(self, client, app):
        self._register_and_login(client)
        resp = client.post("/change-password", data={
            "current_password": "WrongCurrentPass1",
            "new_password": "NewSecurePass456",
            "confirm_new_password": "NewSecurePass456",
        })
        assert resp.status_code == 200
        assert b"Current password is incorrect" in resp.data

    def test_forgot_password_shows_generic_message_for_unknown_email(self, client):
        resp = client.post("/forgot-password", data={"email": "unknown@example.com"})
        assert resp.status_code == 200
        assert b"If an account exists" in resp.data

    def test_reset_password_with_valid_token(self, client, app):
        self._register_and_login(client)
        user = User.query.filter_by(email="jordan@example.com").first()
        token = generate_password_reset_token(user)

        resp = client.post(f"/reset-password/{token}", data={
            "password": "ResetPassABC1", "confirm_password": "ResetPassABC1",
        })
        assert resp.status_code == 302
        assert _extract_next_url(resp).endswith("/login")

        client.post("/logout")
        resp = client.post("/login", data={"email": "jordan@example.com", "password": "ResetPassABC1"})
        assert resp.status_code == 302

    def test_reset_token_self_invalidates_after_use(self, client, app):
        """The core security property of app/auth/tokens.py: a reset
        token is fingerprinted to the password hash at issue time, so
        replaying it after the password has already changed must fail."""
        self._register_and_login(client)
        user = User.query.filter_by(email="jordan@example.com").first()
        token = generate_password_reset_token(user)

        client.post(f"/reset-password/{token}", data={
            "password": "FirstReset123", "confirm_password": "FirstReset123",
        })

        # Replay the SAME token after the password already changed once.
        resp = client.post(f"/reset-password/{token}", data={
            "password": "SecondReset456", "confirm_password": "SecondReset456",
        })
        assert resp.status_code == 302
        assert _extract_next_url(resp).endswith("/forgot-password")  # rejected, not applied

    def test_reset_password_invalid_token_rejected(self, client):
        resp = client.post("/reset-password/not-a-real-token", data={
            "password": "WhateverPass123", "confirm_password": "WhateverPass123",
        })
        assert resp.status_code == 302
        assert _extract_next_url(resp).endswith("/forgot-password")


class TestEmailVerification:
    def test_verify_email_with_valid_token(self, client, app):
        client.post("/register", data={
            "name": "Jordan Smith", "email": "jordan@example.com", "role": "student",
            "password": "SecurePass123", "confirm_password": "SecurePass123",
        })
        user = User.query.filter_by(email="jordan@example.com").first()
        assert user.email_verified is False

        token = generate_email_verification_token(user)
        resp = client.get(f"/verify-email/{token}")
        assert resp.status_code == 302

        db.session.refresh(user)
        assert user.email_verified is True

    def test_verify_email_invalid_token_shows_error(self, client):
        resp = client.get("/verify-email/garbage-token", follow_redirects=True)
        assert resp.status_code == 200
        assert b"invalid or has expired" in resp.data


class TestProfileManagement:
    def test_profile_page_loads_for_logged_in_user(self, client, app):
        client.post("/register", data={
            "name": "Jordan Smith", "email": "jordan@example.com", "role": "student",
            "password": "SecurePass123", "confirm_password": "SecurePass123",
        })
        resp = client.get("/profile")
        assert resp.status_code == 200
        assert b"Jordan Smith" in resp.data

    def test_profile_update_changes_name(self, client, app):
        client.post("/register", data={
            "name": "Jordan Smith", "email": "jordan@example.com", "role": "student",
            "password": "SecurePass123", "confirm_password": "SecurePass123",
        })
        resp = client.post("/profile", data={"name": "Jordan A. Smith", "hint_verbosity_pref": "3"})
        assert resp.status_code == 302

        user = User.query.filter_by(email="jordan@example.com").first()
        assert user.name == "Jordan A. Smith"
        assert user.student_profile.hint_verbosity_pref == 3


class TestRoleBasedAccessControl:
    def test_student_cannot_access_faculty_api_route(self, client, app):
        client.post("/register", data={
            "name": "A Student", "email": "student@example.com", "role": "student",
            "password": "SecurePass123", "confirm_password": "SecurePass123",
        })
        resp = client.get("/api/faculty/roster")
        assert resp.status_code == 403

    def test_faculty_can_access_faculty_api_route(self, client, app):
        client.post("/register", data={
            "name": "A Faculty", "email": "faculty@example.com", "role": "faculty",
            "password": "SecurePass123", "confirm_password": "SecurePass123",
        })
        resp = client.get("/api/faculty/roster")
        assert resp.status_code == 200


class TestRateLimiting:
    def test_login_rate_limit_triggers_after_threshold(self, client):
        for _ in range(10):
            resp = client.post("/login", data={"email": "x@example.com", "password": "wrongpass1"})
            assert resp.status_code == 200

        resp = client.post("/login", data={"email": "x@example.com", "password": "wrongpass1"})
        assert resp.status_code == 429
