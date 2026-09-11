"""
app/ai/services/fallback.py

The Fallback Strategy (Section 1/14). Maps every LLMProviderError
subtype (app/ai/providers/base.py) to a specific, meaningful, in-
character message — never a raw exception or generic "error occurred"
shown to a student mid-lesson. The Tutor Service catches
LLMProviderError once and delegates the message choice here, so every
call site gets consistent, tested fallback behavior.
"""

from app.ai.providers.base import (
    LLMTimeoutError, LLMRateLimitError, LLMConnectionError,
    LLMInvalidResponseError, LLMAuthenticationError, LLMProviderError,
)

_FALLBACK_MESSAGES = {
    LLMTimeoutError: (
        "That's taking longer than expected to think through. Let's try again — could you resend your last message?"
    ),
    LLMRateLimitError: (
        "I'm getting a lot of requests right now and need a moment to catch up. Please try again in about a minute."
    ),
    LLMConnectionError: (
        "I'm having trouble connecting right now (this looks like a network issue on our end, not yours). "
        "Please try again shortly — if this keeps happening, let your instructor know."
    ),
    LLMInvalidResponseError: (
        "I generated something that didn't come through properly. Could you rephrase your question and try again?"
    ),
    LLMAuthenticationError: (
        "The tutor's AI service isn't fully configured yet on this deployment. Please let your instructor or "
        "administrator know so they can check the AI provider setup."
    ),
}

_DEFAULT_FALLBACK = (
    "Something went wrong while I was thinking through that. Please try again — if it keeps happening, "
    "let your instructor know."
)


def fallback_message_for(error: LLMProviderError) -> str:
    for error_type, message in _FALLBACK_MESSAGES.items():
        if isinstance(error, error_type):
            return message
    return _DEFAULT_FALLBACK


def is_configuration_error(error: LLMProviderError) -> bool:
    """Distinguishes 'the AI isn't set up' from a transient failure —
    used by the route layer to decide whether logging at WARNING vs
    ERROR level is appropriate (a missing API key in development is
    expected, not an incident)."""
    return isinstance(error, LLMAuthenticationError)
