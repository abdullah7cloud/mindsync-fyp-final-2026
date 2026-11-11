"""Study guidance per topic and the richer dashboard: real records only, personalised by the form, user-isolated, guest twin."""
from tests.test_assist_api import get, post  # noqa: F401
from tests.test_formplan import form, me, subject, topic  # noqa: F401
from tests.test_formplan import guest_state


def _seed(me):
    subs = [subject("s1", "Mathematics", [topic("m1", "Quadratic equations", "exam", days=7, understanding=1, details={"chapters": 3})]),
            subject("s2", "Python Programming", [topic("p1", "Final project", "project", days=12, progress="half", details={"features_left": 3})])]
    return post(me, "/assist/plan-form", form(subs, availability={"daily_minutes": 120}, obstacles=["procrastinate", "distracted"],
                                                helps=["practice_questions"], feelings={"mood": "tired", "energy": "low", "stress": "medium"})).json()


def test_guidance_is_per_topic_and_personalised(me):
    assert _seed(me)["status"] == "ok"
    g = get(me, "/assist/guidance").json()
    assert g["source"] == "rules" and "not read your course material" in g["note"]
    by = {i["name"]: i for i in g["items"]}
    m, p = by["Quadratic equations"], by["Final project"]
    for item in (m, p):
        for key in ("understand", "why", "first_step", "approach", "exercises", "mistakes", "check", "if_stuck", "review"):
            assert item[key], key
    assert m["type"] == "exam" and p["type"] == "project"
    assert any("do not understand this yet" in s for s in m["approach"])          # understanding 1 changes the advice
    assert any("halfway" in s for s in p["approach"])                              # progress changes the advice
    assert any("5-minute timer" in t for t in m["tips"]) and any("practice questions" in t for t in m["tips"])
    assert m["understand"] != p["understand"]
    assert "Mathematics" == m["subject"] and m["example"]                          # subject flavour


def test_guidance_empty_when_nothing_to_study_and_isolated(me, api):
    assert get(me, "/assist/guidance").json()["items"] == []
    _seed(me)
    other = api.register()
    api.h = other["headers"]
    assert get(api, "/assist/guidance").json()["items"] == []


def test_dashboard_shows_subjects_today_month_deadline_moods_and_achievements(me):
    _seed(me)
    s = get(me, "/assist/dashboard").json()["summary"]
    assert {x["subject"] for x in s["subjects"]} == {"Mathematics", "Python Programming"}
    assert s["next_deadline"]["subject"] == "Mathematics" and s["next_deadline"]["days_left"] in (6, 7)
    assert s["today"]["planned_minutes"] >= 0 and "hours" in s["month"]
    assert s["moods"] and s["moods"][-1]["energy"] == "low"
    ids = {a["id"]: a["earned"] for a in s["achievements"]}
    assert ids["first_session"] is False and ids["topic_1"] is False             # nothing is claimed that did not happen
    assert s["insights"] == []                                                    # no records, no invented insight
    # finish a block -> a real record appears
    st = get(me, "/assist/state").json()
    block = next(x for d in st["plan"]["days"] for x in d["sessions"])
    r = post(me, "/assist/session", {"plan_session_id": block["id"], "task_id": block["task_id"], "status": "done", "actual_minutes": 40, "focus": 4})
    assert r.status_code in (200, 201), r.text
    s2 = get(me, "/assist/dashboard").json()["summary"]
    assert s2["month"]["minutes_studied"] >= 40
    assert {a["id"]: a["earned"] for a in s2["achievements"]}["first_session"] is True
    assert any(x["minutes_studied"] >= 40 for x in s2["subjects"])


def test_mood_entry_cleared_with_wellbeing_data(me):
    _seed(me)
    assert get(me, "/assist/dashboard").json()["summary"]["moods"]
    r = me.client.delete("/account/wellbeing", headers=me.h)
    assert r.status_code in (200, 204)
    assert get(me, "/assist/dashboard").json()["summary"]["moods"] == []


def test_guest_guidance_and_dashboard(api):
    t = topic("t1", "Probability", "exam", days=5, understanding=2)
    f = form([subject(topics=[t])])
    ch = api.client.post("/demo/assist/plan-form", json={"state": guest_state(), "form": f}).json()
    assert ch["status"] == "ok" and ch["changes"]["creates"]
    c = ch["changes"]["creates"][0]
    task = {"id": "g1", "title": c["title"], "description": c["description"], "category": c["category"], "difficulty": c["difficulty"],
            "deadline": c["deadline"], "status": "pending", "meta": c["meta"]}
    st = guest_state(tasks=[task])
    g = api.client.post("/demo/assist/guidance", json={"state": st}).json()
    assert g["items"] and g["items"][0]["type"] == "exam" and g["source"] == "rules"
    d = api.client.post("/demo/assist/dashboard", json={"state": st}).json()["summary"]
    assert d["subjects"][0]["subject"] == "Python Programming" and d["next_deadline"]
