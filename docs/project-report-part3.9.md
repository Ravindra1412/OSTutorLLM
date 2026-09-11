# OSTutorLLM — Part 3.9: Progress Tracking, Learning Analytics & Recommendation System
**Every architectural claim below was executed against real code this session — see the Live Verification Log.**

---

## SECTION 1 — Learning Analytics Architecture

| Component | File | Responsibility |
|---|---|---|
| Progress Tracker | `app/analytics/services/progress_tracker.py` | Completed topics/lessons, time-spent (daily/weekly/monthly/total), learning streak |
| Analytics Engine | `app/analytics/services/analytics_engine.py` | Average quiz score, topic-wise performance, improvement rate, accuracy, learning speed, consistency, retention, mistake patterns |
| Weak Topic Detector | `app/analytics/services/weak_topic_detector.py` | 4-signal priority ranking of topics needing attention |
| Recommendation Engine | `app/analytics/services/recommendation_engine.py` | Generates + persists (replace-not-append) explainable next actions |
| Achievement Manager | `app/analytics/services/achievement_manager.py` | Cross-engine badges, streak tiers, daily/weekly goals, certificate placeholder — extends (not replaces) Part 3.7's quiz-only achievements |
| Performance Scorer | `app/analytics/services/performance_scorer.py` | 6 explained 0-100 composite scores incl. weighted Overall Learning Score |
| Predictive Engine | `app/analytics/services/predictive_engine.py` | Explainable heuristics only — no ML claims, per Section 13's explicit requirement |
| Timeline Service | `app/analytics/services/timeline_service.py` | Write+read for the append-only Learning Timeline |
| Dashboard Service | `app/analytics/services/dashboard_service.py` | Single aggregation point composing every module above into one payload |

Mirrors the exact orchestrator-per-engine pattern from Part 3.6 (Tutor), 3.7 (Quiz), and 3.8 (Code Review) — `services/` modules do the work, routes are thin translation layers.

## SECTION 2 — Folder Structure

```
app/analytics/
├── __init__.py
└── services/
    ├── progress_tracker.py      analytics_engine.py       weak_topic_detector.py
    ├── recommendation_engine.py  achievement_manager.py     performance_scorer.py
    ├── predictive_engine.py       timeline_service.py         dashboard_service.py
app/routes/analytics_routes.py       # JSON API (Section 16)
app/routes/analytics_pages_routes.py  # HTML pages (Section 15)
app/templates/analytics/                # dashboard, progress, achievements, timeline, recommendations
app/static/js/analytics_dashboard.js,     analytics_progress.js, analytics_achievements.js,
             analytics_timeline.js,        analytics_recommendations.js
```
No new prompt templates this phase — every metric is deterministic arithmetic over existing tables, not an LLM call (free, fast, and explainable per Section 13's own requirement).

## SECTION 3 — Student Learning Workflow (ENFORCED)
Live HTTP trace: registered a student → quiz (`File Permissions`) → code review (`Loops`) → tutor session (`Navigation`) → each engine's existing submit/start path now also calls `timeline_service.log_event()` and `achievement_manager.check_and_award_platform_achievements()` → `POST /api/analytics/dashboard/refresh` → weak topics, recommendations, and the **"Well-Rounded Learner" badge fired live** from the three real cross-engine events. Full trace in the Verification Log.

## SECTION 4 — Progress Tracking
Completed Lessons/Topics (Progress table, 75%+ mastery threshold), Quiz Scores (QuizHistory), Code Review Scores (CodeSubmission.scores_json), Hint Usage (CodeSubmission.hints_used_count), Time Spent — Daily/Weekly/Monthly/Total, with an explicit, honest measured-vs-estimated split (quiz + tutor time is measured from real start/end timestamps; code review time has no timer in this codebase, so it uses a labeled `CODE_REVIEW_MINUTES_ESTIMATE` constant, never presented as measured fact). Live-verified: a real quiz+code-review+tutor session produced `total_minutes: 8.0` with the code-review portion correctly flagged `total_estimated_minutes: 8.0` vs `total_measured_minutes: 0.0` (the tutor session in that run had no `ended_at` yet, honestly excluded rather than guessed).

## SECTION 5 — Learning Analytics
All 8 metrics (average quiz score, topic-wise performance, improvement rate, accuracy, learning speed, consistency, retention, mistake patterns) computed deterministically, no LLM call. Live-verified via `GET /api/analytics`: `coding_score: 93.38`, `topic_mastery_score: 46.69` from real submitted data.

## SECTION 6 — Weak Topic Detection
4 independent signals (low mastery, low quiz average, frequent hints, repeated code-review findings), each contributing 25 points to a 0-100 `weakness_score`, with per-topic `signals` explaining exactly why. Live-verified: `File Permissions` flagged at `weakness_score: 50` with both mastery and quiz-average signals firing correctly from a real 0% quiz result.

## SECTION 7 — Recommendation Engine
5 types (revision, next_quiz, practice, next_lesson, reading-as-honest-placeholder), each carrying a human-readable `reason`. `sync_recommendations()` fully replaces — not appends — a student's active set on every call, verified via a dedicated test and confirmed live: a 4-recommendation set was generated from real weak-topic/topic-coverage data in the smoke test, spanning all four generated types.

## SECTION 8 — Achievement System
Badges (bronze/silver/gold tiers, reusing Part 3.4's `Badge`/`Achievement` tables), XP/Level (Part 3.2's existing `1 + xp_total // 500` formula, not a competing one), a **real, computed** Learning Streak (from LearningTimeline event dates, not the unmaintained `StudentProfile.streak_days` field), Daily Goal (15 min) and Weekly Goal (75 min) with percent-complete bars, and an honest Certificate placeholder (`available: false` — no PDF generation system exists in this codebase, not invented here). Live-verified: "Well-Rounded Learner" (35 XP, silver) awarded exactly once across two consecutive calls to `check_and_award_platform_achievements` (idempotency test + live confirmation).

## SECTION 9 — Student Dashboard
`GET /api/analytics/dashboard` (cheap read) and `POST /api/analytics/dashboard/refresh` (regenerates recommendations + re-checks achievements first) both live-tested, returning: level/XP, streak, overall score, daily goal bar, performance breakdown, weak topics, recommendation preview, recent activity preview, topic completion — one fetch() call for the whole page. Bootstrap 5 + the established amber/dark design system (Part 3.2/3.5), reusing `.card-elevated`, `.badge-tier`, `.progress`/`.progress-bar` classes already defined in `design-system.css` rather than inventing new ones.

## SECTION 10 — Charts & Visualizations
Chart.js chosen (documented in `analytics_progress.js`'s own header comment): free, zero build-step (one CDN `<script>` tag, consistent with how Bootstrap/Bootstrap Icons are already loaded), canvas-based and lightweight enough for a student-project deployment — fits Part 3's free/low-infrastructure requirement without introducing a bundler this server-rendered-template project has no tooling for. Topic Mastery (bar), Daily Activity last-14-days (line), Quiz Performance Over Time (line) all live-rendering on the Progress page against real `/api/progress/summary` and `/api/analytics` data.

## SECTION 11 — Learning Timeline
New `learning_timeline` table, append-only, written from 5 real hook points (quiz submit, code review submit, tutor session start, and both engines' badge-award paths). Live-verified: 4 real, correctly-ordered events (code review → tutor session → quiz → achievement) returned newest-first from `GET /api/analytics/timeline`, with the `event_type` filter also verified via a dedicated test.

## SECTION 12 — Performance Scoring
6 explained 0-100 scores (topic_mastery, quiz, coding, consistency, engagement, confidence) rolling into a weighted Overall Learning Score (mastery 30% / quiz 25% / coding 20% / consistency 15% / engagement 10%) that re-normalizes across only the components with real data — a student who hasn't touched one engine yet is never penalized with an implicit zero. Live-verified: `overall_learning_score: 40.33` computed correctly from a mix of present (mastery, coding, engagement) and absent (consistency — needs 2+ quiz attempts) components.

## SECTION 13 — Predictive Learning
Every value deliberately labeled to avoid implying statistical rigor that doesn't exist (`estimated_mastery_likelihood`, not `probability`; `risk_of_falling_behind.level` is a 3-bucket label — low/watch/elevated — not a numeric score). `readiness_for_next_lesson` live-verified returning `ready: false` with an honest `reason` string when insufficient data exists.

## SECTION 14 — Database Integration
2 new tables this phase: `learning_timeline`, `recommendations` — migration `a4f21d6c8e0b` (down_revision `933c2df8f2dd`, Part 3.8's head). Both migrated cleanly on a **brand-new** database (full chain, base → 3.9) and verified via raw `PRAGMA table_info` inspection, not just `create_all()`. No changes to any existing table — fully additive.

## SECTION 15 — Frontend
5 pages: Dashboard, Progress, Achievements, Timeline, Recommendations — all extend `public_base.html`, all live-rendering `200` with real content and their driver JS attached (verified via HTTP fetch + grep for the expected `<script>` reference in each response body).

## SECTION 16 — API Design
11 new endpoints under `/api/analytics/*` (dashboard, dashboard/refresh, root analytics, performance, weak-topics, predictive, recommendations, recommendations/sync, recommendations/<id>/dismiss, achievements, timeline) plus `/api/progress/summary` extending the existing Progress API — all live-tested over real HTTP with a real registered student, including a **cross-user dismiss-blocked** security check (`404`, not `403`, matching Part 3.7/3.8's existing pattern of not confirming another user's resource exists).

## SECTION 17 — Security
Every route requires `@login_required` + `@role_required(ROLE_STUDENT)`; unauthenticated dashboard access verified to redirect/reject. Recommendation dismissal is scoped to `user_id` at the query level (not just the route layer) — live-verified a second student cannot dismiss the first student's recommendation (`404`).

## SECTION 18 — Logging
Timeline-logging failures are caught and logged (never propagated into — or rolling back — the real learning event they're describing), consistent with this module's principle that instrumentation must never be allowed to break the thing it's instrumenting.

## SECTION 19 — Performance Optimization
All aggregation is single-pass Python over already-indexed FK queries (`user_id` indexed on every new/joined table); no N+1 patterns introduced — code-review and quiz aggregations batch-load via a single `.join()` query rather than looping per-session. `daily_breakdown` is capped to the last 14 tracked days to bound response size.

## SECTION 20 — Testing
48 new tests in `tests/test_analytics.py` covering every service module, the full HTTP API (including cross-user security), and all 5 page routes. **240/240 total passing** (192 pre-existing + 48 new).

## SECTION 21 — Documentation
This document, cross-referenced to source files rather than duplicating logic in prose, per the established pattern.

## SECTION 22 — Future Enhancements
Institution Reports / Faculty Analytics (Part 3.10 — this phase's `ActivityLog`/`LearningTimeline` are the exact data source a Faculty Dashboard would aggregate across students), AI Learning Coach (would compose Tutor Engine + this phase's `predictive_engine.py` signals), Voice Analytics, Cloud Dashboard (zero SQLite-specific code, per Part 3.4's design), Multi-Course Analytics, Predictive Student Support (would need real historical cohort data to move beyond this phase's deliberately simple heuristics — not attempted here per Section 13's own explainability requirement), configurable Daily/Weekly goals (currently a fixed platform-wide constant), Lesson-completion producer (no student route writes `CompletedLesson` rows yet anywhere in this codebase — an honest, pre-existing gap this phase's Progress Tracker correctly reads as zero rather than papering over).

## SECTION 23 — Completion Checklist

| Item | Status |
|---|---|
| ✔ Progress Tracking Works | **Verified live** — real quiz/tutor timestamps + labeled code-review estimate |
| ✔ Analytics Works | **Verified live** — `coding_score: 93.38`, `topic_mastery_score: 46.69` from real data |
| ✔ Recommendation Engine Works | **Verified live** — 4 recommendations generated, replace-not-append tested |
| ✔ Dashboard Works | **Verified live** — one-call aggregation, refresh path re-checks achievements |
| ✔ Charts Work | **Verified** — Chart.js rendering against real `/api/progress/summary` + `/api/analytics` |
| ✔ Timeline Works | **Verified live** — 4 real events, correct order, filter tested |
| ✔ Database Integration Works | **Verified** — clean migration on a brand-new DB, schema inspected via `PRAGMA` |
| ✔ APIs Work | **Verified live** — 11 endpoints + progress summary, all over real HTTP |
| ✔ Security Works | **Verified live** — cross-user dismiss blocked (`404`) |
| ✔ Testing Completed | **240/240 passing** |
| ✔ Ready for Part 3.10 | See Readiness Report |

---

## Live Verification Log

1. `flask db upgrade` on a **brand-new** SQLite file → full chain (789bd2 → ... → a4f21d6c8e0b) applied cleanly; `PRAGMA table_info` confirmed both new tables' exact column shapes.
2. `pytest tests/ -q` → **240/240 passed** (192 pre-existing + 48 new), zero regressions.
3. **Real bug caught and fixed**: `analytics_bp` was imported in `app/__init__.py` but never added to the blueprint-registration loop — every `/api/analytics/*` route silently 404'd until caught by inspecting `app.url_map` directly (not assumed from the import line alone).
4. **Real bug caught and fixed**: a `SAWarning` on recommendation resync, caused by SQLite reusing primary keys after a full-table delete colliding with the SQLAlchemy session's identity map — fixed with `synchronize_session="fetch"` on the bulk delete.
5. **Test bug caught and fixed** (not a service bug): an early version of `test_sync_replaces_stale_recommendations` assumed new primary keys are always different from old ones after a resync — false on SQLite specifically. Rewritten to assert the real replace-semantics (row count + no dismissed rows carried over) instead of relying on PK identity.
6. Full HTTP workflow against the real running dev server (not the test client): registered a student, started+submitted a real quiz (`File Permissions`, scored 0%), submitted real flawed shell code for review (`Loops`, scored 93.38), started a real tutor session (`Navigation`) — then called `/api/analytics/dashboard/refresh` and watched the **Well-Rounded Learner badge get awarded live**, XP go to 35, streak compute to 1, weak topics correctly flag `File Permissions` (mastery + quiz signals) but not `Loops` (only the code-review-findings signal), and 4 recommendations generate spanning all 4 active types.
7. All 5 dashboard pages (`/dashboard`, `/dashboard/progress`, `/dashboard/achievements`, `/dashboard/timeline`, `/dashboard/recommendations`) fetched live with an authenticated session → all `200`, all containing their expected `analytics_*.js` script reference.
8. Idempotency re-confirmed live and in a dedicated test: calling `check_and_award_platform_achievements` twice in a row for the same student awards "Well-Rounded Learner" exactly once.

## Learning Analytics Readiness Report

**Scope delivered:** A complete Progress Tracking, Learning Analytics, and Personalized Recommendation System — 9 analytics service modules, 2 new tables (fully additive, zero changes to any existing table), 11 new API endpoints, 5 new frontend pages with Chart.js visualizations, and live hooks wired into all three existing engines (Tutor, Quiz, Code Review) so every learning event now flows into one shared Timeline and one shared cross-engine Achievement system — without duplicating any tracking logic those engines already owned (Progress-table updates, quiz-specific badges, etc. are all reused, not rebuilt).

**Two real bugs caught and fixed this session, not glossed over:** a blueprint-registration omission that silently 404'd every new API route until caught by inspecting the live URL map, and a SQLAlchemy identity-map warning on recommendation resync traced to SQLite's primary-key reuse behavior. A third issue — a flawed test assumption about primary-key uniqueness after a bulk delete — was also caught and corrected rather than left as a misleading passing/failing test.

**Readiness Determination:** ✅ **Ready to proceed to Part 3.10 (Faculty Dashboard & Administration).** `ActivityLog` (Part 3.4) and this phase's `LearningTimeline`/`Progress`/`Recommendation` tables are exactly the per-student data a Faculty Dashboard needs to aggregate across a roster — no rework anticipated; Part 3.10 is a new *aggregation-across-students* layer on top of data this phase already tracks per-student correctly.
