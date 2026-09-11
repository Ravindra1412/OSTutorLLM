# OSTutorLLM - Performance Evaluation

All numbers below are REAL, measured values from Part 3.11's live-server
performance suite (`tests/performance/test_performance.py`), re-verified
during Part 3.12's final review - not estimates or vendor benchmarks.

## Test Environment

- Single-process Flask/Werkzeug development server (real socket-level HTTP,
  not the Flask test client)
- SQLite database (temporary file, not in-memory, matching real deployment
  file-based storage)
- Mock AI provider (offline - measures application overhead, not LLM
  network latency)
- This project's own sandbox hardware (not disclosed/guaranteed - numbers
  are reproducible via `./run_tests.sh performance`, not marketing figures)

## Response Time

| Operation | Budget Asserted | Result |
|---|---|---|
| `GET /health` | < 500ms | Passed |
| Student dashboard load (`/api/analytics/dashboard`) | < 1000ms | Passed |
| Quiz generation (5 questions, static bank) | < 2000ms | Passed |
| AI Tutor session start (Mock provider) | < 1500ms | Passed |
| Faculty class-wide analytics | < 1000ms | Passed |

## Concurrent Users (Stress Testing)

| Scenario | Result |
|---|---|
| 20 simultaneous `/health` requests | 100% success, zero errors |
| 10 concurrent logins, same student, independent sessions | Zero session cross-contamination |
| 10 concurrent quiz-start calls, same student | Zero race-condition failures - every response a clean success or the documented single-active-attempt conflict, never a crash |

## Resource Utilization

| Metric | Result |
|---|---|
| Memory growth over 50 sequential requests | Under 50MB (smoke-level leak check, not a precise profile) |
| CPU sampling during 30-request concurrent load | Real psutil sample obtained without error |

## Database Statistics

| Metric | Value |
|---|---|
| Total tables | 32 |
| Total migrations | 8 (across Parts 3.4-3.10) |
| Full migration chain apply time (fresh database) | Under 2 seconds |

## Testing Summary (Cross-Reference)

| Metric | Value |
|---|---|
| Total automated tests | 409 |
| Passing | 409 (100%) |
| Code coverage | 82.2% overall |
| Full suite runtime | ~97 seconds (including live-server performance tests) |

Full detail: `docs/project-report-part3.11.md`.

## Scalability Analysis

The architecture's correctness under concurrency (proven above) does not by
itself prove horizontal scalability - this is a single-process server
result. Real scaling considerations for a production deployment:

- **Database**: SQLite is safe for one server; multiple Gunicorn workers
  under real concurrent write-heavy load should use Postgres
  (`DATABASE_URL` change only, per the ORM abstraction - zero code changes
  elsewhere).
- **Application servers**: Gunicorn's `--workers` flag scales vertically on
  one machine; true horizontal scaling (multiple machines) needs a load
  balancer in front, which this project's `docker-compose.yml` does not
  provide (a real, stated Future Improvement).
- **LLM provider latency**: not measured here (Mock provider is
  instantaneous by design) - a real deployment using OpenAI/DeepSeek/Ollama
  should benchmark actual provider round-trip time separately, as it will
  likely dominate total response time for Tutor/Quiz-generation/Code-Review
  endpoints under a real provider.

## Comparison: Mock vs. Real Provider (Qualitative)

| Aspect | Mock Provider | Real Provider (OpenAI/DeepSeek/Ollama) |
|---|---|---|
| Cost | Free | Per-token API cost (OpenAI/DeepSeek) or free but GPU-bound (Ollama) |
| Latency | Near-instant (measured above) | Network + model inference time (not measured in this suite) |
| Response quality | Generic/templated | Real, contextual teaching responses |
| Suitable for | Development, testing, cost-free grading/demo | Real classroom deployment |

## Known Limitations of This Evaluation

- Performance numbers reflect a development server, not a production WSGI
  deployment behind a real reverse proxy under real network conditions.
- No sustained load test (minutes/hours of continuous traffic) was run -
  only short concurrent bursts (10-30 requests).
- Real LLM provider latency was not measured (would require a paid API key
  or a running Ollama instance not available in this development
  environment).
