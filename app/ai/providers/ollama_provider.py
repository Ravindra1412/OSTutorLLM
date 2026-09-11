"""
app/ai/providers/ollama_provider.py

Ollama provider (optional, per project requirements) — supports any
locally-served Ollama model, with `ollama_qwen` and `ollama_llama`
both routing through this same class with a different `model` string,
since Ollama's REST API (`/api/chat`) is model-agnostic; the model
name is just a request parameter, not a different endpoint shape.

Unlike OpenAI/DeepSeek, Ollama requires no API key (it's a local
server) — LLMAuthenticationError is never raised here; a missing/
unreachable Ollama server surfaces as LLMConnectionError instead,
which is the more accurate failure mode for a local service.
"""

import requests

from app.ai import config
from app.ai.providers.base import (
    LLMProvider, LLMMessage, LLMResponse,
    LLMTimeoutError, LLMConnectionError, LLMInvalidResponseError,
)
from app.ai.providers.retry import call_with_retry


class OllamaProvider(LLMProvider):
    def __init__(self, model: str, name: str = "ollama"):
        self.name = name
        self.model = model
        self.base_url = config.OLLAMA_BASE_URL.rstrip("/")

    def generate(self, messages: list[LLMMessage], temperature: float, max_tokens: int, timeout: float) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        url = f"{self.base_url}/api/chat"

        def _do_request() -> LLMResponse:
            try:
                resp = requests.post(url, json=payload, timeout=timeout)
            except requests.exceptions.Timeout as exc:
                raise LLMTimeoutError(f"{self.name}: request timed out after {timeout}s.") from exc
            except requests.exceptions.ConnectionError as exc:
                raise LLMConnectionError(
                    f"{self.name}: could not reach Ollama server at {self.base_url} ({exc})."
                ) from exc

            if resp.status_code >= 500:
                raise LLMConnectionError(f"{self.name}: Ollama server error ({resp.status_code}).")
            if resp.status_code >= 400:
                raise LLMInvalidResponseError(f"{self.name}: request rejected ({resp.status_code}): {resp.text[:300]}")

            try:
                data = resp.json()
                text = data["message"]["content"]
            except (ValueError, KeyError, TypeError) as exc:
                raise LLMInvalidResponseError(f"{self.name}: malformed response body ({exc}).") from exc

            if not text or not text.strip():
                raise LLMInvalidResponseError(f"{self.name}: response contained empty content.")

            return LLMResponse(
                text=text.strip(), provider=self.name, model=self.model, raw=data,
                finish_reason=data.get("done_reason"),
            )

        return call_with_retry(_do_request)
