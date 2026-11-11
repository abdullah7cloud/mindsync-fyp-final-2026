"""My Tasks: the whole roadmap is saved, progress is confirmed honestly, edits and replans keep history, reminders never duplicate."""
from datetime import timedelta

import pytest

from app.assist import reminders as RM
from app.assist import roadmap_view as RV
from tests.test_assist_api import get, post  # noqa: F401
from tests.test_formplan import form, iso_in, me, subject, topic, utc_today  # noqa: F401


def patch(me, path, body):
    return me.client.patch(path, json=body, headers=me.h)


def delete(me, path):
    return me.client.delete(path, headers=me.h)


def put(me, path, body):
    return me.client.put(path, json=body, headers=me.h)


def seed(me, days=9, daily=120):
    subs = [subject("s1", "Mathematics", [topic("m1", "Quadratic equations", "exam", days=days, understanding=2)]),
            subject("s2", "Python Programming", [topic("p1", "Loops practice", "homework", days=days + 3)])]
    r = post(me, "/assist/plan-form", form(subs, availability={"daily_minutes": daily}))
    assert r.status_code == 200 and r.json()["status"] == "ok", r.text
    return r.json()


def roadmap(me):
    r = get(me, "/roadmap")
    assert r.status_code == 200, r.text
    return r.json()


def all_items(rm):
    return [i for d in rm["days"] for i in d["items"]]


def first_today_or_next(rm):
    return next(i for i in all_items(rm) if i["status"] == "planned")


# ------------------------------------------------------------------ the entire roadmap is saved
@pytest.mark.parametrize("days", [3, 9, 30, 70])
def test_whole_roadmap_is_saved_for_short_and_long_plans(me, days):
    out = seed(me, days=days)
    plan_min = sum(s["minutes"] for d in out["plan"]["days"] for s in d["sessions"])
    plan_blocks = sum(len(d["sessions"]) for d in out["plan"]["days"])
    rm = roadmap(me)
    assert rm["summary"]["has_roadmap"] and rm["summary"]["total_blocks"] == plan_blocks
    assert rm["summary"]["planned_minutes"] == plan_min and plan_min > 0
    assert rm["summary"]["days_total"] == len([d for d in out["plan"]["days"] if d["sessions"]])
    for d in rm["days"]:
        assert d["date"] and d["label"] and 0 <= d["weekday"] <= 6 and d["day_number"] >= 1
        for i in d["items"]:
            assert i["title"] and i["subject"] in ("Mathematics", "Python Programming") and i["minutes"] >= 5 and i["status"] == "planned"
    assert rm["summary"]["percent"] == 0 and rm["summary"]["studied_minutes"] == 0


def test_roadmap_reloads_identically_and_has_deadline_cards_and_subjects(me):
    seed(me)
    a, b = roadmap(me), roadmap(me)
    assert a == b
    assert {t["title"] for t in a["tasks"]} == {"Quadratic equations", "Loops practice"}
    assert all(t["state"] == "upcoming" and t["days_left"] >= 8 for t in a["tasks"])
    assert {s["subject"] for s in a["subjects"]} == {"Mathematics", "Python Programming"}
    assert a["summary"]["day_number"] in (0, 1) and a["summary"]["first_day"] <= a["summary"]["last_day"]


def test_today_and_tomorrow_lists(me):
    seed(me, days=5)
    rm = roadmap(me)
    today = utc_today().isoformat()
    assert all(i["day"] == today for i in rm["today_items"])
    assert all(i["day"] == (utc_today() + timedelta(days=1)).isoformat() for i in rm["tomorrow_items"])
    assert rm["today_items"] or rm["tomorrow_items"]


def test_every_day_has_the_right_weekday_and_label(me):
    from datetime import date
    seed(me, days=20)
    names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    rm = roadmap(me)
    today = utc_today()
    for d in rm["days"]:
        real = date.fromisoformat(d["date"])
        assert d["weekday"] == real.weekday()
        if real == today:
            assert d["label"].startswith("Today")
        elif real == today + timedelta(days=1):
            assert d["label"].startswith("Tomorrow")
        else:
            assert names[real.weekday()][:3] in d["label"] and str(real.day) in d["label"]


def test_the_students_study_days_are_respected_in_the_saved_roadmap(me):
    from datetime import date
    assert put(me, "/settings", {"study_days": [0, 1, 2, 3, 4]}).status_code == 200      # Monday to Friday only
    seed(me, days=20)
    days = [date.fromisoformat(d["date"]) for d in roadmap(me)["days"]]
    assert days and all(d.weekday() <= 4 for d in days), [d.isoformat() for d in days if d.weekday() > 4]


def test_several_subjects_can_share_one_day(me):
    seed(me, days=9, daily=180)
    rm = roadmap(me)
    shared = [d for d in rm["days"] if len({i["subject"] for i in d["items"]}) >= 2]
    assert shared, "with two subjects and a 3 hour day at least one day should hold both"


# ------------------------------------------------------------------ confirming progress
def test_done_saves_status_minutes_and_updates_progress_and_dashboard(me):
    seed(me)
    rm = roadmap(me)
    it = first_today_or_next(rm)
    r = post(me, f"/roadmap/items/{it['id']}/confirm", {"status": "done", "actual_minutes": it["minutes"] + 5, "felt": "okay"})
    assert r.status_code == 200, r.text
    v = r.json()["view"]
    got = next(i for i in all_items(v) if i["id"] == it["id"])
    assert got["status"] == "done" and got["actual_minutes"] == it["minutes"] + 5 and got["felt"] == "okay"
    assert v["summary"]["done"] == 1 and v["summary"]["studied_minutes"] == it["minutes"] + 5 and v["summary"]["percent"] > 0
    assert got in v["completed"]
    again = roadmap(me)                                                             # survives a reload
    assert next(i for i in all_items(again) if i["id"] == it["id"])["status"] == "done"
    dash = get(me, "/assist/dashboard").json()["summary"]
    assert dash["month"]["minutes_studied"] >= it["minutes"] + 5                    # the Dashboard reads the same confirmed work
    card = next(t for t in again["tasks"] if t["task_id"] == it["task_id"])
    assert card["studied_minutes"] == it["minutes"] + 5 and card["blocks_done"] == 1 and card["percent"] > 0


def test_changing_the_answer_replaces_it_instead_of_adding(me):
    seed(me)
    it = first_today_or_next(roadmap(me))
    post(me, f"/roadmap/items/{it['id']}/confirm", {"status": "done", "actual_minutes": 30})
    r = post(me, f"/roadmap/items/{it['id']}/confirm", {"status": "done", "actual_minutes": 20})
    assert r.json()["view"]["summary"]["studied_minutes"] == 20
    r = post(me, f"/roadmap/items/{it['id']}/confirm", {"status": "not_done"})
    s = r.json()["view"]["summary"]
    assert s["studied_minutes"] == 0 and s["not_done"] == 1 and s["done"] == 0
    assert get(me, "/assist/dashboard").json()["summary"]["month"]["minutes_studied"] == 0


def test_partly_done_keeps_the_rest_and_suggests_a_replan(me):
    seed(me)
    it = first_today_or_next(roadmap(me))
    bad = post(me, f"/roadmap/items/{it['id']}/confirm", {"status": "partial", "actual_minutes": it["minutes"] + 10})
    assert bad.status_code == 422
    r = post(me, f"/roadmap/items/{it['id']}/confirm", {"status": "partial", "actual_minutes": 10})
    out = r.json()
    assert out["replan_suggested"] is True and out["view"]["summary"]["partial"] == 1
    assert out["view"]["summary"]["left_over_minutes"] == it["minutes"] - 10
    assert out["view"]["summary"]["studied_minutes"] == 10


def test_not_done_and_delayed(me):
    seed(me, days=12)
    items = [i for i in all_items(roadmap(me)) if i["status"] == "planned"]
    a, b = items[0], items[1]
    r = post(me, f"/roadmap/items/{a['id']}/confirm", {"status": "not_done", "note": "Too tired"})
    assert r.status_code == 200 and r.json()["replan_suggested"]
    tomorrow = (utc_today() + timedelta(days=3)).isoformat()
    r = post(me, f"/roadmap/items/{b['id']}/confirm", {"status": "delayed", "new_day": tomorrow})
    moved = next(i for i in all_items(r.json()["view"]) if i["id"] == b["id"])
    assert moved["day"] == tomorrow and moved["status"] == "delayed" and moved["original_day"] == b["day"]
    assert moved in r.json()["view"]["overdue"]                                      # delayed work is listed in "Overdue / Delayed"
    assert post(me, f"/roadmap/items/{b['id']}/confirm", {"status": "delayed", "new_day": "2001-01-01"}).status_code == 422


def test_overdue_after_the_day_passes_and_stays_visible(me):
    seed(me)
    it = first_today_or_next(roadmap(me))
    # pretend the block's day has passed (the student never confirmed it)
    r = patch(me, f"/roadmap/items/{it['id']}", {"minutes": it["minutes"]})
    assert r.status_code == 200
    # use the route's own view builder with a later "today": the unfinished block is overdue, nothing is lost
    rm = roadmap(me)
    blocks = [dict(id=i["id"], task_id=i["task_id"], day=i["day"], minutes=i["minutes"], actual_minutes=i["actual_minutes"], status=i["status"], label=i["stage_label"],
                   method="", position=0) for i in all_items(rm)]
    tasks = [dict(id=t["task_id"], title=t["title"], subject=t["subject"], deadline=t["deadline"], status="pending") for t in rm["tasks"]]
    later = RV.build_view(blocks, tasks, utc_today() + timedelta(days=2))
    assert later["summary"]["overdue"] >= 1 and later["overdue"] and all(i["overdue"] for i in later["overdue"] if i["status"] != "delayed")
    assert later["summary"]["remaining_minutes"] >= it["minutes"]


def test_undo_restores_everything(me):
    seed(me)
    it = first_today_or_next(roadmap(me))
    before = get(me, "/assist/state").json()["tasks"]
    post(me, f"/roadmap/items/{it['id']}/confirm", {"status": "done", "actual_minutes": it["minutes"]})
    assert post(me, f"/roadmap/items/{it['id']}/undo").status_code == 200
    rm = roadmap(me)
    assert rm["summary"]["done"] == 0 and rm["summary"]["studied_minutes"] == 0
    assert next(i for i in all_items(rm) if i["id"] == it["id"])["status"] == "planned"
    assert get(me, "/assist/state").json()["tasks"] == before
    assert post(me, f"/roadmap/items/{it['id']}/undo").status_code == 409


def test_finishing_the_last_block_of_a_topic_completes_it_and_undo_reopens_it(me):
    post(me, "/assist/plan-form", form([subject("s1", "Biology", [topic("b1", "Cell notes", "reading", days=4)])], availability={"daily_minutes": 90}))
    rm = roadmap(me)
    blocks = [i for i in all_items(rm)]
    for n, b in enumerate(blocks):
        r = post(me, f"/roadmap/items/{b['id']}/confirm", {"status": "done", "actual_minutes": b["minutes"]})
        assert r.status_code == 200
    final = roadmap(me)
    assert final["tasks"][0]["state"] == "completed" and final["tasks"][0]["percent"] == 100
    assert get(me, "/tasks").json()[0]["status"] == "completed"
    post(me, f"/roadmap/items/{blocks[-1]['id']}/undo")
    assert get(me, "/tasks").json()[0]["status"] == "pending"


# ------------------------------------------------------------------ editing
def test_edit_move_add_remove_with_confirmation(me):
    seed(me, days=12)
    items = [i for i in all_items(roadmap(me)) if i["status"] == "planned"]
    it = items[0]
    r = patch(me, f"/roadmap/items/{it['id']}", {"minutes": 45, "title": "Quadratics: past paper"})
    assert r.status_code == 200
    got = next(i for i in all_items(r.json()["view"]) if i["id"] == it["id"])
    assert got["minutes"] == 45 and got["title"] == "Quadratics: past paper" and got["manual"] is True
    assert patch(me, f"/roadmap/items/{it['id']}", {}).status_code == 422
    assert patch(me, f"/roadmap/items/{it['id']}", {"minutes": 2}).status_code == 422
    target = (utc_today() + timedelta(days=4)).isoformat()
    r = post(me, f"/roadmap/items/{items[1]['id']}/move", {"day": target})
    assert next(i for i in all_items(r.json()["view"]) if i["id"] == items[1]["id"])["day"] == target
    assert post(me, f"/roadmap/items/{items[1]['id']}/move", {"day": "2001-01-01"}).status_code == 422
    # add an own block
    r = post(me, "/roadmap/items", {"title": "Read the library book", "subject": "History", "minutes": 25, "day": target})
    assert r.status_code == 201
    new_id = r.json()["id"]
    assert any(i["id"] == new_id and i["subject"] == "History" and i["manual"] for i in all_items(r.json()["view"]))
    # remove needs confirmation
    assert delete(me, f"/roadmap/items/{new_id}").status_code == 422
    assert delete(me, f"/roadmap/items/{new_id}?confirm=true").status_code == 200
    assert not any(i["id"] == new_id for i in all_items(roadmap(me)))
    # a confirmed block can't be removed or moved
    post(me, f"/roadmap/items/{items[2]['id']}/confirm", {"status": "done", "actual_minutes": 10})
    assert delete(me, f"/roadmap/items/{items[2]['id']}?confirm=true").status_code == 409
    assert post(me, f"/roadmap/items/{items[2]['id']}/move", {"day": target}).status_code == 409
    kinds = [e["kind"] for e in get(me, "/roadmap/history").json()["events"]]
    assert {"edited", "moved", "added", "removed", "confirmed"} <= set(kinds)


def test_cannot_add_a_block_without_a_plan_or_with_hostile_input(me):
    assert post(me, "/roadmap/items", {"title": "x", "minutes": 20, "day": iso_in(1)}).status_code == 409
    seed(me)
    r = post(me, "/roadmap/items", {"title": "<script>alert(1)</script>Study", "minutes": 20, "day": iso_in(1)})
    assert r.status_code == 201
    assert r.headers["content-type"].startswith("application/json") and r.headers.get("x-content-type-options") == "nosniff"
    titles = [i["title"] for i in all_items(r.json()["view"])]
    assert any("Study" in t for t in titles)          # kept as plain text; the page shows it as text and never as markup
    assert post(me, "/roadmap/items", {"title": "x", "minutes": 20, "day": iso_in(1), "extra": 1}).status_code == 422
    assert post(me, "/roadmap/items", {"title": "x", "minutes": 20, "day": "2001-01-01"}).status_code == 422


# ------------------------------------------------------------------ replanning keeps history
def test_replan_preview_changes_nothing_and_apply_needs_confirmation(me):
    seed(me, days=12)
    items = [i for i in all_items(roadmap(me)) if i["status"] == "planned"]
    post(me, f"/roadmap/items/{items[0]['id']}/confirm", {"status": "done", "actual_minutes": items[0]["minutes"]})
    post(me, f"/roadmap/items/{items[1]['id']}/confirm", {"status": "not_done"})
    own = post(me, "/roadmap/items", {"title": "My own block", "minutes": 20, "day": iso_in(3)}).json()["id"]
    before = roadmap(me)
    prev = post(me, "/roadmap/replan/preview")
    assert prev.status_code == 200
    p = prev.json()
    assert p["can_apply"] and p["keeps"]["done"] == 1 and p["keeps"]["own_blocks"] == 1 and p["replaces"]["blocks"] >= 1
    assert roadmap(me) == before                                                      # nothing saved by a preview
    assert post(me, "/roadmap/replan/apply", {}).status_code == 422
    assert roadmap(me) == before
    r = post(me, "/roadmap/replan/apply", {"confirm": True})
    assert r.status_code == 200, r.text
    after = r.json()["view"]
    ids = {i["id"]: i for i in all_items(after)}
    assert ids[items[0]["id"]]["status"] == "done" and ids[items[0]["id"]]["actual_minutes"] == items[0]["minutes"]      # history kept
    assert ids[items[1]["id"]]["status"] == "not_done"
    assert own in ids and ids[own]["title"] == "My own block"                                                             # own block carried over
    assert after["summary"]["studied_minutes"] == items[0]["minutes"]
    assert after["summary"]["remaining_minutes"] > 0
    assert "replan" in [e["kind"] for e in get(me, "/roadmap/history").json()["events"]]
    assert get(me, "/assist/state").json()["plan"]["days"]                           # the Smart Planner shows the new plan


def test_replan_warns_about_blocks_the_student_edited(me):
    seed(me, days=12)
    it = first_today_or_next(roadmap(me))
    patch(me, f"/roadmap/items/{it['id']}", {"minutes": 50})
    p = post(me, "/roadmap/replan/preview").json()
    assert p["edited_blocks"] and p["warning"] and "changed by hand" in p["warning"]


def test_replan_without_a_plan_is_refused(me):
    assert post(me, "/roadmap/replan/preview").status_code == 409
    assert post(me, "/roadmap/replan/apply", {"confirm": True}).status_code == 409
    rm = roadmap(me)
    assert rm["summary"]["has_roadmap"] is False and rm["days"] == []


# ------------------------------------------------------------------ isolation and bad input
def test_other_students_cannot_touch_my_blocks(me, api):
    seed(me)
    it = first_today_or_next(roadmap(me))
    other = api.register()
    api.h = other["headers"]
    assert get(api, "/roadmap").json()["summary"]["has_roadmap"] is False
    for call in (lambda: post(api, f"/roadmap/items/{it['id']}/confirm", {"status": "done"}),
                 lambda: post(api, f"/roadmap/items/{it['id']}/undo"),
                 lambda: post(api, f"/roadmap/items/{it['id']}/move", {"day": iso_in(2)}),
                 lambda: patch(api, f"/roadmap/items/{it['id']}", {"minutes": 30}),
                 lambda: delete(api, f"/roadmap/items/{it['id']}?confirm=true")):
        assert call().status_code == 404
    assert post(api, f"/roadmap/items/not-a-uuid/confirm", {"status": "done"}).status_code == 404
    assert api.client.get("/roadmap").status_code == 401
    assert get(api, "/reminders").json()["items"] == []


def test_bad_confirm_bodies_are_rejected(me):
    seed(me)
    it = first_today_or_next(roadmap(me))
    for body in ({"status": "finished"}, {"status": "done", "actual_minutes": 0}, {"status": "done", "actual_minutes": 99999},
                 {"status": "done", "felt": "great"}, {"status": "done", "extra": 1}, {}):
        assert post(me, f"/roadmap/items/{it['id']}/confirm", body).status_code == 422, body


# ------------------------------------------------------------------ reminders
def open_reminders(me):
    assert put(me, "/settings", {"daily_reminder_time": "00:00"}).status_code == 200


def test_daily_and_deadline_reminders_are_created_once(me):
    seed(me, days=2)
    open_reminders(me)
    r1 = get(me, "/reminders").json()
    r2 = get(me, "/reminders").json()
    daily = [n for n in r2["items"] if n["kind"] == "daily"]
    assert len(daily) == 1 and "Your study plan for today" in daily[0]["title"] and daily[0]["data"]["link"] == "/tasks"
    assert r1["items"] and len(r1["items"]) == len(r2["items"])
    keys = [(n["kind"], n["title"]) for n in r2["items"]]
    assert len(keys) == len(set(keys))
    dl = [n for n in r2["items"] if n["kind"] == "deadline"]
    assert dl and all("Deadline" in n["title"] or "Due" in n["title"] for n in dl)
    assert r2["email_available"] is False and "No email" in r2["delivery_note"] and r2["unread"] == len(r2["items"])


def test_reminders_can_be_marked_read_and_switched_off(me):
    seed(me, days=2)
    open_reminders(me)
    items = get(me, "/reminders").json()["items"]
    assert post(me, f"/reminders/{items[0]['id']}/read").status_code == 200
    assert get(me, "/reminders").json()["unread"] == len(items) - 1
    assert post(me, "/reminders/read-all").status_code == 200 and get(me, "/reminders").json()["unread"] == 0
    put(me, "/settings", {"inapp_reminders": False})
    assert get(me, "/reminders").json()["unread"] == 0


def test_moving_work_updates_todays_reminder_and_changing_a_deadline_replaces_old_ones(me):
    seed(me, days=2)
    open_reminders(me)
    first = [n for n in get(me, "/reminders").json()["items"] if n["kind"] == "daily"][0]
    today_items = roadmap(me)["today_items"]
    if not today_items:                                    # late in the evening nothing is planned for the rest of today, so there is nothing to confirm
        pytest.skip("no study block is left for today at this time of day")
    post(me, f"/roadmap/items/{today_items[0]['id']}/confirm", {"status": "done", "actual_minutes": today_items[0]["minutes"]})
    second = [n for n in get(me, "/reminders").json()["items"] if n["kind"] == "daily"]
    assert len(second) == 1 and second[0]["id"] == first["id"] and second[0]["body"] != first["body"]       # refreshed, not duplicated
    t = next(x for x in get(me, "/tasks").json() if x["title"] == "Quadratic equations")
    before = [n for n in get(me, "/reminders").json()["items"] if n["kind"] == "deadline" and t["id"] == n["task_id"]]
    assert before and before[0]["data"]["days_left"] <= 3
    old_ids = {n["id"] for n in before}
    new_deadline = (utc_today() + timedelta(days=30)).isoformat() + "T23:59:00Z"
    assert patch(me, f"/tasks/{t['id']}", {"deadline": new_deadline}).status_code == 200
    after = [n for n in get(me, "/reminders").json()["items"] if n["kind"] == "deadline" and t["id"] == n["task_id"]]
    assert not (old_ids & {n["id"] for n in after})                  # the unread reminders for the old date are gone
    assert after == []                                                 # 30 days away: no reminder is due yet


def test_reminder_rules_are_pure_and_honour_settings():
    from app.assist.settings_schema import StudySettings
    from datetime import datetime
    from zoneinfo import ZoneInfo
    today = utc_today()
    mk = lambda d: {"id": "t1", "title": "Essay", "subject": "English", "deadline": (today + timedelta(days=d)).isoformat(), "status": "pending"}
    blocks = [{"id": "b1", "task_id": "t1", "day": today.isoformat(), "minutes": 30, "status": "planned", "label": "Draft", "position": 0}]
    now = datetime(today.year, today.month, today.day, 9, 0, tzinfo=ZoneInfo("UTC"))
    st = StudySettings(daily_reminder_time="08:00")
    expect = {8: None, 7: "7d", 5: "7d", 3: "3d", 2: "3d", 1: "1d"}
    for d, lead in expect.items():
        v = RV.build_view(blocks, [mk(d)], today)
        keys = [n["key"] for n in RM.compute(v, st, now, "Abi") if n["kind"] == "deadline"]
        if lead is None:
            assert keys == [], d
        else:
            assert len(keys) == 1 and f":{lead}:" in keys[0], (d, keys)
    v0 = RV.build_view(blocks, [mk(0)], today)
    assert [n["key"].split(":")[2] for n in RM.compute(v0, st, now) if n["kind"] == "deadline"] == ["today"]
    vo = RV.build_view(blocks, [mk(-2)], today)
    assert [n["key"].split(":")[2] for n in RM.compute(vo, st, now) if n["kind"] == "deadline"] == ["overdue"]
    assert RM.compute(vo, StudySettings(deadline_overdue=False, daily_reminder=False), now) == []
    assert RM.compute(v0, StudySettings(inapp_reminders=False), now) == []
    early = datetime(today.year, today.month, today.day, 6, 0, tzinfo=ZoneInfo("UTC"))
    assert not [n for n in RM.compute(v0, st, early) if n["kind"] == "daily"]                         # before the reminder time
    custom = StudySettings(deadline_days=[2])
    assert [n for n in RM.compute(RV.build_view(blocks, [mk(5)], today), custom, now) if n["kind"] == "deadline"] == []
    assert RM.compute(RV.build_view(blocks, [{**mk(3), "status": "completed"}], today), st, now)[0]["kind"] == "daily"
    assert [n for n in RM.compute(RV.build_view(blocks, [{**mk(3), "status": "completed"}], today), st, now) if n["kind"] == "deadline"] == []


def test_new_settings_validate():
    from app.assist.settings_schema import StudySettings
    with pytest.raises(Exception):
        StudySettings(daily_reminder_time="25:00")
    with pytest.raises(Exception):
        StudySettings(deadline_days=[9])
    with pytest.raises(Exception):
        StudySettings(accent="red")
    assert StudySettings(deadline_days=[1, 7, 3]).deadline_days == [7, 3, 1]


# ------------------------------------------------------------------ guests: same numbers, nothing stored
def test_guest_roadmap_view_matches_and_validates(api):
    today = utc_today()
    blocks = [{"id": "b1", "task_id": "t1", "day": today.isoformat(), "minutes": 30, "status": "done", "actual_minutes": 25, "label": "Learn"},
              {"id": "b2", "task_id": "t1", "day": (today + timedelta(days=1)).isoformat(), "minutes": 30, "status": "planned", "label": "Practise"},
              {"id": "b3", "task_id": None, "day": today.isoformat(), "minutes": 15, "status": "planned", "label": "own", "title": "Own", "subject": "Art", "manual": True}]
    tasks = [{"id": "t1", "title": "Essay", "subject": "English", "deadline": (today + timedelta(days=3)).isoformat()}]
    body = {"today": today.isoformat(), "time": "09:00", "name": "Abi Khan", "blocks": blocks, "tasks": tasks}
    r = api.client.post("/demo/assist/roadmap", json=body)
    assert r.status_code == 200, r.text
    v = r.json()
    assert v["summary"]["done"] == 1 and v["summary"]["studied_minutes"] == 25 and len(v["today_items"]) == 2 and len(v["tomorrow_items"]) == 1
    kinds = {n["kind"] for n in v["reminders_due"]}
    assert kinds == {"daily", "deadline"} and v["reminders_due"][0]["title"].startswith("Good morning, Abi")
    bad = dict(body, blocks=[dict(blocks[0], minutes=1)])
    assert api.client.post("/demo/assist/roadmap", json=bad).status_code == 422
    assert api.client.post("/demo/assist/roadmap", json=dict(body, extra=1)).status_code == 422
    assert api.client.post("/demo/assist/roadmap", json=dict(body, blocks=[dict(blocks[0], id="../x")])).status_code == 422
