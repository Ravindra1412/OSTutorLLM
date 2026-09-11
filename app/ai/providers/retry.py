"""
app/ai/providers/retry.py

Shared retry-with-backoff helper (Section 3 — Retry Logic). Used by
every concrete HTTP-based provider (OpenAI, Ollama, DeepSeek) so retry
behavior is implemented once and configured centrally via
app.ai.config.AI_MAX_RETRIES / AI_RETRY_BACKOFF_SECONDS, rather than
each provider re-implementing its own backoff loop.

Only retries on transient failures (timeout, connection error, 429/5xx)
— never on 4xx client errors like a bad API key, since retrying an
authentication failure wastes time and cannot succeed.
"""

import time
from typing import Callable, TypeVar

from app.ai import config
from app.ai.providers.base import LLMTimeoutError, LLMRateLimitError, LLMConnectionError

T = TypeVar("T")

RETRYABLE_EXCEPTIONS = (LLMTimeoutError, LLMRateLimitError, LLMConnectionError)


def call_with_retry(fn: Callable[[], T], max_retries: int = None, backoff_seconds: float = None) -> T:
    max_retries = config.AI_MAX_RETRIES if max_retries is None else max_retries
    backoff_seconds = config.AI_RETRY_BACKOFF_SECONDS if backoff_seconds is None else backoff_seconds

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except RETRYABLE_EXCEPTIONS as exc:
            last_error = exc
            if attempt < max_retries:
                time.sleep(backoff_seconds * (attempt + 1))  # linear backoff
                continue
            raise
    raise last_error  # pragma: no cover — unreachable, satisfies type checkers
