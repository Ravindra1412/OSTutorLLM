# Changelog

All notable changes to OSTutorLLM are documented here, phase by phase, per
`docs/project-report-part3.X.md` for full detail on each release.

Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [3.13.0] — AI Learning Mentor (Final Integration Phase)
### Added
- Central Mentor Engine (`app/mentor/`) orchestrating the Tutor, Quiz, Code Review, Analytics, and Faculty engines — composition, not duplication
- Learning Health Engine — 8-factor, explainable, 0-100 score with a status label
- Confidence Engine — topic/command/programming/overall confidence with a real, evidence-based "why"
- AI Study Planner — daily/weekly/monthly schedules grounded in the student's actual weak topics
- AI Learning Insights — natural-language sentences, each tagged with the exact evidence that produced it
- Student + Faculty AI Assistant — rule-based intent router (explainable, no LLM call needed), Q&A logged to `mentor_interactions`
- New tables: `study_plans`, `mentor_interactions`
- 37 new tests (446 total), 88% coverage on the new mentor package, 83% overall
### Fixed
- `KeyError: 'confidence_score'` in `student_model.py`/`learning_health.py` — both assumed a dict key `performance_scorer.compute_all_scores()` doesn't return
- Faculty topic-keyword extraction missed topics that exist only in `Progress`, not the curriculum `Topic` table

## [3.12.0] — Deployment, Documentation & Final Packaging
### Added
- Docker support (`Dockerfile`, `docker-compose.yml`, idempotent migration entrypoint)
- `gunicorn` added to `requirements.txt` (previously only referenced in `wsgi.py`'s docstring — a real, latent deployment gap, fixed and live-verified with 1 and 2 worker configurations)
- Complete GitHub repository assets: `LICENSE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, this changelog
- Full documentation set: deployment guide, developer guide, student/faculty/administrator manuals, API reference, database docs, architecture docs, troubleshooting/maintenance guides, research summary, viva preparation, final submission checklist

## [3.11.0] — Testing, Quality Assurance & System Validation
### Added
- Reorganized `tests/` into `unit/`/`integration/`/`api/`/`frontend/`/`security/`/`performance/`/`fixtures/`/`reports/`
- 107 new tests: security (21), performance (10, real live-server concurrency), frontend (14), API contract (19), cross-module integration (12), utility unit tests (31)
- `pytest.ini` with markers, `run_tests.sh` single-command test runner, real coverage reporting (82.2% overall)
### Fixed
- `GET /api/quiz/<id>` 500'd on a cross-user probe instead of returning 404
- Faculty topic creation with an out-of-range `difficulty_level` hit a raw DB error instead of clean validation
- `quiz_service.submit_answer()` accepted a `question_id` that didn't belong to the current quiz

## [3.10.0] — Faculty Dashboard & Administration
### Added
- Faculty dashboard, student management, class-wide analytics, content management (topics/lessons/file uploads/version control), faculty-authored quizzes, assignment management, code review monitoring, reports (CSV/Excel/PDF), notification center, AI Tutor admin controls, settings, faculty profile
- New tables: `assignments`, `assignment_submissions`, `content_resources`, `content_revisions`; additive columns on `quizzes` and `faculty_profiles`
- 62 new tests (302 total)

## [3.9.0] — Progress Tracking & Learning Analytics
### Added
- Progress Tracker, Analytics Engine, Weak Topic Detector, Recommendation Engine, Achievement Manager (cross-engine badges/streaks), Performance Scorer, Predictive Engine (explainable heuristics), Learning Timeline, Student Dashboard with Chart.js visualizations
- New tables: `learning_timeline`, `recommendations`
- 48 new tests (240 total)

## [3.8.0] — AI-Powered Shell Programming Code Review
### Added
- Static analysis engine, security scanner (blocks dangerous commands pre-LLM), LLM review engine, 4-stage hint ladder, 8-dimension scoring, code comparison/diffing
- New tables: `code_review_sessions`, `code_submissions`
- 38 new tests (192 total)

## [3.7.0] — AI-Powered Quiz Engine
### Added
- 13 question types, static question bank + LLM-generated fallback, adaptive difficulty, server-authoritative timer, per-type evaluation, achievements/XP/leaderboard
- 57 new tests (154 total)

## [3.6.0] — AI Tutor Engine
### Added
- Multi-provider LLM integration (OpenAI/DeepSeek/Ollama/Mock), staged Socratic teaching workflow, conversation memory, hint ladder, safety layer, teaching modes

## [3.5.0] — Authentication Hardening
### Added
- Email verification, password reset flow, login history, nullable FK fix for pre-verification login attempts

## [3.4.0] — Full Schema & Curriculum
### Added
- Complete database schema: curriculum (topics/lessons/commands/shell programs), quiz tables, gamification (badges/achievements/XP), platform tables (notifications/activity log/system configuration)

## [3.3.0] — Backend Foundation
### Added
- Flask application factory, 8 blueprints, SQLite + Flask-Migrate, session-based authentication (Flask-Login), role-based authorization, structured logging, error handling, security headers

## [3.2.0] — Frontend Foundation
### Added
- Bootstrap 5 design system, chat interface, base templates

## [3.1.0] — Project Foundation
### Added
- Initial architecture and technology stack decisions, project scope definition
