"""
app/ai/services/llm_service.py

The LLM Service (Section 1). Sits between the Tutor Service and the
Provider layer: calls `get_provider().generate(...)`, catches any
LLMProviderError, logs it, and returns either a successful LLMResponse
or a structured LLMServiceResult carrying a fallback message —  so the
Tutor Service never has to import provider exception types directly or
duplicate try/except logic across every call site (Tutor, future Quiz/
Viva/Code-Review engines all funnel through this one function).
"""

from dataclasses import dataclass

from app.ai import config
from app.ai.providers.base import LLMMessage, LLMProviderError
from app.ai.providers.factory import get_provider
from app.ai.services.fallback import fallback_message_for, is_configuration_error
from app.utils.logger import get_ai_logger


@dataclass
class LLMServiceResult:
    success: bool
    text: str
    provider: str
    used_fallback: bool = False
    error_type: str | None = None


def generate_reply(
    messages: list[LLMMessage],
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: float | None = None,
    provider_name: str | None = None,
) -> LLMServiceResult:
    provider = get_provider(provider_name)
    logger = get_ai_logger()

    try:
        response = provider.generate(
            messages=messages,
            temperature=temperature if temperature is not None else config.AI_TEMPERATURE,
            max_tokens=max_tokens if max_tokens is not None else config.AI_MAX_TOKENS,
            timeout=timeout if timeout is not None else config.AI_TIMEOUT_SECONDS,
        )
        return LLMServiceResult(success=True, text=response.text, provider=response.provider)

    except LLMProviderError as exc:
        level = "warning" if is_configuration_error(exc) else "error"
        getattr(logger, level)("LLM provider error (%s): %s", type(exc).__name__, exc)
        return LLMServiceResult(
            success=False,
            text=fallback_message_for(exc),
            provider=provider.name,
            used_fallback=True,
            error_type=type(exc).__name__,
        )
