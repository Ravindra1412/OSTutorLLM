"""
app/utils/helpers.py

Small, genuinely cross-cutting helpers that don't belong to any single
feature module. Currently: the role-based authorization decorator
referenced throughout Part 3.1 Section 12 (Authorization Strategy).
"""

from functools import wraps

from flask import abort
from flask_login import current_user


def role_required(role: str):
    """Route decorator restricting access to a single role.

    Usage:
        @student_bp.route("/dashboard")
        @login_required
        @role_required("student")
        def dashboard(): ...

    Must be stacked *below* @login_required so current_user is guaranteed
    to be authenticated before the role check runs.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated or getattr(current_user, "role", None) != role:
                abort(403)
            return view_func(*args, **kwargs)

        return wrapped

    return decorator


def current_user_or_none():
    """Returns the current user if authenticated, else None — convenience
    for endpoints that behave differently for logged-in vs anonymous users
    without requiring login."""
    return current_user if current_user.is_authenticated else None
