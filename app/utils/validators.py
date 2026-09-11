"""
app/utils/validators.py

Small, dependency-light validation helpers used by route handlers
before any data reaches a service/model layer (Part 3.1, Section 12 —
input validation is enforced before business logic executes).

These are intentionally simple functions (not a full schema library)
to keep the foundation phase's dependency footprint minimal; they can
be swapped for Flask-WTF/marshmallow schemas as each feature module
is built without changing the calling convention (raise ValidationError).
"""

import re

from app.utils.constants import MIN_PASSWORD_LENGTH, VALID_ROLES

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ValidationError(Exception):
    """Raised by validators; caught centrally by the global error handler
    (app/error_handlers.py) and converted into a standardized 400 response."""

    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.message = message
        self.field = field


def require_fields(data: dict, fields: list[str]) -> None:
    missing = [f for f in fields if not data.get(f)]
    if missing:
        raise ValidationError(f"Missing required field(s): {', '.join(missing)}")


def validate_email(email: str) -> str:
    email = (email or "").strip().lower()
    if not EMAIL_PATTERN.match(email):
        raise ValidationError("Please provide a valid email address.", field="email")
    return email


def validate_password(password: str) -> str:
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.", field="password"
        )
    return password


def validate_role(role: str) -> str:
    role = (role or "").strip().lower()
    if role not in VALID_ROLES:
        raise ValidationError(f"Role must be one of: {', '.join(VALID_ROLES)}.", field="role")
    return role


def validate_name(name: str) -> str:
    name = (name or "").strip()
    if len(name) < 2:
        raise ValidationError("Name must be at least 2 characters long.", field="name")
    return name
