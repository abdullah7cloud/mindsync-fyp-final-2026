"""Tests for login rate limiting, security headers, CORS and request validation."""
from fastapi.testclient import TestClient

from app.main import app
from app.ratelimit import LoginRateLimiter, limiter_key


def test_limiter_blocks_after_max_failures_then_recovers():
    lim = LoginRateLimiter(max_failures=3, window_seconds=60)
    k = "a@b.com|1.2.3.4"
    for t in (0, 1, 2):
        assert lim.retry_after(k, now=t) == 0
        lim.record_failure(k, now=t)
    assert lim.retry_after(k, now=3) > 0          # blocked
    assert lim.retry_after(k, now=70) == 0        # window passed


def test_limiter_success_reset_clears_counter():
    lim = LoginRateLimiter(max_failures=2, window_seconds=60)
    k = "a@b.com|1.2.3.4"
    lim.record_failure(k, now=0)
    lim.record_failure(k, now=1)
    assert lim.retry_after(k, now=2) > 0
    lim.reset(k)
    assert lim.retry_after(k, now=3) == 0


def test_limiter_is_per_email_and_ip():
    lim = LoginRateLimiter(max_failures=1, window_seconds=60)
    lim.record_failure(limiter_key("a@b.com", "1.1.1.1"), now=0)
    assert lim.retry_after(limiter_key("a@b.com", "1.1.1.1"), now=1) > 0
    assert lim.retry_after(limiter_key("other@b.com", "1.1.1.1"), now=1) == 0
    assert lim.retry_after(limiter_key("a@b.com", "9.9.9.9"), now=1) == 0


def test_limiter_key_is_case_insensitive():
    assert limiter_key("A@B.com", "1.1.1.1") == limiter_key("a@b.COM ", "1.1.1.1")


def test_security_headers_present():
    r = TestClient(app).get("/health")
    assert r.status_code == 200
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["cache-control"] == "no-store"


def test_protected_route_requires_token():
    assert TestClient(app).get("/tasks").status_code in (401, 403)


def test_cors_rejects_unknown_origin():
    r = TestClient(app).get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in r.headers


def test_task_patch_rejects_explicit_null():
    import pytest
    from pydantic import ValidationError
    from app.schemas import TaskUpdate

    with pytest.raises(ValidationError):
        TaskUpdate(title=None)
    assert TaskUpdate(title="ok").title == "ok"
    assert TaskUpdate().model_fields_set == set()


def test_register_limiter_blocks_after_many_signups():
    from app.ratelimit import LoginRateLimiter

    lim = LoginRateLimiter(max_failures=20, window_seconds=3600)
    for i in range(20):
        assert lim.retry_after("1.1.1.1", now=i) == 0
        lim.record_failure("1.1.1.1", now=i)
    assert lim.retry_after("1.1.1.1", now=21) > 0


def test_unexpected_error_returns_plain_500_and_logs_location_not_message(api):
    """An unexpected crash must give a generic 500 (no stack trace to the user) and be logged without the message."""
    import logging
    from fastapi.testclient import TestClient
    from app import main as app_main

    records = []

    class Grab(logging.Handler):
        def emit(self, record):
            records.append(record.getMessage())

    async def boom():
        raise RuntimeError("secret-value-that-must-not-be-logged")

    handler = Grab()
    app_main.log.addHandler(handler)
    app_main.app.add_api_route("/_test_boom", boom)
    try:
        resp = TestClient(app_main.app, raise_server_exceptions=False).get("/_test_boom")
    finally:
        app_main.log.removeHandler(handler)
        app_main.app.router.routes[:] = [r for r in app_main.app.router.routes if getattr(r, "path", "") != "/_test_boom"]
    assert resp.status_code == 500
    assert resp.json() == {"detail": "Internal Server Error"}
    assert any("RuntimeError" in x and "boom" in x for x in records)
    assert not any("secret-value" in x for x in records)


def test_schema_sql_contains_every_table_of_the_models():
    """database/schema.sql is the reviewable SQL twin of the models; a table missing there is a documentation and set-up risk."""
    import re
    from pathlib import Path

    from app.database import Base
    import app.models  # noqa: F401  (registers the core tables)
    import app.assist.models  # noqa: F401  (registers the planner tables)
    import app.studio.models  # noqa: F401
    import app.simple.models  # noqa: F401
    import app.profile28.models  # noqa: F401

    sql = (Path(__file__).resolve().parents[2] / "database" / "schema.sql").read_text(encoding="utf-8")
    in_sql = set(re.findall(r"CREATE TABLE (?:IF NOT EXISTS )?(\w+)", sql))
    assert len(Base.metadata.tables) >= 18
    assert set(Base.metadata.tables) <= in_sql, set(Base.metadata.tables) - in_sql
