# OSTutorLLM - Maintenance Guide

## Backup Strategy

- In-app (faculty, SQLite only): Settings page -> "Create Backup Now" ->
  downloads a timestamped .db file copy.
- Scheduled (recommended for real deployments): a cron job copying the
  database file (or a full pg_dump for Postgres) to off-server storage
  nightly. Not built into this codebase - a real production deployment
  should add this at the infrastructure level.
- Before any bulk content change (faculty bulk-editing topics/lessons),
  trigger a manual backup first - Content Revisions (Part 3.10) give you
  per-edit undo, but a full backup is still cheap insurance.

## Database Maintenance

- Run `flask db upgrade` after every deployment that includes a new
  migration - idempotent, safe to run even if already current.
- Periodically inspect table sizes on a long-running deployment:
  `sqlite3 database/dev.db "SELECT name FROM sqlite_master WHERE type='table';"`
  then `SELECT COUNT(*) FROM <table>;` for growth-prone tables
  (learning_timeline, activity_log, login_history).
- learning_timeline/activity_log are append-only and will grow
  indefinitely - no archival/pruning job exists yet (a real Future
  Enhancement for a long-lived production deployment).

## Log Maintenance

Rotating handlers are already configured (Part 3.3) - app.log, error.log,
activity.log, ai_tutor.log each rotate automatically. For long-term
retention beyond the rotation window, archive logs/ periodically
(e.g. `tar czf logs_$(date +%Y%m%d).tar.gz logs/*.log.*` via cron).

## Updating Prompts

Faculty can edit prompt templates directly via /faculty/settings ->
Prompt Templates (Part 3.10) - every edit automatically creates a
timestamped .bak file alongside the original before overwriting, so a bad
edit is always recoverable. Templates live at
app/ai/prompts/templates/*.txt if editing directly on disk instead.

## Updating Lessons

Faculty -> Content Management -> Topics -> add/edit a Lesson under a topic.
Every edit is versioned (Part 3.10's Content Revisions) - mistakes can be
restored with one click from the topic's revision history.

## Updating the Quiz Bank

The static question bank (app/quiz/question_bank/seed_bank.py) is a Python
data file, not database-editable via the UI - adding a new static question
means editing that file and redeploying. Faculty-authored quizzes
(Part 3.10, via /faculty/quizzes) are the UI-editable alternative and don't
require a code change or redeploy.

## Updating AI Models

Change the relevant *_MODEL environment variable (OPENAI_MODEL,
DEEPSEEK_MODEL, OLLAMA_QWEN_MODEL, OLLAMA_LLAMA_MODEL) in .env and
restart the app - no code change needed (Part 3.6's provider factory
reads these at request time). To add support for an entirely new provider,
see docs/DEVELOPER_GUIDE.md Section 4.

## Dependency Updates

```bash
pip list --outdated
```
Update requirements.txt version pins deliberately, one at a time where
possible, and re-run ./run_tests.sh all after each - this project's own
history (Part 3.11) shows real bugs can hide in version-specific behavior
(e.g. SQLAlchemy's bulk-delete session-sync behavior).

## Routine Health Checks

- GET /health and GET /status - automated monitoring should poll these.
- ./run_tests.sh coverage periodically to catch coverage regressions as
  new code is added without matching tests.
