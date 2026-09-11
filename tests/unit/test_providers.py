"""
tests/test_providers.py

Section 17 — Provider Tests. Uses unittest.mock to fake `requests.post`
responses, so these tests verify request-building/response-parsing/
error-translation logic for OpenAI, DeepSeek, and Ollama WITHOUT any
real network access — this sandbox's network egress is restricted to
an allowlist that does not include api.openai.com or a local Ollama
server, so genuine live calls to those providers are not possible here
(documented in docs/project-report-part3.6.md's verification log,
rather than silently skipped). The Mock provider IS tested for real,
with no network involved at all, since it's pure Python logic.
"""

from unittest.mock import patch, MagicMock

import pytest
import requests

from app.ai.providers.base import (
    LLMMessage, LLMTimeoutError, LLMRateLimitError, LLMConnectionError,
    LLMInvalidResponseError, LLMAuthenticationError,
)
from app.ai.providers.openai_compatible import OpenAICompatibleProvider
from app.ai.providers.ollama_provider import OllamaProvider
from app.ai.providers.mock_provider import MockProvider
from app.ai.providers.factory import get_provider, UnknownProviderError


def _openai_success_response(text="Here's a hint about chmod."):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"choices": [{"message": {"content": text}, "finish_reason": "stop"}]}
    return mock_resp


class TestMockProvider:
    """The one provider tested with zero mocking — it IS the real code path."""

    def test_diagnostic_stage_asks_question_not_answer(self):
        provider = MockProvider()
        messages = [
            LLMMessage(role="system", content="HINT_STAGE=0\nTOPIC=Loops"),
            LLMMessage(role="user", content="how do I loop over files?"),
        ]
        response = provider.generate(messages, temperature=0.4, max_tokens=200, timeout=5)
        assert "?" in response.text  # diagnostic stage should ask something
        assert response.provider == "mock"

    def test_reveal_stage_mentions_full_explanation(self):
        provider = MockProvider()
        messages = [LLMMessage(role="system", content="HINT_STAGE=4\nTOPIC=Loops"), LLMMessage(role="user", content="x")]
        response = provider.generate(messages, temperature=0.4, max_tokens=200, timeout=5)
        assert "full explanation" in response.text.lower() or "complete solution" in response.text.lower()


class TestOpenAICompatibleProvider:
    def test_raises_authentication_error_when_no_api_key(self):
        provider = OpenAICompatibleProvider(name="test", api_key="", base_url="https://example.com/v1", model="gpt-x")
        with pytest.raises(LLMAuthenticationError):
            provider.generate([LLMMessage(role="user", content="hi")], temperature=0.4, max_tokens=100, timeout=5)

    @patch("app.ai.providers.openai_compatible.requests.post")
    def test_successful_request_parses_response_correctly(self, mock_post):
        mock_post.return_value = _openai_success_response("Think about the permission bits.")
        provider = OpenAICompatibleProvider(name="test", api_key="fake-key", base_url="https://example.com/v1", model="gpt-x")

        response = provider.generate([LLMMessage(role="user", content="hi")], temperature=0.4, max_tokens=100, timeout=5)

        assert response.text == "Think about the permission bits."
        assert response.provider == "test"
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["headers"]["Authorization"] == "Bearer fake-key"
        assert call_kwargs["json"]["model"] == "gpt-x"
        assert call_kwargs["json"]["messages"] == [{"role": "user", "content": "hi"}]

    @patch("app.ai.providers.openai_compatible.requests.post")
    def test_401_raises_authentication_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_post.return_value = mock_resp
        provider = OpenAICompatibleProvider(name="test", api_key="bad-key", base_url="https://example.com/v1", model="gpt-x")
        with pytest.raises(LLMAuthenticationError):
            provider.generate([LLMMessage(role="user", content="hi")], temperature=0.4, max_tokens=100, timeout=5)

    @patch("app.ai.providers.openai_compatible.requests.post")
    def test_429_raises_rate_limit_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_post.return_value = mock_resp
        provider = OpenAICompatibleProvider(name="test", api_key="key", base_url="https://example.com/v1", model="gpt-x")
        with pytest.raises(LLMRateLimitError):
            provider.generate([LLMMessage(role="user", content="hi")], temperature=0.4, max_tokens=100, timeout=5)

    @patch("app.ai.providers.openai_compatible.requests.post")
    def test_500_raises_connection_error_and_retries(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_post.return_value = mock_resp
        provider = OpenAICompatibleProvider(name="test", api_key="key", base_url="https://example.com/v1", model="gpt-x")
        with pytest.raises(LLMConnectionError):
            provider.generate([LLMMessage(role="user", content="hi")], temperature=0.4, max_tokens=100, timeout=5)
        # Retry logic (Section 3): default AI_MAX_RETRIES=2 means 3 total attempts
        assert mock_post.call_count == 3

    @patch("app.ai.providers.openai_compatible.requests.post", side_effect=requests.exceptions.Timeout())
    def test_timeout_raises_llm_timeout_error(self, mock_post):
        provider = OpenAICompatibleProvider(name="test", api_key="key", base_url="https://example.com/v1", model="gpt-x")
        with pytest.raises(LLMTimeoutError):
            provider.generate([LLMMessage(role="user", content="hi")], temperature=0.4, max_tokens=100, timeout=5)

    @patch("app.ai.providers.openai_compatible.requests.post")
    def test_empty_content_raises_invalid_response_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"choices": [{"message": {"content": "   "}, "finish_reason": "stop"}]}
        mock_post.return_value = mock_resp
        provider = OpenAICompatibleProvider(name="test", api_key="key", base_url="https://example.com/v1", model="gpt-x")
        with pytest.raises(LLMInvalidResponseError):
            provider.generate([LLMMessage(role="user", content="hi")], temperature=0.4, max_tokens=100, timeout=5)


class TestOllamaProvider:
    @patch("app.ai.providers.ollama_provider.requests.post")
    def test_successful_request_uses_ollama_chat_shape(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"message": {"role": "assistant", "content": "Try man chmod."}, "done": True}
        mock_post.return_value = mock_resp

        provider = OllamaProvider(model="qwen2.5", name="ollama_qwen")
        response = provider.generate([LLMMessage(role="user", content="hi")], temperature=0.4, max_tokens=100, timeout=5)

        assert response.text == "Try man chmod."
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["json"]["model"] == "qwen2.5"
        assert call_kwargs["json"]["stream"] is False

    @patch("app.ai.providers.ollama_provider.requests.post", side_effect=requests.exceptions.ConnectionError())
    def test_unreachable_server_raises_connection_error_not_auth_error(self, mock_post):
        """Ollama has no API key concept — an unreachable local server
        must surface as LLMConnectionError, never LLMAuthenticationError."""
        provider = OllamaProvider(model="llama3.1", name="ollama_llama")
        with pytest.raises(LLMConnectionError):
            provider.generate([LLMMessage(role="user", content="hi")], temperature=0.4, max_tokens=100, timeout=5)


class TestProviderFactory:
    def test_returns_mock_provider_by_default_name(self):
        provider = get_provider("mock")
        assert isinstance(provider, MockProvider)

    def test_returns_correct_class_per_name(self):
        from app.ai.providers.openai_provider import OpenAIProvider
        from app.ai.providers.deepseek_provider import DeepSeekProvider

        assert isinstance(get_provider("openai"), OpenAIProvider)
        assert isinstance(get_provider("deepseek"), DeepSeekProvider)
        assert isinstance(get_provider("ollama_qwen"), OllamaProvider)
        assert isinstance(get_provider("ollama_llama"), OllamaProvider)

    def test_unknown_provider_raises(self):
        with pytest.raises(UnknownProviderError):
            get_provider("not_a_real_provider")
