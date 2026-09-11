"""
app/models/faculty_profile.py

`faculty_profiles` table (Part 3.4, Section 5) — extends `users` 1:1
for instructor-specific fields, mirroring the StudentProfile pattern
(Part 3.1, Section 8.3 rationale: keep the core auth table lean).
"""

from app.extensions import db
from app.models.mixins import TimestampMixin


class FacultyProfile(TimestampMixin, db.Model):
    __tablename__ = "faculty_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    department = db.Column(db.String(150), nullable=True)
    title = db.Column(db.String(100), nullable=True)  # e.g. "Assistant Professor", "Lab Instructor"
    bio = db.Column(db.Text, nullable=True)
    # Part 3.10, Section 14: comma-separated subject/topic names taught,
    # kept as a simple string (not a join table) — this is a display
    # field on the faculty profile, not a real enrollment/assignment
    # relationship (no such concept exists in this schema; see
    # docs/project-report-part3.10.md for the scope note).
    subjects_taught = db.Column(db.String(255), nullable=True)

    user = db.relationship("User", back_populates="faculty_profile")

    def __repr__(self) -> str:
        return f"<FacultyProfile user_id={self.user_id} department={self.department}>"
