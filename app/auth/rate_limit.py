"""
app/auth/rate_limit.py

Basic rate limiting (Section 13). A minimal in-memory sliding-window
limiter keyed by (client IP, route name) — enough to blunt naive brute-
force login/password-reset scripting in a single-process development
or small deployment, and to demonstrate the pattern the route layer
expects.

Explicitly NOT production-grade for a multi-process/multi-server
deployment: state lives in a plain Python dict in this process's
memory, so it resets on restart and isn't shared across Gunicorn
workers. The documented upgrade path (Section 13 / docs) is
Flask-Limiter backed by Redis, which is a drop-in replacement for this
decorator's call site once that infrastructure exists — this keeps the
foundation dependency-light while making the limiter's interface the
same either way (`@rate_limit(...)`).
"""

import time
from collections import defaultdict
from functools import wraps

from flask import request, current_app

from app.utils.formatters import fail_response

_attempts: dict[str, list[float]] = defaultdict(list)


def rate_limit(max_attempts: int = 5, window_seconds: int = 60):
    """Limits a route to `max_attempts` calls per `window_seconds` per
    client IP. On the (401/403-adjacent) limit-exceeded case, returns a
    standardized 429 fail response rather than raising, so callers see
    the same JSON envelope as any other client error.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            key = f"{request.remote_addr}:{view_func.__name__}"
            now = time.time()
            window_start = now - window_seconds

            _attempts[key] = [t for t in _attempts[key] if t > window_start]

            if len(_attempts[key]) >= max_attempts:
                current_app.logger.warning("Rate limit exceeded for %s", key)
                return fail_response(
                    "Too many attempts. Please wait a moment before trying again.", status_code=429
                )

            _attempts[key].append(now)
            return view_func(*args, **kwargs)

        return wrapped

    return decorator


def reset_rate_limit_store() -> None:
    """Test-only helper to clear state between test cases."""
    _attempts.clear()
