"""
app/routes/faculty_routes.py

Faculty core blueprint (Section 3/4/9/13/14/15). Extends the Part 3.4
placeholder (the `/roster` endpoint below is that original file,
unchanged) with everything that doesn't belong to a more specific
faculty sub-blueprint (students/content/quizzes/assignments/reports —
each of those is its own file, registered separately in app/__init__.py).
"""

from flask import Blueprint, request, send_file
from flask_login import login_required, current_user

from app.utils.constants import ROLE_FACULTY
from app.utils.formatters import success_response, fail_response
from app.utils.helpers import role_required
from app.utils.validators import ValidationError
from app.faculty.services import (
    dashboard_overview, ai_tutor_management, notification_service,
    settings_service, faculty_profile_service,
)

faculty_bp = Blueprint("faculty_bp", __name__, url_prefix="/api/faculty")


@faculty_bp.route("/roster", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def roster():
    """Original Part 3.4 placeholder — see app/faculty/__init__.py's
    scope note on why this schema has no per-faculty enrollment
    concept. Student Management (faculty_student_routes.py) is the
    real, working student-listing surface built this phase."""
    return success_response(
        {"faculty_id": current_user.id, "students": []},
        message="Faculty roster endpoint reachable (no course data yet).",
    )


# --- Dashboard Home (Section 4) ---

@faculty_bp.route("/dashboard", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def dashboard():
    return success_response(dashboard_overview.get_overview(current_user.id))


# --- AI Tutor Management (Section 9) ---

@faculty_bp.route("/ai-tutor/settings", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def get_ai_settings():
    return success_response(ai_tutor_management.get_ai_settings())


@faculty_bp.route("/ai-tutor/settings", methods=["PUT"])
@login_required
@role_required(ROLE_FACULTY)
def update_ai_settings():
    data = request.get_json(silent=True) or {}
    try:
        updated = ai_tutor_management.update_ai_settings(
            ai_tutor_enabled=data.get("ai_tutor_enabled"),
            default_difficulty=data.get("default_difficulty"),
            default_teaching_mode=data.get("default_teaching_mode"),
            max_hint_stage=data.get("max_hint_stage"),
        )
    except ValueError as exc:
        return fail_response(str(exc), status_code=400)
    return success_response(updated, message="AI Tutor settings updated.")


@faculty_bp.route("/ai-tutor/usage", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def get_tutor_usage():
    return success_response(ai_tutor_management.get_tutor_usage_statistics())


@faculty_bp.route("/ai-tutor/prompt-templates", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def list_prompt_templates():
    return success_response({"templates": ai_tutor_management.list_prompt_templates()})


@faculty_bp.route("/ai-tutor/prompt-templates/<string:filename>", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def get_prompt_template(filename):
    try:
        content = ai_tutor_management.get_prompt_template(filename)
    except (ValueError, FileNotFoundError) as exc:
        return fail_response(str(exc), status_code=404)
    return success_response({"filename": filename, "content": content})


@faculty_bp.route("/ai-tutor/prompt-templates/<string:filename>", methods=["PUT"])
@login_required
@role_required(ROLE_FACULTY)
def update_prompt_template(filename):
    data = request.get_json(silent=True) or {}
    if "content" not in data:
        raise ValidationError("Missing required field(s): content")
    try:
        ai_tutor_management.update_prompt_template(filename, data["content"])
    except (ValueError, FileNotFoundError) as exc:
        return fail_response(str(exc), status_code=404)
    return success_response(message=f"Template '{filename}' updated (previous version backed up).")


# --- Notification Center (Section 13) ---

@faculty_bp.route("/notifications", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def get_notifications():
    unread_only = request.args.get("unread_only", "false").lower() == "true"
    return success_response(notification_service.get_faculty_notifications(current_user.id, unread_only))


@faculty_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
@role_required(ROLE_FACULTY)
def mark_notification_read(notification_id):
    ok = notification_service.mark_notification_read(current_user.id, notification_id)
    if not ok:
        return fail_response("Notification not found.", status_code=404)
    return success_response(message="Marked as read.")


@faculty_bp.route("/announcements", methods=["POST"])
@login_required
@role_required(ROLE_FACULTY)
def send_announcement():
    data = request.get_json(silent=True) or {}
    if not data.get("message"):
        raise ValidationError("Missing required field(s): message")
    count = notification_service.send_announcement(data["message"].strip())
    return success_response({"recipient_count": count}, message="Announcement sent.", status_code=201)


@faculty_bp.route("/students/<int:student_id>/alert", methods=["POST"])
@login_required
@role_required(ROLE_FACULTY)
def send_student_alert(student_id):
    data = request.get_json(silent=True) or {}
    if not data.get("message"):
        raise ValidationError("Missing required field(s): message")
    try:
        notification_service.send_student_alert(student_id, data["message"].strip())
    except ValueError as exc:
        return fail_response(str(exc), status_code=404)
    return success_response(message="Alert sent.", status_code=201)


# --- Faculty Profile (Section 14) ---

@faculty_bp.route("/profile", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def get_profile():
    return success_response(faculty_profile_service.get_profile(current_user.id))


@faculty_bp.route("/profile", methods=["PUT"])
@login_required
@role_required(ROLE_FACULTY)
def update_profile():
    data = request.get_json(silent=True) or {}
    updated = faculty_profile_service.update_profile(
        current_user.id, name=data.get("name"), department=data.get("department"),
        title=data.get("title"), subjects_taught=data.get("subjects_taught"), bio=data.get("bio"),
    )
    return success_response(updated, message="Profile updated.")


@faculty_bp.route("/profile/change-password", methods=["POST"])
@login_required
@role_required(ROLE_FACULTY)
def change_password():
    from app.auth.services import change_password as _change_password, AuthError

    data = request.get_json(silent=True) or {}
    require = ["current_password", "new_password"]
    missing = [f for f in require if not data.get(f)]
    if missing:
        raise ValidationError(f"Missing required field(s): {', '.join(missing)}")
    try:
        _change_password(current_user, data["current_password"], data["new_password"], request.remote_addr)
    except AuthError as exc:
        return fail_response(str(exc), status_code=400)
    return success_response(message="Password changed.")


# --- Settings (Section 15) ---

@faculty_bp.route("/settings/security", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def get_security_settings():
    return success_response(settings_service.get_security_settings())


@faculty_bp.route("/settings/backup", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def get_backup_settings():
    return success_response(settings_service.get_backup_settings())


@faculty_bp.route("/settings/backup", methods=["POST"])
@login_required
@role_required(ROLE_FACULTY)
def trigger_backup():
    try:
        filename = settings_service.trigger_backup()
    except ValueError as exc:
        return fail_response(str(exc), status_code=400)
    return success_response({"filename": filename}, message="Backup created.", status_code=201)


@faculty_bp.route("/settings/backup/<string:filename>/download", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def download_backup(filename):
    import os
    from flask import current_app

    if "/" in filename or "\\" in filename:
        return fail_response("Invalid filename.", status_code=400)
    path = os.path.join(current_app.config["BACKUP_FOLDER"], filename)
    if not os.path.isfile(path):
        return fail_response("Backup not found.", status_code=404)
    return send_file(path, as_attachment=True, download_name=filename)
