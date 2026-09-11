"""
app/routes/settings_routes.py

Settings blueprint (Section 4). Implements real (if minimal) read/update
of `student_profiles.hint_verbosity_pref` (Part 3.1 Section 8.3) — this
is plain preference storage, not a feature module, so it is safely in
scope for the foundation phase.
"""

from flask import Blueprint, request

from flask_login import login_required, current_user

from app.extensions import db
from app.utils.constants import ROLE_STUDENT, HINT_VERBOSITY_MIN, HINT_VERBOSITY_MAX
from app.utils.formatters import success_response
from app.utils.helpers import role_required
from app.utils.validators import ValidationError

settings_bp = Blueprint("settings_bp", __name__, url_prefix="/api/settings")


@settings_bp.route("/preferences", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def get_preferences():
    profile = current_user.student_profile
    return success_response({"hint_verbosity_pref": profile.hint_verbosity_pref if profile else None})


@settings_bp.route("/preferences", methods=["PUT"])
@login_required
@role_required(ROLE_STUDENT)
def update_preferences():
    data = request.get_json(silent=True) or {}
    verbosity = data.get("hint_verbosity_pref")

    if verbosity is None or not isinstance(verbosity, int) or not (
        HINT_VERBOSITY_MIN <= verbosity <= HINT_VERBOSITY_MAX
    ):
        raise ValidationError(
            f"hint_verbosity_pref must be an integer between {HINT_VERBOSITY_MIN} and {HINT_VERBOSITY_MAX}.",
            field="hint_verbosity_pref",
        )

    profile = current_user.student_profile
    profile.hint_verbosity_pref = verbosity
    db.session.commit()

    return success_response({"hint_verbosity_pref": profile.hint_verbosity_pref}, message="Preferences updated.")


# --- Part 3.10, Section 15: role-agnostic account settings (theme, ---
# --- language, notification toggles) — backs the pre-existing but ---
# --- previously-unused UserSettings table (Part 3.4). ---

def _settings_dict(s):
    return {
        "theme": s.theme, "language": s.language,
        "email_notifications_enabled": s.email_notifications_enabled,
        "achievement_notifications_enabled": s.achievement_notifications_enabled,
        "streak_reminders_enabled": s.streak_reminders_enabled,
        "high_contrast_enabled": s.high_contrast_enabled,
        "reduce_motion_enabled": s.reduce_motion_enabled,
    }


@settings_bp.route("/account", methods=["GET"])
@login_required
def get_account_settings():
    return success_response(_settings_dict(current_user.settings))


@settings_bp.route("/account", methods=["PUT"])
@login_required
def update_account_settings():
    data = request.get_json(silent=True) or {}
    settings = current_user.settings

    if "theme" in data:
        if data["theme"] not in ("light", "dark"):
            raise ValidationError("theme must be 'light' or 'dark'.", field="theme")
        settings.theme = data["theme"]
    if "language" in data:
        settings.language = data["language"]
    for flag in ("email_notifications_enabled", "achievement_notifications_enabled",
                 "streak_reminders_enabled", "high_contrast_enabled", "reduce_motion_enabled"):
        if flag in data:
            setattr(settings, flag, bool(data[flag]))

    db.session.commit()
    return success_response(_settings_dict(settings), message="Settings updated.")
