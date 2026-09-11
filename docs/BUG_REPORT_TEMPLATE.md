# OSTutorLLM — Bug Report Template

Part 3.11, Section 21 (Bug Tracking). Copy this template for every new
issue filed against the project (GitHub Issues, a spreadsheet, or
whatever tracker the course/team uses — this template is
tool-agnostic).

---

## Bug Report

**Title:** _(one line, specific — "Quiz submit 500s when question_id belongs to a different quiz", not "quiz broken")_

**Reported By:**
**Date Reported:**
**Environment:** _(e.g. local dev / SQLite / Mock provider — or production / Postgres / OpenAI)_

### Description
_What happened, in plain language._

### Steps to Reproduce
1.
2.
3.

### Expected Behavior


### Actual Behavior


### Evidence
_Stack trace, screenshot, failing test name, or `curl` command that reproduces it._

```
(paste here)
```

---

## Severity Levels

| Severity | Definition | Example |
|---|---|---|
| **Critical** | Data loss, security vulnerability, or the application is unusable | Password stored in plaintext; auth bypass; DB corruption |
| **High** | A core feature is broken with no workaround | Quiz submission always fails; login broken for all users |
| **Medium** | A feature is broken but a workaround exists, or it affects a minority of cases | CSV export works but Excel export 500s |
| **Low** | Cosmetic, minor UX friction, or an edge case with negligible impact | A button's icon is misaligned on narrow screens |

## Priority Levels

| Priority | Definition |
|---|---|
| **P0** | Fix immediately, blocks release/demo |
| **P1** | Fix before the next phase begins |
| **P2** | Fix when convenient, doesn't block anything |
| **P3** | Nice-to-have, may be deferred to Future Enhancements |

*Severity describes impact; Priority describes urgency — a Low-severity bug can still be P0 if it will be visible during a graded demo.*

## Bug Workflow

```
   New  →  Confirmed  →  In Progress  →  Fixed  →  Verified  →  Closed
                              ↓
                          Won't Fix / Deferred (documented in
                          the relevant docs/project-report-partX.md's
                          "Future Enhancements" or "Known Limitations")
```

- **New** — reported, not yet reproduced.
- **Confirmed** — reproduced against the current codebase.
- **In Progress** — actively being fixed.
- **Fixed** — code change committed; needs a regression test.
- **Verified** — the regression test (added alongside the fix) passes, and the original repro steps no longer trigger the bug.
- **Closed** — verified and merged.
- **Won't Fix / Deferred** — a deliberate scope decision (document *why* in the relevant phase's docs, not just silently drop it).

## Resolution Tracking

Every fix in this project follows the same pattern established from Part 3.6 onward: **a bug is not "fixed" until it has a regression test that fails before the fix and passes after it.** See this phase's own Live Verification Log (`docs/project-report-part3.11.md`) for real, worked examples of this exact workflow — e.g. the `GET /api/quiz/<id>` cross-user 500 (Section 14) and the `submit_answer` unvalidated `question_id` gap (Section 5), both caught by a new adversarial test, fixed, and proven fixed by that same test passing afterward.
