"""
app/auth/services.py

Authentication service layer (Section 16). Every piece of
authentication business logic lives here — registration, login
verification, password change/reset, profile update, audit logging —
so that the route layer (app/routes/auth_pages_routes.py) stays a thin
translation between HTTP/forms and this layer, per the Controller ->
Service -> Repository layering established in Part 3.1 Section 9.

Every mutating operation here also writes an ActivityLog row (Section
18 — Audit Logging) and a line to the file-based activity logger
(Part 3.3), so audit data is queryable from SQL (ActivityLog) AND
tail-able from the log file, satisfying both use cases with one call
site rather than duplicating logging calls across every route.
"""

from datetime import datetime, timezone

from app.extensions import db
from app.models import User, StudentProfile, FacultyProfile, UserSettings, LoginHistory, ActivityLog
from app.utils.logger import get_activity_logger
from app.auth.tokens import (
    generate_email_verification_token, verify_email_verification_token,
    generate_password_reset_token, verify_password_reset_token,
)


class AuthError(Exception):
    """Raised for any auth-specific failure the route layer should show
    as a user-facing message rather than a generic 500 (Section 17)."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _log_activity(user_id: int | None, action: str, details: str = "", ip_address: str | None = None) -> None:
    db.session.add(ActivityLog(user_id=user_id, action=action, details=details, ip_address=ip_address))
    db.session.commit()
    get_activity_logger().info("%s | user_id=%s | %s | ip=%s", action, user_id, details, ip_address)


# --------------------------------------------------------------------
# Registration
# --------------------------------------------------------------------

def register_user(name: str, email: str, password: str, role: str, ip_address: str | None = None) -> User:
    """Creates a User + the appropriate profile row (StudentProfile or
    FacultyProfile) + a default UserSettings row, all in one committed
    transaction. Duplicate-email checking is done by the form's
    validate_email() before this is ever called (Section 4), but a
    second guard here protects any future caller that skips the form."""
    email = email.strip().lower()
    if User.query.filter_by(email=email).first():
        raise AuthError("An account with this email already exists.")

    user = User(name=name.strip(), email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()  # populate user.id for the dependent rows below

    if role == "student":
        db.session.add(StudentProfile(user_id=user.id))
    elif role == "faculty":
        db.session.add(FacultyProfile(user_id=user.id))

    db.session.add(UserSettings(user_id=user.id))
    db.session.commit()

    _log_activity(user.id, "account_created", details=f"role={role}", ip_address=ip_address)
    return user


# --------------------------------------------------------------------
# Login / Logout
# --------------------------------------------------------------------

def authenticate(email: str, password: str, ip_address: str | None = None, user_agent: str | None = None) -> User:
    """Verifies credentials, records a LoginHistory row either way
    (success or failure — Section 6/18), and raises AuthError with a
    deliberately identical message for "no such user" and "wrong
    password" so a caller cannot enumerate registered emails."""
    email = email.strip().lower()
    user = User.query.filter_by(email=email).first()

    success = bool(user and user.check_password(password) and user.is_active_account)

    db.session.add(LoginHistory(
        user_id=user.id if user else None, ip_address=ip_address, user_agent=user_agent, success=success
    ))
    db.session.commit()

    if not success:
        action = "login_failed"
        _log_activity(user.id if user else None, action, details=f"email={email}", ip_address=ip_address)
        if user and not user.is_active_account:
            raise AuthError("This account has been suspended. Please contact support.")
        raise AuthError("Invalid email or password.")

    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()
    _log_activity(user.id, "login_success", ip_address=ip_address)
    return user


def record_logout(user: User, ip_address: str | None = None) -> None:
    _log_activity(user.id, "logout", ip_address=ip_address)


# --------------------------------------------------------------------
# Password management
# --------------------------------------------------------------------

def change_password(user: User, current_password: str, new_password: str, ip_address: str | None = None) -> None:
    if not user.check_password(current_password):
        raise AuthError("Current password is incorrect.")
    user.set_password(new_password)
    db.session.commit()
    _log_activity(user.id, "password_changed", ip_address=ip_address)


def request_password_reset(email: str) -> tuple[User | None, str | None]:
    """Returns (user, token) if the account exists, else (None, None).
    The route layer deliberately shows the same "check your inbox"
    message either way (Section 7/17) so this function's None case
    does not leak account existence to the caller."""
    user = User.query.filter_by(email=email.strip().lower()).first()
    if not user:
        return None, None
    token = generate_password_reset_token(user)
    _log_activity(user.id, "password_reset_requested")
    return user, token


def reset_password_with_token(token: str, new_password: str, ip_address: str | None = None) -> User:
    user = verify_password_reset_token(token, user_lookup_fn=lambda uid: db.session.get(User, uid) if uid else None)
    if user is None:
        raise AuthError("This password reset link is invalid or has expired. Please request a new one.")
    user.set_password(new_password)
    db.session.commit()
    _log_activity(user.id, "password_reset_completed", ip_address=ip_address)
    return user


# --------------------------------------------------------------------
# Email verification (Section 8)
# --------------------------------------------------------------------

def send_verification_email_stub(user: User) -> str:
    """No real email service exists in this phase (explicitly out of
    scope). This generates the token and returns the link that a real
    email-sending integration would deliver. In development, the route
    layer logs this link and — ONLY when FLASK_ENV=development — returns
    it directly in the response so a developer can click straight
    through without configuring SMTP (Section 8's requested local-dev
    alternative)."""
    token = generate_email_verification_token(user)
    verify_url = f"/verify-email/{token}"
    get_activity_logger().info("Verification link for %s: %s (would be emailed in production)", user.email, verify_url)
    return verify_url


def verify_email_token(token: str) -> User:
    uid = verify_email_verification_token(token)
    if uid is None:
        raise AuthError("This verification link is invalid or has expired.")
    user = db.session.get(User, uid)
    if user is None:
        raise AuthError("This verification link is invalid or has expired.")
    user.email_verified = True
    db.session.commit()
    _log_activity(user.id, "email_verified")
    return user


# --------------------------------------------------------------------
# Profile management (Section 9)
# --------------------------------------------------------------------

def update_profile(user: User, name: str, hint_verbosity_pref: int | None = None, bio: str | None = None) -> User:
    user.name = name.strip()
    if user.is_student and user.student_profile and hint_verbosity_pref is not None:
        user.student_profile.hint_verbosity_pref = hint_verbosity_pref
    if user.is_faculty and user.faculty_profile and bio is not None:
        user.faculty_profile.bio = bio
    db.session.commit()
    _log_activity(user.id, "profile_updated")
    return user
