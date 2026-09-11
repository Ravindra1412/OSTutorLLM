"""
app/faculty/services/assignment_management.py

Assignment Management (Section 10). Faculty CRUD + submission
tracking/grading. Student-side submission itself lives in
app/routes/assignment_student_routes.py (a small, separate blueprint —
without it, "Submission Tracking" would have no real data to track).
"""

from datetime import datetime, timezone

from app.extensions import db
from app.models import Assignment, AssignmentSubmission, Topic, User


class AssignmentError(Exception):
    pass


def create_assignment(
    created_by_user_id: int, topic_id: int, title: str, description: str,
    due_at: datetime, allow_late_submission: bool = True, max_score: float = 100.0, is_published: bool = False,
) -> Assignment:
    if db.session.get(Topic, topic_id) is None:
        raise AssignmentError("Topic not found.")
    assignment = Assignment(
        topic_id=topic_id, created_by_user_id=created_by_user_id, title=title.strip(),
        description=description, due_at=due_at, allow_late_submission=allow_late_submission,
        max_score=max_score, is_published=is_published,
    )
    db.session.add(assignment)
    db.session.commit()
    return assignment


def update_assignment(assignment_id: int, **fields) -> Assignment:
    assignment = db.session.get(Assignment, assignment_id)
    if assignment is None:
        raise AssignmentError("Assignment not found.")
    for key in ("title", "description", "due_at", "allow_late_submission", "max_score", "is_published"):
        if key in fields and fields[key] is not None:
            setattr(assignment, key, fields[key])
    db.session.commit()
    return assignment


def delete_assignment(assignment_id: int) -> bool:
    assignment = db.session.get(Assignment, assignment_id)
    if assignment is None:
        return False
    db.session.delete(assignment)
    db.session.commit()
    return True


def list_assignments(published_only: bool = False) -> list[dict]:
    query = Assignment.query
    if published_only:
        query = query.filter_by(is_published=True)
    assignments = query.order_by(Assignment.due_at.asc()).all()
    return [
        {
            "id": a.id, "title": a.title, "topic_name": a.topic.name, "due_at": a.due_at.isoformat(),
            "is_published": a.is_published, "max_score": a.max_score,
            "submission_count": len(a.submissions),
        }
        for a in assignments
    ]


def get_submissions(assignment_id: int) -> dict | None:
    assignment = db.session.get(Assignment, assignment_id)
    if assignment is None:
        return None
    subs = AssignmentSubmission.query.filter_by(assignment_id=assignment_id).order_by(
        AssignmentSubmission.submitted_at.desc()
    ).all()
    return {
        "assignment_title": assignment.title,
        "due_at": assignment.due_at.isoformat(),
        "submissions": [
            {
                "id": s.id, "student_name": s.user.name, "student_id": s.user_id,
                "submitted_at": s.submitted_at.isoformat(), "is_late": s.is_late,
                "score": s.score, "graded_at": s.graded_at.isoformat() if s.graded_at else None,
            }
            for s in subs
        ],
    }


def grade_submission(submission_id: int, grader_user_id: int, score: float, feedback: str | None) -> AssignmentSubmission:
    submission = db.session.get(AssignmentSubmission, submission_id)
    if submission is None:
        raise AssignmentError("Submission not found.")
    submission.score = score
    submission.feedback = feedback
    submission.graded_at = datetime.now(timezone.utc)
    submission.graded_by_user_id = grader_user_id
    db.session.commit()
    return submission


def assignment_analytics(assignment_id: int) -> dict | None:
    """Section 10 — Assignment Analytics: submission rate + average
    score, computed against every student on the platform (see the
    faculty package's scope note on the lack of enrollment tables)."""
    from app.utils.constants import ROLE_STUDENT

    assignment = db.session.get(Assignment, assignment_id)
    if assignment is None:
        return None

    total_students = User.query.filter_by(role=ROLE_STUDENT).count()
    subs = assignment.submissions
    graded = [s.score for s in subs if s.score is not None]
    late_count = sum(1 for s in subs if s.is_late)

    return {
        "total_students": total_students,
        "submission_count": len(subs),
        "submission_rate_percent": round(100.0 * len(subs) / total_students, 1) if total_students else 0.0,
        "late_submission_count": late_count,
        "average_score": round(sum(graded) / len(graded), 2) if graded else None,
        "graded_count": len(graded),
    }
