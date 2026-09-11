"""
app/faculty/services/content_management.py

Content Management (Section 7). CRUD over the curriculum tables that
already existed (Topic, Lesson, Command, ShellProgram — all Part 3.4)
plus two new capabilities this phase actually needed: file uploads
(ContentResource) and snapshot-based version control (ContentRevision).

Every Topic/Lesson mutation calls `_snapshot()` FIRST, capturing the
row's pre-edit state — this is what makes `restore_revision()` a real
undo, not just a change log.
"""

import json
import os
import uuid

from werkzeug.utils import secure_filename
from flask import current_app

from app.extensions import db
from app.models import Topic, Lesson, Command, ShellProgram, ContentResource, ContentRevision
from app.models.content_revision import CONTENT_TYPE_TOPIC, CONTENT_TYPE_LESSON


class ContentError(Exception):
    pass


def _validate_difficulty(level) -> int:
    try:
        level = int(level)
    except (TypeError, ValueError):
        raise ContentError("difficulty_level must be an integer between 1 and 5.")
    if not (1 <= level <= 5):
        raise ContentError("difficulty_level must be between 1 and 5.")
    return level


# --- Version control (Section 7) ---

def _snapshot(content_type: str, row, edited_by_user_id: int, fields: list[str]) -> None:
    data = {f: getattr(row, f) for f in fields}
    # datetimes aren't JSON-serializable — string-ify defensively
    data = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in data.items()}
    db.session.add(ContentRevision(
        content_type=content_type, content_id=row.id,
        snapshot_json=json.dumps(data), edited_by_user_id=edited_by_user_id,
    ))


def get_revisions(content_type: str, content_id: int) -> list[dict]:
    rows = (
        ContentRevision.query.filter_by(content_type=content_type, content_id=content_id)
        .order_by(ContentRevision.created_at.desc()).all()
    )
    return [
        {"id": r.id, "snapshot": json.loads(r.snapshot_json), "edited_by": r.edited_by.name if r.edited_by else "Unknown",
         "created_at": r.created_at.isoformat()}
        for r in rows
    ]


def restore_revision(revision_id: int) -> bool:
    rev = db.session.get(ContentRevision, revision_id)
    if rev is None:
        return False
    snapshot = json.loads(rev.snapshot_json)

    model = Topic if rev.content_type == CONTENT_TYPE_TOPIC else Lesson
    row = db.session.get(model, rev.content_id)
    if row is None:
        return False

    for field, value in snapshot.items():
        setattr(row, field, value)
    db.session.commit()
    return True


# --- Topics ---

TOPIC_FIELDS = ["name", "category", "description", "difficulty_level"]


def list_topics() -> list[Topic]:
    return Topic.query.order_by(Topic.category.asc(), Topic.difficulty_level.asc()).all()


def create_topic(name: str, category: str, description: str, difficulty_level: int) -> Topic:
    if Topic.query.filter_by(name=name).first():
        raise ContentError(f"A topic named '{name}' already exists.")
    difficulty_level = _validate_difficulty(difficulty_level)
    topic = Topic(name=name.strip(), category=category.strip(), description=description, difficulty_level=difficulty_level)
    db.session.add(topic)
    db.session.commit()
    return topic


def update_topic(topic_id: int, edited_by_user_id: int, **fields) -> Topic:
    topic = db.session.get(Topic, topic_id)
    if topic is None:
        raise ContentError("Topic not found.")
    _snapshot(CONTENT_TYPE_TOPIC, topic, edited_by_user_id, TOPIC_FIELDS)
    if "difficulty_level" in fields and fields["difficulty_level"] is not None:
        fields["difficulty_level"] = _validate_difficulty(fields["difficulty_level"])
    for key, value in fields.items():
        if key in TOPIC_FIELDS and value is not None:
            setattr(topic, key, value)
    db.session.commit()
    return topic


def delete_topic(topic_id: int) -> bool:
    topic = db.session.get(Topic, topic_id)
    if topic is None:
        return False
    db.session.delete(topic)
    db.session.commit()
    return True


# --- Lessons ---

LESSON_FIELDS = ["title", "content_summary", "sequence_order"]


def create_lesson(topic_id: int, title: str, content_summary: str, sequence_order: int) -> Lesson:
    if db.session.get(Topic, topic_id) is None:
        raise ContentError("Topic not found.")
    lesson = Lesson(topic_id=topic_id, title=title.strip(), content_summary=content_summary, sequence_order=sequence_order)
    db.session.add(lesson)
    db.session.commit()
    return lesson


def update_lesson(lesson_id: int, edited_by_user_id: int, **fields) -> Lesson:
    lesson = db.session.get(Lesson, lesson_id)
    if lesson is None:
        raise ContentError("Lesson not found.")
    _snapshot(CONTENT_TYPE_LESSON, lesson, edited_by_user_id, LESSON_FIELDS)
    for key, value in fields.items():
        if key in LESSON_FIELDS and value is not None:
            setattr(lesson, key, value)
    db.session.commit()
    return lesson


def delete_lesson(lesson_id: int) -> bool:
    lesson = db.session.get(Lesson, lesson_id)
    if lesson is None:
        return False
    db.session.delete(lesson)
    db.session.commit()
    return True


# --- Linux Command Library / Shell Program Examples ---

def create_command(name: str, syntax: str, description: str, category: str | None, topic_id: int | None) -> Command:
    cmd = Command(name=name.strip(), syntax=syntax.strip(), description=description, category=category, topic_id=topic_id)
    db.session.add(cmd)
    db.session.commit()
    return cmd


def delete_command(command_id: int) -> bool:
    cmd = db.session.get(Command, command_id)
    if cmd is None:
        return False
    db.session.delete(cmd)
    db.session.commit()
    return True


def create_shell_program(topic_id: int | None, title: str, description: str, sample_code: str, difficulty_level: int) -> ShellProgram:
    program = ShellProgram(
        topic_id=topic_id, title=title.strip(), description=description,
        sample_code=sample_code, difficulty_level=difficulty_level,
    )
    db.session.add(program)
    db.session.commit()
    return program


def delete_shell_program(program_id: int) -> bool:
    program = db.session.get(ShellProgram, program_id)
    if program is None:
        return False
    db.session.delete(program)
    db.session.commit()
    return True


# --- File uploads (Section 7 — Notes/PDFs/PPTs/Images) ---

def save_resource_file(topic_id: int, uploaded_by_user_id: int, file_storage, description: str | None) -> ContentResource:
    """Validates extension + size (Flask's MAX_CONTENT_LENGTH already
    rejects oversized bodies before this runs) and writes to a
    collision-free, non-guessable filename under Config.UPLOAD_FOLDER
    — the client-supplied filename is NEVER used as the on-disk path
    (classic path-traversal/overwrite prevention)."""
    if db.session.get(Topic, topic_id) is None:
        raise ContentError("Topic not found.")

    original_name = secure_filename(file_storage.filename or "")
    if not original_name or "." not in original_name:
        raise ContentError("File must have a valid name and extension.")

    ext = original_name.rsplit(".", 1)[1].lower()
    allowed = current_app.config["ALLOWED_UPLOAD_EXTENSIONS"]
    if ext not in allowed:
        raise ContentError(f"File type '.{ext}' is not allowed. Allowed types: {', '.join(sorted(allowed))}.")

    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)

    stored_filename = f"{uuid.uuid4().hex}.{ext}"
    full_path = os.path.join(upload_dir, stored_filename)
    file_storage.save(full_path)
    size_bytes = os.path.getsize(full_path)

    resource = ContentResource(
        topic_id=topic_id, uploaded_by_user_id=uploaded_by_user_id,
        original_filename=original_name, stored_filename=stored_filename,
        file_type=ext, file_size_bytes=size_bytes, description=description,
    )
    db.session.add(resource)
    db.session.commit()
    return resource


def list_resources(topic_id: int | None = None) -> list[ContentResource]:
    query = ContentResource.query
    if topic_id:
        query = query.filter_by(topic_id=topic_id)
    return query.order_by(ContentResource.created_at.desc()).all()


def delete_resource(resource_id: int) -> bool:
    resource = db.session.get(ContentResource, resource_id)
    if resource is None:
        return False
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    full_path = os.path.join(upload_dir, resource.stored_filename)
    if os.path.exists(full_path):
        os.remove(full_path)
    db.session.delete(resource)
    db.session.commit()
    return True
