"""Profile page backend: full name, phone, preset avatar, secure e-mail change, and erasing every new table with the account."""


def H(u):
    return u["headers"]


def _login(api, email, pw):
    return api.client.post("/auth/login", json={"email": email, "password": pw})


def test_profile_new_fields_save_and_are_validated(api):
    u = api.register()
    r = api.client.put("/profile", json={"full_name": "  Abi   Khan ", "phone": "+45 12 34 56 78", "avatar": "owl", "display_name": "Abi"}, headers=H(u))
    assert r.status_code == 200
    p = r.json()["profile"]
    assert p["full_name"] == "Abi Khan" and p["avatar"] == "owl" and p["phone"] == "+45 12 34 56 78"
    for bad in ({"phone": "call me maybe"}, {"phone": "<script>"}, {"avatar": "<img src=x>"}, {"avatar": "../../etc/passwd"}, {"full_name": "x" * 101}):
        assert api.client.put("/profile", json=bad, headers=H(u)).status_code == 422, bad
    again = api.client.get("/profile", headers=H(u)).json()
    assert again["profile"]["avatar"] == "owl"                   # nothing was overwritten by the bad requests


def test_profile_phone_and_avatar_can_be_cleared(api):
    u = api.register()
    api.client.put("/profile", json={"phone": "12345678", "avatar": "fox"}, headers=H(u))
    p = api.client.put("/profile", json={"phone": "", "avatar": ""}, headers=H(u)).json()["profile"]
    assert p["phone"] == "" and p["avatar"] == ""


def test_old_password_only_email_route_is_closed_since_update_28(api):
    """Changing the e-mail now needs a code sent to the new address (tests/test_profile28.py). The old route must not be a way around it."""
    u = api.register()
    r = api.client.post("/account/email", json={"new_email": "new." + u["email"], "password": u["password"]}, headers=H(u))
    assert r.status_code == 410
    assert api.client.get("/account/export", headers=H(u)).json()["account"]["email"] == u["email"]


def test_delete_account_erases_roadmap_reminders_and_learning_packs(api):
    u = api.register()
    h = H(u)
    assert api.client.post("/studio/sample", headers=h).status_code in (200, 201)
    assert api.client.get("/reminders", headers=h).status_code == 200
    exp = api.client.get("/account/export", headers=h).json()
    assert exp["learning_packs"] and exp["learning_packs"][0]["questions"] and exp["learning_packs"][0]["flashcards"]
    assert "roadmap_blocks" in exp and "in_app_reminders" in exp and "roadmap_history" in exp
    r = api.client.request("DELETE", "/account", json={"password": u["password"]}, headers=h)
    assert r.status_code == 204
    assert _login(api, u["email"], u["password"]).status_code == 401


def test_delete_account_leaves_no_rows_in_the_new_tables(api):
    import asyncio
    from sqlalchemy import func, select
    from app.assist import models as AM
    from app.database import get_db
    from app.main import app
    from app.studio import models as SM
    u = api.register()
    h = H(u)
    api.client.post("/studio/sample", headers=h)
    api.client.get("/reminders", headers=h)

    async def count():
        agen = app.dependency_overrides[get_db]()
        db = await agen.__anext__()
        try:
            return {m.__tablename__: await db.scalar(select(func.count()).select_from(m))
                    for m in (SM.LearningPack, SM.PackQuestion, SM.PackCard, SM.QuizAttempt, AM.PlanEvent, AM.Notification)}
        finally:
            await agen.aclose()

    assert api.client.request("DELETE", "/account", json={"password": u["password"]}, headers=h).status_code == 204
    after = asyncio.run(count())
    assert set(after.values()) == {0}, after
