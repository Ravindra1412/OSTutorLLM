"""
tests/unit/test_utils.py

Part 3.11, Section 4 — Unit Testing for Utilities. These pure
functions (app/utils/validators.py, formatters.py, mixins.py) are
exercised indirectly by nearly every other test in this suite via the
routes that call them, but had no DIRECT unit test isolating their own
edge cases (empty string, boundary length, case sensitivity) until
now — the fastest, cheapest tests in the whole suite (no DB, no app
context needed for most of them).
"""

import time

import pytest

from app.utils.validators import (
    ValidationError, require_fields, validate_email, validate_password, validate_role, validate_name,
)
from app.utils.constants import MIN_PASSWORD_LENGTH, VALID_ROLES

pytestmark = pytest.mark.unit


class TestRequireFields:
    def test_passes_when_all_fields_present(self):
        require_fields({"a": 1, "b": 2}, ["a", "b"])  # no raise

    def test_raises_on_missing_field(self):
        with pytest.raises(ValidationError) as exc:
            require_fields({"a": 1}, ["a", "b"])
        assert "b" in exc.value.message

    def test_raises_on_falsy_field_value(self):
        """An empty string or 0 counts as 'missing' for a required
        field — a real, deliberate choice (not just key-presence)."""
        with pytest.raises(ValidationError):
            require_fields({"name": ""}, ["name"])

    def test_lists_all_missing_fields_not_just_first(self):
        with pytest.raises(ValidationError) as exc:
            require_fields({}, ["a", "b", "c"])
        assert "a" in exc.value.message and "b" in exc.value.message and "c" in exc.value.message


class TestValidateEmail:
    @pytest.mark.parametrize("email", ["user@example.com", "a.b+c@sub.example.co.uk"])
    def test_accepts_valid_emails(self, email):
        assert validate_email(email) == email.lower()

    @pytest.mark.parametrize("email", ["not-an-email", "missing@domain", "@nodomain.com", "spaces in@email.com", ""])
    def test_rejects_invalid_emails(self, email):
        with pytest.raises(ValidationError) as exc:
            validate_email(email)
        assert exc.value.field == "email"

    def test_normalizes_case_and_whitespace(self):
        assert validate_email("  USER@Example.COM  ") == "user@example.com"


class TestValidatePassword:
    def test_accepts_password_at_minimum_length(self):
        pw = "a" * MIN_PASSWORD_LENGTH
        assert validate_password(pw) == pw

    def test_rejects_password_below_minimum_length(self):
        with pytest.raises(ValidationError) as exc:
            validate_password("a" * (MIN_PASSWORD_LENGTH - 1))
        assert exc.value.field == "password"

    def test_rejects_empty_password(self):
        with pytest.raises(ValidationError):
            validate_password("")

    def test_rejects_none_password(self):
        with pytest.raises(ValidationError):
            validate_password(None)


class TestValidateRole:
    @pytest.mark.parametrize("role", list(VALID_ROLES))
    def test_accepts_every_valid_role(self, role):
        assert validate_role(role) == role

    def test_rejects_unknown_role(self):
        with pytest.raises(ValidationError) as exc:
            validate_role("superadmin")
        assert exc.value.field == "role"

    def test_normalizes_case(self):
        role = list(VALID_ROLES)[0]
        assert validate_role(role.upper()) == role


class TestValidateName:
    def test_accepts_normal_name(self):
        assert validate_name("Ada Lovelace") == "Ada Lovelace"

    def test_strips_whitespace(self):
        assert validate_name("  Bob  ") == "Bob"

    def test_rejects_single_character_name(self):
        with pytest.raises(ValidationError):
            validate_name("A")

    def test_rejects_empty_name(self):
        with pytest.raises(ValidationError):
            validate_name("")


class TestResponseFormatters:
    """These need an app context (jsonify requires one) but no DB."""

    def test_success_response_shape(self, app):
        from app.utils.formatters import success_response
        with app.test_request_context():
            resp, code = success_response({"x": 1}, message="done", status_code=201)
            body = resp.get_json()
        assert code == 201
        assert body == {"status": "success", "message": "done", "data": {"x": 1}}

    def test_success_response_defaults_data_to_empty_dict(self, app):
        from app.utils.formatters import success_response
        with app.test_request_context():
            resp, code = success_response()
            body = resp.get_json()
        assert code == 200
        assert body["data"] == {}

    def test_fail_response_includes_field_when_given(self, app):
        from app.utils.formatters import fail_response
        with app.test_request_context():
            resp, code = fail_response("Bad input", status_code=400, field="email")
            body = resp.get_json()
        assert code == 400
        assert body == {"status": "fail", "message": "Bad input", "field": "email"}

    def test_fail_response_omits_field_when_not_given(self, app):
        from app.utils.formatters import fail_response
        with app.test_request_context():
            resp, code = fail_response("Bad input")
            body = resp.get_json()
        assert "field" not in body

    def test_error_response_defaults(self, app):
        from app.utils.formatters import error_response
        with app.test_request_context():
            resp, code = error_response()
            body = resp.get_json()
        assert code == 500
        assert body["status"] == "error"


class TestTimestampMixin:
    def test_created_at_and_updated_at_are_set_on_insert(self, app):
        from app.extensions import db
        from tests.fixtures.factories import make_topic

        topic = make_topic("Mixin Test Topic")
        assert topic.created_at is not None
        assert topic.updated_at is not None

    def test_updated_at_changes_on_update_but_created_at_does_not(self, app):
        from app.extensions import db
        from tests.fixtures.factories import make_topic

        topic = make_topic("Mixin Update Topic")
        original_created = topic.created_at
        original_updated = topic.updated_at

        time.sleep(0.01)
        topic.description = "Changed"
        db.session.commit()

        assert topic.created_at == original_created
        assert topic.updated_at > original_updated
