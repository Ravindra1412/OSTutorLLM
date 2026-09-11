# OSTutorLLM — API Documentation

Generated from the live `app.url_map` during Part 3.12 — every path below
actually exists in this codebase, not reconstructed from memory.

## Response Contract (Every Endpoint)

```json
{"status": "success", "message": "...", "data": {}}
{"status": "fail",    "message": "...", "field": "..."}   // field is optional
{"status": "error",   "message": "..."}
```
Verified by `tests/api/test_api_contract.py` across every blueprint.

## Authentication

All endpoints below except `/api/auth/register` and `/api/auth/login`
require an active session (`@login_required`), and most also require a
specific role (`@role_required(ROLE_STUDENT)` or `ROLE_FACULTY`). Session
cookies are `HttpOnly` and (in production) `Secure`.

---

## Authentication API (`/api/auth`)
| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/register` | Create an account. Body: `name`, `email`, `password`, `role` |
| POST | `/api/auth/login` | Body: `email`, `password` |
| POST | `/api/auth/logout` | Ends the session |
| GET | `/api/auth/me` | Current user's profile |

## Settings API (`/api/settings`)
| Method | Path | Description |
|---|---|---|
| GET/PUT | `/api/settings/account` | Theme, language, notification preferences (any role) |
| GET/PUT | `/api/settings/preferences` | Student-only: `hint_verbosity_pref` |

## Progress API (`/api/progress`)
| Method | Path | Description |
|---|---|---|
| GET | `/api/progress` | Raw per-topic mastery list |
| GET | `/api/progress/summary` | Completed topics/lessons, time-spent breakdown, quiz/code-review score history |

## AI Tutor API (`/api/tutor`)
| Method | Path | Description |
|---|---|---|
| POST | `/api/tutor/session` | Start a session. Body: `topic`, optional `teaching_mode` |
| POST | `/api/tutor/message` | Send a message in an active session |
| POST | `/api/tutor/reveal` | Force the full solution reveal |
| GET | `/api/tutor/session/<id>/history` | Full conversation history |
| POST | `/api/tutor/session/<id>/reset` | Reset a session |
| GET | `/api/tutor/modes` | List valid teaching modes |
| GET | `/api/tutor/recommendation` | Suggested next topic |

## Quiz Engine API (`/api/quiz`)
| Method | Path | Description |
|---|---|---|
| POST | `/api/quiz/start` | Generate an adaptive quiz. Body: `mode`, `topic`, `question_count`, `time_limit_seconds` |
| POST | `/api/quiz/authored/<quiz_id>/start` | Attempt a specific faculty-authored quiz (Part 3.10) |
| GET | `/api/quiz/<attempt_id>` | Attempt detail (auto-submits if expired) |
| POST | `/api/quiz/<attempt_id>/answer` | Body: `question_id`, `answer` |
| POST | `/api/quiz/<attempt_id>/pause` / `/resume` | Timer control |
| POST | `/api/quiz/<attempt_id>/submit` | Final submission — grades and returns score |
| GET | `/api/quiz/<attempt_id>/review` | Post-submission review with explanations |
| GET | `/api/quiz/history` | Your past attempts |
| GET | `/api/quiz/leaderboard` | XP-ranked leaderboard |
| GET | `/api/quiz/topics` / `/api/quiz/types` | Metadata |

## Code Review API (`/api/code-review`)
| Method | Path | Description |
|---|---|---|
| POST | `/api/code-review/submit` | Body: `topic`, `code` |
| GET | `/api/code-review/session/<id>` | Session detail |
| POST | `/api/code-review/submission/<id>/hint` | Request the next hint stage |
| GET | `/api/code-review/session/<id>/compare` | Diff + score delta vs. the original submission |
| GET | `/api/code-review/history` / `/api/code-review/topics` | Metadata |

## Analytics API (`/api/analytics`)
| Method | Path | Description |
|---|---|---|
| GET | `/api/analytics/dashboard` | Full dashboard payload (read-only, cheap) |
| POST | `/api/analytics/dashboard/refresh` | Regenerates recommendations + re-checks achievements first |
| GET | `/api/analytics` | Full analytics (average score, topic performance, retention, mistake patterns) |
| GET | `/api/analytics/performance` | 6 composite 0-100 scores |
| GET | `/api/analytics/weak-topics` | Ranked weak-topic list with explainable signals |
| GET | `/api/analytics/predictive` | Explainable readiness/risk heuristics |
| GET | `/api/analytics/recommendations` | Active (non-dismissed) recommendations |
| POST | `/api/analytics/recommendations/sync` | Regenerate the full set |
| POST | `/api/analytics/recommendations/<id>/dismiss` | Dismiss one |
| GET | `/api/analytics/achievements` | Badges, XP, level, streak, goals |
| GET | `/api/analytics/timeline` | Chronological event log (`?event_type=`, `?limit=`) |

## Assignment API — Student Side (`/api/assignments`)
| Method | Path | Description |
|---|---|---|
| GET | `/api/assignments` | Published assignments + your submission status |
| POST | `/api/assignments/<id>/submit` | Body: `submission_text` |

## Faculty API (`/api/faculty/*`) — all require role `faculty`
| Method | Path | Description |
|---|---|---|
| GET | `/api/faculty/dashboard` | Overview cards |
| GET | `/api/faculty/students` | List/search/filter (`?search=`, `?active_only=`, `?page=`) |
| GET | `/api/faculty/students/<id>` | Full student detail |
| GET | `/api/faculty/students/<id>/report` | Export (`?format=csv\|excel\|pdf`) |
| POST | `/api/faculty/students/<id>/alert` | Send a targeted alert |
| GET | `/api/faculty/analytics/class` | Class-wide analytics |
| GET | `/api/faculty/analytics/code-review` | Code review monitoring |
| GET/POST/PUT/DELETE | `/api/faculty/content/topics[/<id>]` | Topic CRUD |
| POST/PUT/DELETE | `/api/faculty/content/lessons[/<id>]` | Lesson CRUD |
| GET | `/api/faculty/content/revisions/<type>/<id>` | Version history |
| POST | `/api/faculty/content/revisions/<id>/restore` | Real one-click restore |
| POST/DELETE | `/api/faculty/content/commands[/<id>]`, `/shell-programs[/<id>]` | Linux command / shell example library |
| GET/POST/DELETE | `/api/faculty/content/resources[/<id>]` | File uploads; `GET .../download` |
| GET/POST/PUT/DELETE | `/api/faculty/quizzes[/<id>]` | Faculty-authored quiz CRUD |
| GET | `/api/faculty/quizzes/<id>/results[/download]` | Results (`?format=`) |
| GET/POST/PUT/DELETE | `/api/faculty/assignments[/<id>]` | Assignment CRUD |
| GET | `/api/faculty/assignments/<id>/submissions` \| `/analytics` | |
| POST | `/api/faculty/assignments/<id>/remind` | Reminds only students who haven't submitted |
| POST | `/api/faculty/assignments/submissions/<id>/grade` | Body: `score`, `feedback` |
| GET | `/api/faculty/reports/class-performance` \| `/topic-mastery` \| `/faculty-summary` | (`?format=csv\|excel\|pdf`) |
| GET/POST | `/api/faculty/notifications`, `/api/faculty/announcements` | |
| GET/PUT | `/api/faculty/profile` | POST `/change-password` |
| GET/PUT | `/api/faculty/ai-tutor/settings` | Enable/disable, defaults |
| GET | `/api/faculty/ai-tutor/usage` | Session statistics |
| GET/PUT | `/api/faculty/ai-tutor/prompt-templates[/<filename>]` | View/edit with auto-backup |
| GET | `/api/faculty/settings/security` | Informational |
| GET/POST | `/api/faculty/settings/backup` | Trigger + list; GET `/<filename>/download` |

## Legacy / Foundation Endpoints
| Method | Path | Description |
|---|---|---|
| GET | `/api/student/dashboard`, `/api/student/profile` | Part 3.3 originals, superseded in practice by `/api/analytics/dashboard` but kept for compatibility |
| GET | `/api/faculty/roster` | Part 3.4 placeholder — see `docs/ARCHITECTURE.md` for the no-enrollment-tables scope note |

## Example: Full Quiz Flow
```bash
curl -c cookies.txt -X POST /api/auth/login -d '{"email":"...","password":"..."}'
curl -b cookies.txt -X POST /api/quiz/start -d '{"mode":"topic","topic":"Loops","question_count":3}'
# -> {"data": {"attempt_id": 12, "questions": [...]}}
curl -b cookies.txt -X POST /api/quiz/12/answer -d '{"question_id":1,"answer":"..."}'
curl -b cookies.txt -X POST /api/quiz/12/submit
# -> {"data": {"score_percent": 100.0, "newly_earned_badges": [...]}}
```
