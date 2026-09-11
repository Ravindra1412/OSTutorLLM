"""
app/auth/tokens.py

Stateless signed tokens for email verification and password reset
(Section 7 / Section 8). Uses itsdangerous's URLSafeTimedSerializer
(already a Flask dependency — no new package needed for this part).

Design decision: rather than storing a reset/verification token in the
database (which would need its own table + cleanup job for expired
rows), tokens here are self-contained and self-expiring:
  - The token itself encodes the user id + a "purpose" tag, signed with
    SECRET_KEY, and carries no server-side state to store or clean up.
  - Expiration is enforced by itsdangerous at verify-time (max_age).
  - Self-invalidation on password change: the reset-token signature
    includes a hash derived from the user's CURRENT password_hash, so
    the moment a user's password changes, every previously issued reset
    token for them silently stops verifying — no denylist needed.

This is a standard, secure pattern (the same one Flask-Security and
Django's PasswordResetTokenGenerator use) and keeps this phase free of
an extra `tokens` database table for something that doesn't need
persistent state.
"""

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import current_app

PURPOSE_EMAIL_VERIFY = "email-verify"
PURPOSE_PASSWORD_RESET = "password-reset"

RESET_TOKEN_MAX_AGE_SECONDS = 60 * 60          # 1 hour
VERIFY_TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24    # 24 hours


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def generate_email_verification_token(user) -> str:
    return _serializer().dumps({"uid": user.id, "purpose": PURPOSE_EMAIL_VERIFY})


def verify_email_verification_token(token: str, max_age: int = VERIFY_TOKEN_MAX_AGE_SECONDS):
    """Returns the user id if valid, or None if invalid/expired/wrong purpose."""
    try:
        data = _serializer().loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    if data.get("purpose") != PURPOSE_EMAIL_VERIFY:
        return None
    return data.get("uid")


def _password_fingerprint(user) -> str:
    """A short slice of the current password hash, folded into the
    reset token's payload so the token can only ever verify against the
    password that was current when it was issued."""
    return (user.password_hash or "")[-12:]


def generate_password_reset_token(user) -> str:
    return _serializer().dumps({
        "uid": user.id,
        "purpose": PURPOSE_PASSWORD_RESET,
        "pwfp": _password_fingerprint(user),
    })


def verify_password_reset_token(token: str, user_lookup_fn, max_age: int = RESET_TOKEN_MAX_AGE_SECONDS):
    """`user_lookup_fn(uid)` should return the User or None — kept as a
    parameter rather than importing the model here, to avoid this
    low-level token module depending on the ORM layer at import time."""
    try:
        data = _serializer().loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    if data.get("purpose") != PURPOSE_PASSWORD_RESET:
        return None

    user = user_lookup_fn(data.get("uid"))
    if user is None:
        return None
    if _password_fingerprint(user) != data.get("pwfp"):
        # Password has changed since this token was issued -> invalidate.
        return None
    return user
