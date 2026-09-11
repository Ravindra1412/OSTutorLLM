# OSTutorLLM — Administrator Guide

This covers **deployment-level** administration (server, database, logs,
users) — distinct from the in-app Faculty Dashboard covered in
`USER_MANUAL_FACULTY.md`, which handles content/quiz/student administration
within the running application.

## 1. Installation & Deployment
See `docs/DEPLOYMENT_GUIDE.md` for Windows/Ubuntu/Docker/Cloud instructions.

## 2. User & Role Management

There is currently **no CLI command or admin UI to change a user's role**
after registration — this is an honest, real gap (a reasonable Future
Enhancement — see `docs/RESEARCH_AND_INNOVATION.md`), not a hidden feature.
To promote a user to faculty manually:

```bash
flask shell
```
```python
from app.models import User, FacultyProfile
from app.extensions import db
user = User.query.filter_by(email="someone@example.com").first()
user.role = "faculty"
db.session.add(FacultyProfile(user_id=user.id))
db.session.commit()
```
This exact sequence was live-verified during Part 3.12 (see
`docs/project-report-part3.12.md`'s Live Verification Log) — a student
promoted to faculty this way correctly gains a `FacultyProfile` and full
`/faculty/*` access on their next request.

## 3. Database Administration

**Location**: `database/dev.db` (SQLite, default) or wherever `DATABASE_URL`
points.

**Migrations**: `flask db upgrade` applies pending migrations;
`flask db current` shows the current revision; `flask db history` shows the
full chain (8 migrations as of Part 3.10, one per phase that needed a schema
change).

**Backup**: Faculty users can trigger a backup via the in-app Settings page
(Part 3.10), or an administrator can do it directly:
```bash
cp database/dev.db database/backups/backup_$(date +%Y%m%d_%H%M%S).db
```

**Inspecting the schema**:
```bash
sqlite3 database/dev.db ".tables"
sqlite3 database/dev.db ".schema users"
```

## 4. Log Management

Logs live in `logs/` — `app.log` (general), `error.log` (exceptions with
full traceback), `activity.log` (user actions), `ai_tutor.log` (LLM calls).
Rotating file handlers are already configured (Part 3.3) — logs rotate
automatically and don't grow unbounded. For long-term retention, archive the
`logs/` directory periodically (e.g. a nightly cron job) rather than relying
on the rotation alone.

## 5. Monitoring

- `GET /health` — liveness check (used by `docker-compose.yml`'s healthcheck).
- `GET /status` — confirms live database connectivity (Part 3.3).
- `docker compose logs -f web` (Docker) or `tail -f logs/app.log` (bare
  metal) for real-time monitoring.

## 6. Managing the AI Provider

Switch `AI_PROVIDER` in `.env` (`mock`/`openai`/`deepseek`/`ollama_qwen`/
`ollama_llama`) and restart the app — no code change needed (Part 3.6's
provider factory pattern). See `docs/MAINTENANCE_GUIDE.md` for updating
prompts/models.

## 7. Security Administration

See `SECURITY.md` and `docs/SECURITY_REVIEW.md` for the full posture. As an
administrator, your responsibilities:
- Set a real `SECRET_KEY` and `DATABASE_URL` in production (enforced by a
  fail-fast check — the app won't boot without them).
- Put a real reverse proxy with TLS in front of Gunicorn.
- Rotate `SECRET_KEY` periodically (this invalidates all existing sessions —
  plan for it).
- Review `logs/error.log` periodically for repeated failed-login patterns.

## 8. Scaling Beyond a Single Server

SQLite is fine for one server; for real multi-instance/multi-worker scale,
switch to Postgres (`DATABASE_URL`) — see `docker-compose.yml`'s commented
Postgres service — and re-run `./run_tests.sh performance` against it before
trusting it under load.
