"""
app/ai/providers/factory.py

Provider selection (Section 3). The ONE place in the codebase that
reads `config.AI_PROVIDER` and decides which concrete LLMProvider class
to instantiate — every other module (Prompt Manager, Tutor Service)
calls `get_provider()` and works against the LLMProvider interface
only, never a concrete class. Switching providers in production is
therefore a single environment variable change (AI_PROVIDER=openai vs
AI_PROVIDER=ollama_qwen), never a code change.
"""

from flask import current_app

from app.ai import config
from app.ai.providers.base import LLMProvider
from app.ai.providers.mock_provider import MockProvider


class UnknownProviderError(ValueError):
    pass


def get_provider(provider_name: str | None = None) -> LLMProvider:
    """Returns a fresh provider instance for the given name (or the
    configured default). Instantiated fresh per call rather than cached
    as a module-level singleton, so a config change takes effect on the
    next request without requiring a process restart in tests."""
    name = provider_name

    if not name:
        try:
            if current_app:
                if current_app.config.get("TESTING"):
                    name = "mock"
                elif current_app.config.get("AI_PROVIDER"):
                    name = current_app.config.get("AI_PROVIDER")
        except Exception:
            pass

    if not name:
        name = config.AI_PROVIDER

    name = str(name).strip().lower()

    if name == "openai":
        from app.ai.providers.openai_provider import OpenAIProvider
        return OpenAIProvider()

    if name == "deepseek":
        from app.ai.providers.deepseek_provider import DeepSeekProvider
        return DeepSeekProvider()

    if name == "ollama_qwen":
        from app.ai.providers.ollama_provider import OllamaProvider
        return OllamaProvider(model=config.OLLAMA_QWEN_MODEL, name="ollama_qwen")

    if name == "ollama_llama":
        from app.ai.providers.ollama_provider import OllamaProvider
        return OllamaProvider(model=config.OLLAMA_LLAMA_MODEL, name="ollama_llama")

    if name == "mock":
        return MockProvider()

    raise UnknownProviderError(
        f"Unknown AI_PROVIDER '{name}'. Valid options: openai, deepseek, ollama_qwen, ollama_llama, mock."
    )