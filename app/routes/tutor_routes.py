"""
app/routes/tutor_routes.py

Tutor blueprint (Part 3.3, Section 4) — now fully implemented in Part
3.6. Every route here is a thin translation layer: parse/validate the
request, call app.ai.services.tutor_service, shape the JSON response —
exactly the Controller role defined back in Part 3.1 Section 9. All
actual workflow/hint/safety/personalization logic lives in the service
layer, never here.
"""

from flask import Blueprint, request
from flask_login import login_required, current_user

from app.extensions import db
from app.models import ChatSession
from app.utils.constants import ROLE_STUDENT
from app.utils.formatters import success_response, fail_response
from app.utils.helpers import role_required
from app.utils.validators import require_fields, ValidationError
from app.ai.services import tutor_service, personalization
from app.ai.services.teaching_modes import ALL_MODES, DEFAULT_MODE
from app.ai import config as ai_config

tutor_bp = Blueprint("tutor_bp", __name__, url_prefix="/api/tutor")


def _serialize_turn(result) -> dict:
    return {
        "reply": result.reply_text,
        "hint_stage": result.hint_stage,
        "hint_stage_label": result.hint_stage_label,
        "is_final_solution": result.is_final_solution,
        "provider": result.provider_used,
        "used_fallback": result.used_fallback,
        "safety_blocked": result.safety_blocked,
    }


def _get_owned_session_or_404(session_id: int) -> ChatSession:
    session = db.session.get(ChatSession, session_id)
    if session is None or session.user_id != current_user.id:
        # Deliberately identical "not found" for both cases so a student
        # cannot probe for the existence of another student's session id.
        raise ValidationError("Tutor session not found.", field="session_id")
    return session


@tutor_bp.route("/session", methods=["POST"])
@login_required
@role_required(ROLE_STUDENT)
def start_session():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["topic"])
    topic = data["topic"].strip()
    teaching_mode = data.get("teaching_mode", DEFAULT_MODE)

    try:
        session, result = tutor_service.start_session(current_user.id, topic, teaching_mode)
    except ValueError as exc:
        return fail_response(str(exc), status_code=400)

    payload = _serialize_turn(result)
    payload["session_id"] = session.id
    payload["topic"] = session.topic_name
    return success_response(payload, message="Tutor session started.", status_code=201)


@tutor_bp.route("/message", methods=["POST"])
@login_required
@role_required(ROLE_STUDENT)
def send_message():
    data = request.get_json(silent=True) or {}
    require_fields(data, ["session_id", "message"])

    session = _get_owned_session_or_404(data["session_id"])
    result = tutor_service.handle_message(session, data["message"])
    return success_response(_serialize_turn(result), message="Tutor replied.")


@tutor_bp.route("/reveal", methods=["POST"])
@login_required
@role_required(ROLE_STUDENT)
def reveal_answer():
    """Only permitted once the hint ladder is exhausted (Part 2, Section
    27 acceptance criterion) — enforced here at the API boundary, not
    just left to the frontend's disabled-button UX (Part 3.2)."""
    data = request.get_json(silent=True) or {}
    require_fields(data, ["session_id"])
    session = _get_owned_session_or_404(data["session_id"])

    current_stage = session.messages[-1].hint_stage if session.messages else 0
    if current_stage is not None and current_stage < ai_config.MAX_HINT_STAGE:
        return fail_response(
            "Hints haven't been exhausted yet — please try Hint 3 before requesting the full solution.",
            status_code=403,
        )

    result = tutor_service.request_full_reveal(session)
    return success_response(_serialize_turn(result), message="Full solution provided.")


@tutor_bp.route("/session/<int:session_id>/reset", methods=["POST"])
@login_required
@role_required(ROLE_STUDENT)
def reset_session(session_id):
    from app.ai.conversation import manager as conversation_manager
    session = _get_owned_session_or_404(session_id)
    conversation_manager.reset_conversation(session)
    return success_response(message="Conversation reset.")


@tutor_bp.route("/session/<int:session_id>/history", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def get_session_history(session_id):
    session = _get_owned_session_or_404(session_id)
    messages = [
        {"role": m.role, "text": m.message_text, "hint_stage": m.hint_stage, "created_at": m.created_at.isoformat()}
        for m in session.messages
    ]
    return success_response({"session_id": session.id, "topic": session.topic_name, "messages": messages})


@tutor_bp.route("/recommendation", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def get_recommendation():
    """Section 11 — Recommended Next Topic, surfaced as its own
    endpoint so the Student Dashboard (Part 3.2) can call it directly."""
    from app.models import Topic
    available_topics = [t.name for t in Topic.query.all()]
    recommended = personalization.recommend_next_topic(current_user.id, available_topics)
    weak_topics = personalization.get_weak_topics(current_user.id)
    return success_response({"recommended_topic": recommended, "weak_topics": weak_topics})


@tutor_bp.route("/modes", methods=["GET"])
@login_required
@role_required(ROLE_STUDENT)
def list_teaching_modes():
    return success_response({"modes": list(ALL_MODES), "default": DEFAULT_MODE})
