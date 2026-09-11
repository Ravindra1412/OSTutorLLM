"""
app/faculty/services/faculty_profile_service.py

Faculty Profile (Section 14). Password changes reuse
app.auth.services.change_password() unchanged (Part 3.5) — not
duplicated here. This module only adds what didn't exist yet:
updating the FacultyProfile-specific fields (department, title/
designation, subjects_taught, bio) in one call.
"""

from app.extensions import db
from app.models import User


def get_profile(user_id: int) -> dict | None:
    user = db.session.get(User, user_id)
    if user is None or not user.is_faculty:
        return None
    profile = user.faculty_profile
    return {
        "name": user.name, "email": user.email,
        "department": profile.department if profile else None,
        "title": profile.title if profile else None,
        "subjects_taught": profile.subjects_taught if profile else None,
        "bio": profile.bio if profile else None,
    }


def update_profile(
    user_id: int, name: str | None = None, department: str | None = None,
    title: str | None = None, subjects_taught: str | None = None, bio: str | None = None,
) -> dict | None:
    user = db.session.get(User, user_id)
    if user is None or not user.is_faculty:
        return None

    if name:
        user.name = name.strip()

    profile = user.faculty_profile
    if profile:
        if department is not None:
            profile.department = department
        if title is not None:
            profile.title = title
        if subjects_taught is not None:
            profile.subjects_taught = subjects_taught
        if bio is not None:
            profile.bio = bio

    db.session.commit()
    return get_profile(user_id)
