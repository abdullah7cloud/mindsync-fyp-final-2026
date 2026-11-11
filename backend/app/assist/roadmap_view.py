"""
The My Tasks page, as pure calculation.

`build_view` turns the saved roadmap blocks and the student's tasks into everything the page shows: today, tomorrow, the full
roadmap, completed work, overdue / delayed work, deadline cards, subject progress and the "Day N of total" counter.

It has no database, no clock and no network. The signed-in route feeds it rows from PostgreSQL; the guest route feeds it the
blocks the browser keeps in its own storage. Both therefore show exactly the same numbers.

Honest-progress rules used everywhere (page, Dashboard, reminders):
  * a block is "unfinished" when its status is planned, delayed, not_done or missed;
  * "studied minutes" are only minutes the student confirmed (actual_minutes of done and partly done blocks);
  * percent complete = confirmed minutes (capped at the planned minutes of each block) / planned minutes of all blocks
    that were not skipped. It measures work confirmed, not how well the material is understood.
"""
from datetime import date, timedelta
from typing import Optional

UNFINISHED = ("planned", "delayed", "not_done", "missed")
CONFIRMED = ("done", "partial")
STATUS_TEXT = {"planned": "Planned", "done": "Done", "partial": "Partly done", "not_done": "Not done", "delayed": "Delayed",
               "skipped": "Skipped", "missed": "Missed"}


def day_label(d: date, today: date) -> str:
    delta = (d - today).days
    return "Today" if delta == 0 else "Tomorrow" if delta == 1 else "Yesterday" if delta == -1 else d.strftime("%a %d %b")


def deadline_state(deadline: Optional[date], today: date, completed: bool) -> str:
    if completed:
        return "completed"
    if deadline is None:
        return "upcoming"
    return "overdue" if deadline < today else "due_today" if deadline == today else "upcoming"


def _item(s: dict, task: Optional[dict], today: date) -> dict:
    day = date.fromisoformat(s["day"])
    status = s.get("status", "planned")
    title = s.get("title") or (task["title"] if task else None) or "Study block"
    subject = (task or {}).get("subject") or s.get("subject") or "My other tasks"
    deadline = (task or {}).get("deadline")
    overdue = day < today and status in UNFINISHED
    return {"id": s["id"], "task_id": s.get("task_id"), "title": title, "subject": subject, "stage_label": s.get("label", ""), "method": s.get("method", ""),
            "minutes": int(s["minutes"]), "actual_minutes": int(s.get("actual_minutes") or 0), "break_after": int(s.get("break_after") or 0),
            "start_hint": s.get("start_hint"), "status": status, "status_text": STATUS_TEXT.get(status, status), "day": s["day"],
            "day_label": day_label(day, today), "weekday": day.weekday(), "original_day": s.get("original_day"), "manual": bool(s.get("manual")),
            "felt": s.get("felt"), "completed_at": s.get("completed_at"), "overdue": overdue, "task_state": (task or {}).get("state"),
            "deadline": deadline, "removed_task": s.get("task_id") is not None and task is None,
            "text": f"{title}: {s.get('label', '')}, {int(s['minutes'])} minutes" + (f", then a {int(s['break_after'])} minute break" if s.get("break_after") else "") + "."}


def build_view(blocks: list, tasks: list, today: date) -> dict:
    """blocks: [{id, task_id, day (iso), position, minutes, actual_minutes, status, label, method, ...}]; tasks: [{id, title, subject, deadline (iso), status}]."""
    by_task = {}
    for t in tasks:
        dl = date.fromisoformat(t["deadline"]) if t.get("deadline") else None
        by_task[t["id"]] = {**t, "state": deadline_state(dl, today, t.get("status") == "completed")}
    blocks = sorted(blocks, key=lambda b: (b["day"], b.get("position", 0)))
    items = [_item(b, by_task.get(b.get("task_id")), today) for b in blocks]

    counted = [i for i in items if i["status"] != "skipped"]
    planned_total = sum(i["minutes"] for i in counted)
    studied = sum(i["actual_minutes"] for i in items if i["status"] in CONFIRMED)
    credited = sum(min(i["actual_minutes"], i["minutes"]) for i in counted if i["status"] in CONFIRMED)
    days_all = sorted({i["day"] for i in counted})
    today_iso = today.isoformat()
    day_no = {d: n + 1 for n, d in enumerate(days_all)}
    passed = [d for d in days_all if d <= today_iso]
    overdue = [i for i in items if i["overdue"] or i["status"] == "delayed"]
    left_over = sum(max(0, i["minutes"] - i["actual_minutes"]) for i in items if i["status"] == "partial")
    summary = {
        "has_roadmap": bool(items), "total_blocks": len(counted), "done": sum(1 for i in items if i["status"] == "done"),
        "partial": sum(1 for i in items if i["status"] == "partial"), "not_done": sum(1 for i in items if i["status"] == "not_done"),
        "delayed": sum(1 for i in items if i["status"] == "delayed"), "overdue": sum(1 for i in items if i["overdue"]),
        "missed": sum(1 for i in items if i["status"] == "missed"),
        "remaining_blocks": sum(1 for i in items if i["status"] in UNFINISHED or i["status"] == "partial"),
        "planned_minutes": planned_total, "studied_minutes": studied, "left_over_minutes": left_over,
        "remaining_minutes": sum(i["minutes"] for i in items if i["status"] in UNFINISHED) + left_over,
        "percent": round(100 * credited / planned_total) if planned_total else 0,
        "days_total": len(days_all), "day_number": len(passed) if days_all and today_iso >= days_all[0] else 0,
        "first_day": days_all[0] if days_all else None, "last_day": days_all[-1] if days_all else None,
        "starts_in_days": (date.fromisoformat(days_all[0]) - today).days if days_all and today_iso < days_all[0] else 0}

    days = []
    for d in days_all + [x for x in sorted({i["day"] for i in items if i["status"] == "skipped"}) if x not in day_no]:
        its = [i for i in items if i["day"] == d]
        days.append({"date": d, "label": day_label(date.fromisoformat(d), today), "weekday": date.fromisoformat(d).weekday(), "day_number": day_no.get(d),
                     "minutes": sum(i["minutes"] for i in its if i["status"] != "skipped"),
                     "studied": sum(i["actual_minutes"] for i in its if i["status"] in CONFIRMED),
                     "done": sum(1 for i in its if i["status"] == "done"), "is_today": d == today_iso, "is_past": d < today_iso, "items": its})

    cards = []
    for t in tasks:
        its = [i for i in items if i["task_id"] == t["id"] and i["status"] != "skipped"]
        planned = sum(i["minutes"] for i in its)
        cred = sum(min(i["actual_minutes"], i["minutes"]) for i in its if i["status"] in CONFIRMED)
        dl = date.fromisoformat(t["deadline"]) if t.get("deadline") else None
        state = by_task[t["id"]]["state"]
        pct = 100 if state == "completed" else (round(100 * cred / planned) if planned else 0)
        cards.append({"task_id": t["id"], "title": t["title"], "subject": t.get("subject") or "My other tasks", "deadline": t.get("deadline"),
                      "days_left": (dl - today).days if dl else None, "state": state, "planned_minutes": planned,
                      "studied_minutes": sum(i["actual_minutes"] for i in its if i["status"] in CONFIRMED),
                      "blocks_total": len(its), "blocks_done": sum(1 for i in its if i["status"] == "done"),
                      "unfinished_blocks": sum(1 for i in its if i["status"] in UNFINISHED),
                      "unfinished_minutes": sum(i["minutes"] for i in its if i["status"] in UNFINISHED) + sum(max(0, i["minutes"] - i["actual_minutes"]) for i in its if i["status"] == "partial"),
                      "percent": pct})
    order = {"overdue": 0, "due_today": 1, "upcoming": 2, "completed": 3}
    cards.sort(key=lambda c: (order[c["state"]], c["deadline"] or "9999"))

    subjects = {}
    for c in cards:
        s = subjects.setdefault(c["subject"], {"subject": c["subject"], "planned_minutes": 0, "studied_minutes": 0, "topics": 0, "topics_completed": 0, "_cred": 0})
        s["planned_minutes"] += c["planned_minutes"]
        s["studied_minutes"] += c["studied_minutes"]
        s["topics"] += 1
        s["topics_completed"] += 1 if c["state"] == "completed" else 0
        s["_cred"] += min(c["planned_minutes"], c["studied_minutes"])
    subj_list = []
    for s in subjects.values():
        cred = s.pop("_cred")
        s["percent"] = round(100 * cred / s["planned_minutes"]) if s["planned_minutes"] else (100 if s["topics"] and s["topics_completed"] == s["topics"] else 0)
        subj_list.append(s)

    tomorrow = (today + timedelta(days=1)).isoformat()
    return {"today": today_iso, "summary": summary, "today_items": [i for i in items if i["day"] == today_iso and i["status"] != "skipped"],
            "tomorrow_items": [i for i in items if i["day"] == tomorrow and i["status"] != "skipped"], "days": days,
            "completed": sorted([i for i in items if i["status"] in CONFIRMED], key=lambda i: (i.get("completed_at") or i["day"]), reverse=True),
            "overdue": overdue, "tasks": cards, "subjects": subj_list}
