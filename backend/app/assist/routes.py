"""
HTTP API of the connected planner.

  Signed-in students (data in PostgreSQL):  /assist/*   plus /settings and /profile (app/assist/prefs.py)
  Guests (stateless twin, nothing stored):  /demo/assist/*   - the browser sends its own state, the same pure code answers

Slow or optional things (the language model) never block the deterministic parts: /assist/evaluate and /assist/state answer
from rules in milliseconds; /assist/understand, /assist/explain, /assist/ask and /assist/review may use the model and always
fall back to rules, saying which one wrote the text.
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import service as ai
from app.auth import get_current_user
from app.database import get_db
from app.models import EnergyCheckin, SessionLog, Task, TaskOutcome, TaskStatus, User
from app.ratelimit import LoginRateLimiter

from . import core as C
from . import localai, store, summary as SUM
from .models import AiUsage, PlanSession, ReminderLog, TaskMeta, TaskSession, UserProfile, UserSettings, WeeklyReview
from . import formplan as FP
from . import guidance as GD
from .requests import (aware, AskIn, EvaluateIn, GuestAskIn, GuestDashboardIn, GuestEvaluateIn, GuestPlanFormIn, GuestReplanIn, GuestState,
                       GuestUnderstandIn, ReplanApplyIn, SessionFeedbackIn, TaskPlanPatch, UnderstandIn, guest_core)
from .settings_schema import StudyProfile, settings_from

router = APIRouter(prefix="/assist", tags=["assist (connected planner)"])
demo_router = APIRouter(prefix="/demo/assist", tags=["assist (guest mode)"])

_limit = LoginRateLimiter(max_failures=60, window_seconds=600)       # per student, all assist calls that may use the model
_guest_limit = LoginRateLimiter(max_failures=40, window_seconds=600)         # per IP, calls that may reach a language model
# Pure calculation calls (plan, check, dashboard) cost no money, but they carry a bounded request body and use CPU, so they get a
# larger separate allowance. They must not share the model bucket: the browser makes a few of them on every page view.
_guest_calc_limit = LoginRateLimiter(max_failures=600, window_seconds=600)


def _rate(key: str, limiter: LoginRateLimiter = _limit) -> None:
    wait = limiter.retry_after(key)
    if wait:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests. Please wait a moment.", headers={"Retry-After": str(wait)})
    limiter.record_failure(key)


def _guest_rate(request: Request, calc_only: bool = False) -> str:
    ip = request.client.host if request.client else "unknown"
    _rate("g|" + ip, _guest_calc_limit if calc_only else _guest_limit)
    return ip


def _ai_meta(meta: dict) -> dict:
    return {"source": meta["source"], "reason": meta["reason"], "model": meta["model"], "flagged": meta["flagged"]}


# ---------------------------------------------------------------- shared builders (pure)
def _task_card(row: C.TaskRow, core: C.CoreInput) -> dict:
    m = C.ensure_meta(row, core) if row.status == "pending" else (row.meta or None)
    out = {"id": row.id, "title": row.title, "description": row.description, "category": row.category, "difficulty": row.difficulty,
           "deadline": row.deadline.isoformat(), "status": row.status, "completed_at": row.completed_at.isoformat() if row.completed_at else None,
           "meta": None, "remaining_minutes": None}
    if m:
        rem, _ = C.remaining_of(m)
        out["meta"] = {k: m.get(k) for k in ("kind", "kind_label", "intrinsic", "personal", "low", "likely", "high", "done", "source", "priority",
                                            "confidence", "difficulty_label", "stages", "uncertainty", "difficulty_text", "workload_text",
                                            "understanding", "uncertainties", "basis", "size", "skill_kind", "raw_likely", "topic_id", "subject", "task_type",
                                            "progress", "grasp")}
        out["remaining_minutes"] = rem if row.status == "pending" else 0
    return out


def build_report(core: C.CoreInput, res: dict) -> dict:
    f = res["feasibility"]
    tasks = []
    for tid, v in res["tasks"].items():
        row, m = res["_rows"][tid], res["_metas"][tid]
        rem, rem_high = C.remaining_of(m)
        tasks.append({"id": tid, "title": row.title, "kind": m["kind"], "kind_label": m.get("kind_label", m["kind"]),
                      "deadline": row.deadline.isoformat(), "status": v["status"], "finish_date": v["finish_date"], "slack_days": v["slack_days"],
                      "first_day": v["first_day"], "unscheduled": v["unscheduled"], "flag": v["flag"],
                      "difficulty": {"intrinsic": m["intrinsic"], "personal": m["personal"], "label": m.get("difficulty_label"), "text": m.get("difficulty_text")},
                      "workload": {"low": m["low"], "likely": m["likely"], "high": m["high"], "remaining": rem, "remaining_high": rem_high,
                                   "done": m.get("done", 0), "confidence": m.get("confidence"), "text": m.get("workload_text")},
                      "steps": [{"label": s["label"], "method": s["method"], "minutes": s["minutes"]} for s in P_stages(m, rem)],
                      "uncertainties": m.get("uncertainties", []), "understanding": m.get("understanding"), "source": m.get("source"),
                      "priority": m.get("priority", 2), "draft": tid.startswith("draft:")})
    facts = C.plan_facts(core, res)
    narrative = dict(localai.narrate_local(facts), source="local", reason=None, model=None)
    assumptions = [f"Study time: {core.settings.weekday_minutes} min on weekdays, {core.settings.weekend_minutes} min at weekends (Settings).",
                   "Estimates come from the words you gave, the kind of work and your own history. I have not read any course material."]
    if core.energy is None:
        assumptions.append("You have not checked in today, so I assumed normal energy.")
    n_hist = len(core.outcomes)
    assumptions.append(f"Your history: {n_hist} finished task{'s' if n_hist != 1 else ''} with a logged duration." + ("" if n_hist >= 5 else " That is still too few to adjust the estimates much."))
    return {"verdict": {"level": f["level"], "feasible": f["feasible"], "shortfall_minutes": f["shortfall_minutes"], "load_ratio": f["load_ratio"],
                        "critical_task": f["critical_task"], "fits_at_high": f["fits_at_high"], "high_shortfall": f["high_shortfall"],
                        "buffer_used": f["buffer_used"], "total_minutes": f["total_minutes"], "capacity_minutes": f["capacity_minutes"]},
            "narrative": narrative, "tasks": tasks, "schedule": {"days": res["days"], "notes": res["notes"], "gentle": res["gentle"], "pacing": res.get("pacing")},
            "alternatives": res["alternatives"], "milestones": res["milestones"], "explain_steps": C.explain_steps(core, res),
            "assumptions": assumptions, "today": res["today"],
            "limits": "This is a planning aid, not a promise. Estimates can be wrong, and nothing here is advice about your health.",
            "facts": facts}


def P_stages(meta: dict, rem: int) -> list:
    from .profile import stages_after
    return stages_after(meta["stages"], int(meta.get("done", 0)), rem)


def _missing(drafts: list) -> list:
    return [d.ref for d in drafts if d.deadline_date is None]


def _evaluate(core: C.CoreInput, body: EvaluateIn) -> dict:
    drafts = [d.to_core() for d in body.drafts]
    miss = _missing(drafts)
    if miss:
        return {"status": "needs_info", "missing_deadline": miss, "message": "Each new task needs a deadline before I can plan it."}
    res = C.plan_for(core, drafts, today_minutes=body.today_minutes)
    report = build_report(core, res)
    metas = {tid: {k: v for k, v in m.items()} for tid, m in res["_metas"].items()}
    return {"status": "ok", "report": report, "metas": metas}


async def _understand(core_settings, today: date, tz: str, body: UnderstandIn, actx: ai.AICtx, skills, outcomes) -> dict:
    fields = body.fields
    fdict = {k: (v.isoformat() if isinstance(v, date) else v) for k, v in fields.model_dump().items() if v is not None}
    text = body.text or (fields.title or "")
    if not text.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Please describe what you need to get done.")
    data, meta = await ai.understand(actx, text, today=today, weekday=today.strftime("%A"), tz=tz, fields=fdict)
    local = localai.understand_local(text, fields.model_dump(), today)
    if data is None:
        tasks, questions, summary = local["tasks"], local["questions"], local["summary"]
    else:
        tasks, questions, summary = data["tasks"], [dict(q, type="text", options=[], placeholder="") for q in data["questions"]], data["summary"]
        # a structured field the student filled in always beats the model's guess
        if tasks:
            t0 = tasks[0]
            if fields.title:
                t0["title"] = fields.title
            if fields.deadline_date:
                t0["deadline_date"], t0["deadline_hour"] = fields.deadline_date, fields.deadline_hour
            if fields.kind:
                t0["kind"] = fields.kind
            if fields.felt_hard:
                t0["felt_hard"] = fields.felt_hard
            if fields.size:
                t0["size"] = fields.size
        if not questions:
            questions = local["questions"] if (local["questions"] and not tasks[0]["subtasks"]) else []
    out_tasks = []
    for i, t in enumerate(tasks):
        out_tasks.append({"ref": f"d{i + 1}", "title": t["title"], "details": t.get("details", ""), "kind": t.get("kind"),
                          "deadline_date": t["deadline_date"].isoformat() if t.get("deadline_date") else None, "deadline_hour": t.get("deadline_hour"),
                          "size": t.get("size"), "felt_hard": t.get("felt_hard"),
                          "ai_estimate": ({"low": t["low"], "likely": t["likely"], "high": t["high"]} if t.get("likely") else None),
                          "subtasks": t.get("subtasks", [])})
    return {"tasks": out_tasks, "questions": questions, "summary": summary, "ai": _ai_meta(meta)}


async def _explain(core: C.CoreInput, actx: ai.AICtx) -> dict:
    res = C.plan_for(core, alternatives=True)
    facts = C.plan_facts(core, res)
    if facts["level"] == "empty":
        return {"narrative": dict(localai.narrate_local(facts), source="local", reason="nothing_to_plan", model=None), "steps": []}
    data, meta = await ai.narrate(actx, facts)
    narr = data if data is not None else localai.narrate_local(facts)
    return {"narrative": dict(narr, source=meta["source"], reason=meta["reason"], model=meta["model"]), "steps": C.explain_steps(core, res)}


async def _ask(core: C.CoreInput, question: str, actx: ai.AICtx) -> dict:
    res = C.plan_for(core, alternatives=True)
    facts = C.plan_facts(core, res)
    data, meta = await ai.answer(actx, question, facts)
    out = data if data is not None else localai.answer_local(question, facts)
    return dict(out, ai=_ai_meta(meta))


def _subject_of(core: C.CoreInput) -> dict:
    return {r.id: (r.meta or {}).get("subject") for r in core.tasks if (r.meta or {}).get("subject")}


def _summary_inputs_guest(state: GuestState, core: C.CoreInput) -> dict:
    tasks = [{"id": t.id, "title": t.title, "status": t.status, "deadline": aware(t.deadline, C.tz_of(core.settings)).isoformat(),
              "completed_at": t.completed_at.isoformat() if t.completed_at else None} for t in state.tasks]
    ts = [dict(s.model_dump(), created_at=s.created_at.isoformat()) for s in state.task_sessions]
    ch = [{"energy_level": c.energy_level, "created_at": c.created_at.isoformat()} for c in state.checkins]
    wb = [{"label": w.label, "created_at": w.created_at.isoformat()} for w in state.wellbeing]
    outs = [{"kind": o.kind, "raw_minutes": o.raw_minutes, "actual_minutes": o.actual_minutes} for o in state.history.outcomes]
    ps = [{"day": p.day.isoformat(), "minutes": p.minutes, "status": p.status, "task_id": p.task_id} for p in state.plan_sessions]
    return dict(now=core.now, tz=C.tz_of(core.settings), tasks=tasks, task_sessions=ts, checkins=ch, wellbeing=wb, outcomes=outs, plan_sessions=ps,
                goal_hours=core.profile.weekly_goal_hours, subject_of=_subject_of(core), mood_log=core.profile.mood_log)


# ================================================================= signed-in students
@router.get("/state")
async def state(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    core = await store.load_core(db, user)
    await store.persist_missing_meta(db, user, core)
    by_id = {r.id: r for r in core.tasks}
    plan = await store.plan_view(db, user.id, {k: v for k, v in by_id.items()}, core.now.date())
    past, fut = await store.plan_sessions_for_check(db, user.id, core.now.date())
    check = C.replan_check(core, ({"inputs": plan["inputs"], "future": fut} if plan else None), past)
    replan = None
    if check["needed"]:
        prop = C.public_result(check["proposal"])
        replan = {"reasons": check["reasons"], "changes": check["changes"], "unplanned": check["unplanned"],
                  "proposal": {"feasibility": prop["feasibility"], "days": prop["days"][:14], "alternatives": prop["alternatives"], "notes": prop["notes"]}}
    elif check.get("unplanned"):
        replan = {"reasons": [{"code": "tasks", "text": f"{check['unplanned']} task{'s' if check['unplanned'] != 1 else ''} not in a plan yet."}], "changes": [],
                  "unplanned": check["unplanned"], "proposal": None}
    ctx = ai.AICtx(db=db, user_id=user.id, student_allows=core.settings.ai_assist)
    return {"now": core.now.isoformat(), "today": core.now.date().isoformat(), "energy": core.energy, "stress": core.stress,
            "settings": core.settings.model_dump(), "tasks": [_task_card(r, core) for r in core.tasks], "plan": plan, "replan": replan,
            "ai": await ai.status(ctx), "studied_today": core.studied_today,
            "pending_without_plan": check.get("unplanned", 0) if not plan else 0}


@router.post("/understand")
async def understand(body: UnderstandIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    _rate(str(user.id))
    st = await store.get_settings(db, user.id)
    core = await store.load_core(db, user, settings=st)
    actx = ai.AICtx(db=db, user_id=user.id, student_allows=st.ai_assist)
    return await _understand(st, core.now.date(), st.timezone, body, actx, core.skills, core.outcomes)


@router.post("/evaluate")
async def evaluate(body: EvaluateIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    core = await store.load_core(db, user)
    await store.persist_missing_meta(db, user, core)
    return _evaluate(core, body)


@router.post("/accept")
async def accept(body: EvaluateIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    core = await store.load_core(db, user)
    await store.persist_missing_meta(db, user, core)
    drafts = [d.to_core() for d in body.drafts]
    if _missing(drafts):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Each new task needs a deadline.")
    res = C.plan_for(core, drafts, alternatives=False)
    created = 0
    for d in drafts:
        row, meta = res["_rows"][f"draft:{d.ref}"], res["_metas"][f"draft:{d.ref}"]
        task = Task(owner_id=user.id, title=row.title, description=row.description, category=row.category, difficulty=row.difficulty,
                    deadline=row.deadline.astimezone(timezone.utc))
        db.add(task)
        await db.flush()
        await store.save_meta(db, user.id, task.id, meta)
        core.tasks.append(C.TaskRow(id=str(task.id), title=row.title, deadline=row.deadline, description=row.description, category=row.category,
                                    difficulty=row.difficulty, created_at=core.now, meta=meta))
        created += 1
    await db.commit()
    final = C.plan_for(core, alternatives=True)             # the same input, now with real task ids
    plan = await store.store_plan(db, user, core, final, "new" if created else "manual")
    by_id = {r.id: r for r in core.tasks}
    view = await store.plan_view(db, user.id, by_id, core.now.date())
    return {"status": "ok", "created": created, "plan": view}


@router.get("/form")
async def get_form(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    """The Smart Planner form as it should look today: subjects and topics rebuilt from the saved tasks, plus what the student chose last time."""
    core = await store.load_core(db, user)
    await store.persist_missing_meta(db, user, core)
    return FP.form_from_state(core, core.profile.plan_form, core.profile.mood_log)


async def _apply_changes(db: AsyncSession, user: User, core: C.CoreInput, ch: FP.Changes) -> None:
    """Write what the form means. Every id is checked against the student's own tasks first; nothing else is touched."""
    now = datetime.now(timezone.utc)
    mine = {r.id for r in core.tasks}
    # settings
    if ch.settings_patch:
        cur = await store.get_settings(db, user.id)
        new = FP.apply_settings(cur, ch.settings_patch).model_dump()
        row = await db.get(UserSettings, user.id)
        if row is None:
            db.add(UserSettings(user_id=user.id, data=new))
        else:
            row.data = new
    # stored form and check-in
    prof = core.profile.model_dump()
    prof["plan_form"] = ch.stored_form
    if ch.mood_entry:
        prof["mood_log"] = [*prof.get("mood_log", []), ch.mood_entry]
    new_prof = StudyProfile(**prof).model_dump()
    prow = await db.get(UserProfile, user.id)
    if prow is None:
        db.add(UserProfile(user_id=user.id, data=new_prof))
    else:
        prow.data = new_prof
    if ch.energy_level:
        db.add(EnergyCheckin(user_id=user.id, energy_level=ch.energy_level))
    # tasks
    for c in ch.creates:
        task = Task(owner_id=user.id, title=c["title"], description=c["description"], category=c["category"], difficulty=c["difficulty"],
                    deadline=c["deadline"].astimezone(timezone.utc))
        if c.get("completed"):
            task.status = TaskStatus.completed
            task.completed_at = now
        db.add(task)
        await db.flush()
        await store.save_meta(db, user.id, task.id, c["meta"])
    for u in ch.updates:
        if u["task_id"] not in mine:
            continue
        task = await db.get(Task, uuid.UUID(u["task_id"]))
        if task is None or task.owner_id != user.id:
            continue
        f = u["fields"]
        task.title, task.description, task.category = f["title"], f["description"], f["category"]
        if "deadline" in f:
            task.deadline = f["deadline"].astimezone(timezone.utc)
        if "difficulty" in f:
            task.difficulty = f["difficulty"]
        if u.get("reopen"):
            task.status, task.completed_at = TaskStatus.pending, None
        if u["task_id"] in ch.complete:
            task.status, task.completed_at = TaskStatus.completed, now
        if u.get("meta"):
            await store.save_meta(db, user.id, task.id, u["meta"])
    for tid in ch.remove:
        if tid not in mine:
            continue
        uid = uuid.UUID(tid)
        await db.execute(delete(PlanSession).where(PlanSession.task_id == uid, PlanSession.user_id == user.id))
        await db.execute(delete(TaskMeta).where(TaskMeta.task_id == uid, TaskMeta.user_id == user.id))
        task = await db.get(Task, uid)
        if task is not None and task.owner_id == user.id:
            await db.delete(task)
    await db.commit()


@router.get("/guidance")
async def guidance(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    """Subject-specific study guidance for the student's open topics. Rule-written, works offline, labelled as such."""
    core = await store.load_core(db, user)
    return {"items": GD.guidance_for_core(core), "source": "rules", "note": GD.NOTE}


@router.post("/plan-form")
async def plan_form(body: FP.PlanFormIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    """ONE BUTTON. Save the form, work out the minutes, fit them into the student's time and store the plan. No language model is involved,
    so it answers in milliseconds and works offline. Missing key facts come back as at most three questions and nothing is saved."""
    core = await store.load_core(db, user)
    await store.persist_missing_meta(db, user, core)
    ch = FP.build_changes(core, body)
    if ch.questions:
        return {"status": "needs_info", "questions": ch.questions}
    await _apply_changes(db, user, core, ch)
    core = await store.load_core(db, user)
    res = C.plan_for(core, alternatives=True)
    if res["feasibility"]["level"] == "empty":
        return {"status": "ok", **ch.counts(), "report": build_report(core, res), "plan": None}
    reason = "new" if ch.creates else "manual"
    await store.store_plan(db, user, core, res, reason)
    view = await store.plan_view(db, user.id, {r.id: r for r in core.tasks}, core.now.date())
    return {"status": "ok", **ch.counts(), "report": build_report(core, res), "plan": view}


@router.post("/replan/apply")
async def replan_apply(body: ReplanApplyIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    core = await store.load_core(db, user)
    await store.persist_missing_meta(db, user, core)
    res = C.plan_for(core, alternatives=True)
    if res["feasibility"]["level"] == "empty":
        raise HTTPException(status.HTTP_409_CONFLICT, "There is nothing left to plan.")
    await store.store_plan(db, user, core, res, body.reason)
    by_id = {r.id: r for r in core.tasks}
    return {"status": "ok", "plan": await store.plan_view(db, user.id, by_id, core.now.date())}


@router.post("/session", status_code=status.HTTP_201_CREATED)
async def log_session(body: SessionFeedbackIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    core = await store.load_core(db, user)
    ps = None
    if body.plan_session_id:
        try:
            ps = await db.get(PlanSession, uuid.UUID(body.plan_session_id))
        except ValueError:
            ps = None
        if ps is None or ps.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Planned session not found")
    task = None
    tid = body.task_id or (str(ps.task_id) if ps and ps.task_id else None)
    if tid:
        try:
            task = await db.get(Task, uuid.UUID(tid))
        except ValueError:
            task = None
        if task is None or task.owner_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    learned, replan_hint = [], False
    meta = None
    if task is not None:
        row = next((r for r in core.tasks if r.id == str(task.id)), None)
        meta = C.ensure_meta(row, core) if row else None
    kind = meta["kind"] if meta else "general"
    if body.status == "skipped":
        if ps is not None:
            ps.status = "skipped"
        await db.commit()
        return {"saved": True, "learned": ["Skipped. Your plan keeps the work, so it may move to another day."], "replan_suggested": True, "remaining_minutes": None}
    actual = body.actual_minutes or body.planned_minutes or (ps.minutes if ps else 0)
    if actual < 1:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "How many minutes did you study?")
    completed = body.status == "done"
    if body.felt and not body.felt_difficulty:
        body.felt_difficulty = {"easy": 2, "okay": 3, "difficult": 4}[body.felt]
    db.add(TaskSession(user_id=user.id, task_id=task.id if task else None, plan_session_id=ps.id if ps else None, kind=kind,
                       planned_minutes=body.planned_minutes or (ps.minutes if ps else 0), actual_minutes=actual, completed=completed,
                       focus=body.focus, felt_difficulty=body.felt_difficulty, energy_after=body.energy_after, length_feel=body.length_feel))
    db.add(SessionLog(user_id=user.id, kind=kind, minutes=max(5, actual), completed=completed, focus=body.focus))
    if ps is not None:
        ps.status = "partial" if body.status == "partial" else "done"
        ps.actual_minutes = actual
        ps.completed_at = datetime.now(timezone.utc)
        ps.felt = body.felt
    remaining = None
    if meta is not None and task is not None:
        meta["done"] = int(meta.get("done", 0)) + actual
        if body.felt_difficulty:
            meta["personal"] = round(max(1.0, min(5.0, 0.8 * float(meta["personal"]) + 0.2 * body.felt_difficulty)), 2)
            learned.append(f"You rated this block {body.felt_difficulty} out of 5 for difficulty, so I moved this task's difficulty for you to {meta['personal']:.1f}.")
        if body.remaining_minutes is not None:
            C.apply_remaining(meta, body.remaining_minutes)
            learned.append("I used your own estimate of what is left.")
        if body.task_done:
            raw = int(meta.get("raw_likely") or meta["likely"])
            task.status = TaskStatus.completed
            task.completed_at = datetime.now(timezone.utc)
            total_actual = int(meta["done"]) + int(meta.get("actual_before", 0))
            db.add(TaskOutcome(user_id=user.id, kind=kind, raw_minutes=max(1, min(6000, raw)), actual_minutes=max(1, min(6000, total_actual)),
                               felt=body.felt_difficulty, predicted_personal=float(meta["personal"])))
            learned.append(f"Finished. It took about {total_actual} minutes in total; I will use that to calibrate future {meta.get('kind_label', kind).lower()} estimates.")
            remaining = 0
        else:
            remaining, _ = C.remaining_of(meta)
            if meta["done"] > meta["likely"] and body.remaining_minutes is None:
                replan_hint = True
                learned.append("This task is taking longer than estimated. Check the plan to see if it still fits.")
        await store.save_meta(db, user.id, task.id, meta)
    if body.length_feel in ("short", "long"):
        learned.append(f"Noted that this block felt too {body.length_feel}. After a few similar answers I will change your block length for this kind of work.")
    if body.energy_after and body.energy_after <= 2:
        replan_hint = True
        learned.append("Your energy is low after this block. A lighter plan may help.")
    await db.commit()
    return {"saved": True, "learned": learned, "remaining_minutes": remaining, "replan_suggested": replan_hint,
            "task_completed": bool(body.task_done and task is not None)}


@router.patch("/tasks/{task_id}")
async def patch_task_plan(task_id: uuid.UUID, body: TaskPlanPatch, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    task = await db.get(Task, task_id)
    if task is None or task.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    core = await store.load_core(db, user)
    row = next(r for r in core.tasks if r.id == str(task_id))
    meta = C.ensure_meta(row, core)
    if body.priority is not None:
        meta["priority"] = body.priority
    if body.remaining_minutes is not None:
        C.apply_remaining(meta, body.remaining_minutes)
    await store.save_meta(db, user.id, task_id, meta)
    await db.commit()
    return {"saved": True, "remaining_minutes": C.remaining_of(meta)[0], "priority": meta["priority"]}


@router.post("/explain")
async def explain(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    _rate(str(user.id))
    st = await store.get_settings(db, user.id)
    core = await store.load_core(db, user, settings=st)
    await store.persist_missing_meta(db, user, core)
    return await _explain(core, ai.AICtx(db=db, user_id=user.id, student_allows=st.ai_assist))


@router.post("/ask")
async def ask(body: AskIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    _rate(str(user.id))
    st = await store.get_settings(db, user.id)
    core = await store.load_core(db, user, settings=st)
    await store.persist_missing_meta(db, user, core)
    return await _ask(core, body.question, ai.AICtx(db=db, user_id=user.id, student_allows=st.ai_assist))


async def _dashboard_inputs(db: AsyncSession, user: User, core: C.CoreInput) -> dict:
    from app.models import EnergyCheckin, WellbeingCheck
    tasks = [{"id": r.id, "title": r.title, "status": r.status, "deadline": r.deadline.isoformat(),
              "completed_at": r.completed_at.isoformat() if r.completed_at else None} for r in core.tasks]
    ts = (await db.scalars(select(TaskSession).where(TaskSession.user_id == user.id).order_by(TaskSession.created_at.desc()).limit(500))).all()
    ch = (await db.scalars(select(EnergyCheckin).where(EnergyCheckin.user_id == user.id).order_by(EnergyCheckin.created_at.desc()).limit(200))).all()
    wb = (await db.scalars(select(WellbeingCheck).where(WellbeingCheck.user_id == user.id).order_by(WellbeingCheck.created_at.desc()).limit(10))).all()
    since = core.now.date() - timedelta(days=21)
    ps = (await db.scalars(select(PlanSession).where(PlanSession.user_id == user.id, PlanSession.day >= since))).all()
    return dict(now=core.now, tz=C.tz_of(core.settings), tasks=tasks,
                task_sessions=[{"task_id": str(s.task_id) if s.task_id else None, "kind": s.kind, "planned_minutes": s.planned_minutes, "actual_minutes": s.actual_minutes,
                                "completed": s.completed, "focus": s.focus, "felt_difficulty": s.felt_difficulty, "created_at": s.created_at} for s in ts],
                checkins=[{"energy_level": c.energy_level, "created_at": c.created_at} for c in ch],
                wellbeing=[{"label": w.risk_label, "created_at": w.created_at} for w in wb],
                outcomes=[{"kind": o.kind, "raw_minutes": o.raw_minutes, "actual_minutes": o.actual_minutes} for o in core.outcomes],
                plan_sessions=[{"day": p.day.isoformat(), "minutes": p.minutes, "status": p.status, "task_id": str(p.task_id) if p.task_id else None} for p in ps],
                goal_hours=core.profile.weekly_goal_hours, subject_of=_subject_of(core), mood_log=core.profile.mood_log)


@router.get("/dashboard")
async def dashboard(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    core = await store.load_core(db, user)
    s = SUM.summarize(**(await _dashboard_inputs(db, user, core)))
    wk = date.fromisoformat(s["week"]["start"])
    cached = await db.scalar(select(WeeklyReview).where(WeeklyReview.user_id == user.id, WeeklyReview.week_start == wk))
    review = None
    if cached is not None:
        import json
        try:
            review = dict(json.loads(cached.text), source=cached.source, created_at=cached.created_at.isoformat())
        except ValueError:
            review = None
    return {"summary": s, "review": review, "ai": await ai.status(ai.AICtx(db=db, user_id=user.id, student_allows=core.settings.ai_assist))}


@router.post("/review")
async def make_review(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    import json
    _rate(str(user.id))
    core = await store.load_core(db, user)
    s = SUM.summarize(**(await _dashboard_inputs(db, user, core)))
    stats = SUM.review_stats(s)
    data, meta = await ai.review(ai.AICtx(db=db, user_id=user.id, student_allows=core.settings.ai_assist), stats)
    out = data if data is not None else localai.review_local(stats)
    wk = date.fromisoformat(s["week"]["start"])
    row = await db.scalar(select(WeeklyReview).where(WeeklyReview.user_id == user.id, WeeklyReview.week_start == wk))
    text = json.dumps(out, ensure_ascii=False)
    if row is None:
        db.add(WeeklyReview(user_id=user.id, week_start=wk, stats=stats, text=text, source="ai" if meta["source"] == "ai" else "local"))
    else:
        row.stats, row.text, row.source = stats, text, ("ai" if meta["source"] == "ai" else "local")
    await db.commit()
    return dict(out, source=meta["source"], reason=meta["reason"], stats=stats)


@router.get("/usage")
async def usage(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    st = await store.get_settings(db, user.id)
    out = await ai.status(ai.AICtx(db=db, user_id=user.id, student_allows=st.ai_assist))
    rows = (await db.scalars(select(AiUsage).where(AiUsage.user_id == user.id).order_by(AiUsage.created_at.desc()).limit(10))).all()
    out["recent"] = [{"purpose": r.purpose, "outcome": r.outcome, "tokens": r.input_tokens + r.output_tokens, "cost_usd": r.cost_usd,
                      "latency_ms": r.latency_ms, "when": r.created_at.isoformat()} for r in rows]
    out["month_total_usd"] = round(float(sum(r.cost_usd for r in rows)), 6) if rows else 0.0
    return out


@router.get("/reminders")
async def reminder_history(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    rows = (await db.scalars(select(ReminderLog).where(ReminderLog.user_id == user.id).order_by(ReminderLog.created_at.desc()).limit(20))).all()
    return {"items": [{"kind": r.kind, "status": r.status, "detail": r.detail, "attempts": r.attempts, "when": r.created_at.isoformat()} for r in rows]}


# ================================================================= guests (stateless)
def _changes_json(ch: FP.Changes) -> dict:
    """The guest's browser applies these to its own storage; ids and datetimes become plain JSON."""
    iso = lambda dt: dt.isoformat()
    return {"creates": [dict(c, deadline=iso(c["deadline"])) for c in ch.creates],
            "updates": [dict(u, fields={k: (iso(v) if hasattr(v, "isoformat") else v) for k, v in u["fields"].items()}) for u in ch.updates],
            "complete": ch.complete, "remove": ch.remove, "settings_patch": ch.settings_patch, "stored_form": ch.stored_form,
            "mood_entry": ch.mood_entry, "energy_level": ch.energy_level, "today_minutes": ch.today_minutes, "counts": ch.counts()}


@demo_router.post("/form")
async def demo_form(body: GuestReplanIn, request: Request) -> dict:
    _guest_rate(request, calc_only=True)
    core = guest_core(body.state)
    return FP.form_from_state(core, core.profile.plan_form, core.profile.mood_log)


@demo_router.post("/guidance")
async def demo_guidance(body: GuestReplanIn, request: Request) -> dict:
    _guest_rate(request, calc_only=True)
    return {"items": GD.guidance_for_core(guest_core(body.state)), "source": "rules", "note": GD.NOTE}


@demo_router.post("/plan-form")
async def demo_plan_form(body: GuestPlanFormIn, request: Request) -> dict:
    """The guest twin of /assist/plan-form: it only works out the changes; the browser stores them and then asks for the plan."""
    _guest_rate(request, calc_only=True)
    core = guest_core(body.state)
    ch = FP.build_changes(core, body.form)
    if ch.questions:
        return {"status": "needs_info", "questions": ch.questions}
    return {"status": "ok", "changes": _changes_json(ch)}


@demo_router.post("/understand")
async def demo_understand(body: GuestUnderstandIn, request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    ip = _guest_rate(request)
    st = settings_from(body.settings)
    actx = ai.AICtx(db=db, user_id=None, guest=True, ip=ip, student_allows=st.ai_assist)
    return await _understand(st, body.today, body.time_zone, UnderstandIn(text=body.text, fields=body.fields), actx, {}, [])


@demo_router.post("/evaluate")
async def demo_evaluate(body: GuestEvaluateIn, request: Request) -> dict:
    _guest_rate(request, calc_only=True)
    return _evaluate(guest_core(body.state), body)


@demo_router.post("/replan-check")
async def demo_replan_check(body: GuestReplanIn, request: Request) -> dict:
    _guest_rate(request, calc_only=True)
    core = guest_core(body.state)
    ap = body.state.active_plan
    active = {"inputs": ap.inputs, "future": [p.model_dump(mode="json") for p in ap.future]} if ap else None
    past = [{"day": p.day.isoformat(), "task_id": p.task_id, "minutes": p.minutes, "status": p.status} for p in (ap.past if ap else [])]
    chk = C.replan_check(core, active, past)
    if chk["proposal"] is not None:
        chk = dict(chk, proposal=C.public_result(chk["proposal"]))
    return chk


@demo_router.post("/plan")
async def demo_plan(body: GuestReplanIn, request: Request) -> dict:
    """Plan all of a guest's pending tasks. Returns the plan plus the snapshot the browser must keep for later checks."""
    _guest_rate(request, calc_only=True)
    core = guest_core(body.state)
    res = C.plan_for(core, alternatives=True)
    metas = {tid: m for tid, m in res["_metas"].items()}
    return {"report": build_report(core, res), "metas": metas, "snapshot": C.snapshot(core, res) if res["feasibility"]["level"] != "empty" else None,
            "plan": dict(C.public_result(res), explain=C.explain_steps(core, res))}


@demo_router.post("/explain")
async def demo_explain(body: GuestReplanIn, request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    ip = _guest_rate(request)
    core = guest_core(body.state)
    return await _explain(core, ai.AICtx(db=db, user_id=None, guest=True, ip=ip, student_allows=core.settings.ai_assist))


@demo_router.post("/ask")
async def demo_ask(body: GuestAskIn, request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    ip = _guest_rate(request)
    core = guest_core(body.state)
    return await _ask(core, body.question, ai.AICtx(db=db, user_id=None, guest=True, ip=ip, student_allows=core.settings.ai_assist))


@demo_router.post("/dashboard")
async def demo_dashboard(body: GuestDashboardIn, request: Request) -> dict:
    _guest_rate(request, calc_only=True)
    core = guest_core(body.state)
    return {"summary": SUM.summarize(**_summary_inputs_guest(body.state, core)), "review": None}


@demo_router.post("/review")
async def demo_review(body: GuestDashboardIn, request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    ip = _guest_rate(request)
    core = guest_core(body.state)
    s = SUM.summarize(**_summary_inputs_guest(body.state, core))
    stats = SUM.review_stats(s)
    data, meta = await ai.review(ai.AICtx(db=db, user_id=None, guest=True, ip=ip, student_allows=core.settings.ai_assist), stats)
    out = data if data is not None else localai.review_local(stats)
    return dict(out, source=meta["source"], reason=meta["reason"], stats=stats)
