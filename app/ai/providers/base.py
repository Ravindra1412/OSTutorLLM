"""
app/ai/providers/base.py

The LLM Provider Interface (Section 3). Every concrete provider
(OpenAI, Ollama, DeepSeek, Mock) implements this same abstract
contract, so the rest of the AI Tutor Engine (Prompt Manager, Tutor
Service) never knows or cares which provider is actually configured —
it only ever calls `provider.generate(messages, ...)`. This is the
architectural chokepoint that makes "provider selection should be
configurable" (project requirement) a one-line config change rather
than a rewrite.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMMessage:
    """One turn in the conversation, in the universal role/content shape
    every provider's chat API expects (OpenAI, Ollama, and DeepSeek all
    accept this exact {role, content} shape natively)."""
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    raw: dict = field(default_factory=dict)
    finish_reason: str | None = None


# --------------------------------------------------------------------
# Exceptions (Section 3 error handling / Section 14 fallback strategy)
# --------------------------------------------------------------------

class LLMProviderError(Exception):
    """Base class for all provider-layer failures. The Tutor Service
    catches this ONE type (Section 14) rather than needing to know
    about every provider's specific SDK exceptions."""


class LLMTimeoutError(LLMProviderError):
    pass


class LLMRateLimitError(LLMProviderError):
    pass


class LLMConnectionError(LLMProviderError):
    """No internet / provider unreachable."""


class LLMInvalidResponseError(LLMProviderError):
    """Provider returned a 200 but the response body was malformed,
    empty, or otherwise unusable."""


class LLMAuthenticationError(LLMProviderError):
    """Missing/invalid API key — distinguished from other errors so the
    fallback message can be more specific in development."""


# --------------------------------------------------------------------
# Interface
# --------------------------------------------------------------------

class LLMProvider(ABC):
    """Abstract interface every concrete provider must implement."""

    name: str = "base"

    @abstractmethod
    def generate(
        self,
        messages: list[LLMMessage],
        temperature: float,
        max_tokens: int,
        timeout: float,
    ) -> LLMResponse:
        """Sends `messages` to the underlying model and returns a
        normalized LLMResponse. Implementations MUST translate any
        provider-specific failure into one of the LLMProviderError
        subclasses above — callers never see requests/openai-sdk-
        specific exceptions."""
        raise NotImplementedError
