"""
app/routes/code_review_routes.py

Code Review JSON API (Section 15). Thin translation layer over
app.code_review.services.review_service, mirroring the exact
Controller pattern from Part 3.6 (tutor_routes.py) and Part 3.7
(quiz_routes.py) — all workflow/security/scoring logic lives in the
service layer, never here.
"""

from flask import Blueprint, request
from flask_login import login_required, current_user

from app.extensions import db
from app.models import CodeReviewSession, CodeSubmission
from app.utils.constants import ROLE_STUDENT
from app.utils.formatters import success_response, fail_response
from app.utils.helpers import role_required
from app.utils.validators import require_fields, ValidationError
from app.code_review.services import review_service
from app.code_review.topics import CODE_REVIEW_TOPICS

code_review_bp = Blueprint("code_review_bp", __name__, url_prefix="/api/code-review")


def _serialize_submission(submission: CodeSubmission) -> dict:
    import json
    return {
        "submission_id": submission.id,
        "session_id": submission.session_id,
        "submission_number": submission.submission_number,
        "code_text": submission.code_text,
        "hint_stage": submission.hint_stage,
        "hints_used_count": submission.hints_used_count,
        "static_findings": json.loads(submission.static_analysis_json) if submission.static_analysis_json else [],
        "feedback": json.loads(submission.llm_feedback_json) if submission.llm_feedback_json else None,
        "scores": json.loads(submission.scores_json) if submission.scores_json else None,
        "created_at": submission.created_at.isoformat(),
    }


# --------------------------------------------------------------------
# Submit Code API / Review API (Section 15)
# --------------------------------------------------------------------

@code_review_bp.route("/submit", methods=["POST"])
@login_required
@role_required(ROLE_STUDENT)
def submit():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["topic", "code"])

    try:
        outcome = review_service.submit_for_review(
            user_id=current_user.id, topic_name=data["topic"], code=data["code"],
            session_id=data.get("session_id"),
        )
    except review_service.CodeReviewBlockedError as exc:
        return success_response({
            "blocked": True, "explanation": exc.message,
            "security_categories": [f.category for f in exc.security_findings],
        }, message="Submission was not reviewed for safety reasons.", status_code=200)

    return success_response({
        "blocked": False,
        "session_id": outcome.session.id,
        "submission": _serialize_submission(outcome.submission),
    }, message="Code reviewed.", status_code=201)


@code_review_bp.route("/session/<int:session_id>", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def get_session(session_id):
    session = db.session.get(CodeReviewSession, session_id)
    if session is None or session.user_id != current_user.id:
        return fail_response("Code review session not found.", status_code=404)

    return success_response({
        "session_id": session.id, "topic": session.topic_name, "status": session.status,
        "submissions": [_serialize_submission(s) for s in session.submissions],
    })


# --------------------------------------------------------------------
# Hint API (Section 15)
# --------------------------------------------------------------------

@code_review_bp.route("/submission/<int:submission_id>/hint", methods=["POST"])
@login_required
@role_required(ROLE_STUDENT)
def get_hint(submission_id):
    data = request.get_json(silent=True) or {}
    try:
        hint = review_service.request_hint(
            current_user.id, submission_id, requested_final=bool(data.get("requested_final", False))
        )
    except ValidationError as exc:
        return fail_response(exc.message, status_code=404, field=exc.field)

    return success_response(hint, message="Hint provided.")


# --------------------------------------------------------------------
# Comparison API (Section 15/10)
# --------------------------------------------------------------------

@code_review_bp.route("/session/<int:session_id>/compare", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def compare(session_id):
    try:
        comparison = review_service.get_comparison(current_user.id, session_id)
    except ValidationError as exc:
        return fail_response(exc.message, status_code=400, field=exc.field)

    return success_response({
        "original_code": comparison.original_code,
        "improved_code": comparison.improved_code,
        "diff_lines": comparison.diff_lines,
        "score_deltas": comparison.score_deltas,
        "improvement_summary": comparison.improvement_summary,
    })


# --------------------------------------------------------------------
# History API (Section 15/13)
# --------------------------------------------------------------------

@code_review_bp.route("/history", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def history():
    sessions = (
        CodeReviewSession.query.filter_by(user_id=current_user.id)
        .order_by(CodeReviewSession.created_at.desc())
        .limit(20)
        .all()
    )
    return success_response([
        {
            "session_id": s.id, "topic": s.topic_name, "status": s.status,
            "submission_count": len(s.submissions),
            "latest_score": (
                __import__("json").loads(s.submissions[-1].scores_json).get("overall")
                if s.submissions and s.submissions[-1].scores_json else None
            ),
            "created_at": s.created_at.isoformat(),
        }
        for s in sessions
    ])


# --------------------------------------------------------------------
# Metadata
# --------------------------------------------------------------------

@code_review_bp.route("/topics", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def list_topics():
    return success_response({"topics": CODE_REVIEW_TOPICS})
