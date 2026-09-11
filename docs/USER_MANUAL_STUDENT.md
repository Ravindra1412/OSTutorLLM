# OSTutorLLM — Student User Manual

## Quick Start

After the app is running (`docs/DEPLOYMENT_GUIDE.md`) and seed data is
loaded (`flask seed-db`), log in with a seeded demo account:

| Email | Password |
|---|---|
| `aisha.khan@example.edu` | `Password123!` |
| `ravi.menon@example.edu` | `Password123!` |
| `tom.lee@example.edu` | `Password123!` |

Or register your own account at `/register` with role **Student**.

## 1. Dashboard (`/dashboard`)

Your home screen: current level/XP, learning streak, daily goal progress,
your overall learning score, topics needing attention, recommended next
activities, and a feed of your recent learning activity. Click **Refresh**
to regenerate recommendations based on your latest performance.

## 2. Learning with the AI Tutor

1. Go to a topic and start a Tutor session.
2. The tutor teaches step-by-step — it will ask you questions and guide you,
   not just dump an answer. If you're stuck, ask for a hint; hints escalate
   through 4 stages (a nudge → a structural hint → a near-complete scaffold
   → the full explanation) so you're never stuck forever, but also never
   handed the answer immediately.
3. Your session is automatically logged to your Timeline and counts toward
   your learning streak.

## 3. Taking a Quiz

- **Adaptive quizzes** (`/quiz`): the engine picks questions matched to your
  tracked mastery on a topic. Difficulty increases as you improve.
- **Faculty-assigned quizzes**: if your instructor has published one, it
  appears as a specific quiz you can attempt directly.
- Quizzes may be timed — the timer is server-side, so refreshing the page
  won't reset it. Submitting is final; you'll see your score and an
  explanation for each question immediately.

## 4. Code Review

1. Pick a topic and paste your shell script.
2. You'll get static-analysis findings (syntax, style, common mistakes) plus
   AI-generated feedback on logic, readability, and best practices — the
   reviewer explains *why* something needs fixing and gives you a direction,
   not a rewritten solution (except at the final hint stage, if you use all
   your hints).
3. You can resubmit an improved version to the same session and see a real
   diff + score comparison against your first attempt.

## 5. Assignments (`/assignments` via the dashboard, or `/api/assignments`)

View assignments your instructor has published, see due dates, and submit
your work as text. Late submissions are flagged automatically (if your
instructor allows them at all) — check the assignment's rules before the
deadline.

## 6. Achievements & Progress

Badges are earned automatically — for quiz performance, code review
consistency, using all three engines (Tutor/Quiz/Code Review), and keeping a
learning streak. Check `/dashboard/achievements` for your full badge
collection, XP, and level.

## 7. Settings

`/dashboard` → Settings (or `/api/settings/account`): theme (dark/light),
notification preferences.

## Frequently Asked Questions

**Q: The AI Tutor says it's "currently disabled."**
A: Your instructor has temporarily turned it off platform-wide (a real
admin control, Part 3.10). Try again later or contact your instructor.

**Q: My quiz timer ran out before I finished.**
A: The quiz auto-submits with whatever answers you'd saved — this is by
design (a server-authoritative timer, so it can't be bypassed by pausing
your browser).

**Q: Can I retake a quiz?**
A: Adaptive quizzes generate a fresh question set every time you start one
on a topic. A specific faculty-authored quiz can only be attempted once per
the single-active-attempt rule, unless your instructor re-publishes it.

**Q: I submitted code for review — why didn't it just fix my bug?**
A: By design — the Code Review Engine teaches, it doesn't autocomplete. Use
the hint ladder if you're stuck; the final hint stage does reveal the fix.
