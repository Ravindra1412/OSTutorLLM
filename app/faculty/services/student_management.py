"""
app/faculty/services/student_management.py

Student Management (Section 5). List/search/filter reuses simple
SQL; the per-student detail view reuses Part 3.9's analytics services
wholesale (they already take an arbitrary `user_id` parameter, not
`current_user` — built that way in Part 3.9 specifically so a future
faculty view could reuse them without modification, and that
assumption holds here with zero changes to any Part 3.9 file).
"""

from datetime import datetime, timezone, timedelta

from app.models import User, StudentProfile, ChatSession, CodeReviewSession
from app.utils.constants import ROLE_STUDENT
from app.analytics.services import (
    progress_tracker, analytics_engine, achievement_manager,
    performance_scorer, timeline_service,
)

ACTIVE_WINDOW_DAYS = 7


def list_students(search: str | None = None, active_only: bool = False, page: int = 1, per_page: int = 20) -> dict:
    query = User.query.filter_by(role=ROLE_STUDENT)

    if search:
        like = f"%{search.strip()}%"
        query = query.filter((User.name.ilike(like)) | (User.email.ilike(like)))

    if active_only:
        cutoff = datetime.now(timezone.utc) - timedelta(days=ACTIVE_WINDOW_DAYS)
        query = query.filter(User.last_login_at.isnot(None), User.last_login_at >= cutoff)

    query = query.order_by(User.name.asc())
    total = query.count()
    students = query.offset((page - 1) * per_page).limit(per_page).all()

    results = []
    for s in students:
        profile: StudentProfile | None = s.student_profile
        scores = performance_scorer.compute_all_scores(s.id)
        results.append({
            "id": s.id,
            "name": s.name,
            "email": s.email,
            "account_status": s.account_status,
            "last_login_at": s.last_login_at.isoformat() if s.last_login_at else None,
            "level": profile.level if profile else 1,
            "xp_total": profile.xp_total if profile else 0,
            "overall_learning_score": scores["overall_learning_score"],
        })

    return {"students": results, "total": total, "page": page, "per_page": per_page}


def get_student_detail(student_id: int) -> dict | None:
    student = User.query.filter_by(id=student_id, role=ROLE_STUDENT).first()
    if student is None:
        return None

    return {
        "profile": {
            "id": student.id, "name": student.name, "email": student.email,
            "account_status": student.account_status,
            "last_login_at": student.last_login_at.isoformat() if student.last_login_at else None,
            "created_at": student.created_at.isoformat(),
        },
        "progress": {
            "tracked_topics": progress_tracker.get_completed_topics(student_id),
            "time_spent": progress_tracker.get_time_spent_summary(student_id),
        },
        "quiz_history": progress_tracker.get_quiz_scores(student_id),
        "code_review_history": progress_tracker.get_code_review_scores(student_id),
        "tutor_sessions": [
            {"id": cs.id, "topic_name": cs.topic_name, "started_at": cs.started_at.isoformat(),
             "ended_at": cs.ended_at.isoformat() if cs.ended_at else None}
            for cs in ChatSession.query.filter_by(user_id=student_id).order_by(ChatSession.started_at.desc()).limit(20).all()
        ],
        "achievements": achievement_manager.get_achievements_summary(student_id),
        "performance_scores": performance_scorer.compute_all_scores(student_id),
        "analytics": analytics_engine.build_full_analytics(student_id),
        "recent_timeline": timeline_service.get_timeline(student_id, limit=20),
    }
