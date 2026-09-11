# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in OSTutorLLM, please **do not**
open a public GitHub issue. Instead, report it privately to the project
maintainers (see the repository's contact information) with:

- A description of the vulnerability and its potential impact
- Steps to reproduce it
- Any suggested fix, if you have one

You should expect an initial response within a reasonable timeframe and be
kept informed as the issue is triaged and (if confirmed) fixed. See
`docs/BUG_REPORT_TEMPLATE.md`'s Severity/Priority definitions — a confirmed
security vulnerability is treated as at minimum **High** severity, often
**Critical**.

## Supported Versions

This is an actively developed academic project (Parts 3.1-3.12). Security
fixes are applied to the current `main` branch only — there is no long-term-
support branch strategy at this stage of the project's life.

## What This Project Has Already Reviewed

A full security review was conducted in Part 3.11 (adversarial testing) and
re-verified in Part 3.12 (final review) — see `docs/SECURITY_REVIEW.md` for
the complete writeup. Summary:

| Area | Status |
|---|---|
| Password hashing (Werkzeug PBKDF2) | ✅ Verified — never stored/logged in plaintext |
| Session cookies (`HttpOnly`, `Secure` in production) | ✅ Verified |
| Role-based access control (`@role_required`) | ✅ Verified across every protected route |
| SQL injection | ✅ Structurally prevented — 100% SQLAlchemy ORM, no raw string-interpolated SQL anywhere in the codebase |
| XSS | ✅ Jinja auto-escaping verified on every template that renders user-supplied content |
| CSRF | ✅ JSON APIs deliberately CSRF-exempt (no HTML `<form>` submits them); Flask-WTF forms elsewhere are protected |
| File upload validation | ✅ Extension whitelist, size cap, UUID-based storage filenames (path-traversal-proof) |
| Cross-user resource access | ✅ Ownership checked at the query level, not just the route layer — returns `404`, never confirms existence via `403` |
| Prompt injection | ⚠️ Safety layer processes injection-shaped input without crashing; **not** validated against a live LLM (only the offline Mock provider) — see Known Limitations below |

## Known Limitations (Documented, Not Hidden)

- **No live-LLM adversarial testing.** The default and CI-tested AI provider
  is `mock` (fully offline). If you enable a real provider (OpenAI, DeepSeek,
  Ollama) in production, run your own prompt-injection red-teaming pass
  before trusting it with sensitive data.
- **SQLite by default.** Suitable for a single-server, low-concurrency
  deployment (the intended use case — a course project or small class). For
  a real multi-tenant production deployment, switch to Postgres (`DATABASE_URL`)
  and re-run the performance suite (`./run_tests.sh performance`).
- **No rate limiting is actually enforced yet.** `RATE_LIMIT_PER_MINUTE` is a
  reserved config value (Part 3.3) with no enforcing middleware wired in —
  a real internet-facing deployment should add one (e.g. Flask-Limiter)
  before going live.
- **No dedicated secrets manager.** `.env` file-based secrets are adequate
  for a course project; a real production deployment should use a proper
  secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.).

## Security-Relevant Configuration

- Always set a real, random `SECRET_KEY` in production (`ProductionConfig`
  refuses to boot with the default placeholder value — see
  `app/config/config.py`).
- Always set `DATABASE_URL` explicitly in production (same fail-fast check).
- Set `APP_ENV=production` so `SESSION_COOKIE_SECURE=True` is applied
  (cookies only sent over HTTPS).
- Put the app behind a real reverse proxy with TLS termination (nginx, Caddy,
  or your cloud provider's load balancer) — Gunicorn itself does not
  terminate TLS.
