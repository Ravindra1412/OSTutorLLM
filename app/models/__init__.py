"""
app/models/__init__.py

Imports every model class so that:
  1. `from app.models import User, Topic, Quiz, ...` works from anywhere.
  2. SQLAlchemy's metadata (db.metadata) is fully populated before
     `db.create_all()` or a Flask-Migrate autogenerate runs — a model
     that is never imported is invisible to SQLAlchemy, a very common
     beginner bug this file exists specifically to prevent.

Part 3.4 expands this from the 7 foundation-phase models (Part 3.3) to
the full 20-plus-model schema. Import order below is grouped by domain
(Authentication -> Curriculum -> Quiz -> Tutor -> Learning ->
Gamification -> Platform) purely for human readability; SQLAlchemy
resolves relationship() string references lazily, so import order has
no functional effect on correctness.
"""

# --- Authentication & Identity ---
from app.models.user import User
from app.models.login_history import LoginHistory
from app.models.student_profile import StudentProfile
from app.models.faculty_profile import FacultyProfile
from app.models.user_settings import UserSettings

# --- Curriculum / Content ---
from app.models.topic import Topic
from app.models.lesson import Lesson
from app.models.command import Command
from app.models.shell_program import ShellProgram

# --- Quiz Schema ---
from app.models.quiz import Quiz
from app.models.quiz_question import QuizQuestion
from app.models.quiz_attempt import QuizAttempt
from app.models.quiz_result import QuizResult
from app.models.quiz_history import QuizHistory  # legacy summary table, Part 3.3

# --- Tutor Session ---
from app.models.chat_session import ChatSession
from app.models.chat_message import ChatMessage

# --- Code Review (Part 3.8) ---
from app.models.code_review_session import CodeReviewSession
from app.models.code_submission import CodeSubmission

# --- Learning Tracking ---
from app.models.progress import Progress
from app.models.completed_lesson import CompletedLesson
from app.models.bookmark import Bookmark

# --- Learning Analytics (Part 3.9) ---
from app.models.learning_timeline import LearningTimeline
from app.models.recommendation import Recommendation

# --- Gamification ---
from app.models.badge import Badge
from app.models.achievement import Achievement

# --- Platform ---
from app.models.notification import Notification
from app.models.activity_log import ActivityLog
from app.models.system_configuration import SystemConfiguration

# --- Faculty Dashboard & Administration (Part 3.10) ---
from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.content_resource import ContentResource
from app.models.content_revision import ContentRevision

# --- AI Learning Mentor (Part 3.13) ---
from app.models.study_plan import StudyPlan
from app.models.mentor_interaction import MentorInteraction

__all__ = [
    "User",
    "LoginHistory",
    "StudentProfile",
    "FacultyProfile",
    "UserSettings",
    "Topic",
    "Lesson",
    "Command",
    "ShellProgram",
    "Quiz",
    "QuizQuestion",
    "QuizAttempt",
    "QuizResult",
    "QuizHistory",
    "ChatSession",
    "ChatMessage",
    "CodeReviewSession",
    "CodeSubmission",
    "Progress",
    "CompletedLesson",
    "Bookmark",
    "LearningTimeline",
    "Recommendation",
    "Badge",
    "Achievement",
    "Notification",
    "ActivityLog",
    "SystemConfiguration",
    "Assignment",
    "AssignmentSubmission",
    "ContentResource",
    "ContentRevision",
    "StudyPlan",
    "MentorInteraction",
]
