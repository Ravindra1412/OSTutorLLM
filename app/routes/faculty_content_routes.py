"""
app/routes/faculty_content_routes.py

Content Management (Section 7) — Topics, Lessons, the Linux Command
Library, Shell Programming Examples, file uploads, and version
control, all over app/faculty/services/content_management.py.
"""

from flask import Blueprint, request, send_file
from flask_login import login_required, current_user

from app.utils.constants import ROLE_FACULTY
from app.utils.formatters import success_response, fail_response
from app.utils.helpers import role_required
from app.utils.validators import ValidationError, require_fields
from app.faculty.services import content_management as svc

faculty_content_bp = Blueprint("faculty_content_bp", __name__, url_prefix="/api/faculty/content")


def _topic_dict(t):
    return {"id": t.id, "name": t.name, "category": t.category, "description": t.description,
            "difficulty_level": t.difficulty_level, "lesson_count": len(t.lessons)}


def _lesson_dict(l):
    return {"id": l.id, "topic_id": l.topic_id, "title": l.title,
            "content_summary": l.content_summary, "sequence_order": l.sequence_order}


# --- Topics ---

@faculty_content_bp.route("/topics", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def list_topics():
    return success_response([_topic_dict(t) for t in svc.list_topics()])


@faculty_content_bp.route("/topics", methods=["POST"])
@login_required
@role_required(ROLE_FACULTY)
def create_topic():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["name", "category"])
    try:
        topic = svc.create_topic(data["name"], data["category"], data.get("description", ""), data.get("difficulty_level", 1))
    except svc.ContentError as exc:
        return fail_response(str(exc), status_code=400)
    return success_response(_topic_dict(topic), message="Topic created.", status_code=201)


@faculty_content_bp.route("/topics/<int:topic_id>", methods=["PUT"])
@login_required
@role_required(ROLE_FACULTY)
def update_topic(topic_id):
    data = request.get_json(silent=True) or {}
    try:
        topic = svc.update_topic(topic_id, current_user.id, **data)
    except svc.ContentError as exc:
        return fail_response(str(exc), status_code=404)
    return success_response(_topic_dict(topic), message="Topic updated.")


@faculty_content_bp.route("/topics/<int:topic_id>", methods=["DELETE"])
@login_required
@role_required(ROLE_FACULTY)
def delete_topic(topic_id):
    if not svc.delete_topic(topic_id):
        return fail_response("Topic not found.", status_code=404)
    return success_response(message="Topic deleted.")


# --- Lessons ---

@faculty_content_bp.route("/lessons", methods=["POST"])
@login_required
@role_required(ROLE_FACULTY)
def create_lesson():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["topic_id", "title", "content_summary"])
    try:
        lesson = svc.create_lesson(data["topic_id"], data["title"], data["content_summary"], data.get("sequence_order", 0))
    except svc.ContentError as exc:
        return fail_response(str(exc), status_code=400)
    return success_response(_lesson_dict(lesson), message="Lesson created.", status_code=201)


@faculty_content_bp.route("/lessons/<int:lesson_id>", methods=["PUT"])
@login_required
@role_required(ROLE_FACULTY)
def update_lesson(lesson_id):
    data = request.get_json(silent=True) or {}
    try:
        lesson = svc.update_lesson(lesson_id, current_user.id, **data)
    except svc.ContentError as exc:
        return fail_response(str(exc), status_code=404)
    return success_response(_lesson_dict(lesson), message="Lesson updated.")


@faculty_content_bp.route("/lessons/<int:lesson_id>", methods=["DELETE"])
@login_required
@role_required(ROLE_FACULTY)
def delete_lesson(lesson_id):
    if not svc.delete_lesson(lesson_id):
        return fail_response("Lesson not found.", status_code=404)
    return success_response(message="Lesson deleted.")


# --- Version Control (Section 7) ---

@faculty_content_bp.route("/revisions/<string:content_type>/<int:content_id>", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def get_revisions(content_type, content_id):
    if content_type not in ("topic", "lesson"):
        return fail_response("content_type must be 'topic' or 'lesson'.", status_code=400)
    return success_response(svc.get_revisions(content_type, content_id))


@faculty_content_bp.route("/revisions/<int:revision_id>/restore", methods=["POST"])
@login_required
@role_required(ROLE_FACULTY)
def restore_revision(revision_id):
    if not svc.restore_revision(revision_id):
        return fail_response("Revision not found.", status_code=404)
    return success_response(message="Content restored to the selected revision.")


# --- Linux Command Library ---

@faculty_content_bp.route("/commands", methods=["POST"])
@login_required
@role_required(ROLE_FACULTY)
def create_command():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["name", "syntax", "description"])
    cmd = svc.create_command(data["name"], data["syntax"], data["description"], data.get("category"), data.get("topic_id"))
    return success_response({"id": cmd.id, "name": cmd.name}, message="Command added.", status_code=201)


@faculty_content_bp.route("/commands/<int:command_id>", methods=["DELETE"])
@login_required
@role_required(ROLE_FACULTY)
def delete_command(command_id):
    if not svc.delete_command(command_id):
        return fail_response("Command not found.", status_code=404)
    return success_response(message="Command deleted.")


# --- Shell Programming Examples ---

@faculty_content_bp.route("/shell-programs", methods=["POST"])
@login_required
@role_required(ROLE_FACULTY)
def create_shell_program():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["title", "description", "sample_code"])
    program = svc.create_shell_program(
        data.get("topic_id"), data["title"], data["description"], data["sample_code"], data.get("difficulty_level", 1)
    )
    return success_response({"id": program.id, "title": program.title}, message="Shell program added.", status_code=201)


@faculty_content_bp.route("/shell-programs/<int:program_id>", methods=["DELETE"])
@login_required
@role_required(ROLE_FACULTY)
def delete_shell_program(program_id):
    if not svc.delete_shell_program(program_id):
        return fail_response("Shell program not found.", status_code=404)
    return success_response(message="Shell program deleted.")


# --- File Uploads (Notes/PDFs/PPTs/Images) ---

@faculty_content_bp.route("/resources", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def list_resources():
    topic_id = request.args.get("topic_id", type=int)
    resources = svc.list_resources(topic_id)
    return success_response([
        {"id": r.id, "topic_id": r.topic_id, "original_filename": r.original_filename,
         "file_type": r.file_type, "file_size_bytes": r.file_size_bytes, "description": r.description,
         "uploaded_by": r.uploaded_by.name if r.uploaded_by else "Unknown", "created_at": r.created_at.isoformat()}
        for r in resources
    ])


@faculty_content_bp.route("/resources", methods=["POST"])
@login_required
@role_required(ROLE_FACULTY)
def upload_resource():
    if "file" not in request.files:
        raise ValidationError("Missing required field(s): file")
    topic_id = request.form.get("topic_id", type=int)
    if not topic_id:
        raise ValidationError("Missing required field(s): topic_id")

    try:
        resource = svc.save_resource_file(topic_id, current_user.id, request.files["file"], request.form.get("description"))
    except svc.ContentError as exc:
        return fail_response(str(exc), status_code=400)
    return success_response(
        {"id": resource.id, "original_filename": resource.original_filename}, message="File uploaded.", status_code=201
    )


@faculty_content_bp.route("/resources/<int:resource_id>/download", methods=["GET"])
@login_required
@role_required(ROLE_FACULTY)
def download_resource(resource_id):
    import os
    from flask import current_app
    from app.models import ContentResource

    resource = ContentResource.query.get(resource_id)
    if resource is None:
        return fail_response("Resource not found.", status_code=404)
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], resource.stored_filename)
    if not os.path.isfile(path):
        return fail_response("File missing on disk.", status_code=404)
    return send_file(path, as_attachment=True, download_name=resource.original_filename)


@faculty_content_bp.route("/resources/<int:resource_id>", methods=["DELETE"])
@login_required
@role_required(ROLE_FACULTY)
def delete_resource(resource_id):
    if not svc.delete_resource(resource_id):
        return fail_response("Resource not found.", status_code=404)
    return success_response(message="Resource deleted.")
