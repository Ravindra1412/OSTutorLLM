"""
wsgi.py

Production WSGI entrypoint. Gunicorn is pointed at this module:
    gunicorn wsgi:app

Flask's built-in development server (run.py) is explicitly unsuitable
for production (Part 3.1, Section 2 / Section 24) — Gunicorn is the
process manager that actually serves `app` under real load.
"""

import os

from app import create_app

app = create_app(os.environ.get("APP_ENV", "production"))
