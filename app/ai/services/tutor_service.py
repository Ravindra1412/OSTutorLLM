"""
app/ai/services/tutor_service.py

The Tutor Workflow orchestrator (Section 1/7) — THE central file of
this entire phase. Every other module (providers, prompts, conversation,
memory, hint engine, safety layer, formatter, fallback, personalization)
exists to be called from here, in the exact order the Section 7 flow
diagram specifies:

    student message
        -> Safety Layer (topic restriction, injection, unsafe commands)
        -> Conversation Manager (load history + current hint stage)
        -> Personalization (competency summary, teaching mode)
        -> Hint Engine (classify intent -> determine NEXT stage)
        -> Prompt Manager (build the layered message list for that stage)
        -> LLM Service (call provider, with fallback on failure)
        -> Response Formatter (sanitize + structural repair)
        -> Conversation Manager (persist both turns)
        -> Memory Manager (update learning state)
        -> return to the route layer

This ordering IS the enforcement mechanism for the workflow diagram in
the prompt: the hint stage for turn N+1 is decided by the Hint Engine
BEFORE the LLM is ever called for turn N+1, so the LLM is always told
which stage to produce — it is never in a position to "decide" to skip
ahead, because the Prompt Manager's developer-layer instruction for
that stage is the only content describing what to say.
"""

from dataclasses import dataclass

from app.models import ChatSession
from app.ai import config
from app.ai.providers.base import LLMMessage
from app.ai.prompts import manager as prompt_manager
from app.ai.conversation import manager as conversation_manager
from app.ai.memory import manager as memory_manager
from app.ai.services import hint_engine, safety_layer, personalization
from app.ai.services.llm_service import generate_reply
from app.ai.services.response_formatter import format_response
from app.ai.services.teaching_modes import DEFAULT_MODE, is_valid_mode
from app.utils.logger import get_ai_logger


@dataclass
class TutorTurnResult:
    reply_text: str
    hint_stage: int
    hint_stage_label: str
    is_final_solution: bool
    provider_used: str
    used_fallback: bool
    safety_blocked: bool = False


_STAGE_LABELS = {
    config.HINT_STAGE_DIAGNOSTIC: "diagnostic",
    1: "hint_1", 2: "hint_2", 3: "hint_3",
    config.HINT_STAGE_REVEAL: "full_solution",
}


def start_session(user_id: int, topic_name: str, teaching_mode: str = DEFAULT_MODE) -> tuple[ChatSession, TutorTurnResult]:
    """Begins a brand-new tutoring session on a topic. Immediately
    produces the first diagnostic-stage message (Section 7, step 1-2)
    rather than waiting for the student to ask something — this matches
    the Tutor Chat UI's expectation (Part 3.2) of an opening tutor
    message already present when the chat screen loads."""
    from app.faculty.services.ai_tutor_management import is_ai_tutor_enabled
    if not is_ai_tutor_enabled():
        raise ValueError("The AI Tutor is currently disabled by the administrator. Please try again later.")

    if not is_valid_mode(teaching_mode):
        teaching_mode = DEFAULT_MODE

    session = conversation_manager.start_session(user_id, topic_name)
    memory_manager.set_teaching_mode(session, teaching_mode)

    # Part 3.9: Learning Timeline — one entry per session start (not per
    # turn, which would flood the timeline with near-duplicate rows).
    from app.analytics.services import timeline_service
    from app.models.learning_timeline import EVENT_TUTOR_SESSION
    timeline_service.log_event(
        user_id, EVENT_TUTOR_SESSION, title=f"Tutor session: {topic_name}", topic_name=topic_name,
    )

    opening_prompt = (
        f"The student has just started a session on '{topic_name}'. Greet them briefly and ask your "
        f"diagnostic opening question for this topic."
    )
    result = _run_turn(session, student_message=opening_prompt, is_opening=True)
    return session, result


def handle_message(session: ChatSession, student_message: str) -> TutorTurnResult:
    """Handles one turn of an ongoing conversation (Section 7, the
    student-reply -> tutor-evaluates loop)."""
    safety_check = safety_layer.run_all_checks(student_message)
    if not safety_check.allowed:
        get_ai_logger().info(
            "Safety layer blocked message (session_id=%s, reason=%s)", session.id, safety_check.reason
        )
        # A safety block is NOT persisted with a hint_stage advance and
        # is NOT sent to the LLM at all — it is handled entirely within
        # this structural layer, per Section 13's design intent.
        conversation_manager.record_message(session, role="student", text=student_message)
        conversation_manager.record_message(session, role="tutor", text=safety_check.canned_response)
        current_stage = conversation_manager.get_last_hint_stage(session)
        return TutorTurnResult(
            reply_text=safety_check.canned_response,
            hint_stage=current_stage,
            hint_stage_label=_STAGE_LABELS.get(current_stage, "unknown"),
            is_final_solution=False,
            provider_used="safety_layer",
            used_fallback=False,
            safety_blocked=True,
        )

    return _run_turn(session, student_message=student_message, is_opening=False)


def request_full_reveal(session: ChatSession) -> TutorTurnResult:
    """Explicit 'show full answer' action from the frontend's dedicated
    button (Part 3.2), only permitted once hints are exhausted — this
    mirrors the Part 2 Section 27 acceptance criterion enforced at the
    API layer too (see app/routes/tutor_routes.py)."""
    return _run_turn(session, student_message="Please show the full solution now.", is_opening=False, force_reveal=True)


def _run_turn(session: ChatSession, student_message: str, is_opening: bool, force_reveal: bool = False) -> TutorTurnResult:
    ai_logger = get_ai_logger()

    current_stage = config.HINT_STAGE_DIAGNOSTIC if is_opening else conversation_manager.get_last_hint_stage(session)

    if force_reveal:
        next_hint_stage = config.HINT_STAGE_REVEAL
    elif is_opening:
        next_hint_stage = config.HINT_STAGE_DIAGNOSTIC
    else:
        intent = hint_engine.classify_intent(student_message)
        next_hint_stage = hint_engine.next_stage(current_stage, intent)
        ai_logger.info(
            "session_id=%s intent=%s current_stage=%s -> next_stage=%s", session.id, intent, current_stage, next_hint_stage
        )

    state = memory_manager.load_state(session)
    teaching_mode = state.get("teaching_mode", DEFAULT_MODE)
    competency_summary = personalization.get_competency_summary(session.user_id, session.topic_name)
    history = conversation_manager.get_history(session)

    prompt_messages = prompt_manager.build_tutor_messages(
        topic=session.topic_name,
        hint_stage=next_hint_stage,
        teaching_mode=teaching_mode,
        competency_summary=competency_summary,
        history=history,
        student_message=student_message,
    )

    ai_logger.info("session_id=%s student_message=%r", session.id, student_message[:300])
    llm_result = generate_reply(prompt_messages)
    formatted_text = format_response(llm_result.text)
    ai_logger.info(
        "session_id=%s provider=%s used_fallback=%s tutor_response=%r",
        session.id, llm_result.provider, llm_result.used_fallback, formatted_text[:300],
    )

    if not is_opening:
        conversation_manager.record_message(session, role="student", text=student_message)
    conversation_manager.record_message(session, role="tutor", text=formatted_text, hint_stage=next_hint_stage)

    memory_manager.mark_step_completed(session, _STAGE_LABELS.get(next_hint_stage, str(next_hint_stage)))

    return TutorTurnResult(
        reply_text=formatted_text,
        hint_stage=next_hint_stage,
        hint_stage_label=_STAGE_LABELS.get(next_hint_stage, "unknown"),
        is_final_solution=(next_hint_stage == config.HINT_STAGE_REVEAL),
        provider_used=llm_result.provider,
        used_fallback=llm_result.used_fallback,
    )
