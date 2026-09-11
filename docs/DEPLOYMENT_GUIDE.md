# OSTutorLLM — Deployment Guide

Part 3.12, Section 3. Every command below was actually run against this
exact codebase during Part 3.12's live verification (see
`docs/project-report-part3.12.md`'s Live Verification Log) — not assumed
correct from memory.

---

## 1. Prerequisites (All Platforms)

- Python 3.12+
- Git
- (Optional) Docker + Docker Compose, if deploying via containers
- (Optional) An API key for OpenAI/DeepSeek, or a local Ollama install, if
  you want a real LLM instead of the default offline Mock provider

## 2. Local Windows Deployment

```powershell
git clone <your-repo-url> ostutorllm
cd ostutorllm
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
```
This script (`scripts/setup_windows.ps1`) creates a venv, installs
dependencies, generates a real `SECRET_KEY` into `.env`, and runs migrations.

**Manual steps** (if you prefer not to use the script):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
notepad .env    # set SECRET_KEY
$env:FLASK_APP = "run.py"
flask db upgrade
flask seed-db          # optional
python run.py
```
Open **http://localhost:5000**.

**Stopping the server**: `Ctrl+C` in the terminal running `python run.py`.

## 3. Ubuntu Linux Deployment

```bash
git clone <your-repo-url> ostutorllm
cd ostutorllm
chmod +x scripts/setup_ubuntu.sh
./scripts/setup_ubuntu.sh
```
Live-verified this exact script, from a completely fresh clone (no
pre-existing venv, no `.env`), on this exact codebase: virtual environment
created, all dependencies installed, `.env` generated with a real random
`SECRET_KEY`, all 8 migrations applied cleanly, server started, and
`GET /health` returned a real `200` response.

**Manual steps**:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env    # set SECRET_KEY
export FLASK_APP=run.py
flask db upgrade
flask seed-db          # optional
python run.py
```

**Stopping the server**: `Ctrl+C`, or if backgrounded: `kill $(pgrep -f "python run.py")`.

**Running in production on Ubuntu** (Gunicorn, not the dev server):
```bash
export APP_ENV=production
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
export DATABASE_URL="sqlite:////absolute/path/to/database/dev.db"
flask db upgrade
gunicorn wsgi:app --bind 0.0.0.0:5000 --workers 3 --timeout 60
```
Live-verified this exact command (with a real generated `SECRET_KEY` and a
real `DATABASE_URL`) against this codebase with both 1 and 2 Gunicorn
workers — `GET /health` returned `200` in both configurations.

Put a real reverse proxy (nginx/Caddy) in front of Gunicorn for TLS
termination — Gunicorn itself does not terminate HTTPS.

## 4. Docker Deployment

```bash
git clone <your-repo-url> ostutorllm
cd ostutorllm
cp .env.example .env
nano .env    # set SECRET_KEY at minimum
docker compose up --build
```
Open **http://localhost:5000** (or whatever `PORT` you set in `.env`).

What happens under the hood (`Dockerfile` + `docker-compose.yml`, Section 4):
1. Image builds from `python:3.12-slim`, installs `requirements.txt`
   (including the now-present `gunicorn` — see Section 20's note on this).
2. Container starts as a non-root user (`ostutor`).
3. `scripts/docker-entrypoint.sh` runs `flask db upgrade` (idempotent —
   safe on every restart) before starting Gunicorn.
4. Three named volumes persist the SQLite database, uploaded content, and
   logs across container restarts (`docker compose down` keeps them; only
   `docker compose down -v` removes them).

**Stopping**: `docker compose down` (keeps data) or `docker compose down -v`
(also deletes volumes — destructive, confirm first).

**Viewing logs**: `docker compose logs -f web`

**Rebuilding after a code change**: `docker compose up --build`

## 5. Optional Cloud Deployment

This app has no cloud-provider-specific code — `DATABASE_URL` and
`AI_PROVIDER` are pure environment variables, so any platform that can run a
Docker container or a Python/Gunicorn process works:

- **Render / Railway / Fly.io**: point at this repo's `Dockerfile` directly,
  set the environment variables from `.env.example` in the platform's
  dashboard, and use their built-in Postgres add-on (`DATABASE_URL`
  environment variable format is already Postgres-compatible).
- **AWS/GCP/Azure VM**: follow the Ubuntu instructions above, put the app
  behind the cloud provider's load balancer for TLS.
- **A managed Postgres database** is strongly recommended over SQLite for
  any deployment expecting real concurrent multi-user traffic — see
  `docker-compose.yml`'s commented-out `postgres` service for the exact
  environment variable to change (`DATABASE_URL`), and re-run
  `./run_tests.sh performance` against the new database before trusting it
  under load.

## 6. Environment Variables Reference

See `.env.example` for the full, commented list. The ones that matter most
for deployment:

| Variable | Required? | Notes |
|---|---|---|
| `APP_ENV` | Yes | `development` for local, `production` for real deployment |
| `SECRET_KEY` | **Yes in production** | `ProductionConfig` refuses to boot with the placeholder default — a deliberate fail-fast check |
| `DATABASE_URL` | **Yes in production** | Same fail-fast check applies |
| `AI_PROVIDER` | No (defaults to `mock`) | Set to `openai`/`deepseek`/`ollama_qwen`/`ollama_llama` for a real LLM |
| `PORT` | No (defaults to 5000) | |
| `MAX_UPLOAD_SIZE_MB` | No (defaults to 10) | Faculty content upload cap |

## 7. Database Setup

Every deployment path above already includes `flask db upgrade` — this
applies all 8 migrations (Parts 3.4 through 3.10) in order, on top of
whatever schema state already exists (safe to re-run; Alembic tracks the
current revision and no-ops if already current).

**Optional seed data** (`flask seed-db`): creates sample topics, lessons,
Linux commands, a demo quiz, and demo user accounts — see
`docs/USER_MANUAL_STUDENT.md` for the actual seeded credentials.

**Fresh start** (wipes all data): delete the SQLite file (`database/dev.db`
locally, or the Docker volume `ostutorllm_data`) and re-run
`flask db upgrade`.

## 8. Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `RuntimeError: DATABASE_URL must be set in the production environment` | `APP_ENV=production` but `DATABASE_URL` unset | Set `DATABASE_URL` in `.env` |
| `RuntimeError: SECRET_KEY must be overridden...` | `APP_ENV=production` with the placeholder `SECRET_KEY` | Generate a real one: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ModuleNotFoundError: No module named 'flask_sqlalchemy'` | Dependencies not installed, or wrong Python/venv active | `pip install -r requirements.txt` inside the activated venv |
| `sqlite3.OperationalError: no such table` | Migrations never ran | `flask db upgrade` |
| Port 5000 already in use | Another process (often macOS AirPlay Receiver) is on 5000 | Set `PORT=5001` in `.env`, or stop the other process |
| Faculty file upload fails with 400 | File extension not in the allowed whitelist | See `Config.ALLOWED_UPLOAD_EXTENSIONS` in `app/config/config.py` |
| Docker container exits immediately | Check `docker compose logs web` — usually a missing/invalid `SECRET_KEY` in `.env` | Set it, `docker compose up --build` again |
| AI Tutor says "currently disabled" | A faculty user toggled it off (Part 3.10, Section 9) | Log in as faculty → Settings → enable it |

For anything not listed here, check `logs/error.log` (or `docker compose logs web`)
for the full traceback — every unhandled exception in this codebase logs
full detail server-side while returning a sanitized message to the client
(Part 3.3's error-handling design).
