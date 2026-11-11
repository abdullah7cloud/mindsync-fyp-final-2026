"""
Dashboard and history numbers. REAL records only: every figure is computed from the tasks, sessions, check-ins and plan rows
passed in. When there is no data the field is None (or an empty list) and the screen shows an empty state, never a placeholder
number. Pure function: the same code serves signed-in students (rows from PostgreSQL) and guests (rows from the browser).
"""
from datetime import timezone, date, datetime, timedelta
from statistics import median
from typing import Optional
from zoneinfo import ZoneInfo

from app.taskaware import taxonomy as T


def _d(dt, tz) -> date:
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    if dt.tzinfo is None:  # SQLite hands back naive datetimes; every stored time is UTC (PostgreSQL returns aware ones)
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz).date()


def _dt(x) -> datetime:
    return datetime.fromisoformat(x) if isinstance(x, str) else x


def _mon(d: date) -> date:
    return d - timedelta(days=d.weekday())


def summarize(*, now: datetime, tz: ZoneInfo, tasks: list, task_sessions: list, checkins: list, wellbeing: list, outcomes: list,
              plan_sessions: list, goal_hours: Optional[float], subject_of: Optional[dict] = None, mood_log: Optional[list] = None) -> dict:
    """
    tasks: [{id,title,status,deadline,completed_at,kind?}]
    task_sessions: [{task_id,kind,planned_minutes,actual_minutes,completed,focus,felt_difficulty,created_at}]
    checkins: [{energy_level,created_at}]       wellbeing: [{label,created_at}]
    outcomes: [{kind,raw_minutes,actual_minutes}]
    plan_sessions: [{day,minutes,status,task_id}]   (planned blocks, any plan)
    """
    today = now.astimezone(tz).date()
    wk = _mon(today)
    prev = wk - timedelta(days=7)
    sess = [dict(s, _day=_d(s["created_at"], tz)) for s in task_sessions]
    done_tasks = [t for t in tasks if t["status"] == "completed" and t.get("completed_at")]
    pending = [t for t in tasks if t["status"] == "pending"]

    def minutes(lo: date, hi: date) -> int:
        return sum(s["actual_minutes"] for s in sess if lo <= s["_day"] <= hi)

    week_sess = [s for s in sess if wk <= s["_day"] <= today]
    week_done = [t for t in done_tasks if wk <= _d(t["completed_at"], tz) <= today]
    focus_vals = [s["focus"] for s in week_sess if s.get("focus")]
    planned_past = sum(p["minutes"] for p in plan_sessions if wk <= date.fromisoformat(str(p["day"])[:10]) <= today)
    adherence = None
    if planned_past > 0:
        adherence = round(min(1.5, sum(s["actual_minutes"] for s in week_sess if s.get("planned_minutes", 0) > 0) / planned_past), 2)
    week = {"start": wk.isoformat(), "minutes_studied": minutes(wk, today), "sessions": len(week_sess),
            "tasks_completed": len(week_done),
            "completion_rate": round(sum(1 for s in week_sess if s["completed"]) / len(week_sess), 2) if week_sess else None,
            "avg_focus": round(sum(focus_vals) / len(focus_vals), 2) if focus_vals else None,
            "plan_adherence": adherence, "goal_hours": goal_hours,
            "goal_progress": round(minutes(wk, today) / (goal_hours * 60), 2) if goal_hours else None,
            "prev_week_minutes": minutes(prev, wk - timedelta(days=1))}
    daily = []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        ds = [s for s in sess if s["_day"] == d]
        daily.append({"date": d.isoformat(), "minutes": sum(s["actual_minutes"] for s in ds), "sessions": len(ds)})
    en = {}
    for c in checkins:
        d = _d(c["created_at"], tz)
        if today - timedelta(days=13) <= d <= today:
            en.setdefault(d, []).append(c["energy_level"])
    energy = [{"date": d.isoformat(), "level": round(sum(v) / len(v), 1)} for d, v in sorted(en.items())]
    by_kind = {}
    for s in sess:
        if s["_day"] >= today - timedelta(days=29):
            by_kind[s["kind"]] = by_kind.get(s["kind"], 0) + s["actual_minutes"]
    kinds = [{"kind": k, "label": T.KINDS.get(k, T.KINDS["general"])["label"], "minutes": m} for k, m in sorted(by_kind.items(), key=lambda kv: -kv[1])]
    ratios = [o["actual_minutes"] / o["raw_minutes"] for o in outcomes if o.get("raw_minutes")]
    on_time = round(sum(1 for t in done_tasks if _dt(t["completed_at"]) <= _dt(t["deadline"])) / len(done_tasks), 2) if done_tasks else None
    active_days = {s["_day"] for s in sess} | {_d(t["completed_at"], tz) for t in done_tasks}
    streak, d = 0, today if today in active_days else today - timedelta(days=1)
    while d in active_days:
        streak += 1
        d -= timedelta(days=1)
    events = []
    for s in sess:
        events.append({"when": s["created_at"] if isinstance(s["created_at"], str) else s["created_at"].isoformat(), "type": "session",
                       "text": f"{s['actual_minutes']} min of {T.KINDS.get(s['kind'], T.KINDS['general'])['label'].lower()}" + ("" if s["completed"] else " (stopped early)"),
                       "task_id": s.get("task_id")})
    for t in done_tasks:
        events.append({"when": t["completed_at"] if isinstance(t["completed_at"], str) else t["completed_at"].isoformat(), "type": "task",
                       "text": f"Finished “{t['title']}”", "task_id": t["id"]})
    events.sort(key=lambda e: e["when"], reverse=True)
    overdue = [t for t in pending if _dt(t["deadline"]) < now]
    soon = [t for t in pending if now <= _dt(t["deadline"]) <= now + timedelta(days=7)]
    wb = sorted(wellbeing, key=lambda w: w["created_at"], reverse=True)
    extra = _extras(now, tz, today, tasks, sess, done_tasks, pending, plan_sessions, subject_of or {}, mood_log or [], streak, goal_hours)
    return {
        **extra,
        "has_data": bool(sess or done_tasks or checkins),
        "totals": {"pending": len(pending), "completed": len(done_tasks), "overdue": len(overdue), "due_next_7_days": len(soon),
                   "all_time_minutes": sum(s["actual_minutes"] for s in sess), "all_time_sessions": len(sess)},
        "week": week, "daily": daily, "energy": energy, "by_kind": kinds, "streak_days": streak,
        "on_time_rate": on_time, "estimate_accuracy": ({"ratio": round(median(ratios), 2), "tasks": len(ratios)} if ratios else None),
        "wellbeing_latest": ({"label": wb[0]["label"], "when": wb[0]["created_at"] if isinstance(wb[0]["created_at"], str) else wb[0]["created_at"].isoformat()} if wb else None),
        "recent": events[:20],
    }


def review_stats(summary: dict) -> dict:
    """The few numbers the weekly review may talk about (and the language model may quote)."""
    w = summary["week"]
    acc = summary.get("estimate_accuracy")
    return {"week_start": w["start"], "minutes_studied": w["minutes_studied"], "sessions": w["sessions"], "tasks_completed": w["tasks_completed"],
            "completion_rate": w["completion_rate"], "avg_focus": w["avg_focus"], "plan_adherence": w["plan_adherence"],
            "goal_hours": w["goal_hours"], "prev_week_minutes": w["prev_week_minutes"], "streak_days": summary["streak_days"],
            "estimate_ratio": acc["ratio"] if acc else None, "overdue": summary["totals"]["overdue"], "pending": summary["totals"]["pending"]}


# ---------------------------------------------------------------- the richer dashboard (all from real records)
def _extras(now, tz, today, tasks, sess, done_tasks, pending, plan_sessions, subject_of, mood_log, streak, goal_hours) -> dict:
    sub = lambda t: subject_of.get(t["id"]) or t.get("subject") or "My other tasks"
    # --- today
    todays = [s for s in sess if s["_day"] == today]
    planned_today = [p for p in plan_sessions if str(p["day"])[:10] == today.isoformat()]
    today_view = {"studied_minutes": sum(s["actual_minutes"] for s in todays), "sessions_logged": len(todays),
                  "planned_minutes": sum(p["minutes"] for p in planned_today), "planned_blocks": len(planned_today),
                  "blocks_done": sum(1 for p in planned_today if p["status"] == "done")}
    # --- month
    first = today.replace(day=1)
    month_min = sum(s["actual_minutes"] for s in sess if s["_day"] >= first)
    month = {"label": today.strftime("%B %Y"), "minutes_studied": month_min, "hours": round(month_min / 60, 1),
             "days_studied": len({s["_day"] for s in sess if s["_day"] >= first})}
    # --- next deadline
    nxt = None
    upcoming = sorted((t for t in pending if _dt(t["deadline"]) >= now), key=lambda t: _dt(t["deadline"]))
    if upcoming:
        t = upcoming[0]
        nxt = {"title": t["title"], "subject": sub(t), "deadline": _dt(t["deadline"]).isoformat(),
               "days_left": max(0, (_d(t["deadline"], tz) - today).days)}
    # --- subjects
    names = {}
    for t in tasks:
        names.setdefault(sub(t), []).append(t)
    minutes_by_task = {}
    for s in sess:
        if s.get("task_id"):
            minutes_by_task[s["task_id"]] = minutes_by_task.get(s["task_id"], 0) + s["actual_minutes"]
    subjects = []
    for name, ts in names.items():
        done = sum(1 for t in ts if t["status"] == "completed")
        pend = sorted((t for t in ts if t["status"] == "pending"), key=lambda t: _dt(t["deadline"]))
        subjects.append({"subject": name, "topics": len(ts), "completed": done, "pending": len(pend),
                         "percent": round(100 * done / len(ts)) if ts else 0,
                         "minutes_studied": sum(minutes_by_task.get(t["id"], 0) for t in ts),
                         "next_deadline": _dt(pend[0]["deadline"]).isoformat() if pend else None,
                         "next_topic": pend[0]["title"] if pend else None})
    subjects.sort(key=lambda x: (x["pending"] == 0, x["next_deadline"] or "9999"))
    # --- feelings (the daily check-in)
    moods = sorted(mood_log, key=lambda m: m.get("date", ""))[-14:]
    mood_counts = {}
    for m in moods:
        if m.get("mood"):
            mood_counts[m["mood"]] = mood_counts.get(m["mood"], 0) + 1
    # --- insights: only said when the records really support them
    insights = []
    if sess:
        parts = {"morning": range(5, 12), "afternoon": range(12, 17), "evening": range(17, 22), "night": list(range(22, 24)) + list(range(0, 5))}
        score = {}
        for s in sess:
            ca = _dt(s["created_at"])
            if ca.tzinfo is None:
                ca = ca.replace(tzinfo=timezone.utc)
            h = ca.astimezone(tz).hour
            for k, r in parts.items():
                if h in r:
                    score.setdefault(k, []).append(s["focus"] if s.get("focus") else (4 if s["completed"] else 2))
        ranked = sorted(((sum(v) / len(v), len(v), k) for k, v in score.items() if len(v) >= 3), reverse=True)
        if ranked:
            insights.append(f"You seem to focus best in the {ranked[0][2]} (from {ranked[0][1]} sessions).")
        top = sorted(subjects, key=lambda x: -x["minutes_studied"])
        if top and top[0]["minutes_studied"] > 0 and len(subjects) > 1:
            insights.append(f"You have spent the most time on {top[0]['subject']} ({round(top[0]['minutes_studied'] / 60, 1)} hours).")
        short = [x for x in subjects if x["pending"] and x["minutes_studied"] == 0 and x["topics"] > 0]
        if short and len(subjects) > 1:
            insights.append(f"You have not studied {short[0]['subject']} yet; its next deadline is the thing to watch.")
    low_e = [m for m in moods if m.get("energy") == "low"]
    if len(moods) >= 4 and len(low_e) >= 3:
        insights.append("Your energy was low on several recent days. Shorter blocks and earlier rest may help.")
    high_s = [m for m in moods if m.get("stress") == "high"]
    if len(moods) >= 4 and len(high_s) >= 3:
        insights.append("You reported high stress on several days. It is a good time to look at the plan’s lighter options.")
    # --- achievements: milestones that are true in the records
    ach = []
    def add(key, title, text, earned):
        ach.append({"id": key, "title": title, "text": text, "earned": bool(earned)})
    total_min = sum(s["actual_minutes"] for s in sess)
    add("first_session", "First study session", "You logged your first study session.", len(sess) >= 1)
    add("streak_3", "3-day streak", "You studied three days in a row.", streak >= 3)
    add("streak_7", "7-day streak", "A whole week of studying.", streak >= 7)
    add("hours_10", "10 hours studied", "Ten hours of focused study logged.", total_min >= 600)
    add("topic_1", "First topic finished", "You finished your first topic.", len(done_tasks) >= 1)
    add("topics_5", "5 topics finished", "Five topics finished.", len(done_tasks) >= 5)
    add("on_time", "On time", "You finished a topic before its deadline.", any(_dt(t["completed_at"]) <= _dt(t["deadline"]) for t in done_tasks))
    if goal_hours:
        add("weekly_goal", "Weekly goal reached", f"You reached your {goal_hours:g}-hour weekly goal.",
            sum(s["actual_minutes"] for s in sess if _mon(today) <= s["_day"] <= today) >= goal_hours * 60)
    return {"today": today_view, "month": month, "next_deadline": nxt, "subjects": subjects, "moods": moods,
            "mood_counts": mood_counts, "insights": insights, "achievements": ach}
