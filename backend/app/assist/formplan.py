"""
The Smart Planner form: subjects -> topics -> tasks.

One structured form replaces the "describe, understand, evaluate, accept" steps. Everything in this file is pure (no database, no
network, no clock: `now` comes from the core input), so the signed-in route and the guest twin share it:

    form_from_state(core)          the form as it should look when the student comes back (rebuilt from saved tasks + stored form)
    build_changes(core, form)      what saving the form means: new tasks, updated tasks, finished tasks, removed tasks, settings

A topic IS a task. The student's subject is the task's category; everything the form knows beyond the task (type, progress choice,
understanding, follow-up answers) is kept next to the task's planning facts in its meta, so there is one source of truth and the
other pages (Dashboard, Toolkit, Profile) read the same rows.

The language model plays no part here. Minutes, order and feasibility come from the existing deterministic engine.
"""
import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.ai.sanitize import clean_text

from . import core as C
from .settings_schema import (FOCUS_LEVELS, HELPS, LEVELS3, MOODS, OBSTACLES, MoodEntry, StoredForm, StudySettings)

TASK_TYPES = ("exam", "assignment", "project", "report", "presentation", "homework", "revision", "reading", "other")
TASK_TYPE_LABELS = {"exam": "Examination", "assignment": "Assignment", "project": "Programming project", "report": "Research report",
                    "presentation": "Presentation", "homework": "Homework", "revision": "Revision", "reading": "Reading", "other": "Other"}
PROGRESS = ("none", "some", "half", "most", "done")
PROGRESS_LABELS = {"none": "Not started", "some": "A little", "half": "Halfway", "most": "Almost finished", "done": "Finished"}
LARGE_TYPES = ("exam", "assignment", "project", "report", "presentation")        # types where "how much is finished?" changes the plan a lot
EXPERIENCE_TO_SKILL = {1: 1, 2: 2, 3: 3, 4: 5}                                     # Beginner / a little / intermediate / advanced -> engine skill 1-5
ENERGY_TO_LEVEL = {"low": 2, "medium": 3, "high": 4}                               # the 1-5 energy scale the rest of MindSync uses
MAX_TOPICS = 40
MAX_QUESTIONS = 3

YesNo = Literal["yes", "no", "partly"]


class TopicDetails(BaseModel):
    """Optional follow-up answers. Only the ones that belong to the chosen task type are ever shown."""
    model_config = ConfigDict(extra="forbid")
    features_left: Optional[int] = Field(default=None, ge=0, le=200)
    coding_started: Optional[YesNo] = None
    testing_done: Optional[YesNo] = None
    words_required: Optional[int] = Field(default=None, ge=50, le=50000)
    words_written: Optional[int] = Field(default=None, ge=0, le=50000)
    research_done: Optional[YesNo] = None
    chapters: Optional[int] = Field(default=None, ge=1, le=100)
    hard_topics: str = Field(default="", max_length=200)
    revision_started: Optional[YesNo] = None
    slides: Optional[int] = Field(default=None, ge=1, le=200)
    content_ready: Optional[YesNo] = None
    rehearsal_needed: Optional[Literal["yes", "no"]] = None
    questions: Optional[int] = Field(default=None, ge=1, le=500)
    pages: Optional[int] = Field(default=None, ge=1, le=2000)

    @field_validator("hard_topics")
    @classmethod
    def _t(cls, v: str) -> str:
        return clean_text(v, 200)


class TopicIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    task_id: Optional[str] = Field(default=None, max_length=64)            # the saved task this topic already is
    name: str = Field(min_length=1, max_length=120)
    type: Literal[TASK_TYPES] = "other"
    progress: Optional[Literal[PROGRESS]] = None                              # None = the student has not said yet
    difficulty: Optional[int] = Field(default=None, ge=1, le=5)               # 1 very easy ... 5 very difficult
    understanding: Optional[int] = Field(default=None, ge=1, le=4)            # 1 not yet ... 4 very well (self-reported)
    description: str = Field(default="", max_length=600)
    deadline: Optional[date] = None
    deadline_hour: Optional[int] = Field(default=None, ge=0, le=23)
    priority: int = Field(default=2, ge=1, le=3)
    details: TopicDetails = Field(default_factory=TopicDetails)
    status: Optional[Literal["pending", "completed"]] = None                # echoed back by GET /form; the server decides it, so it is ignored

    @field_validator("name", "description")
    @classmethod
    def _clean(cls, v: str) -> str:
        return clean_text(v, 600)

    @model_validator(mode="after")
    def _name_not_blank(self):
        if not self.name.strip():
            raise ValueError("Give every topic a name")
        return self


class SubjectIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=60)
    experience: Optional[int] = Field(default=None, ge=1, le=4)
    topics: list[TopicIn] = Field(default_factory=list, max_length=MAX_TOPICS)

    @field_validator("name")
    @classmethod
    def _n(cls, v: str) -> str:
        v = clean_text(v, 60)
        if not v.strip():
            raise ValueError("Give every subject a name")
        return v


class AvailabilityIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    daily_minutes: Optional[int] = Field(default=None, ge=15, le=720)
    day_minutes: Optional[dict[str, int]] = None                    # {"0": 90, ...} 0 = Monday; 0 minutes = not available
    preferred_time: Optional[Literal["morning", "afternoon", "evening", "night", "flexible"]] = None
    unavailable_periods: Optional[list[Literal["morning", "afternoon", "evening", "night"]]] = None


class FeelingsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mood: Optional[Literal[MOODS]] = None
    energy: Optional[Literal[LEVELS3]] = None
    stress: Optional[Literal[LEVELS3]] = None
    focus: Optional[Literal[FOCUS_LEVELS]] = None

    def any(self) -> bool:
        return any(v is not None for v in (self.mood, self.energy, self.stress, self.focus))


class PlanFormIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subjects: list[SubjectIn] = Field(default_factory=list, max_length=12)
    availability: AvailabilityIn = Field(default_factory=AvailabilityIn)
    experience: Optional[int] = Field(default=None, ge=1, le=4)
    obstacles: list[Literal[OBSTACLES]] = Field(default_factory=list, max_length=9)
    helps: list[Literal[HELPS]] = Field(default_factory=list, max_length=8)
    extra: str = Field(default="", max_length=600)
    feelings: FeelingsIn = Field(default_factory=FeelingsIn)
    today_minutes: Optional[int] = Field(default=None, ge=0, le=720)
    removed: list[str] = Field(default_factory=list, max_length=MAX_TOPICS)        # topic ids the student deleted

    @field_validator("extra")
    @classmethod
    def _e(cls, v: str) -> str:
        return clean_text(v, 600)

    @model_validator(mode="after")
    def _limits(self):
        topics = [t for s in self.subjects for t in s.topics]
        if len(topics) > MAX_TOPICS:
            raise ValueError(f"Please keep to {MAX_TOPICS} topics at a time")
        ids = [t.id for t in topics]
        if len(set(ids)) != len(ids):
            raise ValueError("Every topic needs its own id")
        if len({s.id for s in self.subjects}) != len(self.subjects):
            raise ValueError("Every subject needs its own id")
        return self


# ---------------------------------------------------------------- reading what the student chose
SUBJECT_HINTS = (
    ("mathematics", ("math", "maths", "calculus", "algebra", "statistics", "geometry", "trigonometry", "probability")),
    ("programming", ("python", "java", "javascript", "c++", "c#", "programming", "coding", "software", "web development", "computer science", "algorithms")),
    ("data", ("data science", "data analysis", "analytics", "machine learning", "databases", "database", "sql")),
    ("writing", ("english", "literature", "history", "philosophy", "law", "business", "management", "economics", "marketing", "sociology", "psychology")),
)


def _subject_kind(subject: str, name: str) -> Optional[str]:
    text = f"{subject} {name}".lower()
    for kind, words in SUBJECT_HINTS:
        if any(w in text for w in words):
            return kind
    return None


def kind_for(task_type: str, subject: str, name: str) -> Optional[str]:
    """The engine's kind of work for a topic. None lets the engine read the words itself."""
    if task_type == "exam" or task_type == "revision":
        return "exam"
    if task_type == "project":
        return "programming"
    if task_type == "report":
        return "writing"
    if task_type == "presentation":
        return "presentation"
    if task_type == "reading":
        return "reading"
    if task_type in ("assignment", "homework"):
        hint = _subject_kind(subject, name)
        return hint or ("general" if task_type == "homework" else None)
    return None


def _yn(v: Optional[str], yes: str, no: str, partly: str = "") -> str:
    return {"yes": yes, "no": no, "partly": partly or yes}.get(v or "", "")


def compose_details(t: TopicIn, subject: str) -> tuple:
    """(text for the engine, progress to give the engine). The follow-up answers become plain sentences the engine already understands.
    A count of what is LEFT (features, words still to write) replaces the percentage, so the same progress is never subtracted twice."""
    d = t.details
    parts = [t.description.strip()] if t.description.strip() else []
    progress = t.progress or "none"
    counted = False
    if t.type == "project":
        if d.features_left is not None:
            parts.append(f"{d.features_left} features left to build.")
            counted = True
        parts.append(_yn(d.coding_started, "Coding has started.", "Coding has not started yet.", "Coding is partly done."))
        parts.append(_yn(d.testing_done, "Testing is finished.", "Testing is not finished.", "Testing is partly done."))
    elif t.type == "report":
        if d.words_required is not None:
            left = max(0, d.words_required - (d.words_written or 0))
            parts.append(f"A report of {left} words still to write." if left else "All the words are written; checking and editing remain.")
            counted = left > 0
        parts.append(_yn(d.research_done, "Research is finished.", "Research is not finished.", "Research is partly done."))
    elif t.type in ("exam", "revision"):
        if d.chapters is not None:
            parts.append(f"{d.chapters} chapters to revise.")
            counted = True
        if d.hard_topics:
            parts.append(f"Difficult topics: {d.hard_topics}.")
        parts.append(_yn(d.revision_started, "Revision has started.", "Revision has not started.", "Revision is partly done."))
    elif t.type == "presentation":
        if d.slides is not None:
            parts.append(f"{d.slides} slides.")
        parts.append(_yn(d.content_ready, "The content is ready.", "The content is not prepared yet.", "The content is partly prepared."))
        parts.append(_yn(d.rehearsal_needed, "Rehearsal is needed.", "No rehearsal is needed."))
    elif t.type == "homework":
        if d.questions is not None:
            parts.append(f"{d.questions} questions.")
            counted = True
    elif t.type == "reading":
        if d.pages is not None:
            parts.append(f"{d.pages} pages to read.")
            counted = True
    if counted and progress in ("some", "half", "most"):
        progress = "none"
    return "\n".join(p for p in parts if p), progress


def topic_sig(t: TopicIn, subject: str, experience: Optional[int]) -> str:
    """What a new estimate depends on. When it is unchanged the stored estimate (and the student's own corrections to it) stays."""
    body = {"n": t.name, "ty": t.type, "d": t.description, "df": t.difficulty, "g": t.understanding, "x": experience,
            "k": kind_for(t.type, subject, t.name), "det": t.details.model_dump(exclude_none=True)}
    return hashlib.sha1(json.dumps(body, sort_keys=True).encode()).hexdigest()[:12]


def to_draft(t: TopicIn, subject: str, experience: Optional[int], progress_override: Optional[str] = None) -> C.Draft:
    text, progress = compose_details(t, subject)
    if progress_override is not None:
        progress = progress_override
    answers: dict[str, Any] = {"progress": progress if progress in ("none", "some", "half", "most") else "none"}
    kind = kind_for(t.type, subject, t.name)
    if kind:
        answers["kind"] = kind
    if experience in EXPERIENCE_TO_SKILL:
        answers["skill"] = EXPERIENCE_TO_SKILL[experience]
    if t.understanding:
        answers["grasp"] = t.understanding
    return C.Draft(ref=("t" + t.id)[:40], title=t.name, deadline_date=t.deadline, deadline_hour=t.deadline_hour, details=text, kind=kind,
                   felt_hard=t.difficulty, answers=answers, priority=t.priority)


# ---------------------------------------------------------------- the changes a form means
@dataclass
class Changes:
    questions: list = field(default_factory=list)
    creates: list = field(default_factory=list)       # {topic_id, subject, title, description, category, difficulty, deadline (aware datetime), meta}
    updates: list = field(default_factory=list)       # {task_id, topic_id, fields{...}, meta | None, reopen}
    complete: list = field(default_factory=list)      # task ids to mark finished (the student said "Finished")
    remove: list = field(default_factory=list)        # task ids
    settings_patch: dict = field(default_factory=dict)
    stored_form: dict = field(default_factory=dict)
    mood_entry: Optional[dict] = None
    energy_level: Optional[int] = None
    today_minutes: Optional[int] = None

    def counts(self) -> dict:
        return {"created": len(self.creates), "updated": len(self.updates), "completed": len(self.complete), "removed": len(self.remove)}


def _topic_meta(meta: dict, t: TopicIn, subject: str, sig: str, progress: Optional[str]) -> dict:
    meta["topic_id"] = t.id
    meta["subject"] = subject
    meta["task_type"] = t.type
    meta["progress"] = progress
    meta["grasp"] = t.understanding
    meta["form_sig"] = sig
    meta["priority"] = t.priority
    meta["form_desc"] = t.description                                    # what the student typed, so the form comes back exactly as it was left
    meta["details"] = t.details.model_dump(exclude_none=True)
    return meta


def _question(topic: TopicIn, subject: str, key: str) -> dict:
    where = f"“{topic.name}”" + (f" ({subject})" if subject else "")
    if key == "deadline":
        return {"id": f"{topic.id}:deadline", "topic_id": topic.id, "key": "deadline", "type": "date", "options": [],
                "text": f"When do you need to finish {where}?", "why": "I need the deadline to spread the work over the days you have."}
    return {"id": f"{topic.id}:progress", "topic_id": topic.id, "key": "progress", "type": "choice",
            "options": [{"value": k, "label": PROGRESS_LABELS[k]} for k in PROGRESS],
            "text": f"How much of {where} have you finished?", "why": "Finished work does not need to be planned again."}


def _find_task(core: C.CoreInput, t: TopicIn) -> Optional[C.TaskRow]:
    if t.task_id:
        for r in core.tasks:
            if r.id == t.task_id:
                return r
    for r in core.tasks:
        if r.meta and r.meta.get("topic_id") == t.id:
            return r
    return None


def build_changes(core: C.CoreInput, form: PlanFormIn) -> Changes:
    ch = Changes()
    tz = C.tz_of(core.settings)
    topics = [(s, t) for s in form.subjects for t in s.topics]

    # --- the few questions that would otherwise make the plan a guess (deadline first; never more than three; none for finished work)
    asks = []
    for s, t in topics:
        if t.progress == "done":
            continue
        if t.deadline is None:
            asks.append((0, _question(t, s.name, "deadline")))
        elif t.progress is None and t.type in LARGE_TYPES:
            asks.append((1, _question(t, s.name, "progress")))
    if asks:
        asks.sort(key=lambda a: a[0])
        ch.questions = [q for _, q in asks[:MAX_QUESTIONS]]
        return ch

    removed = set(form.removed)
    seen_task_ids = set()
    for s, t in topics:
        t_experience = s.experience if s.experience is not None else form.experience
        row = _find_task(core, t)
        sig = topic_sig(t, s.name, t_experience)
        deadline_dt = C.make_deadline(t.deadline, t.deadline_hour, tz) if t.deadline else None
        if row is not None:
            seen_task_ids.add(row.id)

        if t.progress == "done":
            if row is None:
                # finished before it was ever planned: keep it as a finished task so progress and history show it
                draft = to_draft(t, s.name, t_experience, "none")
                drow, meta = C.draft_to_row(draft, core)
                meta = _topic_meta(meta, t, s.name, sig, "done")
                ch.creates.append({"topic_id": t.id, "subject": s.name, "title": t.name, "description": drow.description, "category": s.name[:100],
                                   "difficulty": drow.difficulty, "deadline": drow.deadline, "meta": meta, "completed": True})
            elif row.status == "pending":
                ch.complete.append(row.id)
                ch.updates.append({"task_id": row.id, "topic_id": t.id, "reopen": False, "fields": _fields(t, s.name, deadline_dt, row),
                                   "meta": _finished_meta(row, t, s.name, sig)})
            continue

        if row is None:
            draft = to_draft(t, s.name, t_experience)
            drow, meta = C.draft_to_row(draft, core)
            meta = _topic_meta(meta, t, s.name, sig, t.progress)
            ch.creates.append({"topic_id": t.id, "subject": s.name, "title": t.name, "description": drow.description, "category": s.name[:100],
                               "difficulty": drow.difficulty, "deadline": drow.deadline, "meta": meta, "completed": False})
            continue

        old = C.ensure_meta(row, core) if row.status == "pending" else (row.meta or {})
        reopen = row.status == "completed"
        legacy = not old.get("form_sig")
        same_progress = (old.get("progress") == t.progress) and not reopen
        adopt = legacy and t.progress is None and t.difficulty is None and t.understanding is None and not reopen
        if adopt:
            meta = dict(old)                      # an older task the student has not touched on this form: keep its estimate as it is
        elif old.get("form_sig") == sig and same_progress:
            meta = dict(old)
        else:
            draft = to_draft(t, s.name, t_experience)
            _, fresh = C.draft_to_row(draft, core)
            before = int(old.get("actual_before", 0))
            if same_progress:
                fresh["done"] = int(old.get("done", 0))            # same starting point: the minutes already worked still count
            else:
                fresh["done"] = 0                                    # the student restated where they are: minutes worked so far are history
                before += int(old.get("done", 0))
            fresh["actual_before"] = before
            meta = fresh
        meta = _topic_meta(meta, t, s.name, sig, t.progress)
        if old.get("actual_before") and "actual_before" not in meta:
            meta["actual_before"] = old["actual_before"]
        ch.updates.append({"task_id": row.id, "topic_id": t.id, "reopen": reopen, "fields": _fields(t, s.name, deadline_dt, row), "meta": meta})

    for r in core.tasks:                          # tasks of topics the student explicitly deleted (never anything that was merely left out)
        tid = (r.meta or {}).get("topic_id")
        if r.id not in seen_task_ids and ((tid and tid in removed) or r.id in removed):
            ch.remove.append(r.id)

    ch.settings_patch = settings_patch_from(form.availability)
    ch.stored_form = StoredForm(subjects=[{"id": s.id, "name": s.name, "experience": s.experience} for s in form.subjects],
                                experience=form.experience, obstacles=form.obstacles, helps=form.helps, extra=form.extra).model_dump()
    if form.feelings.any() or form.today_minutes is not None:
        entry = {"date": core.now.date().isoformat()}
        entry.update({k: v for k, v in form.feelings.model_dump().items() if v is not None})
        if form.today_minutes is not None:
            entry["today_minutes"] = form.today_minutes
        ch.mood_entry = MoodEntry(**entry).model_dump(exclude_none=True)
        if form.feelings.energy:
            ch.energy_level = ENERGY_TO_LEVEL[form.feelings.energy]
    ch.today_minutes = form.today_minutes
    return ch


def _fields(t: TopicIn, subject: str, deadline_dt: Optional[datetime], row: C.TaskRow) -> dict:
    text, _ = compose_details(t, subject)
    out = {"title": t.name, "description": text, "category": subject[:100]}
    if deadline_dt is not None:
        out["deadline"] = deadline_dt
    if t.difficulty:
        out["difficulty"] = t.difficulty
    return out


def _finished_meta(row: C.TaskRow, t: TopicIn, subject: str, sig: str) -> dict:
    meta = dict(row.meta or {})
    if meta:
        _topic_meta(meta, t, subject, sig, "done")
    return meta


def settings_patch_from(a: AvailabilityIn) -> dict:
    patch: dict[str, Any] = {}
    if a.day_minutes is not None:
        patch["day_minutes"] = {str(k): int(v) for k, v in a.day_minutes.items()}
        if a.daily_minutes is None and patch["day_minutes"]:
            vals = list(patch["day_minutes"].values())
            patch["weekday_minutes"] = max(15, min(720, max(vals))) if max(vals) > 0 else 15
    if a.daily_minutes is not None:
        patch["weekday_minutes"] = a.daily_minutes
        patch["weekend_minutes"] = a.daily_minutes
        if a.day_minutes is None:
            patch["day_minutes"] = {}                       # one number for every day replaces any earlier per-day numbers
    if a.preferred_time is not None:
        patch["preferred_time"] = a.preferred_time
    if a.unavailable_periods is not None:
        patch["unavailable_periods"] = a.unavailable_periods
    return patch


def apply_settings(current: StudySettings, patch: dict) -> StudySettings:
    """The settings that result from the form; anything that does not validate is ignored (never an error for the student)."""
    data = current.model_dump()
    for k, v in patch.items():
        try:
            StudySettings(**{**data, k: v})
            data[k] = v
        except Exception:
            continue
    return StudySettings(**data)


# ---------------------------------------------------------------- the form as it should look when the student comes back
def form_from_state(core: C.CoreInput, plan_form: Optional[dict], mood_log: Optional[list]) -> dict:
    stored = StoredForm(**(plan_form or {})) if plan_form else StoredForm()
    by_subject: dict[str, dict] = {}
    order: list[str] = []
    for s in stored.subjects:
        by_subject[s.name.lower()] = {"id": s.id, "name": s.name, "experience": s.experience, "topics": []}
        order.append(s.name.lower())
    tz = C.tz_of(core.settings)
    for r in sorted(core.tasks, key=lambda x: (x.status != "pending", x.deadline)):
        m = r.meta or {}
        sname = m.get("subject") or "My other tasks"
        key = sname.lower()
        if key not in by_subject:
            by_subject[key] = {"id": "s" + hashlib.sha1(key.encode()).hexdigest()[:10], "name": sname, "experience": None, "topics": []}
            order.append(key)
        done = r.status == "completed"
        by_subject[key]["topics"].append({
            "id": m.get("topic_id") or "t" + r.id.replace("-", "")[:20], "task_id": r.id, "name": r.title,
            "type": m.get("task_type") or _type_from_kind(m.get("kind")), "progress": "done" if done else m.get("progress"),
            "difficulty": r.difficulty if m.get("form_sig") else None, "understanding": m.get("grasp"),
            "description": (m["form_desc"] if "form_desc" in m else (r.description or ""))[:600],
            "deadline": r.deadline.astimezone(tz).date().isoformat(), "deadline_hour": None if r.deadline.hour == 23 and r.deadline.minute == 59 else r.deadline.hour,
            "priority": int(m.get("priority", 2)), "details": m.get("details") or {}, "status": r.status})
    subjects = [by_subject[k] for k in order]
    s = core.settings
    last = (mood_log or [])[-1] if mood_log else None
    return {"subjects": subjects,
            "availability": {"daily_minutes": s.weekday_minutes if s.weekday_minutes == s.weekend_minutes else None,
                             "day_minutes": s.day_minutes or {}, "weekday_minutes": s.weekday_minutes, "weekend_minutes": s.weekend_minutes,
                             "preferred_time": s.preferred_time, "unavailable_periods": s.unavailable_periods, "study_days": s.study_days},
            "experience": stored.experience, "obstacles": stored.obstacles, "helps": stored.helps, "extra": stored.extra,
            "last_checkin": last, "checked_in_today": bool(last and last.get("date") == core.now.date().isoformat())}


def _type_from_kind(kind: Optional[str]) -> str:
    return {"exam": "exam", "programming": "project", "writing": "report", "presentation": "presentation", "reading": "reading",
            "mathematics": "homework"}.get(kind or "", "other")
