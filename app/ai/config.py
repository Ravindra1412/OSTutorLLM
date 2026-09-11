"""
app/ai/config.py

AI Tutor Engine configuration (Section 16). All values are read from
environment variables at import time, following the exact pattern
established in app/config/config.py (Part 3.1/3.3) — no value is
hardcoded elsewhere in the AI module, and every variable declared here
has a matching entry in .env.example.

Provider selection (`AI_PROVIDER`) is the single switch that
determines which LLMProvider implementation the factory
(app/ai/providers/factory.py) instantiates — see Section 3.
"""

import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

# --- Provider selection ---
# One of: "openai" | "ollama_qwen" | "ollama_llama" | "deepseek" | "mock"
# "mock" is the local-development/offline fallback (Section 14) used
# automatically when no real provider is configured, so the tutor is
# runnable and testable without any API key or network access.
AI_PROVIDER = os.environ.get("AI_PROVIDER", "mock").strip().lower()

# --- OpenAI ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

# --- Ollama (local models — Qwen / Llama) ---
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_QWEN_MODEL = os.environ.get("OLLAMA_QWEN_MODEL", "qwen2.5")
OLLAMA_LLAMA_MODEL = os.environ.get("OLLAMA_LLAMA_MODEL", "llama3.1")

# --- DeepSeek (OpenAI-compatible API) ---
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# --- Generation parameters (shared across providers) ---
AI_TEMPERATURE = float(os.environ.get("AI_TEMPERATURE", 0.4))
AI_MAX_TOKENS = int(os.environ.get("AI_MAX_TOKENS", 500))
AI_TIMEOUT_SECONDS = float(os.environ.get("AI_TIMEOUT_SECONDS", 20))
AI_MAX_RETRIES = int(os.environ.get("AI_MAX_RETRIES", 2))
AI_RETRY_BACKOFF_SECONDS = float(os.environ.get("AI_RETRY_BACKOFF_SECONDS", 1.5))

# --- Conversation / context window ---
AI_MAX_HISTORY_TURNS = int(os.environ.get("AI_MAX_HISTORY_TURNS", 12))  # Section 5

# --- Hint ladder (Section 7/8) ---
# Stage 0 = diagnostic question, 1-3 = hints, 4 = full reveal.
HINT_STAGE_DIAGNOSTIC = 0
HINT_STAGE_1 = 1
HINT_STAGE_2 = 2
HINT_STAGE_3 = 3
HINT_STAGE_REVEAL = 4
MAX_HINT_STAGE = HINT_STAGE_3


def provider_display_name() -> str:
    return {
        "openai": f"OpenAI ({OPENAI_MODEL})",
        "ollama_qwen": f"Ollama ({OLLAMA_QWEN_MODEL})",
        "ollama_llama": f"Ollama ({OLLAMA_LLAMA_MODEL})",
        "deepseek": f"DeepSeek ({DEEPSEEK_MODEL})",
        "mock": "Mock (offline/local development)",
    }.get(AI_PROVIDER, AI_PROVIDER)
