"""
app/ai/conversation/manager.py

The Conversation Manager (Section 1/5). Persists conversation turns to
the real database (ChatSession/ChatMessage — Part 3.4) rather than an
in-memory structure, so a session survives across requests/process
restarts, exactly like every other piece of student data in this
project. Responsible for:
  - Starting/resetting a session
  - Storing each turn (student + tutor messages)
  - Producing a trimmed message list for the Prompt Manager, bounded by
    AI_MAX_HISTORY_TURNS (Section 5 — Context Window), so token usage
    stays bounded regardless of how long a conversation runs
"""

from app.extensions import db
from app.models import ChatSession, ChatMessage
from app.ai import config
from app.ai.providers.base import LLMMessage


def start_session(user_id: int, topic_name: str) -> ChatSession:
    session = ChatSession(user_id=user_id, topic_name=topic_name)
    db.session.add(session)
    db.session.commit()
    return session


def end_session(session: ChatSession) -> None:
    from datetime import datetime, timezone
    session.ended_at = datetime.now(timezone.utc)
    db.session.commit()


def reset_conversation(session: ChatSession) -> None:
    """Conversation Reset (Section 5): deletes all messages in this
    session but keeps the ChatSession row itself (and therefore its
    topic), so the student starts the topic over rather than losing
    their place entirely."""
    ChatMessage.query.filter_by(session_id=session.id).delete()
    db.session.commit()


def record_message(session: ChatSession, role: str, text: str, hint_stage: int | None = None) -> ChatMessage:
    message = ChatMessage(session_id=session.id, role=role, message_text=text, hint_stage=hint_stage)
    db.session.add(message)
    db.session.commit()
    return message


def get_history(session: ChatSession, max_turns: int | None = None) -> list[LLMMessage]:
    """Returns the trimmed conversation history as LLMMessages, mapping
    this project's 'student'/'tutor' role names to the universal
    'user'/'assistant' roles every provider's chat API expects."""
    max_turns = config.AI_MAX_HISTORY_TURNS if max_turns is None else max_turns

    all_messages = (
        ChatMessage.query.filter_by(session_id=session.id).order_by(ChatMessage.id).all()
    )
    trimmed = all_messages[-max_turns:] if max_turns else all_messages

    role_map = {"student": "user", "tutor": "assistant"}
    return [LLMMessage(role=role_map.get(m.role, m.role), content=m.message_text) for m in trimmed]


def get_last_hint_stage(session: ChatSession) -> int:
    """Reads the most recent tutor message's hint_stage to determine
    where this conversation currently stands in the hint ladder — the
    Hint Engine (Section 8) uses this as its starting point, so hint
    progression survives across separate HTTP requests without needing
    any additional server-side session state."""
    last_tutor_message = (
        ChatMessage.query.filter_by(session_id=session.id, role="tutor")
        .order_by(ChatMessage.id.desc())
        .first()
    )
    if last_tutor_message is None or last_tutor_message.hint_stage is None:
        return config.HINT_STAGE_DIAGNOSTIC
    return last_tutor_message.hint_stage
