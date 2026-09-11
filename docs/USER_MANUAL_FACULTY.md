# OSTutorLLM — Faculty User Manual

## Quick Start

Log in with the seeded demo faculty account:

| Email | Password |
|---|---|
| `elena.ruiz@example.edu` | `Password123!` |

Or register your own account at `/register` with role **Faculty**.

**Scope note**: this platform has no course/enrollment concept — every
faculty view (dashboard, analytics, student list) shows the entire student
population, not a per-instructor roster. See `docs/ARCHITECTURE.md` for why.

## 1. Dashboard (`/faculty`)

Overview cards: total/active students (login within 7 days), completed
lessons, average quiz score, average learning time, recent activity across
all students, and system health (database + AI provider status).

## 2. Student Management (`/faculty/students`)

Search/filter students, click into any student to see their full profile:
progress, quiz history, code review history, tutor sessions, and
achievements. Use **Export Report** (top of a student's page) to download
their progress as CSV, Excel, or PDF. Use **Send Alert** to message a
specific student about a weak topic you've spotted.

## 3. Learning Analytics (`/faculty/analytics`)

Class-wide topic performance, weak/strong topics across everyone, quiz
statistics (mean/median/min/max), code review statistics, common mistakes
and most-frequent errors by topic, and a score-trend-over-time chart.

## 4. Content Management (`/faculty/content`)

- **Topics tab**: create/edit/delete topics; add lessons under a topic.
  Every edit is versioned — click a topic's history to see prior versions
  and **restore** one with a single click if you make a mistake.
- **Files tab**: upload lecture notes/PDFs/slides against a topic (allowed
  types: pdf, ppt, pptx, png, jpg, jpeg, gif, txt, md; 10MB default cap).

## 5. Quiz Management (`/faculty/quizzes`)

Author your own quiz: pick a topic, add MCQ questions with a correct answer,
optionally set a time limit, and publish it. Published quizzes appear to
students as a specific, attemptable quiz (separate from the engine's own
adaptive quizzes). View and download results per quiz once students have
attempted it.

## 6. Assignment Management (`/faculty/assignments`)

Create an assignment with a due date, description, and max score. Track
submissions, grade them with a score + written feedback, and send reminders
to students who haven't submitted yet (only pending students are notified —
already-submitted students are automatically excluded).

## 7. Reports (`/faculty/reports`)

Five report types (Student Progress, Class Performance, Quiz Report, Topic
Mastery, Faculty Summary), each downloadable as CSV, Excel, or PDF.

## 8. Notifications (`/faculty/notifications`)

Send an announcement to every student, or review notifications sent to you.

## 9. AI Tutor Settings (`/faculty/settings`)

- **Enable/Disable**: a real kill-switch — disabling it immediately blocks
  new tutor sessions platform-wide (in-progress sessions are allowed to
  finish).
- **Default difficulty / teaching mode / max hint stage**: platform-wide
  defaults for new sessions.
- **Prompt templates**: view and edit the actual prompt text the AI uses —
  every edit automatically backs up the previous version first.

## 10. Backup Settings

Trigger a real database backup (SQLite deployments only) and download it —
useful before making bulk content changes.

## Frequently Asked Questions

**Q: Why can't I see which students are "in my class"?**
A: There's no course/enrollment feature yet (see Scope note above) — every
faculty view is platform-wide. This is a documented, deliberate boundary,
not a bug.

**Q: I published a quiz — how do students find it?**
A: They attempt it directly by ID (via the quiz notification sent
automatically on publish, or a link you share). It doesn't appear mixed in
with the adaptive quiz generator's own topic-based quizzes.

**Q: Can I un-publish a quiz after students have attempted it?**
A: Yes, but existing attempts/results are preserved — un-publishing only
blocks *new* attempts.

**Q: I disabled the AI Tutor by accident — did I break students' sessions?**
A: No — sessions already in progress finish normally. Only *new* session
starts are blocked until you re-enable it.
