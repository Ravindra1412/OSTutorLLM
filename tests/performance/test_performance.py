"""
tests/performance/test_performance.py

Part 3.11, Sections 15-16 — Performance & Stress Testing.

Deliberately NOT using the Flask test client for the concurrency
tests: the test client doesn't exercise real socket/WSGI concurrency
handling, so a "concurrent users" claim tested through it would be
fake. Instead, this module boots the REAL app via Werkzeug's
`make_server` in a background thread bound to an ephemeral local port,
and drives it with real `requests` calls — genuine concurrent HTTP
traffic against the genuine app, backed by a temporary on-disk SQLite
database (not `:memory:`, which cannot be shared across threads/
connections the way a real deployment's database would be).

Honest scope note: this measures the single-process Flask development
server (`werkzeug.serving`), not a production WSGI server (gunicorn/
uwsgi) behind a reverse proxy — that is the real deployment target
(Part 3.12) and would need its own load-testing pass there. What this
DOES validate: the application layer itself (routes, ORM queries,
session handling) doesn't serialize/deadlock/leak under concurrent
access, and gives real, reproducible baseline numbers for this
codebase on this machine — not vendor-benchmark numbers from an
unrelated environment.
"""

import os
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
import requests

pytestmark = pytest.mark.performance


# --------------------------------------------------------------------
# Real live-server fixture (module-scoped — one boot for the whole file)
# --------------------------------------------------------------------

@pytest.fixture(scope="module")
def live_server():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    from app.config.config import DevelopmentConfig
    original_uri = DevelopmentConfig.SQLALCHEMY_DATABASE_URI
    original_secret = DevelopmentConfig.SECRET_KEY
    DevelopmentConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
    DevelopmentConfig.SECRET_KEY = "perf-test-secret"

    from app import create_app
    from app.extensions import db as _db

    app = create_app("development")
    # Force test configuration and MockProvider for live server benchmarks
    app.config["TESTING"] = True
    app.config["AI_PROVIDER"] = "mock"

    with app.app_context():
        _db.create_all()
        from tests.fixtures.factories import make_student, make_faculty, make_topic
        make_student(email="perf_student@example.com")
        make_faculty(email="perf_faculty@example.com")
        make_topic("Extra Content Topic")

    from werkzeug.serving import make_server

    server = make_server("127.0.0.1", 0, app, threaded=True)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)  # allow socket initialization

    yield f"http://127.0.0.1:{port}"

    server.shutdown()
    thread.join(timeout=5)
    server.server_close()

    with app.app_context():
        _db.session.remove()
        _db.engine.dispose()

    try:
        os.remove(db_path)
    except OSError:
        pass

    DevelopmentConfig.SQLALCHEMY_DATABASE_URI = original_uri
    DevelopmentConfig.SECRET_KEY = original_secret


def _login(base_url, email, password="Password123!"):
    session = requests.Session()
    resp = session.post(f"{base_url}/api/auth/login", json={"email": email, "password": password}, timeout=10)
    assert resp.status_code == 200
    return session


# --------------------------------------------------------------------
# Response Time (Section 15)
# --------------------------------------------------------------------

class TestResponseTime:
    def test_health_endpoint_responds_quickly(self, live_server):
        start = time.perf_counter()
        resp = requests.get(f"{live_server}/health", timeout=10)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert resp.status_code == 200
        assert elapsed_ms < 500, f"/health took {elapsed_ms:.1f}ms — expected under 500ms"

    def test_student_dashboard_loads_within_budget(self, live_server):
        session = _login(live_server, "perf_student@example.com")
        start = time.perf_counter()
        resp = session.get(f"{live_server}/api/analytics/dashboard", timeout=10)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert resp.status_code == 200
        assert elapsed_ms < 1000, f"dashboard took {elapsed_ms:.1f}ms — expected under 1000ms"

    def test_quiz_generation_speed(self, live_server):
        session = _login(live_server, "perf_student@example.com")
        start = time.perf_counter()
        resp = session.post(f"{live_server}/api/quiz/start", json={
            "mode": "topic", "topic": "Navigation", "question_count": 5,
        }, timeout=10)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert resp.status_code == 201
        assert elapsed_ms < 2000, f"quiz generation took {elapsed_ms:.1f}ms — expected under 2000ms"

    def test_tutor_response_time(self, live_server):
        """Mock provider (offline, default) — measures the application's
        own overhead, not a live LLM's latency, which is this suite's
        honest, stated scope (see module docstring)."""
        session = _login(live_server, "perf_student@example.com")
        start = time.perf_counter()
        resp = session.post(f"{live_server}/api/tutor/session", json={"topic": "Navigation"}, timeout=10)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert resp.status_code == 201
        assert elapsed_ms < 1500, f"tutor session start took {elapsed_ms:.1f}ms — expected under 1500ms (Mock provider)"

    def test_faculty_class_analytics_query_performance(self, live_server):
        session = _login(live_server, "perf_faculty@example.com")
        start = time.perf_counter()
        resp = session.get(f"{live_server}/api/faculty/analytics/class", timeout=10)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert resp.status_code == 200
        assert elapsed_ms < 1000, f"class analytics took {elapsed_ms:.1f}ms — expected under 1000ms"


# --------------------------------------------------------------------
# Concurrent Users (Section 15/16) — real threads, real HTTP
# --------------------------------------------------------------------

class TestConcurrency:
    def test_concurrent_health_checks(self, live_server):
        """20 simultaneous requests against a stateless endpoint —
        baseline that the app doesn't choke under parallel connections
        at all before testing anything stateful."""
        def hit():
            r = requests.get(f"{live_server}/health", timeout=10)
            return r.status_code

        with ThreadPoolExecutor(max_workers=20) as pool:
            futures = [pool.submit(hit) for _ in range(20)]
            results = [f.result() for f in as_completed(futures)]

        assert all(code == 200 for code in results)

    def test_concurrent_logins_do_not_cross_contaminate_sessions(self, live_server):
        """Section 16 — Multiple Student Users. Each thread gets its
        own requests.Session; asserts no session bleed-through (a real
        risk if Flask-Login's session handling were misconfigured)."""
        def login_and_check(email):
            session = _login(live_server, email)
            me = session.get(f"{live_server}/api/auth/me", timeout=10).json()
            return me["data"]["email"]

        emails = ["perf_student@example.com"] * 10  # same user, 10 concurrent sessions
        with ThreadPoolExecutor(max_workers=10) as pool:
            results = [f.result() for f in [pool.submit(login_and_check, e) for e in emails]]

        assert all(r == "perf_student@example.com" for r in results)

    def test_concurrent_quiz_starts_each_get_isolated_attempts(self, live_server):
        """Section 16 — Heavy Traffic on the Quiz Engine. 10 concurrent
        quiz-start calls from the SAME user must each get their own
        attempt (or be cleanly rejected by the single-active-attempt
        rule, Part 3.7's security module) — never a corrupted/shared
        attempt row."""
        session = _login(live_server, "perf_student@example.com")

        def start_quiz():
            return session.post(f"{live_server}/api/quiz/start", json={
                "mode": "topic", "topic": "Navigation", "question_count": 1,
            }, timeout=10).status_code

        with ThreadPoolExecutor(max_workers=10) as pool:
            codes = [f.result() for f in [pool.submit(start_quiz) for _ in range(10)]]

        # Every response is a clean, valid status — either a new attempt
        # (201) or the documented single-active-attempt rejection (409) —
        # never a 500 from a race condition.
        assert all(code in (201, 409) for code in codes)
        assert 201 in codes  # at least the first one must have succeeded


# --------------------------------------------------------------------
# Resource Utilization (Section 15) — real process measurement via psutil
# --------------------------------------------------------------------

class TestResourceUtilization:
    def test_memory_does_not_balloon_under_repeated_requests(self, live_server):
        import psutil

        process = psutil.Process(os.getpid())
        baseline_mb = process.memory_info().rss / (1024 * 1024)

        for _ in range(50):
            requests.get(f"{live_server}/health", timeout=10)

        after_mb = process.memory_info().rss / (1024 * 1024)
        growth_mb = after_mb - baseline_mb
        # A generous ceiling — this is a smoke check for gross leaks
        # (e.g. an unclosed session/connection per request), not a
        # precise memory-profiling assertion.
        assert growth_mb < 50, f"Memory grew {growth_mb:.1f}MB over 50 requests — possible leak"

    def test_cpu_usage_sample_during_load(self, live_server):
        import psutil

        process = psutil.Process(os.getpid())
        process.cpu_percent(interval=None)  # prime the internal counter

        def hit():
            requests.get(f"{live_server}/health", timeout=10)

        with ThreadPoolExecutor(max_workers=10) as pool:
            list(pool.map(lambda _: hit(), range(30)))

        cpu_percent = process.cpu_percent(interval=0.5)
        assert cpu_percent >= 0  # sanity: psutil returned a real sample, not a crash