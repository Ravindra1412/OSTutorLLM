"""
app/faculty/services/notification_service.py

Notification Center (Section 13). Writes into the existing
`notifications` table (Part 3.4) that already backs the navbar bell
(Part 3.2) — a faculty announcement is just a Notification row created
for every student, using the `faculty` type Part 3.4 already reserved
for exactly this.
"""

from app.extensions import db
from app.models import User, Notification
from app.models.notification import TYPE_FACULTY, TYPE_SYSTEM, TYPE_PROGRESS
from app.utils.constants import ROLE_STUDENT


def send_announcement(message: str) -> int:
    """Section 13 — Announcements, broadcast to every student."""
    student_ids = [u.id for u in User.query.filter_by(role=ROLE_STUDENT).all()]
    for sid in student_ids:
        db.session.add(Notification(user_id=sid, message=message, notification_type=TYPE_FACULTY))
    db.session.commit()
    return len(student_ids)


def send_student_alert(student_id: int, message: str) -> Notification:
    """Section 13 — Student Alerts, targeted at one student (e.g. after
    reviewing their weak-topic signals on the Student Detail page)."""
    if db.session.get(User, student_id) is None:
        raise ValueError("Student not found.")
    notif = Notification(user_id=student_id, message=message, notification_type=TYPE_PROGRESS)
    db.session.add(notif)
    db.session.commit()
    return notif


def send_assignment_reminder(assignment_id: int) -> int:
    """Section 13 — Assignment Reminders, to every student who has not
    yet submitted."""
    from app.models import Assignment, AssignmentSubmission

    assignment = db.session.get(Assignment, assignment_id)
    if assignment is None:
        raise ValueError("Assignment not found.")

    submitted_ids = {s.user_id for s in AssignmentSubmission.query.filter_by(assignment_id=assignment_id).all()}
    all_student_ids = {u.id for u in User.query.filter_by(role=ROLE_STUDENT).all()}
    pending_ids = all_student_ids - submitted_ids

    for sid in pending_ids:
        db.session.add(Notification(
            user_id=sid, notification_type=TYPE_SYSTEM,
            message=f"Reminder: '{assignment.title}' is due {assignment.due_at.strftime('%Y-%m-%d %H:%M')}.",
        ))
    db.session.commit()
    return len(pending_ids)


def notify_quiz_published(quiz_id: int) -> int:
    """Section 13 — Quiz Notifications, sent automatically when a
    faculty-authored quiz is published (see faculty_quiz_routes.py)."""
    from app.models import Quiz

    quiz = db.session.get(Quiz, quiz_id)
    if quiz is None:
        raise ValueError("Quiz not found.")

    student_ids = [u.id for u in User.query.filter_by(role=ROLE_STUDENT).all()]
    for sid in student_ids:
        db.session.add(Notification(
            user_id=sid, notification_type=TYPE_SYSTEM,
            message=f"New quiz published: '{quiz.title}' ({quiz.topic.name}).",
        ))
    db.session.commit()
    return len(student_ids)


def get_faculty_notifications(faculty_user_id: int, unread_only: bool = False) -> list[dict]:
    query = Notification.query.filter_by(user_id=faculty_user_id)
    if unread_only:
        query = query.filter_by(is_read=False)
    rows = query.order_by(Notification.created_at.desc()).limit(50).all()
    return [
        {"id": n.id, "message": n.message, "type": n.notification_type, "is_read": n.is_read,
         "created_at": n.created_at.isoformat()}
        for n in rows
    ]


def mark_notification_read(faculty_user_id: int, notification_id: int) -> bool:
    notif = Notification.query.filter_by(id=notification_id, user_id=faculty_user_id).first()
    if notif is None:
        return False
    notif.is_read = True
    db.session.commit()
    return True
