#!/bin/bash
# =============================================================================
# scripts/docker-entrypoint.sh — Part 3.12, Section 4
#
# Runs on every container start, before the CMD (gunicorn) executes.
# `flask db upgrade` is idempotent — Alembic no-ops if the schema is
# already at head, so this is safe to run every single time rather
# than requiring a separate manual "first run only" step.
# =============================================================================
set -e

echo "[entrypoint] Running database migrations..."
flask db upgrade

echo "[entrypoint] Migrations complete. Starting application..."
exec "$@"
