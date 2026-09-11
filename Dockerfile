# =============================================================================
# Dockerfile — Part 3.12, Section 4
#
# Single-stage build (no compiled C extensions/heavy build toolchain in
# requirements.txt, so a multi-stage build would add complexity without
# a real image-size benefit here — a deliberate, documented choice, not
# an oversight).
#
# Runs under Gunicorn (wsgi.py, Part 3.1) — never Flask's dev server —
# consistent with this project's own "run.py is for local dev only"
# rule, now actually enforceable since Part 3.12 adds gunicorn to
# requirements.txt (it was referenced in wsgi.py's docstring since
# Part 3.1 but never actually installed until now — see
# docs/project-report-part3.12.md Section 20 for the full story).
# =============================================================================

FROM python:3.12-slim

LABEL maintainer="OSTutorLLM Project" \
      description="OSTutorLLM — AI-Powered Linux/Shell Tutor (Flask backend)"

# Prevents .pyc clutter and forces stdout/stderr to flush immediately
# (so `docker logs` shows output in real time, not buffered).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (separate layer) so `docker build` only
# re-installs packages when requirements.txt actually changes, not on
# every source-code edit.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Runtime directories the app writes to at request time (uploads,
# backups, logs, the SQLite file, migration state) — created here so
# they exist even before a volume is mounted over them (Section 4 —
# Volume Configuration, see docker-compose.yml).
RUN mkdir -p database logs uploads/content uploads/backups

# Non-root user — a real container hardens itself, doesn't run as root
# by default just because the base image does.
RUN useradd --create-home --shell /bin/bash ostutor && \
    chown -R ostutor:ostutor /app
USER ostutor

EXPOSE 5000

# Runs migrations before starting Gunicorn, every time the container
# starts — idempotent (Alembic no-ops if the schema is already current)
# and means a fresh volume gets its schema created automatically
# without a separate manual step.
COPY --chown=ostutor:ostutor scripts/docker-entrypoint.sh /app/scripts/docker-entrypoint.sh
RUN chmod +x /app/scripts/docker-entrypoint.sh

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["gunicorn", "wsgi:app", "--bind", "0.0.0.0:5000", "--workers", "3", "--timeout", "60"]
