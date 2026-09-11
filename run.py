"""
run.py

Local development entrypoint. Run with:  python run.py
Uses Flask's built-in dev server (auto-reload + debugger when DEBUG=True
via DevelopmentConfig). NOT used in production — see wsgi.py + Gunicorn
for that (Part 3.1, Section 24).
"""

import os

from app import create_app

app = create_app(os.environ.get("APP_ENV", "development"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=app.config["DEBUG"])
