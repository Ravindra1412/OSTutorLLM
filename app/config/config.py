"""
app/config/config.py

Environment-based configuration classes. The application factory
(app/__init__.py) selects one of these by name at startup, based on
the FLASK_ENV / APP_ENV environment variable (see get_config()).

Design principle (per Part 3.1, Section 7.4): no environment-specific
value is ever hardcoded elsewhere in the codebase — everything that
varies between dev/test/prod is read from the environment here, once.
"""

import os
from datetime import timedelta

from dotenv import load_dotenv

# Load variables from a local .env file (development convenience only —
# in production these are expected to be injected by the host/platform).
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class BaseConfig:
    """Shared configuration common to every environment."""

    # --- Core Flask ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key-change-me")
    JSON_SORT_KEYS = False

    # --- Database ---
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # --- Session / Auth ---
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Only force secure cookies where we can guarantee HTTPS (Production overrides this True)
    SESSION_COOKIE_SECURE = False

    # --- App-specific ---
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT_PER_MINUTE", 30))
    # AI provider config (AI_PROVIDER, per-provider keys) lives in
    # app/ai/config.py, established Part 3.6 — not duplicated here.

    # --- Part 3.10: Faculty content uploads + DB backups ---
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", os.path.join(BASE_DIR, "uploads", "content"))
    BACKUP_FOLDER = os.environ.get("BACKUP_FOLDER", os.path.join(BASE_DIR, "uploads", "backups"))
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_SIZE_MB", 10)) * 1024 * 1024
    ALLOWED_UPLOAD_EXTENSIONS = {"pdf", "ppt", "pptx", "png", "jpg", "jpeg", "gif", "txt", "md"}


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'database', 'dev.db')}"
    )


class TestingConfig(BaseConfig):
    DEBUG = False
    TESTING = True
    # Force Mock AI during automated test suite runs
    AI_PROVIDER = "mock"
    # In-memory database keeps the test suite fast and fully isolated
    # from any developer's local dev.db.
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False  # simplifies posting test forms without a live CSRF token


class ProductionConfig(BaseConfig):
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SESSION_COOKIE_SECURE = True  # cookies only ever sent over HTTPS in production

    def __init__(self):
        if not self.SQLALCHEMY_DATABASE_URI:
            raise RuntimeError(
                "DATABASE_URL must be set in the production environment."
            )
        if self.SECRET_KEY == BaseConfig.SECRET_KEY:
            raise RuntimeError(
                "SECRET_KEY must be overridden via environment variable in production."
            )


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(env_name: str | None = None):
    """Resolve a config class from an environment name string.

    Falls back to 'development' if APP_ENV/FLASK_ENV is unset or unrecognized,
    which keeps `python run.py` working out of the box for a new contributor.
    """
    env_name = env_name or os.environ.get("APP_ENV") or os.environ.get("FLASK_ENV") or "development"
    return CONFIG_MAP.get(env_name.lower(), DevelopmentConfig)