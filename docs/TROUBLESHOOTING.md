# OSTutorLLM -- Troubleshooting Guide

Deployment-specific issues are in docs/DEPLOYMENT_GUIDE.md Section 8. This
covers development-time and in-app issues.

## Installation / Setup

**"ModuleNotFoundError" for any package** -- your venv isn't activated, or
`pip install -r requirements.txt` didn't complete. Check `pip list` inside
the activated venv.

**`flask db upgrade` fails with "Can't locate revision"** -- your local
`migrations/versions/` folder is out of sync with the database's own
`alembic_version` table (usually from switching branches). Check
`flask db current` vs the files actually present; in a dev environment it's
usually safe to delete the SQLite file and re-run `flask db upgrade` from
scratch.

**Seed data already exists / "UNIQUE constraint failed"** -- `flask seed-db`
is idempotent by design (checks `filter_by(email=...).first()` before
inserting) -- if you see this, something else already inserted a
conflicting row. Check what's actually in the `users` table before assuming
a bug.

## Authentication

**Registration returns 400 with no clear reason** -- check the response
`message` field: `validate_password`/`validate_email`/`validate_role` all
raise specific, readable messages (see `app/utils/validators.py`).

**Login succeeds but every subsequent request returns 401/302** -- session
cookie isn't being sent. Check you're using the SAME `requests.Session()` /
browser tab, not a fresh client per request.

## AI Tutor

**Tutor gives generic/repetitive responses** -- you're on the `mock`
provider (the default, offline). This is expected -- Mock exists for
free/offline development and testing, not for realistic teaching quality.
Set `AI_PROVIDER=openai` (or another real provider) with a valid API key for
real LLM responses.

**"The AI Tutor is currently disabled by the administrator"** -- a faculty
user turned it off (Part 3.10's real kill-switch). Check
`/api/faculty/ai-tutor/settings` or have a faculty user re-enable it.

**Session seems stuck / doesn't progress past the opening message** -- check
`app/ai/prompts/manager.py`'s stage logic and `logs/ai_tutor.log` for the
actual prompt/response exchange.

## Quiz Engine

**"No questions available for this topic"** -- the topic has no static bank
entries (`app/quiz/question_bank/seed_bank.py`) AND the LLM fallback (Mock
provider) couldn't produce parseable questions. Use a topic from the static
bank (Navigation, File Permissions, Loops, Conditionals, Piping &
Redirection, etc.) for reliable quiz generation without a real LLM.

**409 on quiz submit** -- either already submitted (check `is_submitted`),
or expired (server-authoritative timer -- refreshing the page doesn't reset
it).

## Code Review

**Submission blocked with "unsafe"** -- the Security Scanner
(`app/code_review/services/security_scanner.py`) detected a dangerous
pattern (e.g. `curl | bash`, `rm -rf /`) and blocked it BEFORE any LLM call,
by design. Legitimate uses of similar-looking commands (`chmod 755`, a
scoped `rm`) should pass -- if a legitimate script is being blocked, that's
a real bug worth reporting (`docs/BUG_REPORT_TEMPLATE.md`).

## Faculty Dashboard

**File upload returns 400** -- check the extension against
`Config.ALLOWED_UPLOAD_EXTENSIONS` (`app/config/config.py`) and the file
size against `MAX_UPLOAD_SIZE_MB`.

**Backup button does nothing / errors** -- automatic backup only works for a
file-based SQLite database (`get_backup_settings()`'s `supported: false` for
Postgres/in-memory -- see `docs/ADMINISTRATOR_GUIDE.md` for the manual
alternative).

## Tests

**A test fails that passed before, with no code change** -- check for test
pollution: did a previous manual `python run.py` or script run against the
SAME `database/dev.db` the tests also point to? Tests should use
`TestingConfig`'s in-memory database (`conftest.py`) -- if you're seeing
cross-run state, something is bypassing that fixture. See
`docs/DEVELOPER_GUIDE.md` Section 8's "Class-attribute config gotcha" for a
real historical example of exactly this failure mode.

**Performance tests fail intermittently** -- they boot a real server thread
and use real sockets; a genuinely overloaded CI runner can occasionally miss
a generous timing budget. Re-run in isolation
(`pytest tests/performance/ -v -m performance`) before assuming a regression.

## General Debugging

1. Check `logs/error.log` -- every unhandled exception logs full detail
   server-side (Part 3.3's design), even though the client only sees a
   sanitized message.
2. Check `logs/activity.log` for what the user actually did before the
   error.
3. Reproduce with `curl`/`requests` directly against the API to rule out a
   frontend-only issue.
4. Check `./run_tests.sh` still passes -- if it doesn't, the bug is likely
   already caught by an existing test's failure message.
