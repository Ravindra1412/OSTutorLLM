"""
app/ai/providers/openai_provider.py

The primary supported provider (per this phase's requirements). Thin
wrapper supplying OpenAI's specific credentials/endpoint to the shared
OpenAICompatibleProvider HTTP implementation.
"""

from app.ai import config
from app.ai.providers.openai_compatible import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    def __init__(self):
        super().__init__(
            name="openai",
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL,
            model=config.OPENAI_MODEL,
        )
