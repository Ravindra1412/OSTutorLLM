"""
app/models/user.py

Core `users` table (Part 3.1, Section 8.2; extended Part 3.4 Section 6 —
Authentication Models). Flask-Login integration via UserMixin. Password
hashing uses Werkzeug's PBKDF2-based generate_password_hash/
check_password_hash (Part 3.1, Section 12) — plaintext passwords are
never stored or logged.

Part 3.4 additions:
  - account_status: supports suspending an account without deleting data
  - last_login_at: quick-access denormalized field, updated on each
    successful login (full history lives in LoginHistory)
  - updated_at: general mutation timestamp (name/email edits, etc.)
  - relationships to every new Part 3.4 table

Note on Role/Permissions (Section 6 requirement): this schema uses a
simple `role` string column (student/faculty) rather than separate
Role/Permission tables. For a 2-role academic platform, a full RBAC
join-table system would add migration/query overhead with no real
benefit; the future-scalability path to a proper Role/Permission model
is documented in docs/project-report-part3.4.md, Section 21.
"""

from datetime import datetime, timezone

from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db

ACCOUNT_STATUS_ACTIVE = "active"
ACCOUNT_STATUS_SUSPENDED = "suspended"
ACCOUNT_STATUS_DEACTIVATED = "deactivated"


def _utcnow():
    return datetime.now(timezone.utc)


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student", index=True)  # 'student' | 'faculty'
    account_status = db.Column(db.String(20), nullable=False, default=ACCOUNT_STATUS_ACTIVE)
    email_verified = db.Column(db.Boolean, nullable=False, default=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        db.CheckConstraint("role IN ('student','faculty')", name="ck_users_role"),
        db.CheckConstraint(
            "account_status IN ('active','suspended','deactivated')", name="ck_users_account_status"
        ),
    )

    # --- Relationships (back_populates kept explicit for readability) ---
    student_profile = db.relationship(
        "StudentProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    faculty_profile = db.relationship(
        "FacultyProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    settings = db.relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    progress_entries = db.relationship("Progress", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = db.relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    quiz_history = db.relationship("QuizHistory", back_populates="user", cascade="all, delete-orphan")
    quiz_attempts = db.relationship("QuizAttempt", back_populates="user", cascade="all, delete-orphan")
    achievements = db.relationship("Achievement", back_populates="user", cascade="all, delete-orphan")
    bookmarks = db.relationship("Bookmark", back_populates="user", cascade="all, delete-orphan")
    completed_lessons = db.relationship("CompletedLesson", back_populates="user", cascade="all, delete-orphan")
    notifications = db.relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    login_history = db.relationship("LoginHistory", back_populates="user", cascade="all, delete-orphan")
    activity_logs = db.relationship("ActivityLog", back_populates="user", cascade="all, delete-orphan")
    code_review_sessions = db.relationship("CodeReviewSession", back_populates="user", cascade="all, delete-orphan")
    timeline_events = db.relationship("LearningTimeline", back_populates="user", cascade="all, delete-orphan")
    recommendations = db.relationship("Recommendation", back_populates="user", cascade="all, delete-orphan")

    # --- Password helpers ---
    def set_password(self, raw_password: str) -> None:
        try:
            if current_app and current_app.config.get("TESTING"):
                self.password_hash = generate_password_hash(raw_password, method="pbkdf2:sha256:1")
                return
        except Exception:
            pass
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    # --- Convenience / authorization helpers ---
    @property
    def is_faculty(self) -> bool:
        return self.role == "faculty"

    @property
    def is_student(self) -> bool:
        return self.role == "student"

    @property
    def is_active_account(self) -> bool:
        """Distinct from Flask-Login's UserMixin.is_active (session concept) —
        this checks the persisted account_status field."""
        return self.account_status == ACCOUNT_STATUS_ACTIVE

    def to_dict(self) -> dict:
        """Safe, public-facing representation — never includes password_hash."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "account_status": self.account_status,
            "email_verified": self.email_verified,
            "created_at": self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"