# OSTutorLLM

**An Interactive AI-Powered Step-by-Step Tutor for Linux Commands and Shell Programming Using Large Language Models**

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-black)
![License](https://img.shields.io/badge/License-MIT-green)
![Tests](https://img.shields.io/badge/tests-446%20passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-83%25-yellowgreen)
![Status](https://img.shields.io/badge/status-university%20submission%20ready-success)

---

## 1. Project Overview

OSTutorLLM is a complete educational web platform that teaches Operating
Systems concepts, Linux commands, and shell programming through an
AI-powered, step-by-step Socratic tutor — not a generic chatbot. Built across
13 development phases, it combines an LLM-driven Tutor Engine, an adaptive
Quiz Engine, an AI-assisted Code Review system, cross-engine Learning
Analytics, a full Faculty Administration Dashboard, and — as its final,
capstone layer — an **AI Learning Mentor** that orchestrates every engine
into one coherent, explainable picture of each student's learning (Learning
Health, Confidence, a real Study Planner, and an AI Assistant for both
students and faculty), backed by 446 automated tests at 83% code coverage.

It was built to be **genuinely runnable by a student with zero budget**: the
default AI provider (`mock`) needs no API key, no GPU, and no network access,
while still exercising the platform's complete teaching workflow.

## 2. Features

### For Students
- **AI Learning Mentor** (`/mentor`) — the "brain" that ties everything
  below together: a real, explainable Learning Health score, per-topic and
  per-category Confidence, an AI-generated Study Planner grounded in your
  actual weak topics, plain-language Insights (each tagged with the real
  evidence behind it), and an AI Assistant you can ask things like
  "What should I study today?" or "Why is my confidence low?"
- **AI Tutor** — staged, Socratic (not answer-dumping) teaching across
  beginner/intermediate/advanced/exam-prep/lab-practice modes, with a 4-stage
  hint ladder and persistent conversation memory per topic.
- **Adaptive Quiz Engine** — 13 question types, difficulty adapts to your
  tracked mastery, server-authoritative timer, instant feedback with
  explanations.
- **AI Code Review** — submit shell scripts for review: deterministic static
  analysis + LLM feedback on logic/readability/security/best-practices,
  never just handing you the fixed code.
- **Learning Dashboard** — progress, weak-topic detection, personalized
  recommendations, achievements/XP/streaks, a full activity timeline.
- **Assignments** — view and submit faculty-assigned coursework, see grades
  and feedback.

### For Faculty
- **Class-wide Analytics** — topic-wise performance, weak/strong topics
  across every student, quiz/code-review statistics.
- **Content Management** — create/edit topics and lessons, upload notes/PDFs/
  slides, full version history with real one-click restore.
- **Quiz Authoring** — build and publish your own quizzes (separate from the
  engine's own adaptive per-attempt generation), schedule availability,
  export results to CSV/Excel/PDF.
- **Assignment Management** — create, track submissions, grade, send
  reminders to students who haven't submitted yet.
- **AI Tutor Administration** — a real enable/disable switch, default
  difficulty/teaching-mode/hint-stage configuration, prompt template editing
  with automatic backups.
- **Reports & Notifications** — 5 report types in 3 export formats,
  announcements, targeted student alerts, automatic quiz-publish notices.

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Browser (Bootstrap 5 + vanilla JS)          │
│      Student pages          Faculty pages         Auth pages    │
└──────────────────────────────┬──────────────────────────────────┘
                                │  JSON over HTTPS
┌──────────────────────────────▼─────────────────────────────────────┐
│                      Flask Application (Gunicorn)                  │
│  ┌────────┐ ┌────────┐ ┌──────────┐ ┌────────────┐ ┌────────────┐  │
│  │  Auth  │ │  Tutor │ │   Quiz   │ │Code Review │ │  Analytics │  │
│  │ Engine │ │ Engine │ │  Engine  │ │  Engine    │ │   Engine   │  │
│  └────┬───┘ └────┬───┘ └────┬─────┘ └─────┬──────┘ └──────┬─────┘  │
│       │          │          │             │               │        │
│       └──────────┴─────┬────┴─────────────┴───────────────┘        │
│                        │           ┌──────────────┐                │
│                    Faculty Admin ──┤ shared tables│                │
│                                    └──────┬───────┘                │
└───────────────────────────────────────────┼────────────────────────┘
                                            │  SQLAlchemy ORM
                                    ┌───────▼─────────────┐
                                    │  SQLite / Postgres  │
                                    └────────┬────────────┘
                                             │
                              ┌──────────────▼────────────────┐
                              │   LLM Provider (pluggable)    │
                              │  Mock / OpenAI / DeepSeek /   │
                              │           Ollama              │
                              └───────────────────────────────┘
```

Every engine (Tutor, Quiz, Code Review, Analytics, Faculty) is its own
package under `app/` with a `services/` layer doing the real work and thin
Flask blueprints translating HTTP ↔ service calls — see
`docs/ARCHITECTURE.md` for the full component breakdown.

## 4. Screenshots

*(Add screenshots here before final submission — see `docs/DEMO_SCRIPT.md`
for a suggested capture list: student dashboard, tutor chat, quiz in
progress, code review feedback, faculty analytics, faculty content manager.)*

```
docs/screenshots/
├── 01-student-dashboard.png
├── 02-tutor-chat.png
├── 03-quiz-in-progress.png
├── 04-code-review-feedback.png
├── 05-faculty-dashboard.png
└── 06-faculty-analytics.png
```

## 5. Installation

**Quick start (local, Mock AI provider — no API key needed):**

```bash
git clone <your-repo-url> ostutorllm
cd ostutorllm
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # edit SECRET_KEY at minimum
flask db upgrade
flask seed-db                          # optional: sample topics/lessons/users
python run.py
```
Open **http://localhost:5000**.

**Docker (recommended for a clean, reproducible run):**
```bash
cp .env.example .env    # edit SECRET_KEY
docker compose up --build
```

Full OS-specific instructions (Windows, Ubuntu, Docker, cloud) with
troubleshooting: **`docs/DEPLOYMENT_GUIDE.md`**.

## 6. Usage

| Role | Try this first |
|---|---|
| Student | Register → start a Tutor session on any topic → try a quiz → submit a shell script for review → check your Dashboard |
| Faculty | Register with role `faculty` → `/faculty` → create a Topic → author a Quiz → view Class Analytics |

Seeded demo accounts (after `flask seed-db`): see `docs/USER_MANUAL_STUDENT.md`
Quick Start section for real seeded credentials.

## 7. Configuration

All configuration is via environment variables (`.env`, copied from
`.env.example`). Key settings:

| Variable | Purpose |
|---|---|
| `APP_ENV` | `development` \| `testing` \| `production` |
| `SECRET_KEY` | Flask session signing — **must** be overridden in production |
| `DATABASE_URL` | SQLite (default) or Postgres connection string |
| `AI_PROVIDER` | `mock` (default, offline) \| `openai` \| `deepseek` \| `ollama_qwen` \| `ollama_llama` |
| `MAX_UPLOAD_SIZE_MB` | Faculty content upload size cap (default 10MB) |

Full reference: **`docs/DEPLOYMENT_GUIDE.md`** Section "Environment Variables".

## 8. Folder Structure

```
ostutorllm-backend/
├── app/
│   ├── ai/            # Tutor Engine — providers, prompts, conversation memory, safety layer
│   ├── analytics/       # Learning Analytics — progress, recommendations, achievements
│   ├── auth/               # Authentication — registration, login, password reset
│   ├── code_review/          # AI Code Review — static analysis, LLM review, hints, scoring
│   ├── config/                  # Environment-specific Flask configuration
│   ├── faculty/                    # Faculty Dashboard services (12 modules)
│   ├── models/                       # SQLAlchemy models (33 tables)
│   ├── quiz/                            # Quiz Engine — question bank, evaluation, timer
│   ├── routes/                             # Flask blueprints (22 total)
│   ├── static/                                # CSS, JS (vanilla — no build step)
│   ├── templates/                                # Jinja2 HTML templates
│   └── utils/                                       # Validators, formatters, shared helpers
├── database/            # SQLite file + seed data (gitignored except seed scripts)
├── docs/                   # Full documentation set — see Section 9 below
├── migrations/                # Alembic migration history (11 phases)
├── scripts/                      # Deployment/setup scripts
├── tests/                           # 446 tests — unit/integration/api/frontend/security/performance
├── uploads/                             # Faculty file uploads + DB backups (gitignored contents)
├── Dockerfile, docker-compose.yml
├── requirements.txt
├── run.py                                             # Local dev entrypoint
├── wsgi.py                                              # Production entrypoint (Gunicorn)
└── run_tests.sh                                            # Test runner
```

## 9. Documentation

| Document | Audience |
|---|---|
| `docs/DEPLOYMENT_GUIDE.md` | Anyone installing/running the app |
| `docs/DEVELOPER_GUIDE.md` | Contributors/developers |
| `docs/ARCHITECTURE.md` | Anyone wanting the technical deep-dive |
| `docs/API_DOCUMENTATION.md` | Frontend/integration developers |
| `docs/DATABASE_DOCUMENTATION.md` | Anyone touching the schema |
| `docs/USER_MANUAL_STUDENT.md`, `USER_MANUAL_FACULTY.md`, `ADMINISTRATOR_GUIDE.md` | End users |
| `docs/TROUBLESHOOTING.md`, `MAINTENANCE_GUIDE.md` | Operators |
| `docs/RESEARCH_AND_INNOVATION.md` | Academic evaluators |
| `docs/PROJECT_REPORT_SUPPORT.md` | Writing the formal university report |
| `docs/PRESENTATION_GUIDE.md`, `DEMO_SCRIPT.md` | Preparing the viva/demo |
| `docs/PERFORMANCE_EVALUATION.md`, `SECURITY_REVIEW.md` | Evaluation criteria |
| `docs/VIVA_PREPARATION.md` | 100 Q&A for the viva |
| `docs/FINAL_SUBMISSION_CHECKLIST.md` | Packaging for submission |
| `docs/project-report-part3.3.md` through `part3.13.md` | Full phase-by-phase build history (Parts 3.1-3.2 were the initial proposal/blueprint, not phase-completion reports) |

## 10. Technologies

**Backend**: Python 3.12, Flask 3.0, SQLAlchemy, Flask-Migrate (Alembic), Flask-Login, Flask-WTF, Gunicorn
**Database**: SQLite (default) / PostgreSQL (production-scale option)
**AI**: Pluggable provider layer — OpenAI, DeepSeek, Ollama (local), or an offline Mock provider
**Frontend**: Server-rendered Jinja2 + Bootstrap 5 + vanilla JavaScript + Chart.js — no build step, no framework lock-in
**Reports**: openpyxl (Excel), reportlab (PDF)
**Testing**: pytest, pytest-cov, BeautifulSoup4 (frontend structure), psutil (resource monitoring), real live-server concurrency testing
**Deployment**: Docker, Gunicorn, Alembic migrations

## 11. API Overview

159 routes across 25 blueprints. Every JSON response follows one contract:
```json
{"status": "success|fail|error", "message": "...", "data": {}}
```
Representative endpoints:

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/auth/register` | Create an account |
| `POST` | `/api/tutor/session` | Start an AI Tutor session |
| `POST` | `/api/quiz/start` | Generate an adaptive quiz |
| `POST` | `/api/code-review/submit` | Submit code for AI review |
| `GET` | `/api/analytics/dashboard` | Student learning dashboard |
| `GET` | `/api/faculty/dashboard` | Faculty overview |
| `POST` | `/api/faculty/quizzes` | Author a quiz |
| `GET` | `/api/faculty/reports/class-performance` | Download a report |

Full reference with request/response examples: **`docs/API_DOCUMENTATION.md`**.

## 12. Future Scope

Multi-course/enrollment support, cloud storage for uploads, voice tutor
(speech-to-text/text-to-speech), multilingual support, an LMS integration
(Canvas/Moodle), a mobile app, RAG over institution-specific course notes, a
fine-tuned (not just prompted) LLM, and a fully offline local-LLM deployment
mode. Full list with rationale: **`docs/RESEARCH_AND_INNOVATION.md`**.

## 13. License

MIT — see `LICENSE`.

## 14. Contributors

Built as a 12-phase university course project. See `CONTRIBUTING.md` to get
involved.

## 15. Acknowledgements

Built with Flask, SQLAlchemy, Bootstrap, Chart.js, and the broader open-source
Python ecosystem. Developed with AI-assisted engineering practices —
every phase's `docs/project-report-part3.X.md` documents real bugs found and
fixed via genuine test-driven verification, not just generated and assumed
correct.
