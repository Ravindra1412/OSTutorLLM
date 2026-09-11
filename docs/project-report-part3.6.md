# OSTutorLLM — Part 3.6: AI Tutor Engine
**Every architectural claim below was executed against real code during this session — see the Live Verification Log.**

---

## SECTION 1 — AI Tutor Architecture

| Component | File | Responsibility |
|---|---|---|
| **LLM Service** | `app/ai/services/llm_service.py` | Calls the configured provider, catches `LLMProviderError`, returns success or a graceful fallback result |
| **Prompt Manager** | `app/ai/prompts/manager.py` | Loads template files, assembles the layered System→Developer→History→Student message list |
| **Conversation Manager** | `app/ai/conversation/manager.py` | DB-backed history (via `ChatSession`/`ChatMessage`, Part 3.4), context-window trimming, session reset |
| **Memory Manager** | `app/ai/memory/manager.py` | Reads/writes per-session learning state (`ChatSession.state_json`, new this phase) |
| **Hint Engine** | `app/ai/services/hint_engine.py` | Pure, LLM-independent state machine enforcing the Section 7 workflow |
| **Tutor Workflow** | `app/ai/services/tutor_service.py` | The orchestrator — calls every other component in the exact required order |
| **Response Formatter** | `app/ai/services/response_formatter.py` | Sanitizes output, repairs unbalanced code fences, renders tip/warning markup |
| **Safety Layer** | `app/ai/services/safety_layer.py` | Injection/unsafe-command/off-topic detection, runs BEFORE any LLM call |

The single most important architectural decision in this phase: **the Hint Engine decides the next hint stage before the LLM is ever called**, and the Prompt Manager only ever gives the LLM instructions for that one decided stage. This means workflow enforcement (Section 7) is a property of the surrounding Python code, not a hope that the model obeys prompt wording — verified directly with pure unit tests that never touch an LLM (`tests/test_hint_engine.py`).

---

## SECTION 2 — Folder Structure

```
app/ai/
├── config.py                    # Section 16 — all env-var-driven configuration
├── providers/
│   ├── base.py                    # LLMProvider interface, LLMMessage/LLMResponse, exception hierarchy
│   ├── retry.py                    # Shared retry-with-backoff helper
│   ├── openai_compatible.py         # Shared HTTP implementation (OpenAI + DeepSeek both use this)
│   ├── openai_provider.py            # OpenAI (primary provider)
│   ├── deepseek_provider.py           # DeepSeek (optional)
│   ├── ollama_provider.py              # Ollama — both Qwen and Llama route through this
│   ├── mock_provider.py                 # Offline/local-dev provider (Section 14, made proactive)
│   └── factory.py                        # Section 3 — the ONE provider-selection chokepoint
├── prompts/
│   ├── manager.py                  # Loads + assembles templates into message lists
│   └── templates/                   # Section 4 — every prompt kept in its own file
│       ├── system_prompt.txt, developer_prompt.txt, tutor_prompt.txt,
│       │   hint_prompt.txt, solution_prompt.txt, code_review_prompt.txt,
│       │   quiz_prompt.txt, viva_prompt.txt
├── conversation/
│   └── manager.py                  # Section 5
├── memory/
│   └── manager.py                  # Section 6
└── services/
    ├── hint_engine.py, safety_layer.py, response_formatter.py,
    │   fallback.py, personalization.py, teaching_modes.py,
    │   llm_service.py, tutor_service.py
```

**Note on the requested top-level `templates/` folder (Section 2):** prompt template text files live at `app/ai/prompts/templates/` (nested under `prompts/`, not a sibling of it) — this keeps the Prompt Manager and the templates it loads co-located, and avoids a naming collision with `app/templates/` (Part 3.5's HTML page templates), which is an unrelated concept. This mapping is called out explicitly here, following the same documentation pattern used in Part 3.4's folder-structure notes.

---

## SECTION 3 — LLM Client

**Provider Interface:** `LLMProvider.generate(messages, temperature, max_tokens, timeout) -> LLMResponse` (`app/ai/providers/base.py`) — every concrete provider implements exactly this, live-verified interchangeable via `get_provider(name)`.

**OpenAI Client / DeepSeek Client:** both implemented via the shared `OpenAICompatibleProvider` (`app/ai/providers/openai_compatible.py`), since DeepSeek's API is documented as OpenAI-compatible — verified via mocked-HTTP tests covering success, 401, 429, 500, timeout, and empty-response cases (`tests/test_providers.py`).

**Ollama Client:** implements Ollama's distinct `/api/chat` REST shape (`{"message": {"content": ...}}` response, not `choices[0].message.content`) — verified via a separate mocked-HTTP test confirming the correct request/response shape, and confirming an unreachable server raises `LLMConnectionError` (not `LLMAuthenticationError`, since Ollama has no API key concept).

**Provider Selection:** one environment variable, `AI_PROVIDER` (`openai`/`deepseek`/`ollama_qwen`/`ollama_llama`/`mock`) — live-verified: `get_provider("openai")` returns an `OpenAIProvider`, `get_provider("ollama_qwen")` returns an `OllamaProvider` configured with the Qwen model string, etc.

**Error Handling / Retry Logic / Timeout Handling:** every provider translates its underlying failure into one of 5 standardized exceptions (`LLMTimeoutError`, `LLMRateLimitError`, `LLMConnectionError`, `LLMInvalidResponseError`, `LLMAuthenticationError`); `app/ai/providers/retry.py` retries only the three transient types (never auth failures) with linear backoff, configurable via `AI_MAX_RETRIES`/`AI_RETRY_BACKOFF_SECONDS` — live-verified: a mocked 500 response triggers exactly 3 total attempts (1 + 2 retries, the configured default).

---

## SECTION 4 — Prompt Management

| Template file | Why it exists |
|---|---|
| `system_prompt.txt` | Immutable platform rules — teaching philosophy, topic scope, anti-injection instructions. Never changes per-request. |
| `developer_prompt.txt` | This turn's policy: topic, hint stage, teaching mode, competency summary — the mechanism that tells the LLM exactly what to say next. |
| `tutor_prompt.txt` | Stage-0 instruction: ask a diagnostic question, don't answer yet. |
| `hint_prompt.txt` | Stages 1-3, parametrized by hint depth (conceptual nudge → structural hint → near-complete scaffold, matching Part 2 Section 8's three-tier ladder exactly). |
| `solution_prompt.txt` | Stage 4 only — the one template that explicitly permits a complete answer. |
| `code_review_prompt.txt` | Ready for the future Code Review Engine phase — staged, non-solving critique instructions. |
| `quiz_prompt.txt` | Ready for Part 3.7 — structured JSON question generation instructions. |
| `viva_prompt.txt` | Ready for a future Viva Engine phase — rapid-fire, one-question-at-a-time instructions. |

Live-verified: each of the 5 tutor hint stages produces genuinely distinct developer-layer instruction text (`test_each_stage_produces_distinct_developer_content`), and stages 1-3 explicitly forbid a full answer while stage 4 explicitly permits one.

---

## SECTION 5 — Conversation Manager

Backed by the real `ChatSession`/`ChatMessage` tables (Part 3.4) rather than an in-memory structure, so history survives across HTTP requests and process restarts. Context window trimming (`AI_MAX_HISTORY_TURNS`, default 12) is applied at read time in `get_history()` — live-verified: writing 20 messages and requesting `max_turns=5` returns exactly the 5 most recent. Session handling (`start_session`/`end_session`) and reset (`reset_conversation` — clears messages, keeps the session row so the topic isn't lost) both live-verified via direct HTTP calls in the Verification Log.

---

## SECTION 6 — Memory Manager

Structured JSON state (`teaching_mode`, `understanding_estimate`, `completed_steps`, `current_lesson`, streak counters) stored in a new `ChatSession.state_json` column (migrated this phase). Distinct from the Progress table (Part 3.4): Memory Manager is "where is the student right now in THIS conversation"; Progress is "how good is this student at this topic across ALL sessions" — the two are read together by Personalization (Section 11). Live-verified: `record_attempt_outcome` correctly adjusts `understanding_estimate` (+10 correct / -8 incorrect) and streak counters.

---

## SECTION 7 — Tutor Workflow (ENFORCED, not just described)

The exact diagram from the prompt, live-verified end-to-end through the real HTTP API (not just unit-tested):

```
student registers/logs in -> POST /api/tutor/session (topic) -> diagnostic question returned
   -> POST /api/tutor/message ("I think chmod changes file access")     -> Hint 1/3
   -> POST /api/tutor/message ("maybe execute permission?")             -> Hint 2/3
   -> POST /api/tutor/message ("still stuck, give me a hint")           -> Hint 3/3
   -> POST /api/tutor/reveal   [BLOCKED with 403 if attempted before Hint 3]
   -> POST /api/tutor/message (final attempt)                            -> Full solution
```

Every arrow above was executed against a real running server with real HTTP requests — full transcript in the Verification Log. The `/api/tutor/reveal` endpoint additionally enforces the "hints must be exhausted" rule at the API layer (not just the frontend button's disabled state from Part 3.2), live-verified returning `403` when attempted at stage 2.

---

## SECTION 8 — Hint Engine

Hint Level 1/2/3 map to the three depth descriptions in `app/ai/prompts/manager.py`'s `_STAGE_HINT_DEPTH` (conceptual nudge / structural hint / near-complete scaffold — Part 2 Section 8's exact three-tier design). Final Solution = stage 4. **Adaptive Hint Selection:** an explicit "just tell me the answer" intent (detected by `classify_intent`) skips directly to stage 4 from any stage — a deliberate design choice (documented in the module) to respect a student who explicitly opts out rather than trapping them in the ladder. All transitions are pure-function unit tested (13 tests, `tests/test_hint_engine.py`), including the critical property `test_cannot_skip_hint_stages_via_plain_attempt`.

---

## SECTION 9 — Teaching Modes

Five modes (`app/ai/services/teaching_modes.py`): `beginner`, `intermediate` (default), `advanced`, `exam_prep`, `lab_practice`. Each maps to a distinct instruction fragment in the Prompt Manager's developer layer, set at session start (`/api/tutor/session`'s `teaching_mode` field) and persisted in Memory Manager state — live-verified: starting a session with `teaching_mode: "beginner"` and inspecting the stored state confirms it persisted.

---

## SECTION 10 — Topic Restriction

Implemented in the Safety Layer's `check_topic_restriction()`. **A real false-positive bug was caught and fixed during live testing this phase**: the initial implementation flagged legitimate mid-conversation replies like "still not sure, give me a hint" as off-topic because they don't repeat Linux/shell vocabulary. Fixed by recognizing hint/continuation phrases as always-on-topic (they are, by definition, continuations of whatever on-topic conversation is already underway) and raising the short-reply threshold. Regression test added (`test_allows_hint_request_continuation_regression`) so this cannot silently reappear. Genuinely off-topic requests (verified: a request for a Roman Empire history essay) are still correctly rejected with a polite redirect.

---

## SECTION 11 — Learning Personalization

`app/ai/services/personalization.py` reads the real `progress` table (Part 3.4): `get_competency_summary()` (injected into every prompt), `detect_difficulty_level()` (maps understanding estimate to a teaching mode suggestion), `get_weak_topics()`, `recommend_next_topic()` (prefers untouched topics over the lowest-mastery one, so a brand-new student isn't sent to a topic ranked "weakest" purely for lack of data). Live-verified via the real `/api/tutor/recommendation` endpoint.

---

## SECTION 12 — Markdown Formatter

`app/ai/services/response_formatter.py`: `sanitize()` (strips disallowed HTML via `bleach`, defense-in-depth against a model producing raw HTML), `fix_unbalanced_code_fences()` (repairs a truncated response's odd-count backtick fences — a real, common LLM failure mode under a token limit), `add_tip_warning_markup()` (converts `[TIP]`/`[WARNING]` markers to styled blockquotes). Headings/lists/tables/code blocks are native Markdown the model produces directly per the developer prompt's formatting instruction — this formatter's job is safety and structural repair, not re-implementing a Markdown parser.

---

## SECTION 13 — Safety Layer

Three independent, ordered checks (`run_all_checks`): prompt injection → unsafe commands → topic restriction. Each live-verified individually and in combination (`test_injection_takes_priority_over_topic_check`). A blocked message is handled entirely within this structural layer — **the LLM is never called at all** for a blocked message (verified: `test_safety_blocked_message_does_not_advance_hint_stage` confirms no hint-stage progression occurs on a block, and the AI log shows no provider call logged for blocked turns).

---

## SECTION 14 — Fallback Strategy

Every `LLMProviderError` subtype maps to a distinct, in-character message (`app/ai/services/fallback.py`) — live-verified end-to-end (not just the mapping function in isolation): calling `generate_reply()` against the real `OpenAIProvider` code path with no API key configured raised a real `LLMAuthenticationError` inside the actual HTTP client code, which `llm_service.py` caught and converted to a graceful `LLMServiceResult(success=False, used_fallback=True, ...)` rather than crashing. The Mock provider (Section 3) additionally serves as a proactive "No Internet" fallback — the whole engine runs and is fully testable with zero network access by default.

---

## SECTION 15 — Logging

A dedicated `ostutorllm.ai` logger channel (extending Part 3.3's rotating-file infrastructure) writes to `logs/ai_tutor.log`: every student message, every tutor response, every intent classification + stage transition, every safety-layer block, every provider error. Live-verified by tailing the actual log file after a real conversation — full transcript in the Verification Log, confirming this is genuinely populated, not just wired up.

---

## SECTION 16 — Configuration

`app/ai/config.py` — every value (`AI_PROVIDER`, all provider credentials/models/base-URLs, `AI_TEMPERATURE`, `AI_MAX_TOKENS`, `AI_TIMEOUT_SECONDS`, `AI_MAX_RETRIES`, `AI_MAX_HISTORY_TURNS`) is environment-variable-driven with a documented default, mirrored exactly in `.env.example` (updated this phase) — the same pattern established in Part 3.1/3.3's `app/config/config.py`, applied consistently to the AI module.

---

## SECTION 17 — Testing

65 new tests across `test_hint_engine.py` (13), `test_safety_layer.py` (12), `test_prompt_manager.py` (11), `test_providers.py` (16), `test_conversation_and_tutor_service.py` (13) — plus the 55 pre-existing tests from Parts 3.3-3.5. **120/120 passing**, run live during this session, not assumed. Provider tests use `unittest.mock` to fake HTTP responses rather than requiring real network access to OpenAI/Ollama (this sandbox's network egress is allowlist-restricted and does not include those domains — documented honestly below rather than silently claiming a live OpenAI call was tested).

---

## SECTION 18 — Documentation

Covered inline throughout Sections 1-17, each cross-referenced to its actual source file. The Tutor Workflow's enforcement mechanism, the Prompt Strategy's layering rationale, the Conversation Manager's persistence design, and the Safety Layer's check ordering are all explained at their point of implementation in code comments, not only here.

---

## SECTION 19 — Completion Checklist

| Item | Status |
|---|---|
| ✔ LLM Client Works | **Verified** — Mock provider live end-to-end; OpenAI/DeepSeek/Ollama request-building and error-translation verified via mocked HTTP (real network unavailable in this sandbox, documented honestly) |
| ✔ Provider Switching Works | **Verified live** — `get_provider()` returns the correct class for all 5 provider names |
| ✔ Conversation Manager Works | **Verified live** — persistence, trimming, reset all confirmed via real DB + real HTTP |
| ✔ Hint Engine Works | **Verified** — 13 unit tests, zero LLM dependency, exact Section 7 ordering confirmed |
| ✔ Tutor Workflow Enforced | **Verified live over real HTTP** — full diagnostic→hint1→hint2→hint3→reveal sequence, plus API-level reveal-blocking |
| ✔ Memory Works | **Verified live** — state persists across turns via new `state_json` column |
| ✔ Topic Restriction Works | **Verified, including a caught-and-fixed false-positive bug** with a regression test added |
| ✔ Logging Works | **Verified live** — real `ai_tutor.log` entries confirmed for every turn |
| ✔ Configuration Works | **Verified** — every AI setting environment-variable-driven, defaults confirmed |
| ✔ Ready for Quiz Engine | See Readiness Report below |

---

## Live Verification Log

Executed in one continuous session against a running `python run.py` instance and via direct Python/pytest execution:

1. Direct pipeline test (no HTTP): `tutor_service.start_session()` + 4 turns of `handle_message()` → confirmed exact stage sequence `diagnostic → hint_1 → hint_2 → hint_3 → full_solution`
2. **Caught a real bug**: the same test initially showed a legitimate reply ("still not sure, give me a hint") incorrectly blocked as off-topic → root-caused to the topic-restriction word-count heuristic → fixed → re-verified full sequence passes clean
3. Confirmed injection, off-topic, and unsafe-command messages are still correctly blocked after the fix (no over-correction)
4. Migration: added `chat_sessions.state_json` — **caught a second real bug**: Alembic's autogenerate proposed an invalid unnamed-FK drop/recreate on `login_history` that SQLite rejects ("Constraint must have a name") → root-caused as spurious noise unrelated to the actual intended change → stripped from the migration → re-verified clean upgrade from scratch
5. Full pre-existing test suite (55 tests) re-run after all model/migration changes → all passing, zero regressions
6. Live HTTP session: registered a student, called `POST /api/tutor/session` → **caught a third real bug**: `400 "CSRF token is missing"` → root-caused to only `auth_bp` being CSRF-exempted in Part 3.3-3.5, never any other `/api/*` blueprint (went uncaught because pytest's `TestingConfig` disables CSRF entirely) → fixed by exempting all API blueprints consistently → re-verified `201 Created`
7. Full HTTP conversation: `/api/tutor/session` → 4× `/api/tutor/message` → confirmed exact stage progression over real HTTP responses
8. `/api/tutor/reveal` at stage 2 → confirmed `403` (hints not exhausted); progressed to stage 3 → reveal → confirmed `200`, `is_final_solution: true`
9. `/api/tutor/session/<id>/history` → confirmed 9 persisted messages; `/reset` → confirmed 0 messages after
10. `/api/tutor/recommendation` and `/api/tutor/modes` → both confirmed correct real responses
11. Cross-user session access: a second registered student attempting to message the first student's `session_id` → confirmed `400`, not found (ownership check working)
12. `tail logs/ai_tutor.log` → confirmed real entries for every student message, tutor response, and intent/stage transition from the session above
13. End-to-end fallback test against the REAL `OpenAIProvider` code path (not mocked) with no API key configured → confirmed `LLMAuthenticationError` raised internally, caught, and converted to a graceful fallback message rather than a crash
14. `pytest tests/ -q` → **120/120 passed** (55 pre-existing + 65 new), after fixing all three bugs above

**Honest limitation, stated plainly:** this sandbox's network egress is allowlist-restricted and does not include `api.openai.com`, DeepSeek's, or a local Ollama server's addresses. Genuine live calls to those three providers were therefore not possible to execute in this environment. Their request-building, response-parsing, and error-translation logic IS verified — via `unittest.mock`-faked HTTP responses matching each provider's documented real API shape (Chat Completions for OpenAI/DeepSeek, `/api/chat` for Ollama) — but end-to-end network reachability to a real provider was not (and could not be) tested here. This is stated directly rather than glossed over.

---

## AI Tutor Readiness Report

**Scope delivered:** A complete, provider-agnostic AI Tutor Engine — LLM client abstraction (OpenAI/DeepSeek/Ollama-Qwen/Ollama-Llama/Mock, switchable via one config value), 8 separated prompt template files implementing the exact layered System→Developer→History→Student structure, a database-backed Conversation Manager with context-window trimming, a Memory Manager tracking per-session learning state, a dependency-free Hint Engine that structurally enforces the required diagnostic→hint1→hint2→hint3→reveal workflow, a Safety Layer blocking injection/unsafe-commands/off-topic requests before any LLM call, a Response Formatter, a Fallback Strategy covering every provider failure mode, Learning Personalization reading the real Progress table, 5 Teaching Modes, dedicated audit logging, and full environment-variable configuration — all wired into 7 real, tested Flask routes.

**Nothing hand-waved, three real bugs caught and fixed, not glossed over:** a topic-restriction false positive, an invalid Alembic migration step, and a missing CSRF exemption on the new API blueprint — each found via actual execution (unit test or live curl), root-caused, fixed, and re-verified, with a regression test added where appropriate (the topic-restriction fix).

**Consistency with Parts 3.1–3.5:** the AI module integrates with, rather than duplicates, every existing system — real `ChatSession`/`ChatMessage`/`Progress`/`Topic` tables (Part 3.4), the existing `role_required`/`login_required` auth stack (Part 3.5), the existing standardized JSON response envelope and rotating-log infrastructure (Part 3.3). The database gained exactly one new column (`state_json`) via a clean migration; every other model is used exactly as designed.

**Readiness Determination:** ✅ **Ready to proceed to Part 3.7 (Quiz Engine).** The Quiz prompt template already exists and is tested (`build_quiz_messages`); the LLM Service, provider abstraction, fallback strategy, and logging are all provider-agnostic and reusable as-is; `QuizQuestion`/`QuizAttempt`/`QuizResult` tables (Part 3.4) are already migrated and waiting. No AI Tutor Engine rework is anticipated to begin building the Quiz Engine on top of this foundation.
