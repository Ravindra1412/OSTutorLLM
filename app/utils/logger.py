"""
app/utils/logger.py

Configures Python's standard `logging` module with rotating file
handlers, per Part 3.1 Section 13 (Application / Error / Activity logs)
and this phase's Section 7 (log rotation). Called once from the
application factory (app/__init__.py).
"""

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
MAX_BYTES = 1_000_000  # ~1MB per log file before rotating
BACKUP_COUNT = 5

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def _make_handler(filename: str, level: int) -> RotatingFileHandler:
    os.makedirs(LOG_DIR, exist_ok=True)
    handler = RotatingFileHandler(
        os.path.join(LOG_DIR, filename), maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT
    )
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    return handler


def init_logging(app) -> None:
    """Attach rotating file handlers to the Flask app's logger and to
    dedicated named loggers for errors and request activity.

    Usage elsewhere in the codebase:
        current_app.logger.info("...")               -> logs/app.log
        logging.getLogger("ostutorllm.error")         -> logs/error.log
        logging.getLogger("ostutorllm.activity")      -> logs/activity.log
    """
    level = getattr(logging, app.config.get("LOG_LEVEL", "INFO").upper(), logging.INFO)

    # Application log — general lifecycle/info events
    app.logger.setLevel(level)
    app.logger.addHandler(_make_handler("app.log", level))

    # Error log — ERROR and above only, separate file for fast incident triage
    error_logger = logging.getLogger("ostutorllm.error")
    error_logger.setLevel(logging.ERROR)
    error_logger.addHandler(_make_handler("error.log", logging.ERROR))

    # Activity log — login/logout and other key user actions
    activity_logger = logging.getLogger("ostutorllm.activity")
    activity_logger.setLevel(logging.INFO)
    activity_logger.addHandler(_make_handler("activity.log", logging.INFO))

    # AI Tutor Engine log (Part 3.6, Section 15) — student questions,
    # tutor responses, hint usage, provider errors, session events, all
    # in one dedicated file so a reviewer can audit hint-policy
    # compliance (Part 2, Section 27) by tailing exactly one log.
    ai_logger = logging.getLogger("ostutorllm.ai")
    ai_logger.setLevel(logging.INFO)
    ai_logger.addHandler(_make_handler("ai_tutor.log", logging.INFO))

    app.logger.info("Logging initialized (level=%s)", app.config.get("LOG_LEVEL", "INFO"))


def get_error_logger() -> logging.Logger:
    return logging.getLogger("ostutorllm.error")


def get_activity_logger() -> logging.Logger:
    return logging.getLogger("ostutorllm.activity")


def get_ai_logger() -> logging.Logger:
    return logging.getLogger("ostutorllm.ai")
