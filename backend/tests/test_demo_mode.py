"""Guest mode: works without login, stores nothing, is size-limited and rate-limited."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import demo
from app.main import app
from app.ratelimit import LoginRateLimiter


@pytest.fixture(autouse=True)
def fresh_limiter(monkeypatch):
    monkeypatch.setattr(demo, "demo_rank_limiter", LoginRateLimiter(120, 600))


client = TestClient(app)
NOW = datetime.now(timezone.utc)


def task(title, hours, difficulty=3, status="pending"):
    return {"id": str(uuid.uuid4()), "title": title, "description": "", "category": "general",
            "difficulty": difficulty, "deadline": (NOW + timedelta(hours=hours)).isoformat(),
            "status": status, "created_at": NOW.isoformat()}


def test_guest_recommendation_needs_no_login_and_ranks_by_urgency():
    r = client.post("/demo/recommend", json={"tasks": [task("later", 200), task("soon", 5)], "recent_energy": [3]})
    assert r.status_code == 200
    body = r.json()
    assert body["top_task"]["task"]["title"] == "soon"
    assert body["explanation_source"] == "local_rules" and body["burnout_mode"] is False
    assert "'soon' is first because" in body["explanation"]


def test_guest_burnout_mode_hides_hard_tasks():
    r = client.post("/demo/recommend", json={"tasks": [task("hard", 5, 5), task("easy", 100, 1)], "recent_energy": [1]})
    body = r.json()
    assert body["burnout_mode"] is True and body["burnout_reason"] == "low_energy"
    assert [t["task"]["title"] for t in body["ranked_tasks"]] == ["easy"]


def test_high_stress_result_switches_burnout_mode_on_even_with_good_energy():
    r = client.post("/demo/recommend", json={"tasks": [task("hard", 5, 5), task("easy", 100, 1)],
                                             "recent_energy": [5], "stress_risk": "High"})
    body = r.json()
    assert body["burnout_mode"] is True and body["burnout_reason"] == "high_stress_risk"
    assert [t["task"]["title"] for t in body["ranked_tasks"]] == ["easy"]
    assert "wellbeing check" in body["explanation"]


def test_invalid_stress_risk_value_is_rejected():
    r = client.post("/demo/recommend", json={"tasks": [], "stress_risk": "Extreme"})
    assert r.status_code == 422


def test_completed_tasks_are_ignored_and_empty_is_ok():
    r = client.post("/demo/recommend", json={"tasks": [task("done", 5, status="completed")], "recent_energy": []})
    assert r.status_code == 200 and r.json()["top_task"] is None and r.json()["explanation_source"] == "no_tasks"


def test_a_guest_with_forty_topics_still_gets_a_suggestion():
    r = client.post("/demo/recommend", json={"tasks": [task(f"t{i}", 5 + i) for i in range(40)], "recent_energy": [3]})
    assert r.status_code == 200 and r.json()["top_task"] is not None


def test_size_limits():
    assert client.post("/demo/recommend", json={"tasks": [task(f"t{i}", 5) for i in range(61)]}).status_code == 422
    assert client.post("/demo/recommend", json={"tasks": [], "recent_energy": [1, 2, 3, 4, 5, 3]}).status_code == 422


def test_guest_ranking_is_rate_limited(monkeypatch):
    monkeypatch.setattr(demo, "demo_rank_limiter", LoginRateLimiter(2, 600))
    codes = [client.post("/demo/recommend", json={"tasks": []}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_models_status_is_public_and_reports_whether_an_external_model_is_configured():
    from app.ai import service as ai_service
    ai_service.set_provider(None)
    try:
        body = client.get("/models/status").json()
    finally:
        ai_service.reset_provider()
    assert body["external_ai_used"] is False and "No external language model" in body["external_ai_note"]
    assert body["task_fit"]["kind"] == "logistic_regression" and body["task_fit"]["evaluation"]["data_is_simulated"] is True
    assert "wellbeing" in body


def test_removed_cloud_ai_routes_are_gone():
    # The app no longer contains any external-AI feature.
    for path in ("/demo/coach/stream", "/demo/breakdown", "/ai/status", "/ai/coach"):
        assert client.post(path, json={}).status_code in (404, 405)
