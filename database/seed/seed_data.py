"""
database/seed/seed_data.py

Database seeding script (Part 3.4, Section 14). Populates a fresh
database with representative sample data for development and demo
purposes: sample students, faculty, topics, lessons, commands, and a
quiz with questions.

Usage:
    flask seed-db          (registered CLI command — see app/__init__.py)

or directly:
    python database/seed/seed_data.py

Idempotent: re-running this script is safe — it checks for existing
records (by unique field) before inserting, so it won't create
duplicates if run twice against the same database.
"""

import json
import os
import sys

# Allow running this file directly (`python database/seed/seed_data.py`)
# by ensuring the project root is on sys.path, since it lives two
# directories below the root rather than at top level like run.py.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.extensions import db
from app.models import (
    User, StudentProfile, FacultyProfile, Topic, Lesson, Command,
    Quiz, QuizQuestion, Badge,
)


def seed_topics_and_lessons():
    topics_data = [
        {"name": "Navigation", "category": "Linux Commands", "difficulty_level": 1,
         "description": "Moving around the filesystem: pwd, cd, ls."},
        {"name": "File Permissions", "category": "Linux Commands", "difficulty_level": 2,
         "description": "Understanding and modifying read/write/execute permissions."},
        {"name": "Piping & Redirection", "category": "Linux Commands", "difficulty_level": 2,
         "description": "Connecting commands together and redirecting output."},
        {"name": "Loops", "category": "Shell Scripting", "difficulty_level": 3,
         "description": "for, while, and until loops in Bash."},
        {"name": "Conditionals", "category": "Shell Scripting", "difficulty_level": 3,
         "description": "if/elif/else and test expressions in Bash."},
    ]

    created = {}
    for data in topics_data:
        topic = Topic.query.filter_by(name=data["name"]).first()
        if not topic:
            topic = Topic(**data)
            db.session.add(topic)
            db.session.flush()
        created[topic.name] = topic

    lesson_data = [
        ("Navigation", "Understanding the filesystem tree", 1),
        ("Navigation", "pwd, cd, and relative vs absolute paths", 2),
        ("File Permissions", "Reading permission strings (rwxr-xr-x)", 1),
        ("File Permissions", "Using chmod with octal notation", 2),
        ("Loops", "The for loop over a list", 1),
        ("Loops", "The while loop and break/continue", 2),
    ]
    for topic_name, title, seq in lesson_data:
        topic = created[topic_name]
        exists = Lesson.query.filter_by(topic_id=topic.id, sequence_order=seq).first()
        if not exists:
            db.session.add(Lesson(
                topic_id=topic.id, title=title,
                content_summary=f"Reference summary for: {title}", sequence_order=seq,
            ))

    db.session.commit()
    return created


def seed_commands(topics: dict):
    commands_data = [
        {"name": "ls", "syntax": "ls [OPTIONS] [PATH]", "description": "List directory contents.",
         "category": "Navigation", "topic_id": topics["Navigation"].id},
        {"name": "cd", "syntax": "cd [PATH]", "description": "Change the current working directory.",
         "category": "Navigation", "topic_id": topics["Navigation"].id},
        {"name": "chmod", "syntax": "chmod [OPTIONS] MODE FILE", "description": "Change file mode/permissions.",
         "category": "File Permissions", "topic_id": topics["File Permissions"].id},
        {"name": "grep", "syntax": "grep [OPTIONS] PATTERN [FILE...]", "description": "Search text using patterns.",
         "category": "Piping & Redirection", "topic_id": topics["Piping & Redirection"].id},
    ]
    for data in commands_data:
        exists = Command.query.filter_by(name=data["name"], syntax=data["syntax"]).first()
        if not exists:
            db.session.add(Command(**data))
    db.session.commit()


def seed_badges():
    badges_data = [
        {"name": "First Steps", "description": "Complete your first tutor session.", "tier": "gold", "xp_reward": 50},
        {"name": "5-Day Streak", "description": "Practice 5 days in a row.", "tier": "gold", "xp_reward": 75},
        {"name": "Quiz Master", "description": "Score 90%+ on any quiz.", "tier": "silver", "xp_reward": 40},
        {"name": "Debugger", "description": "Correctly identify 10 script bugs.", "tier": "bronze", "xp_reward": 25},
    ]
    for data in badges_data:
        if not Badge.query.filter_by(name=data["name"]).first():
            db.session.add(Badge(**data))
    db.session.commit()


def seed_quiz(topics: dict):
    topic = topics["Loops"]
    quiz = Quiz.query.filter_by(title="Shell Loops Basics").first()
    if not quiz:
        quiz = Quiz(topic_id=topic.id, title="Shell Loops Basics", difficulty_level=2)
        db.session.add(quiz)
        db.session.flush()

        db.session.add(QuizQuestion(
            quiz_id=quiz.id,
            question_text="What does `for i in 1 2 3; do echo $i; done` print?",
            question_type="mcq",
            options_json=json.dumps(["1 2 3 on one line", "1, 2, 3 on separate lines", "A syntax error", "Nothing"]),
            correct_answer="1, 2, 3 on separate lines",
            difficulty_level=1,
        ))
        db.session.add(QuizQuestion(
            quiz_id=quiz.id,
            question_text="Complete: chmod ___ deploy.sh (to make it executable)",
            question_type="fill_blank",
            correct_answer="+x",
            difficulty_level=2,
        ))
    db.session.commit()


def seed_users():
    students = [
        {"name": "Aisha Khan", "email": "aisha.khan@example.edu"},
        {"name": "Ravi Menon", "email": "ravi.menon@example.edu"},
        {"name": "Tom Lee", "email": "tom.lee@example.edu"},
    ]
    for data in students:
        if not User.query.filter_by(email=data["email"]).first():
            user = User(name=data["name"], email=data["email"], role="student")
            user.set_password("Password123!")
            db.session.add(user)
            db.session.flush()
            db.session.add(StudentProfile(user_id=user.id))

    faculty = {"name": "Dr. Elena Ruiz", "email": "elena.ruiz@example.edu"}
    if not User.query.filter_by(email=faculty["email"]).first():
        user = User(name=faculty["name"], email=faculty["email"], role="faculty")
        user.set_password("Password123!")
        db.session.add(user)
        db.session.flush()
        db.session.add(FacultyProfile(user_id=user.id, department="Computer Science", title="Lab Instructor"))

    db.session.commit()


def run_seed():
    topics = seed_topics_and_lessons()
    seed_commands(topics)
    seed_badges()
    seed_quiz(topics)
    seed_users()
    print("Database seeding complete.")
    print(f"  Topics: {Topic.query.count()}")
    print(f"  Lessons: {Lesson.query.count()}")
    print(f"  Commands: {Command.query.count()}")
    print(f"  Badges: {Badge.query.count()}")
    print(f"  Quizzes: {Quiz.query.count()} (with {QuizQuestion.query.count()} questions)")
    print(f"  Users: {User.query.count()}")


if __name__ == "__main__":
    from app import create_app

    app = create_app(os.environ.get("APP_ENV", "development"))
    with app.app_context():
        run_seed()
