# OSTutorLLM — Architecture Documentation

## 1. High-Level Architecture

Layered, monolithic Flask application (deliberately not microservices — a
single-deployable, student-reproducible app is the actual requirement here,
not a distributed-systems showcase):

```
Browser (Bootstrap 5 + vanilla JS, no build step)
        |  JSON over HTTP
Flask Blueprints (22) -- thin, validate + delegate
        |
Service Layer (app/*/services/) -- all real business logic
        |
SQLAlchemy ORM --> SQLite (default) / PostgreSQL
        |
Pluggable LLM Provider Layer (Mock / OpenAI / DeepSeek / Ollama)
```

## 2. Package-Per-Engine Pattern

Every major feature is its own top-level package under `app/`, each
following the identical internal shape established in Part 3.6 and repeated
in every subsequent phase:

```
app/<engine>/
├── services/          one file per responsibility, orchestrator pattern
└── (topics.py, question_types.py, static_analysis/, etc. -- engine-specific extras)
```
`app/routes/<engine>_routes.py` is the thin HTTP-facing layer per engine.
This is why Part 3.9 (Analytics) and Part 3.10 (Faculty) could be added
without modifying Parts 3.6-3.8's code at all -- new packages, not edits to
old ones.

## 3. Data Flow: A Complete Quiz Attempt

```
1. Student -> POST /api/quiz/start
2. quiz_routes.py validates -> quiz_service.start_quiz()
3. question_generator.py: static bank preferred, LLM fallback fills gaps
4. QuizAttempt + QuizQuestion rows created
5. Student -> POST /api/quiz/<id>/answer (per question)
6. Student -> POST /api/quiz/<id>/submit
7. evaluation_engine.py grades each QuizResult
8. progress_updater.py blends the score into the shared Progress table
9. achievements.py checks quiz-specific badges
10. timeline_service.py (Part 3.9) logs a LearningTimeline event
11. achievement_manager.py (Part 3.9) checks CROSS-ENGINE badges
    (e.g. "Well-Rounded Learner" needs Tutor + Quiz + Code Review)
12. Response returned to student; Faculty's class_analytics.py (Part 3.10)
    will see this attempt's data on its very next query -- no batch job,
    no cache to invalidate, because everyone reads the same live tables.
```

## 4. The AI Provider Abstraction

```
app/ai/config.py             -> selects provider by AI_PROVIDER env var
app/ai/providers/{openai,deepseek,ollama,mock}.py -> same interface each
app/ai/prompts/manager.py    -> builds the actual prompt (teaching mode,
                                  stage, topic-restriction instructions)
app/ai/services/tutor_service.py -> orchestrates: safety_layer check ->
                                      prompt build -> provider call ->
                                      conversation_manager persists it
```
Swapping providers is a one-line config change; nothing above this
abstraction (Quiz Engine's LLM-fallback question generation, Code Review's
LLM review engine) knows or cares which provider is actually running.

## 5. Cross-Engine Data Sharing (Part 3.9's Key Architectural Decision)

Rather than each engine tracking its own analytics, every engine writes into
tables Part 3.9/3.10 read directly:
- `Progress` -- written by Tutor (indirectly, via lessons), Quiz, Code Review
- `LearningTimeline` -- written by all three engines' hook points
- `Notification` -- written by Faculty announcements/alerts, system events

This is why `app/faculty/services/student_management.py` could reuse
`app/analytics/services/*` **completely unmodified** -- those services were
deliberately built to take an arbitrary `user_id` parameter rather than
`current_user`, anticipating exactly this reuse before Part 3.10 existed.

## 6. Security Architecture

- **AuthN**: Flask-Login session cookies, `HttpOnly` + `Secure` (production).
- **AuthZ**: `@role_required(ROLE_STUDENT|ROLE_FACULTY)` decorator on every
  protected route -- verified via a full role-sweep test suite (Part 3.11).
- **Ownership**: resource-level checks at the query layer (e.g.
  `QuizAttempt.query.filter_by(id=..., user_id=current_user.id)`), never
  just at the route layer -- a cross-user probe gets `404`, never confirms
  existence via `403`.
- **Input validation**: `app/utils/validators.py` + DB-level `CHECK`
  constraints as defense in depth (see `docs/DATABASE_DOCUMENTATION.md`
  point 3).
- **File uploads**: extension whitelist, size cap, UUID-based storage
  filenames (path-traversal-proof).

Full review: `docs/SECURITY_REVIEW.md`.

## 7. Deployment Architecture

```
             +-------------+
Internet --> |  Reverse     |  (nginx/Caddy -- TLS termination,
             |  Proxy       |   not provided by this codebase)
             +------+------+
                    |
             +------v------+
             |  Gunicorn    |  (3 workers default -- see wsgi.py)
             |  (WSGI)      |
             +------+------+
                    |
             +------v------+
             |  Flask App   |
             +------+------+
                    |
             +------v------+
             | SQLite file  |  or Postgres (DATABASE_URL)
             | (1 process)  |
             +-------------+
```
See `docs/DEPLOYMENT_GUIDE.md` and `Dockerfile`/`docker-compose.yml`.

## 8. Known Architectural Boundaries (Documented, Not Hidden)

- **No course/enrollment schema.** Every "faculty view" is platform-wide,
  not per-instructor. This is the single largest piece of unbuilt
  infrastructure -- see `app/faculty/__init__.py`'s own scope-note docstring.
- **SQLite by default.** Fine for one server; real concurrent multi-worker
  production load needs Postgres (`DATABASE_URL` change only -- zero code
  changes required elsewhere, per the ORM abstraction).
- **No lesson-completion producer route.** `CompletedLesson` exists in the
  schema and Progress Tracker correctly reads it (as empty) -- no UI flow
  writes to it yet.
