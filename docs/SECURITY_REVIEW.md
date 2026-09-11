# OSTutorLLM — Security Review

Final security review, Part 3.12. Consolidates and re-verifies Part 3.11's
adversarial testing (`tests/security/test_security.py`, 21 tests) rather
than re-deriving findings from scratch — see
`docs/project-report-part3.11.md` Section 14 for the original discovery
process and Live Verification Log.

## 1. Authentication
- Passwords hashed with Werkzeug's PBKDF2 (`pbkdf2:` format), never stored
  or logged in plaintext — verified by `TestPasswordSecurity`.
- Weak passwords (below `MIN_PASSWORD_LENGTH`) rejected at registration.
- `ProductionConfig` refuses to boot with a default `SECRET_KEY` or missing
  `DATABASE_URL` — a fail-fast check, not a soft warning.

## 2. Authorization
- Every protected route: `@login_required` + `@role_required(<ROLE>)`.
- Cross-role probes verified in both directions (student → faculty routes,
  faculty → student-only routes) — both correctly `403`.
- Cross-user resource access (e.g. another student's quiz attempt) returns
  `404`, never `403` — never confirms another user's resource exists.

## 3. Session Management
- Session cookies: `HttpOnly` always; `Secure` in production
  (`SESSION_COOKIE_SECURE = True` under `ProductionConfig`).
- Logout actually invalidates the session (verified — a subsequent
  `/api/auth/me` after logout returns `401`/redirects, not a stale profile).

## 4. Password Hashing
See Section 1 — PBKDF2 via Werkzeug, industry-standard, never plaintext.

## 5. Protected Routes
All 146 routes swept in Part 3.11's `TestAuthenticationGatesAllModules` and
this phase's re-verification — every module (Tutor, Quiz, Code Review,
Analytics, Faculty) rejects unauthenticated access consistently.

## 6. Input Validation
`app/utils/validators.py` (`require_fields`, `validate_email`,
`validate_password`, `validate_role`, `validate_name`) — centrally applied
across every route accepting user input, 31 direct unit tests
(`tests/unit/test_utils.py`).

## 7. SQL Injection Protection
100% SQLAlchemy ORM — no raw string-interpolated SQL anywhere in the
codebase (verified by code review, not just testing). A SQL-injection-shaped
login attempt (`' OR '1'='1`) was tested and correctly fails as a normal
auth rejection, not a bypass or a 500.

## 8. XSS Protection
Jinja2 auto-escaping is on by default and was specifically verified: HTML
stored via the API (e.g. a topic name containing `<script>`) is correctly
neutralized when rendered into any template.

## 9. CSRF Protection
JSON APIs are deliberately CSRF-exempt (no HTML `<form>` submits them
directly — a documented, tested posture, not an oversight); Flask-WTF forms
elsewhere (login, registration) carry real CSRF tokens.

## 10. File Upload Validation
- Extension whitelist (`ALLOWED_UPLOAD_EXTENSIONS`) enforced server-side.
- Size cap via `MAX_CONTENT_LENGTH`.
- Storage filenames are UUID-generated, never the client-supplied name —
  verified path-traversal-proof (`../../evil.txt` correctly cannot escape
  the upload directory).

## 11. API Security
- Consistent response envelope (no stack traces leaked to the client —
  full detail goes to `logs/error.log` server-side only).
- Consistent, correct status codes (`400`/`401`/`403`/`404`/`409` used per
  their actual REST meaning, verified in `tests/api/test_api_contract.py`).

## 12. Prompt Injection Resistance
The safety layer (`app/ai/services/safety_layer.py`, Part 3.6) processes an
injection-shaped message ("ignore all previous instructions...") without
crashing or bypassing topic-restriction plumbing. **Honest limitation**:
this is verified against the offline Mock provider only — real adversarial
red-teaming against a live LLM provider has not been performed and should
happen before a production deployment with a real provider enabled (see
`SECURITY.md`'s Known Limitations).

## Two Real Vulnerabilities Found and Fixed (Part 3.11)
1. `GET /api/quiz/<attempt_id>` — a cross-user probe hit an unguarded call
   one line above its own exception handler, returning a raw `500` (which
   could leak stack-trace detail in a misconfigured deployment) instead of
   a clean `404`. **Fixed.**
2. Faculty topic creation with an out-of-range `difficulty_level` hit a raw
   database `IntegrityError` instead of clean input validation. **Fixed**
   with service-layer bounds checking, defense-in-depth on top of the
   existing DB `CHECK` constraint.

## Residual Risk Summary (Honest, Not Hidden)

| Risk | Severity | Status |
|---|---|---|
| No live-LLM prompt injection red-teaming | Medium | Documented, deferred to whoever enables a real provider |
| No rate limiting enforced | Medium | Config value reserved (`RATE_LIMIT_PER_MINUTE`), no middleware wired — real gap for internet-facing deployment |
| SQLite (no built-in encryption at rest) | Low (for a course project) | Fine for the intended single-server, offline-capable use case |
| No dedicated secrets manager | Low | `.env` is adequate for this project's scale; flagged for anyone deploying at real production scale |

## Recommendation
Ready for university/course submission as-is. Before any real internet-
facing production deployment: add rate limiting, perform live-LLM
adversarial testing if a real provider is enabled, and put a secrets
manager in front of `.env`.
