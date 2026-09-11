"""
app/faculty/services/ai_tutor_management.py

AI Tutor Management (Section 9). Runtime-configurable settings persist
in `system_configuration` (Part 3.4's pre-existing, previously-unused
key-value table — see its own docstring: "for values an admin may want
to change at runtime without a redeploy," exactly this use case).
Provider/model/API-key selection stays in `.env` (app/ai/config.py) —
those genuinely are deployment-time secrets, not something to expose
through a web form.

Prompt template "management" is a real, working file-level view +
edit, not a stub: `list_prompt_templates`/`get_prompt_template`/
`update_prompt_template` operate on the actual .txt files in
`app/ai/prompts/templates/` that the AI Engine already reads at
request time (Part 3.6) — an edit here takes effect on the very next
tutor/quiz/code-review call, with a timestamped `.bak` copy written
alongside so a bad edit is always recoverable.
"""

import os
import shutil
from datetime import datetime, timezone

from app.extensions import db
from app.models import SystemConfiguration, ChatSession, Topic
from app.ai.services.teaching_modes import ALL_MODES, DEFAULT_MODE, is_valid_mode

CONFIG_AI_TUTOR_ENABLED = "ai_tutor_enabled"
CONFIG_DEFAULT_DIFFICULTY = "ai_default_difficulty"
CONFIG_DEFAULT_TEACHING_MODE = "ai_default_teaching_mode"
CONFIG_MAX_HINT_STAGE = "ai_max_hint_stage"

_DEFAULTS = {
    CONFIG_AI_TUTOR_ENABLED: "true",
    CONFIG_DEFAULT_DIFFICULTY: "2",
    CONFIG_DEFAULT_TEACHING_MODE: DEFAULT_MODE,
    CONFIG_MAX_HINT_STAGE: "3",
}

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "ai", "prompts", "templates")


def _get_config(key: str) -> str:
    row = SystemConfiguration.query.filter_by(config_key=key).first()
    return row.config_value if row else _DEFAULTS.get(key, "")


def _set_config(key: str, value: str, description: str = "") -> None:
    row = SystemConfiguration.query.filter_by(config_key=key).first()
    if row is None:
        row = SystemConfiguration(config_key=key, config_value=str(value), description=description)
        db.session.add(row)
    else:
        row.config_value = str(value)
    db.session.commit()


def get_ai_settings() -> dict:
    return {
        "ai_tutor_enabled": _get_config(CONFIG_AI_TUTOR_ENABLED).lower() == "true",
        "default_difficulty": int(_get_config(CONFIG_DEFAULT_DIFFICULTY)),
        "default_teaching_mode": _get_config(CONFIG_DEFAULT_TEACHING_MODE),
        "available_teaching_modes": list(ALL_MODES),
        "max_hint_stage": int(_get_config(CONFIG_MAX_HINT_STAGE)),
        "supported_topics": [t.name for t in Topic.query.order_by(Topic.name.asc()).all()],
    }


def update_ai_settings(
    ai_tutor_enabled: bool | None = None, default_difficulty: int | None = None,
    default_teaching_mode: str | None = None, max_hint_stage: int | None = None,
) -> dict:
    if ai_tutor_enabled is not None:
        _set_config(CONFIG_AI_TUTOR_ENABLED, "true" if ai_tutor_enabled else "false", "Global AI Tutor on/off switch")
    if default_difficulty is not None:
        _set_config(CONFIG_DEFAULT_DIFFICULTY, default_difficulty, "Default difficulty (1-5) for new tutor sessions")
    if default_teaching_mode is not None:
        if not is_valid_mode(default_teaching_mode):
            raise ValueError(f"default_teaching_mode must be one of: {', '.join(ALL_MODES)}.")
        _set_config(CONFIG_DEFAULT_TEACHING_MODE, default_teaching_mode, "Default teaching mode")
    if max_hint_stage is not None:
        _set_config(CONFIG_MAX_HINT_STAGE, max_hint_stage, "Max hint ladder stage before full reveal")
    return get_ai_settings()


def is_ai_tutor_enabled() -> bool:
    return _get_config(CONFIG_AI_TUTOR_ENABLED).lower() == "true"


def get_tutor_usage_statistics() -> dict:
    sessions = ChatSession.query.all()
    by_topic: dict[str, int] = {}
    for s in sessions:
        by_topic[s.topic_name] = by_topic.get(s.topic_name, 0) + 1
    completed = [s for s in sessions if s.ended_at is not None]

    return {
        "total_sessions": len(sessions),
        "completed_sessions": len(completed),
        "sessions_by_topic": [{"topic_name": t, "session_count": c} for t, c in sorted(by_topic.items(), key=lambda x: -x[1])],
    }


# --- Prompt template file management ---

def list_prompt_templates() -> list[str]:
    directory = os.path.abspath(TEMPLATES_DIR)
    if not os.path.isdir(directory):
        return []
    return sorted(f for f in os.listdir(directory) if f.endswith(".txt"))


def _safe_template_path(filename: str) -> str:
    """Prevents path traversal — filename must be a bare .txt name
    with no directory separators."""
    if "/" in filename or "\\" in filename or not filename.endswith(".txt"):
        raise ValueError("Invalid template filename.")
    return os.path.join(os.path.abspath(TEMPLATES_DIR), filename)


def get_prompt_template(filename: str) -> str:
    path = _safe_template_path(filename)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Template '{filename}' not found.")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def update_prompt_template(filename: str, content: str) -> None:
    path = _safe_template_path(filename)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Template '{filename}' not found.")

    backup_path = f"{path}.{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.bak"
    shutil.copy2(path, backup_path)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
