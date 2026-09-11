"""
app/faculty/services/dashboard_overview.py

Faculty Dashboard Home (Section 4). Platform-wide overview cards —
"active" is defined as a real, visible threshold (login within the
last 7 days) rather than a hidden heuristic, consistent with Part
3.9's own explainability principle.
"""

from datetime import datetime, timezone, timedelta

from app.extensions import db
from app.models import User, QuizHistory, CompletedLesson, LearningTimeline, Notification
from app.utils.constants import ROLE_STUDENT
from app.ai.config import provider_display_name

ACTIVE_WINDOW_DAYS = 7


def get_overview(faculty_user_id: int) -> dict:
    total_students = User.query.filter_by(role=ROLE_STUDENT).count()

    cutoff = datetime.now(timezone.utc) - timedelta(days=ACTIVE_WINDOW_DAYS)
    active_students = User.query.filter(
        User.role == ROLE_STUDENT, User.last_login_at.isnot(None), User.last_login_at >= cutoff
    ).count()

    completed_lessons = CompletedLesson.query.count()

    scores = [r.score for r in QuizHistory.query.all() if r.score is not None]
    average_quiz_score = round(sum(scores) / len(scores), 2) if scores else None

    from app.analytics.services.progress_tracker import get_time_spent_summary
    student_ids = [u.id for u in User.query.filter_by(role=ROLE_STUDENT).all()]
    total_minutes = 0.0
    for sid in student_ids:
        total_minutes += get_time_spent_summary(sid)["total_minutes"]
    average_learning_time_minutes = round(total_minutes / len(student_ids), 1) if student_ids else 0.0

    recent_activity = (
        LearningTimeline.query.order_by(LearningTimeline.created_at.desc()).limit(10).all()
    )
    recent_activity_data = [
        {**e.to_dict(), "student_name": (db.session.get(User, e.user_id).name if db.session.get(User, e.user_id) else "Unknown")}
        for e in recent_activity
    ]

    unread_notifications = Notification.query.filter_by(user_id=faculty_user_id, is_read=False).count()

    return {
        "total_students": total_students,
        "active_students": active_students,
        "active_window_days": ACTIVE_WINDOW_DAYS,
        "completed_lessons": completed_lessons,
        "average_quiz_score": average_quiz_score,
        "average_learning_time_minutes": average_learning_time_minutes,
        "recent_activity": recent_activity_data,
        "system_health": {
            "database": "connected",
            "ai_provider": provider_display_name(),
        },
        "unread_notifications": unread_notifications,
    }
