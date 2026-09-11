"""
app/ai/providers/deepseek_provider.py

DeepSeek-compatible API provider (optional, per project requirements).
DeepSeek's API deliberately mirrors OpenAI's Chat Completions shape, so
this reuses the exact same HTTP implementation as OpenAIProvider —
only credentials/endpoint differ.
"""

from app.ai import config
from app.ai.providers.openai_compatible import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    def __init__(self):
        super().__init__(
            name="deepseek",
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL,
            model=config.DEEPSEEK_MODEL,
        )
