# OSTutorLLM — Viva Preparation (100 Questions & Model Answers)

Grouped by category. Answers are grounded in what this codebase actually
does — cite a real file/mechanism where useful, don't overclaim.

---

## A. Architecture & System Design (1-15)

**1. What architectural style does OSTutorLLM use?**
A layered, monolithic Flask application — not microservices. Each feature
area (Tutor, Quiz, Code Review, Analytics, Faculty) is its own Python
package under `app/` with a `services/` layer for logic and thin route
blueprints for HTTP translation.

**2. Why monolithic instead of microservices?**
The actual requirement is a single, student-reproducible deployment — one
`pip install`, one process. Microservices would add distributed-systems
complexity (service discovery, network calls, partial failure handling)
with no real benefit at this scale.

**3. How do the different engines (Tutor, Quiz, Code Review) communicate?**
Indirectly, through shared database tables (`Progress`, `LearningTimeline`,
`Notification`) rather than direct function calls between engines — e.g.
the Quiz Engine writes to `Progress`, and the Analytics Engine reads it
back. This is proven directly in `tests/integration/test_cross_module_integration.py`.

**4. What is the "thin routes, fat services" pattern and why use it?**
Route functions only validate input, call one service function, and format
the response — all real logic lives in `app/*/services/*.py`. This makes
logic reusable (Part 3.10's Faculty Dashboard reused Part 3.9's Analytics
services unmodified) and testable without spinning up HTTP.

**5. How is the frontend built?**
Server-rendered Jinja2 templates + Bootstrap 5 + vanilla JavaScript — no
frontend framework, no build step. Each page fetches its own data via the
JSON API on load.

**6. Why no React/Vue?**
A build pipeline is more infrastructure than a course project needs, and
this project's own principle is "free, low-infrastructure, student-
reproducible." Server-rendered HTML + fetch() covers every requirement here.

**7. How many database tables does the project have?**
32-33 tables (see `docs/DATABASE_DOCUMENTATION.md`), spanning identity,
curriculum, quiz, tutor, code review, analytics, and faculty administration.

**8. What design pattern does the AI provider layer use?**
A factory/strategy pattern — every provider (OpenAI, DeepSeek, Ollama, Mock)
implements the same interface, selected at runtime via the `AI_PROVIDER`
environment variable (`app/ai/config.py`). Swapping providers needs zero
code changes in the engines that call it.

**9. How is configuration managed across environments?**
Three config classes (`DevelopmentConfig`, `TestingConfig`,
`ProductionConfig`) in `app/config/config.py`, selected via `APP_ENV`.
Production refuses to boot without a real `SECRET_KEY`/`DATABASE_URL` — a
deliberate fail-fast safety check.

**10. What is the response envelope contract?**
Every JSON API returns `{"status": "success|fail|error", "message": "...",
"data": {}}` — verified consistently across all 22 blueprints by
`tests/api/test_api_contract.py`.

**11. How does the project avoid tight coupling between the Quiz Engine and Analytics?**
Analytics services take an explicit `user_id` parameter rather than reading
Flask's `current_user`. This is why Faculty (viewing OTHER users) could
reuse them unmodified.

**12. What's the single biggest architectural limitation?**
No `courses`/`enrollments` concept — every "class-wide" faculty view is
actually platform-wide, not scoped to a real roster. Documented explicitly
since Part 3.10.

**13. How is versioning handled for database schema changes?**
Alembic migrations, one file per phase that needed a schema change (8
migrations across Parts 3.4-3.10), always additive (new tables/nullable
columns), never dropping/renaming what existing code depends on.

**14. What happens if two students hit the same endpoint simultaneously?**
Verified directly: `tests/performance/test_performance.py`'s concurrency
tests hit the real app with 10-20 simultaneous threads and confirm no
race-condition 500s — either a clean success or the documented
single-active-attempt `409` for quizzes.

**15. Why SQLite instead of Postgres by default?**
Zero-infrastructure, free-tier-first — a student can run the whole project
with no separate database server. `DATABASE_URL` is a pure environment
variable, so switching to Postgres for real production scale needs no code
change (see `docker-compose.yml`'s commented Postgres service).

## B. Flask & Backend Engineering (16-27)

**16. What is the Flask application factory pattern, and does this project use it?**
Yes — `create_app(config_name)` in `app/__init__.py` builds and returns a
configured Flask app rather than a module-level global, which is what makes
`TestingConfig`'s isolated in-memory database possible for every test.

**17. How are blueprints organized?**
22 blueprints, one per feature/concern (e.g. `quiz_bp` for the student-
facing Quiz API, `faculty_quiz_bp` for faculty quiz authoring — kept
separate even though both touch quizzes, because they're different
concerns).

**18. How does authentication work?**
Flask-Login session-based auth. `@login_required` gates any protected
route; `@role_required(ROLE)` (a custom decorator, `app/utils/helpers.py`)
additionally checks the user's role.

**19. Why session cookies instead of JWT?**
Server-rendered app with same-origin API calls — sessions are simpler,
don't need client-side token storage/refresh logic, and Flask-Login handles
the security details (HttpOnly, Secure in production) out of the box.

**20. How is the database accessed?**
SQLAlchemy ORM exclusively — no raw SQL string interpolation anywhere,
which is also the structural reason SQL injection isn't possible here.

**21. How are migrations run?**
`flask db upgrade` (Flask-Migrate/Alembic). Idempotent — safe to run on
every deploy/container start (see `scripts/docker-entrypoint.sh`).

**22. What production WSGI server does this project use?**
Gunicorn (`wsgi.py`), never Flask's built-in dev server in production — a
real gap (gunicorn was referenced in `wsgi.py`'s docstring since Part 3.1
but never actually in `requirements.txt`) found and fixed in Part 3.12.

**23. How does error handling work?**
Centralized error handlers (`app/error_handlers.py`, Part 3.3) — every
exception is caught, full detail logged server-side to `logs/error.log`,
and a sanitized message returned to the client. No stack traces ever leak
over the API.

**24. What's the difference between `run.py` and `wsgi.py`?**
`run.py` is for local development (Flask's dev server, debug mode);
`wsgi.py` exposes the `app` object for Gunicorn in production. Both call
the same `create_app()` factory.

**25. How is file upload handled securely?**
`werkzeug.utils.secure_filename` sanitizes the input name, but the actual
stored filename is a freshly generated UUID — the client-supplied name is
never used as a path, which defeats path traversal by construction, not
just by filtering.

**26. How does the app know if a quiz question was answered correctly?**
`app/quiz/services/evaluation_engine.py` — per-question-type evaluation
logic (exact match for MCQ, fuzzy/partial credit for others), called from
`quiz_service.submit_quiz()`.

**27. What logging strategy does the project use?**
Python's standard `logging` module with rotating file handlers — separate
logs for general app activity, errors, user activity, and AI-specific calls
(`logs/*.log`), configured once in `app/utils/logger.py` (Part 3.3).

## C. Database Design (28-39)

**28. What ORM does this project use?**
SQLAlchemy, via Flask-SQLAlchemy.

**29. How is a User connected to StudentProfile/FacultyProfile?**
A 1:1 relationship — `User.role` determines which profile table applies;
`user.student_profile`/`user.faculty_profile` relationships give direct
access to the role-specific extension.

**30. How does the Progress table work?**
One row per (student, topic) pair with a `mastery_score` — written by
multiple engines (Quiz Engine after grading, Code Review after scoring),
making it the shared source of truth Analytics/Faculty both read from.

**31. What's the LearningTimeline table for?**
An append-only chronological event log (Part 3.9) — every quiz attempt,
code review, tutor session, and achievement earned writes one row, giving
both the student's own activity feed and the faculty dashboard's
"recent activity" the same real data source.

**32. How are quiz questions stored, and how does answer-checking avoid tampering?**
`QuizQuestion.correct_answer` is JSON-encoded server-side; it's never
serialized into the `/start` response — verified explicitly (grepped the
response body in Part 3.7's testing) to contain zero leaked answers.

**33. What's the difference between a dynamically-generated quiz and a faculty-authored one?**
Dynamic: `quiz_service.start_quiz()` creates a brand-new `Quiz` +
`QuizQuestion` row set on every call (per-attempt generation). Authored:
faculty create ONE `Quiz` row (with `created_by_user_id` set) that many
students can each attempt via the separate `start_authored_quiz()` function
— a deliberate parallel design, not a rewrite of the first.

**34. How does the schema support content versioning?**
`ContentRevision` (Part 3.10) snapshots a Topic/Lesson's full field state as
JSON before every edit; `restore_revision()` writes that snapshot back — a
real, working undo, not just an audit log.

**35. What database constraints does the schema use for data integrity?**
Foreign keys (with `ondelete` cascade/set-null rules per relationship), `UNIQUE`
constraints (e.g. one submission per student per assignment), and `CHECK`
constraints (e.g. `difficulty_level BETWEEN 1 AND 5`).

**36. Give an example of a real bug caught by a database constraint.**
Part 3.7's Alembic autogenerate silently missed a `CHECK` constraint
expansion (6→13 quiz question types) — caught by manually inspecting the
generated migration against the model diff, not by trusting the tool.

**37. How would you scale this database for more concurrent users?**
Switch `DATABASE_URL` to Postgres (zero code change, since it's pure
SQLAlchemy) and re-run the performance suite against it — SQLite's
single-writer model is the real ceiling for concurrent write-heavy load.

**38. What's stored in SystemConfiguration and why?**
A generic key-value table (Part 3.4) for runtime-toggleable settings — used
in Part 3.10 for the AI Tutor enable/disable switch and default difficulty/
teaching-mode, so faculty can change these without a redeploy.

**39. How are database backups handled?**
A real, working file-copy backup for SQLite (`settings_service.trigger_backup()`,
Part 3.10) — copies the live `.db` file to a timestamped backup, downloadable
by faculty. Honestly documented as SQLite-only; Postgres would need
`pg_dump`.

## D. LLM / AI Engineering (40-54)

**40. How does the AI Tutor decide what to say?**
A staged prompt-construction pipeline (`app/ai/prompts/manager.py`) builds a
system prompt from the current teaching stage, topic, difficulty, and
conversation history, then sends it to whichever provider is configured.

**41. What LLM providers are supported?**
OpenAI, DeepSeek, Ollama (local models), and an offline Mock provider (the
default) — one class per provider, same interface, swapped via `AI_PROVIDER`.

**42. Why is Mock the default provider?**
So the entire platform — including all 409 automated tests — runs with zero
API cost, zero API key, and zero network dependency. A student can clone
and run the whole thing offline.

**43. How does conversation memory work?**
`ChatSession.state_json` (Part 3.6) persists conversation state between
turns — the conversation manager reloads it each turn rather than the LLM
call being stateless.

**44. What is the "teaching mode" concept?**
Five validated modes (`beginner`/`intermediate`/`advanced`/`exam_prep`/
`lab_practice`, `app/ai/services/teaching_modes.py`) that change the
prompt's instructional style — a centralized, validated vocabulary so a
typo'd mode string can't silently fall back to a wrong default.

**45. How does the hint ladder work?**
Both the Tutor and Code Review engines use a staged hint system — an early
stage gives a conceptual nudge, a later stage a structural hint, and only
the final stage reveals the actual answer/fix. This is enforced at the
prompt-authoring level, not just instructions the model could ignore.

**46. How is topic restriction (staying on-topic) enforced?**
The safety layer (`app/ai/services/safety_layer.py`) plus prompt-level
scoping — every prompt explicitly constrains the model to the current
topic's domain.

**47. What happens if the LLM call fails or times out?**
A fallback path (Part 3.6) — configurable retries (`AI_MAX_RETRIES`,
`AI_RETRY_BACKOFF_SECONDS`) with a graceful degraded response rather than a
500 to the student.

**48. How does the Quiz Engine use the LLM?**
As a fallback question source when the static question bank doesn't have
enough questions for a topic/difficulty — the static bank (hand-authored,
free, instant) is preferred; the LLM only fills gaps.

**49. How does Code Review avoid the LLM just rewriting the student's code?**
Every review prompt explicitly requests a "direction," never corrected
code — enforced at the prompt-authoring level for every stage except the
final hint (a deliberate, single exception once hints are exhausted).

**50. What's the Security Scanner in Code Review, and why is it separate from the LLM review?**
A pre-LLM gate (`app/code_review/services/security_scanner.py`) that blocks
genuinely dangerous submissions (`rm -rf /`, `curl | bash`, fork bombs)
BEFORE they ever reach the LLM — deterministic, not dependent on the model
choosing to refuse.

**51. How is prompt injection handled?**
The safety layer processes injection-shaped input without crashing or
bypassing topic restriction (tested). Honestly: this is verified against
the offline Mock provider only — real adversarial testing against a live
model hasn't been done (see `docs/SECURITY_REVIEW.md`).

**52. What is RAG, and does this project use it?**
Retrieval-Augmented Generation — grounding LLM output in retrieved
documents rather than pure model knowledge. This project does NOT currently
use RAG; it's listed as a genuine Future Enhancement (institution-specific
notes) in `docs/RESEARCH_AND_INNOVATION.md`.

**53. How would you add a new LLM provider?**
One new file in `app/ai/providers/` implementing the same interface as the
existing providers, plus one line in the provider factory
(`app/ai/config.py`) — zero changes anywhere else, by design.

**54. Why not fine-tune a model instead of prompting?**
Cost and infrastructure — fine-tuning needs training data, GPU time, and
ongoing retraining. Prompt engineering against a general model is free-
tier-compatible and was the right tradeoff for a course project; fine-tuning
is listed as Future Scope.

## E. Linux / Operating Systems Concepts (55-64)

**55. What OS topics does the curriculum cover?**
Process management, CPU scheduling (FCFS/SJF/RR/Priority), deadlocks
(Banker's Algorithm), synchronization (semaphores/monitors/classic
problems), memory management (paging/segmentation/page replacement), file
systems, disk scheduling, and Linux/shell fundamentals.

**56. What is a process vs. a thread, and does the tutor teach the distinction?**
Yes — this is core curriculum content in the Process Management module,
covered through the Tutor Engine's staged teaching and the Quiz Engine's
question bank.

**57. What is a race condition, and how does this project's own backend avoid one?**
Two threads/processes accessing shared state without synchronization,
producing a result dependent on timing. This project's own quiz-attempt
locking (single-active-attempt rule, Part 3.7) is a real, working example
of exactly this concept applied to the backend itself — tested under real
concurrency in Part 3.11.

**58. What is a deadlock, and how does the curriculum teach it?**
A cycle of processes each waiting on a resource held by another. Taught via
the Banker's Algorithm and Resource Allocation Graphs in the curriculum, and
assessed through dedicated quiz question types.

**59. What is virtual memory, and where does it appear in the curriculum?**
An abstraction giving each process its own address space larger than
physical RAM, backed by paging/page replacement — covered in the Memory
Management module.

**60. What disk scheduling algorithms does the curriculum cover?**
FCFS, SSTF, SCAN, C-SCAN, LOOK, C-LOOK.

**61. What is the difference between paging and segmentation?**
Paging divides memory into fixed-size frames; segmentation divides it into
variable-size logical segments (code/data/stack). Both are taught as
distinct memory management strategies.

**62. What classic synchronization problems does the tutor cover?**
Producer-Consumer, Readers-Writers, Dining Philosophers.

**63. Why teach OS concepts through Linux commands and shell programming specifically?**
Practical, hands-on reinforcement — a student learning process management
can immediately run `ps`, `kill`, `jobs` and see the concept in a real
running system rather than only in the abstract.

**64. What's the significance of file permissions (chmod/chown) in the curriculum?**
Ties directly into OS access-control concepts (owner/group/other,
read/write/execute bits) — taught as both a Linux command topic and
reinforced through Code Review submissions that use permission commands.

## F. Shell Programming (65-72)

**65. What shell programming concepts does the platform teach?**
Variables, conditionals, loops, functions, arrays, file handling, text
processing (grep/sed/awk), process management, redirection, and pipes.

**66. How does the Code Review Engine's static analysis work?**
Deterministic, LLM-free checks (`app/code_review/static_analysis/analyzer.py`)
— syntax balance (loops/conditionals/quotes), missing shebang, unused
variables, unsafe commands, style issues — computed via regex/heuristics,
not by executing the script.

**67. Why not just run the student's script to check it (like a real interpreter would)?**
Security and simplicity — executing arbitrary student-submitted shell code
server-side is a real attack surface. Deterministic static analysis + LLM
review avoids that entirely; live sandboxed execution is a documented
Future Enhancement.

**68. What's a real bug the static analyzer had, and how was it fixed?**
A false positive: a valid `for...done` loop was incorrectly flagged as a
mismatched `while`/`until` before the fix grouped all three loop openers
under one shared-closer check — now covered by a permanent regression test
(Part 3.8).

**69. How does the platform score a shell script?**
8 dimensions (correctness, logic, syntax, readability, efficiency, style,
documentation, best practices) computed deterministically from static
findings — never an LLM call, so it's consistent, explainable, and free.

**70. What dangerous shell patterns does the Security Scanner block?**
`curl | bash`, `rm -rf /`, fork bombs, and similar destructive/injection
patterns — blocked before the LLM ever sees the submission, with legitimate
similar-looking commands (`chmod 755`, scoped `rm`) correctly passing
through (false-positive-tested).

**71. How does code comparison/diffing work across resubmissions?**
A student can resubmit an improved version to the same review session;
`GET /compare` returns the real diff plus per-dimension score deltas — a
genuine, computed comparison, not a template.

**72. What shell programming topics does the Linux Command Library cover, and who manages it?**
Faculty manage it via Content Management (Part 3.10) — commands with
syntax/description/category, tied optionally to a curriculum topic.

## G. Security (73-84)

**73. How are passwords stored?**
Hashed with Werkzeug's PBKDF2, never plaintext — verified directly (the
stored hash never equals the raw password, and starts with the expected
`pbkdf2:` prefix).

**74. How is SQL injection prevented?**
Structurally — 100% SQLAlchemy ORM, parameterized queries throughout, no
raw string-interpolated SQL anywhere in the codebase.

**75. How is XSS prevented?**
Jinja2 auto-escaping (on by default) — verified explicitly: HTML stored via
the API renders as inert text in every template, never executed markup.

**76. Why are the JSON APIs CSRF-exempt — isn't that a vulnerability?**
No — CSRF matters when a browser auto-submits credentials (cookies) to a
form/endpoint from a malicious third-party page. This project's JSON APIs
are never submitted via an HTML `<form>`, so the classic CSRF attack vector
doesn't apply to them; the actual HTML forms (login, registration) DO carry
real CSRF tokens via Flask-WTF.

**77. How is file upload secured?**
Extension whitelist, size cap, and — critically — the stored filename is a
generated UUID, never the client-supplied name, which defeats path
traversal by construction.

**78. What's the difference between 401 and 403 in this API, and is it applied consistently?**
401 = not authenticated at all; 403 = authenticated but the wrong role.
Explicitly tested to never be confused (`tests/security/test_security.py`).

**79. Why does accessing another user's resource return 404 instead of 403?**
So the API never confirms the resource even exists to someone who
shouldn't see it — a deliberate information-disclosure-avoidance pattern,
consistent since Part 3.7.

**80. What real security bug was found during this project's own testing?**
A cross-user quiz-attempt probe hit an unguarded exception path and
returned a raw `500` instead of the intended `404` — found by adversarial
testing in Part 3.11, fixed by moving the vulnerable call inside the
existing (but previously bypassed) exception handler.

**81. How are sessions secured?**
`HttpOnly` cookies always (JavaScript can't read them, mitigating XSS-based
session theft); `Secure` (HTTPS-only) in production.

**82. What's missing from this project's security posture, honestly?**
No enforced rate limiting (config value reserved, no middleware wired), no
live-LLM prompt-injection red-teaming, no dedicated secrets manager — all
documented in `SECURITY.md`, not hidden.

**83. How would you add rate limiting?**
Flask-Limiter, keyed by IP or user ID, applied as a decorator on
authentication and other abuse-prone endpoints — the config value
(`RATE_LIMIT_PER_MINUTE`) already exists, reserved for exactly this.

**84. How does the AI Tutor's safety layer relate to general web security?**
It's a distinct concern (LLM-specific: topic restriction, injection-shaped
input handling) layered on top of, not instead of, the standard web-security
measures (auth, input validation, ORM) covering the rest of the app.

## H. Testing & Quality Assurance (85-92)

**85. How many tests does this project have, and what's the coverage?**
409 tests, 82.2% overall code coverage (Part 3.11), reorganized into
unit/integration/api/frontend/security/performance suites.

**86. What testing types does the suite cover?**
Unit, integration, API (contract-level), frontend (HTML structure/
accessibility), security (adversarial), and performance (real concurrent
load against a live server thread) — 6 pytest markers, one per type.

**87. How is performance actually tested, given no load-testing tool is installed?**
By booting the real app via `werkzeug.serving.make_server` in a background
thread and driving it with genuine concurrent `requests` calls —
deliberately NOT the Flask test client, which doesn't exercise real socket
concurrency.

**88. Give an example of a bug found by the test suite itself (not the product).**
The performance-test fixture initially set `os.environ["DATABASE_URL"]`
too late (after config module import) and briefly, silently wrote real
test data into the project's actual development database before this was
caught by a reproducibility check (running the suite twice in a row).

**89. What's the project's policy on bug fixes and tests?**
Every fix ships with a regression test that fails before the fix and passes
after — documented explicitly in `docs/BUG_REPORT_TEMPLATE.md` and followed
consistently since Part 3.6.

**90. Why is frontend testing done with BeautifulSoup instead of Selenium?**
Honest, stated limitation — no headless browser is available in this
project's development/CI environment. BeautifulSoup verifies real
server-rendered HTML structure (navigation, forms, accessibility, JS/DOM
contracts) but can't test actual visual rendering or cross-browser behavior.

**91. How is regression testing handled across 12 development phases?**
The entire suite runs together every time — this is the exact mechanism
that has kept every earlier phase's original test count passing unchanged
through every later phase (8 → 192 → 240 → 302 → 409).

**92. What would you test next if given more time?**
Real browser automation (Selenium/Playwright) once available, live-LLM
adversarial red-teaming, and a production-WSGI-server (not dev-server)
load test — all explicitly listed in Part 3.11's Future Improvements.

## I. Future Scope (93-100)

**93. What's the single most valuable next feature?**
A real courses/enrollments schema — it would unlock true per-instructor
rosters, department dashboards, and multi-section support, and is the
architectural boundary every later Faculty feature has bumped into.

**94. How would you add voice interaction?**
Speech-to-text on the input side (e.g. Web Speech API or a server-side
model) feeding into the existing Tutor message pipeline unchanged, and
text-to-speech on the output side — the Tutor Engine's interface doesn't
care whether the input originated as typed text or transcribed speech.

**95. How would you support multiple languages?**
Locale-aware prompt templates (the prompt manager already centralizes
templates in one location) plus i18n on the frontend strings — a
substantial but well-scoped addition given the existing prompt-template
architecture.

**96. What would a mobile app need from this backend?**
Nothing new on the backend — the JSON API is already fully separate from
the server-rendered HTML frontend; a mobile app would just be a second
client consuming the same `/api/*` routes.

**97. How would RAG over institutional notes work here?**
Faculty already upload content files (Part 3.10's `ContentResource`) — RAG
would add an embedding/retrieval step over those files, injected into the
Tutor's prompt construction alongside the existing topic/difficulty
context.

**98. What would it take to deploy this for real multi-institution use?**
The courses/enrollments schema (Q93), Postgres instead of SQLite, rate
limiting, a secrets manager, and horizontal scaling behind a load balancer
— each individually well-scoped, none requiring a full rewrite.

**99. Why is a fine-tuned model listed as future work instead of done now?**
Cost and infrastructure — fine-tuning needs curated training data and GPU
time neither available nor necessary for a free-tier-first course project;
prompt engineering against the Mock/API providers achieves the same
educational goal at zero infrastructure cost today.

**100. What's the project's overall status and what would you tell an evaluator?**
Feature-complete across 12 phases (auth through faculty administration,
testing, and deployment packaging), 409 passing tests at 82% coverage, real
bugs found and fixed via genuine adversarial testing rather than assumed
correct, and every phase's scope decisions documented rather than hidden —
see `docs/project-report-part3.12.md`'s Final Completion Report.
