"""
Shared test fixtures.

`api` gives integration tests a real FastAPI app wired to a throw-away in-memory SQLite
database instead of PostgreSQL, so register / login / tasks / check-ins / wellbeing can be tested
end to end (HTTP -> validation -> authentication -> database -> JSON) in milliseconds, with no
server to start. SQLite is used only in tests; the real app uses PostgreSQL.
"""
import itertools

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app import auth, main, notifier, ratelimit, wellbeing
from app.ai import service as ai_service
from app.assist import routes as assist_routes
from app.config import settings
from app.database import Base, get_db
from app.main import app
from tests.dbutil import make_engine

_counter = itertools.count(1)


class Api:
    """Small helper around TestClient: create users and call routes as them."""

    def __init__(self, client: TestClient):
        self.client = client

    def register(self, name: str = "Test Student", email: str | None = None, password: str = "Study-pass-1") -> dict:
        email = email or f"user{next(_counter)}@example.com"
        r = self.client.post("/auth/register", json={"email": email, "display_name": name, "password": password})
        assert r.status_code == 201, r.text
        return {"email": email, "password": password, "headers": {"Authorization": f"Bearer {r.json()['access_token']}"}}


@pytest.fixture()
def api(monkeypatch):
    pytest.importorskip("aiosqlite")
    # never start the e-mail background job or touch the real PostgreSQL during tests
    monkeypatch.setattr(settings, "reminders_enabled", False)
    monkeypatch.setattr(settings, "task_reminders_enabled", False)       # Update 28 background job: tests call the cycle directly

    async def _no_schema():
        return None
    monkeypatch.setattr(main, "ensure_schema", _no_schema)

    # fresh rate limiters so tests cannot affect each other
    monkeypatch.setattr(auth, "register_limiter", ratelimit.LoginRateLimiter(1000, 3600))
    monkeypatch.setattr(auth, "login_limiter", ratelimit.LoginRateLimiter(5, 900))
    monkeypatch.setattr(wellbeing, "assess_limiter", ratelimit.LoginRateLimiter(1000, 3600))

    # the language model is OFF in every test unless a test installs a mock; the real API is never called
    monkeypatch.setattr(settings, "openai_api_key", "")
    ai_service.set_provider(None)
    monkeypatch.setattr(assist_routes, "_limit", ratelimit.LoginRateLimiter(1000, 600))
    monkeypatch.setattr(assist_routes, "_guest_limit", ratelimit.LoginRateLimiter(1000, 600))
    monkeypatch.setattr(ai_service, "guest_ip_limiter", ratelimit.LoginRateLimiter(5, 86400))

    state: dict = {}

    async def override_get_db():
        # The engine is created lazily INSIDE the app's event loop (SQLite connections are loop-bound).
        if "Session" not in state:
            engine = await make_engine()
            state["engine"] = engine
            state["Session"] = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with state["Session"]() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:   # one shared event loop for the whole test
        yield Api(client)
    app.dependency_overrides.clear()
    ai_service.reset_provider()
