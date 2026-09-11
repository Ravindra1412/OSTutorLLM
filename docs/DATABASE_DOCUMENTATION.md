# OSTutorLLM — Database Documentation

32 tables (verified against a freshly-migrated database this phase), grouped
by the phase that introduced them. Full column-level detail lives in each
table's model file (`app/models/<name>.py`) — every model has a docstring
explaining its design decisions; this document is the map, not a duplicate
of that detail.

## Schema by Phase

### Part 3.4 — Foundation Schema
| Table | Purpose |
|---|---|
| `users` | Core account: email, password hash, role (student/faculty), timestamps |
| `student_profiles`, `faculty_profiles` | 1:1 role-specific extension of `users` |
| `user_settings` | Theme/language/notification preferences (per-user) |
| `topics`, `lessons` | Curriculum structure |
| `commands`, `shell_programs` | Linux command library, shell programming examples |
| `badges`, `achievements` | Gamification — badge definitions + earned records |
| `bookmarks` | Saved content references |
| `notifications` | Cross-feature notification inbox (student alerts, faculty announcements, system messages) |
| `activity_log` | Generic platform-wide audit trail (distinct from `learning_timeline` — see Part 3.9) |
| `system_configuration` | Key-value store for runtime-configurable settings (unused until Part 3.10's AI Tutor admin controls) |
| `login_history` | Login attempt audit trail |
| `quizzes`, `quiz_questions`, `quiz_attempts`, `quiz_results`, `quiz_history` | Quiz data model (extended in 3.7) |
| `chat_sessions`, `chat_messages` | Tutor conversation storage (extended in 3.6) |
| `progress` | THE shared per-topic mastery table every engine writes into |
| `completed_lessons` | Lesson completion tracking (no producer route exists yet — an honest, documented gap) |

### Part 3.5 — Auth Hardening
Additive columns only: `users.email_verified`; `login_history.user_id` made nullable (to log pre-verification failed attempts).

### Part 3.6 — AI Tutor
Additive: `chat_sessions.state_json` (conversation memory state).

### Part 3.7 — Quiz Engine
Additive: extended `quiz_questions.question_type` CHECK constraint (6→13 types), added timer/security/scoring columns to `quiz_attempts`/`quizzes`.

### Part 3.8 — Code Review
| Table | Purpose |
|---|---|
| `code_review_sessions` | One per topic/student review session |
| `code_submissions` | Each submission within a session — static findings, LLM findings, scores, hint state, all as JSON columns |

### Part 3.9 — Learning Analytics
| Table | Purpose |
|---|---|
| `learning_timeline` | Append-only chronological event log — quiz/code-review/tutor/achievement events, written by hooks in each engine |
| `recommendations` | Persisted, explainable recommendations (replace-not-append on regeneration) |

### Part 3.10 — Faculty Dashboard
| Table | Purpose |
|---|---|
| `assignments`, `assignment_submissions` | Faculty-created coursework + student submissions |
| `content_resources` | Uploaded file metadata (bytes on disk, path never client-controlled) |
| `content_revisions` | Full snapshot-before-edit for Topic/Lesson — enables real one-click restore |
| Additive: `quizzes.is_published`, `quizzes.scheduled_at`, `faculty_profiles.subjects_taught` | |

## Key Relationships

```
User (1) ──< StudentProfile / FacultyProfile (1)
User (1) ──< Progress (many)  ←── written by Tutor, Quiz, Code Review engines
User (1) ──< QuizAttempt (many) ──< QuizResult (many, per question)
User (1) ──< ChatSession (many) ──< ChatMessage (many)
CodeReviewSession (1) ──< CodeSubmission (many, resubmission chain)
Topic (1) ──< Lesson, Command, ShellProgram, ContentResource, Assignment (many)
Assignment (1) ──< AssignmentSubmission (many, unique per student)
User (1) ──< LearningTimeline, Recommendation, Notification, Achievement (many)
```

## Design Principles

1. **One shared `Progress` table**, not per-engine copies — every engine
   (Tutor, Quiz, Code Review) writes into the same table with its own
   blending formula, so Analytics/Faculty views read ONE number per topic,
   not three competing ones.
2. **Additive migrations only** — no column has ever been dropped or renamed
   across 8 migrations spanning 7 phases; every schema change is backward
   compatible with code from an earlier phase.
3. **CHECK constraints for enums** — `event_type`, `notification_type`,
   `question_type`, `content_type` etc. are all DB-level `CHECK` constraints,
   not just application-level validation, so bad data can't get in even via
   a bug that bypasses the service layer (though — see
   `docs/project-report-part3.11.md` Section 7 — service-layer validation is
   still needed too, since a raw `IntegrityError` is a poor user-facing
   error message).
4. **JSON columns for genuinely variable-shape data** — `CodeSubmission`'s
   static/LLM findings and scores are JSON text columns, since their
   internal shape varies by finding type and would need many nullable
   columns otherwise.

## Migrations

```bash
flask db current      # show current revision
flask db history       # show full chain
flask db upgrade         # apply pending migrations (idempotent)
flask db downgrade -1      # roll back one migration (use with real caution)
```
Full chain: `789bd2` (3.4) → `6be156`+`cc04a2` (3.5) → `fe5ae7` (3.6) →
`abd286` (3.7) → `933c2d` (3.8) → `a4f21d` (3.9) → `b7e3a9` (3.10).
