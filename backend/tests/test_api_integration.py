"""
Integration tests: real HTTP requests through the FastAPI app into an in-memory database.

These cover the whole chain - request validation -> authentication (JWT) -> authorisation
(owner checks) -> database -> response - for the core student workflow.
"""
from datetime import datetime, timedelta, timezone


def future(hours: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def task_body(title="Write essay", difficulty=3, hours=30):
    return {"title": title, "description": "", "category": "general", "difficulty": difficulty, "deadline": future(hours)}


# ---------- authentication ----------
def test_register_login_me_roundtrip(api):
    u = api.register("Abi Tester", "abi@example.com")
    me = api.client.get("/auth/me", headers=u["headers"])
    assert me.status_code == 200 and me.json()["email"] == "abi@example.com"
    login = api.client.post("/auth/login", json={"email": "abi@example.com", "password": u["password"]})
    assert login.status_code == 200 and login.json()["token_type"] == "bearer"


def test_duplicate_email_is_rejected_with_clear_message(api):
    api.register(email="dup@example.com")
    r = api.client.post("/auth/register", json={"email": "dup@example.com", "display_name": "X", "password": "Study-pass-1"})
    assert r.status_code == 409 and "already exists" in r.json()["detail"].lower()


def test_wrong_password_is_401_and_brute_force_is_locked_out(api):
    api.register(email="victim@example.com")
    codes = [api.client.post("/auth/login", json={"email": "victim@example.com", "password": f"wrong-pass-{i}"}).status_code
             for i in range(7)]
    assert codes[0] == 401 and 429 in codes
    # even the correct password is refused while locked out
    assert api.client.post("/auth/login", json={"email": "victim@example.com", "password": "Study-pass-1"}).status_code == 429


def test_password_is_never_returned_or_stored_in_plain_text(api):
    u = api.register(email="p@example.com")
    assert "password" not in api.client.get("/auth/me", headers=u["headers"]).text.lower().replace("password_hash", "")


def test_protected_routes_reject_missing_and_forged_tokens(api):
    for path in ("/tasks", "/energy-checkins", "/recommend", "/wellbeing/history", "/notifications/status"):
        assert api.client.get(path).status_code in (401, 403), path
    forged = {"Authorization": "Bearer not.a.real.token"}
    assert api.client.get("/tasks", headers=forged).status_code == 401


# ---------- tasks + authorisation (IDOR) ----------
def test_task_crud(api):
    u = api.register()
    created = api.client.post("/tasks", json=task_body(), headers=u["headers"])
    assert created.status_code == 201
    tid = created.json()["id"]
    assert api.client.get("/tasks", headers=u["headers"]).json()[0]["id"] == tid
    patched = api.client.patch(f"/tasks/{tid}", json={"status": "completed"}, headers=u["headers"])
    assert patched.json()["status"] == "completed"
    assert api.client.delete(f"/tasks/{tid}", headers=u["headers"]).status_code in (200, 204)
    assert api.client.get("/tasks", headers=u["headers"]).json() == []


def test_task_validation(api):
    u = api.register()
    for bad in ({**task_body(), "difficulty": 9}, {**task_body(), "title": ""}, {**task_body(), "deadline": "not-a-date"}):
        assert api.client.post("/tasks", json=bad, headers=u["headers"]).status_code == 422


def test_user_cannot_read_change_or_delete_another_users_task(api):
    a, b = api.register(), api.register()
    tid = api.client.post("/tasks", json=task_body(), headers=a["headers"]).json()["id"]
    assert api.client.get(f"/tasks/{tid}", headers=b["headers"]).status_code == 404      # 404, not 403: no existence leak
    assert api.client.patch(f"/tasks/{tid}", json={"title": "hacked"}, headers=b["headers"]).status_code == 404
    assert api.client.delete(f"/tasks/{tid}", headers=b["headers"]).status_code == 404
    assert api.client.get("/tasks", headers=b["headers"]).json() == []
    assert api.client.get(f"/tasks/{tid}", headers=a["headers"]).json()["title"] == "Write essay"


# ---------- energy check-ins + recommendation ----------
def test_energy_checkin_validation_and_order(api):
    u = api.register()
    assert api.client.post("/energy-checkins", json={"energy_level": 6}, headers=u["headers"]).status_code == 422
    for level in (4, 2):
        assert api.client.post("/energy-checkins", json={"energy_level": level}, headers=u["headers"]).status_code == 201
    levels = [c["energy_level"] for c in api.client.get("/energy-checkins", headers=u["headers"]).json()]
    assert levels == [2, 4]            # newest first


def test_recommend_with_no_tasks(api):
    u = api.register()
    body = api.client.get("/recommend", headers=u["headers"]).json()
    assert body["top_task"] is None and body["explanation_source"] == "no_tasks"


def test_recommend_ranks_urgent_task_first_and_explains(api):
    u = api.register()
    api.client.post("/tasks", json=task_body("later", 3, 500), headers=u["headers"])
    api.client.post("/tasks", json=task_body("soon", 3, 5), headers=u["headers"])
    api.client.post("/energy-checkins", json={"energy_level": 3}, headers=u["headers"])
    body = api.client.get("/recommend", headers=u["headers"]).json()
    assert body["top_task"]["task"]["title"] == "soon"
    assert "'soon' is first because" in body["explanation"]
    # the experimental task-fit model is OFF by default (simulated training data), so only the formula ranks
    assert body["ml_model"] is None


def test_low_energy_turns_on_burnout_mode_and_hides_hard_tasks(api):
    u = api.register()
    api.client.post("/tasks", json=task_body("hard", 5, 5), headers=u["headers"])
    api.client.post("/tasks", json=task_body("easy", 1, 200), headers=u["headers"])
    api.client.post("/energy-checkins", json={"energy_level": 1}, headers=u["headers"])
    body = api.client.get("/recommend", headers=u["headers"]).json()
    assert body["burnout_mode"] is True and body["burnout_reason"] == "low_energy"
    assert [t["task"]["title"] for t in body["ranked_tasks"]] == ["easy"]


def test_recommendations_only_use_the_callers_own_tasks(api):
    a, b = api.register(), api.register()
    api.client.post("/tasks", json=task_body("secret", 3, 5), headers=a["headers"])
    body = api.client.get("/recommend", headers=b["headers"]).json()
    assert body["top_task"] is None


# ---------- study planner (account route) ----------
def test_planner_route_for_logged_in_user(api):
    u = api.register()
    r = api.client.post("/planner/plan", headers=u["headers"], json={
        "category": "Computer Science", "energy": 3, "topics": [{"title": "Python basics"}, {"title": "SQL joins"}]})
    assert r.status_code == 200 and r.json()["mode"] == "normal" and r.json()["plan"]


def test_experimental_task_fit_model_can_be_switched_on(api, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "ml_enabled", True)
    u = api.register()
    api.client.post("/tasks", json=task_body("a", 3, 10), headers=u["headers"])
    body = api.client.get("/recommend", headers=u["headers"]).json()
    assert body["ml_model"] == "logistic_regression"
    assert "ml_score" in body["top_task"]["score_breakdown"]


def test_completed_at_is_set_and_cleared(api):
    u = api.register()
    t = api.client.post("/tasks", json=task_body("done soon", 2, 24), headers=u["headers"]).json()
    assert t["completed_at"] is None
    r = api.client.patch(f"/tasks/{t['id']}", json={"status": "completed"}, headers=u["headers"]).json()
    assert r["completed_at"] is not None
    r = api.client.patch(f"/tasks/{t['id']}", json={"status": "pending"}, headers=u["headers"]).json()
    assert r["completed_at"] is None


def test_feedback_is_saved_validated_and_summarised(api):
    u = api.register()
    good = {"helpful": True, "energy_level": 3, "difficulty": 4, "hours_left": 20.5, "burnout_mode": False}
    assert api.client.post("/feedback", json=good, headers=u["headers"]).status_code == 201
    assert api.client.post("/feedback", json={**good, "helpful": False}, headers=u["headers"]).status_code == 201
    assert api.client.post("/feedback", json={**good, "energy_level": 9}, headers=u["headers"]).status_code == 422
    assert api.client.post("/feedback", json={**good, "helpful": "maybe"}, headers=u["headers"]).status_code == 422
    assert api.client.post("/feedback", json={**good, "task_title": "secret"}, headers=u["headers"]).status_code == 201  # extra keys ignored, never stored
    s = api.client.get("/feedback/summary", headers=u["headers"]).json()
    assert s == {"total": 3, "helpful": 2, "helpful_percent": 66.7}
    assert api.client.post("/feedback", json=good).status_code == 401


def test_feedback_summary_is_private_to_each_user(api):
    a, b = api.register(), api.register()
    api.client.post("/feedback", json={"helpful": True, "energy_level": 3, "difficulty": 3, "hours_left": 5}, headers=a["headers"])
    assert api.client.get("/feedback/summary", headers=b["headers"]).json()["total"] == 0


def test_account_export_contains_own_data_and_no_password_hash(api):
    a, b = api.register(name="Alice"), api.register(name="Bob")
    api.client.post("/tasks", json=task_body("alice task", 3, 30), headers=a["headers"])
    api.client.post("/tasks", json=task_body("bob task", 3, 30), headers=b["headers"])
    api.client.post("/energy-checkins", json={"energy_level": 4}, headers=a["headers"])
    r = api.client.get("/account/export", headers=a["headers"])
    assert r.status_code == 200
    data = r.json()
    assert data["account"]["display_name"] == "Alice"
    assert [t["title"] for t in data["tasks"]] == ["alice task"]
    assert data["energy_checkins"][0]["energy_level"] == 4
    assert "password" not in r.text.lower() and "argon2" not in r.text.lower()
    assert api.client.get("/account/export").status_code == 401


def test_delete_account_needs_the_right_password_and_erases_everything(api):
    a, b = api.register(), api.register()
    api.client.post("/tasks", json=task_body("mine", 3, 30), headers=a["headers"])
    api.client.post("/tasks", json=task_body("theirs", 3, 30), headers=b["headers"])
    api.client.post("/energy-checkins", json={"energy_level": 2}, headers=a["headers"])
    api.client.post("/feedback", json={"helpful": True, "energy_level": 3, "difficulty": 3, "hours_left": 5}, headers=a["headers"])
    wrong = api.client.request("DELETE", "/account", json={"password": "Not-the-password-1"}, headers=a["headers"])
    assert wrong.status_code == 403
    assert api.client.get("/auth/me", headers=a["headers"]).status_code == 200      # still exists
    ok = api.client.request("DELETE", "/account", json={"password": a["password"]}, headers=a["headers"])
    assert ok.status_code == 204
    assert api.client.get("/auth/me", headers=a["headers"]).status_code == 401      # token no longer maps to a user
    login = api.client.post("/auth/login", json={"email": a["email"], "password": a["password"]})
    assert login.status_code == 401
    # the other student is untouched
    assert [t["title"] for t in api.client.get("/tasks", headers=b["headers"]).json()] == ["theirs"]


def test_delete_account_wrong_passwords_get_locked_out(api):
    a = api.register()
    codes = [api.client.request("DELETE", "/account", json={"password": f"wrong-{i}-pass"}, headers=a["headers"]).status_code
             for i in range(7)]
    assert 429 in codes and codes[0] == 403


def test_delete_wellbeing_history_only_removes_wellbeing(api):
    a = api.register()
    api.client.post("/tasks", json=task_body("keep me", 3, 30), headers=a["headers"])
    assert api.client.delete("/account/wellbeing", headers=a["headers"]).status_code == 204
    assert len(api.client.get("/tasks", headers=a["headers"]).json()) == 1
    assert api.client.delete("/account/wellbeing").status_code == 401
