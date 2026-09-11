"""
app/ai/providers/openai_compatible.py

A single HTTP client implementation for any provider that speaks the
OpenAI Chat Completions API shape — which includes OpenAI itself AND
DeepSeek (DeepSeek's API is explicitly documented as OpenAI-compatible,
using the same request/response JSON shape at a different base URL).
Rather than duplicating near-identical HTTP code in two files, both
`openai_provider.py` and `deepseek_provider.py` are thin subclasses
that just supply a different base_url/api_key/model.

Uses `requests` directly (not the `openai` SDK package) to keep the
dependency footprint small — the Chat Completions REST shape is simple
and stable enough that a raw HTTP call is entirely sufficient here and
avoids pinning to a specific SDK major version.
"""

import requests

from app.ai.providers.base import (
    LLMProvider, LLMMessage, LLMResponse,
    LLMTimeoutError, LLMRateLimitError, LLMConnectionError,
    LLMInvalidResponseError, LLMAuthenticationError,
)
from app.ai.providers.retry import call_with_retry


class OpenAICompatibleProvider(LLMProvider):
    """Base class for any OpenAI-Chat-Completions-shaped API."""

    def __init__(self, name: str, api_key: str, base_url: str, model: str):
        self.name = name
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate(self, messages: list[LLMMessage], temperature: float, max_tokens: int, timeout: float) -> LLMResponse:
        if not self.api_key:
            raise LLMAuthenticationError(
                f"{self.name}: no API key configured (set the appropriate *_API_KEY environment variable)."
            )

        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        url = f"{self.base_url}/chat/completions"

        def _do_request() -> LLMResponse:
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
            except requests.exceptions.Timeout as exc:
                raise LLMTimeoutError(f"{self.name}: request timed out after {timeout}s.") from exc
            except requests.exceptions.ConnectionError as exc:
                raise LLMConnectionError(f"{self.name}: could not connect ({exc}).") from exc

            if resp.status_code == 401:
                raise LLMAuthenticationError(f"{self.name}: authentication failed — check the API key.")
            if resp.status_code == 429:
                raise LLMRateLimitError(f"{self.name}: rate limit exceeded.")
            if resp.status_code >= 500:
                raise LLMConnectionError(f"{self.name}: upstream server error ({resp.status_code}).")
            if resp.status_code >= 400:
                raise LLMInvalidResponseError(f"{self.name}: request rejected ({resp.status_code}): {resp.text[:300]}")

            try:
                data = resp.json()
                text = data["choices"][0]["message"]["content"]
                finish_reason = data["choices"][0].get("finish_reason")
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                raise LLMInvalidResponseError(f"{self.name}: malformed response body ({exc}).") from exc

            if not text or not text.strip():
                raise LLMInvalidResponseError(f"{self.name}: response contained empty content.")

            return LLMResponse(text=text.strip(), provider=self.name, model=self.model, raw=data, finish_reason=finish_reason)

        return call_with_retry(_do_request)
