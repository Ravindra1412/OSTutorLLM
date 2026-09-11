# OSTutorLLM — Developer Guide

## 1. Codebase Tour

```
app/
├── ai/            Tutor Engine (Part 3.6)
│   ├── config.py         Provider selection (AI_PROVIDER env var)
│   ├── providers/           OpenAI / DeepSeek / Ollama / Mock — one class each, same interface
│   ├── prompts/                Jinja-templated prompt files (app/ai/prompts/templates/*.txt) + manager.py
│   └── services/                  tutor_service.py (orchestrator), conversation_manager, memory_manager, safety_layer
├── analytics/       Learning Analytics (Part 3.9) — services/ only, no routes (see app/routes/analytics_routes.py)
├── auth/              Authentication (Part 3.3/3.5) — services.py has register_user/login_user/change_password/etc.
├── code_review/         AI Code Review (Part 3.8) — static_analysis/, services/ (security_scanner, llm_review_engine, hint_engine, scoring_engine)
├── faculty/               Faculty Dashboard (Part 3.10) — 12 single-responsibility service modules
├── models/                  One file per table, all registered in models/__init__.py
├── quiz/                      Quiz Engine (Part 3.7) — question_bank/, services/ (question_generator, evaluation_engine, timer_service, security)
├── routes/                      22 Flask blueprints — thin, business logic lives in services/
├── static/                        css/design-system.css (the ONE design system, reused everywhere), js/ (vanilla, one file per page)
├── templates/                        Jinja2, organized by feature area (auth/, quiz/, code_review/, analytics/, faculty/)
└── utils/                              validators.py, formatters.py (the {status,message,data} contract), helpers.py (role_required)
```

## 2. Architectural Principles (Established Since Part 3.6, Never Violated)

1. **Routes are thin.** A route function validates input, calls exactly one
   service function, and formats the response. If you're writing an `if`
   statement with real business logic inside a route, it belongs in
   `services/` instead.
2. **Services take explicit parameters, not `current_user`.** Every service
   function takes a `user_id` (or similar) parameter rather than reaching
   for Flask's `current_user` global. This is why Part 3.10's Faculty
   Dashboard could reuse 100% of Part 3.9's Analytics services unmodified —
   they were built to be called on behalf of *any* user, not just "the
   currently logged in one."
3. **One shared table per cross-cutting concern.** `Progress`, `Notification`,
   `ActivityLog`, `LearningTimeline` are each written to by multiple engines
   rather than each engine keeping its own private copy — this is what makes
   the Faculty Dashboard's cross-student aggregation possible without a
   second data pipeline.
4. **Additive migrations only.** Every migration since Part 3.4 adds tables/
   nullable columns; none has ever dropped or renamed an existing column
   that other code depends on. Check `migrations/versions/` for the pattern
   before writing a new one.
5. **Every bug fix ships with a regression test.** See
   `docs/BUG_REPORT_TEMPLATE.md`'s Resolution Tracking section — this is not
   optional in this codebase's own history.

## 3. Adding a New Feature — Worked Example

Say you want to add a "Bookmark a Lesson" feature:

1. **Model** (if new data is needed): `app/models/bookmark.py` already
   exists from Part 3.4 — check `app/models/__init__.py` before assuming you
   need a new table.
2. **Service**: add `bookmark_lesson(user_id, lesson_id)` to a relevant
   `services/` module — takes `user_id` explicitly, not `current_user`.
3. **Route**: a thin wrapper in the relevant `routes/*.py` — validate input,
   call the service, `return success_response(...)`.
4. **Test**: add to the relevant `tests/{unit,integration,api}/` file, or a
   new one if it's a new concern — use `tests/fixtures/factories.py`'s
   `make_student`/`login` helpers rather than reinventing them.
5. **Run**: `./run_tests.sh` before committing.

## 4. The AI Provider Abstraction

`app/ai/providers/` — every provider (OpenAI, DeepSeek, Ollama, Mock)
implements the same interface (`generate(messages) -> str`, roughly). Adding
a new provider means adding one new file there and one line in
`app/ai/config.py`'s provider factory — no changes anywhere else in the
Tutor/Quiz/Code Review engines that call it.

## 5. Database Migrations

```bash
# After changing a model:
flask db migrate -m "Part 3.X: describe the change"
# ALWAYS review the generated file before applying — Alembic's
# autogenerate has missed things before in this project's own history
# (see Part 3.7's CHECK-constraint bug in docs/project-report-part3.7.md
# equivalent notes) — never trust it blindly.
flask db upgrade
```

## 6. Frontend Conventions

- No build step, no framework — Bootstrap 5 (CDN) + vanilla JS.
- One `*.js` file per page, matching the page's template name
  (`app/templates/faculty/dashboard.html` ↔ `app/static/js/faculty_dashboard.js`).
- Every page fetches its own data via the JSON API on load — templates are
  thin shells with the right `id` attributes for the JS to hook into (see
  `tests/frontend/test_page_rendering.py`'s `TestDashboardJSContract` for
  why this contract matters and how it's tested).
- Reuse `app/static/css/design-system.css`'s existing classes
  (`.card-elevated`, `.badge-tier`, `.btn-accent`, etc.) — don't invent new
  CSS for something the design system already covers.

## 7. Testing Conventions

See `docs/project-report-part3.11.md` for the full testing architecture.
Quick reference:
```bash
./run_tests.sh unit          # fast, isolated
./run_tests.sh integration    # cross-module, real DB
./run_tests.sh api             # real HTTP via test client
./run_tests.sh security          # adversarial
./run_tests.sh performance         # slow — real live-server concurrency
./run_tests.sh coverage              # full run + HTML report
```

## 8. Common Pitfalls (Real Bugs This Project Has Actually Hit)

- **Naive vs. aware datetimes**: SQLite strips timezone info on storage.
  Compare `stored_dt.replace(tzinfo=timezone.utc)` against
  `datetime.now(timezone.utc)`, never compare them directly — see
  `app/quiz/services/timer_service.py` for the established pattern.
- **Class-attribute config gotcha**: `DevelopmentConfig.SQLALCHEMY_DATABASE_URI`
  is evaluated once at import time. Setting `os.environ["DATABASE_URL"]`
  after any module has already imported `app.config.config` has no effect —
  mutate the class attribute directly and do it *before* `create_app()` runs
  if you need to redirect the database at test/script time (see
  `tests/performance/test_performance.py`'s `live_server` fixture for the
  correct pattern — this exact mistake briefly polluted the real dev
  database during Part 3.11's own development).
- **Blueprint registered but not wired**: importing a blueprint in
  `app/__init__.py` is not the same as adding it to the registration loop —
  always verify with `app.url_map.iter_rules()` after adding a new
  blueprint, not just by reading the import line.

## 9. Where to Find Everything Else

`docs/API_DOCUMENTATION.md` (endpoint reference), `docs/DATABASE_DOCUMENTATION.md`
(schema), `docs/ARCHITECTURE.md` (component diagram + data flow),
`docs/project-report-part3.1.md` through `part3.12.md` (full build history,
one file per phase, each with a real Live Verification Log).
