"""
The settings and profile a student can change. Every field here is read by real code:

  weekday_minutes / weekend_minutes / study_days  -> daily capacity in the scheduler
  buffer_days                                      -> the scheduler stops planning this many days before a deadline
  pacing                                           -> "even" spreads work, "early" front-loads it
  preferred_time                                   -> order and clock hints of the day's sessions
  session_style / break_style                      -> length of blocks and breaks
  gentle_mode                                      -> auto / always / off: lowers load when energy or wellbeing is low
  ai_assist                                        -> off = the language model is never called for this student
  reminders                                        -> the reminder job (lead times, same-day, overdue, time zone)
  reduce_motion                                    -> the interface switches animations off
"""
import re
from typing import Literal, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.config import settings as _env

LEAD_CHOICES = (1, 3, 6, 12, 24, 48, 72, 168)
DEADLINE_DAY_CHOICES = (14, 10, 7, 5, 3, 2, 1)


class StudySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weekday_minutes: int = Field(default=120, ge=15, le=720)
    weekend_minutes: int = Field(default=90, ge=0, le=720)
    study_days: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6])      # 0 = Monday
    buffer_days: int = Field(default=1, ge=0, le=5)
    pacing: Literal["even", "early"] = "even"
    preferred_time: Literal["morning", "afternoon", "evening", "night", "flexible"] = "flexible"
    # optional minutes for single weekdays ("0".."6", 0 = Monday); a weekday listed here overrides weekday_minutes / weekend_minutes
    day_minutes: dict[str, int] = Field(default_factory=dict)
    # parts of the day the student cannot study; only used to pick the clock hint of a block, never to add or remove minutes
    unavailable_periods: list[Literal["morning", "afternoon", "evening", "night"]] = Field(default_factory=list, max_length=4)
    theme: Literal["system", "light", "dark"] = "system"
    session_style: Literal["auto", "short", "standard", "long"] = "auto"
    break_style: Literal["short", "standard", "long"] = "standard"
    gentle_mode: Literal["auto", "always", "off"] = "auto"
    ai_assist: bool = True
    # reminders
    remind_enabled: bool = True
    remind_lead_hours: list[int] = Field(default_factory=lambda: [_env.reminder_hours_before if _env.reminder_hours_before in LEAD_CHOICES else 48])
    same_day_reminder: bool = False
    same_day_hour: int = Field(default=8, ge=0, le=23)
    overdue_reminder: bool = False
    timezone: str = "UTC"
    reduce_motion: bool = False
    # appearance (applied by the interface on every page)
    accent: Literal["blue", "purple", "green", "pink", "neutral"] = "blue"
    text_size: Literal["normal", "larger"] = "normal"
    high_contrast: bool = False
    # in-app reminders (shown inside MindSync; nothing is emailed)
    inapp_reminders: bool = True
    daily_reminder: bool = True
    daily_reminder_time: str = Field(default="08:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    deadline_days: list[int] = Field(default_factory=lambda: [7, 3, 1])
    deadline_on_day: bool = True
    deadline_overdue: bool = True
    # stored for later; there is no email delivery in this version
    email_reminders_future: bool = False

    @field_validator("study_days")
    @classmethod
    def _days(cls, v: list) -> list:
        v = sorted({int(d) for d in v})
        if any(d < 0 or d > 6 for d in v):
            raise ValueError("Days must be 0 (Monday) to 6 (Sunday)")
        if not v:
            raise ValueError("Choose at least one study day")
        return v

    @field_validator("day_minutes")
    @classmethod
    def _day_minutes(cls, v: dict) -> dict:
        out = {}
        for k, m in (v or {}).items():
            if str(k) not in {"0", "1", "2", "3", "4", "5", "6"}:
                raise ValueError("Weekdays are 0 (Monday) to 6 (Sunday)")
            if isinstance(m, bool) or not isinstance(m, int) or not 0 <= m <= 720:
                raise ValueError("Minutes per day must be between 0 and 720")
            out[str(k)] = m
        return out

    @field_validator("unavailable_periods")
    @classmethod
    def _periods(cls, v: list) -> list:
        return sorted(set(v), key=["morning", "afternoon", "evening", "night"].index)

    @field_validator("remind_lead_hours")
    @classmethod
    def _leads(cls, v: list) -> list:
        v = sorted({int(h) for h in v}, reverse=True)
        if any(h not in LEAD_CHOICES for h in v):
            raise ValueError(f"Reminder times must be among {LEAD_CHOICES}")
        if len(v) > 3:
            raise ValueError("Choose at most three reminder times")
        return v

    @field_validator("deadline_days")
    @classmethod
    def _deadline_days(cls, v: list) -> list:
        v = sorted({int(d) for d in v}, reverse=True)
        if any(d not in DEADLINE_DAY_CHOICES for d in v):
            raise ValueError(f"Deadline reminder days must be among {DEADLINE_DAY_CHOICES}")
        return v

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError, OSError):
            raise ValueError("Unknown time zone")
        return v


def settings_from(data: Optional[dict]) -> StudySettings:
    """Stored (or guest-sent) settings; anything missing or invalid falls back to the defaults field by field."""
    data = dict(data or {})
    try:
        return StudySettings(**data)
    except Exception:
        clean = {}
        for k, v in data.items():
            try:
                StudySettings(**{k: v})
                clean[k] = v
            except Exception:
                continue
        try:
            return StudySettings(**clean)
        except Exception:
            return StudySettings()


MOODS = ("happy", "calm", "okay", "tired", "worried", "stressed", "sad", "frustrated", "overwhelmed")
LEVELS3 = ("low", "medium", "high")
FOCUS_LEVELS = ("difficult", "okay", "focused")
OBSTACLES = ("distracted", "procrastinate", "forget", "struggle_to_understand", "dont_know_where_to_start", "need_practice", "overwhelmed",
             "not_enough_time", "nothing")
HELPS = ("practice_questions", "solving_problems", "reading_notes", "flashcards", "writing_summaries", "building_projects",
         "watching_explanations", "not_sure")
EDUCATION_LEVELS = ("school", "college", "undergraduate", "postgraduate", "other")


class StoredSubject(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=60)
    experience: Optional[int] = Field(default=None, ge=1, le=4)

    @field_validator("name")
    @classmethod
    def _n(cls, v: str) -> str:
        return " ".join(v.split())


class StoredForm(BaseModel):
    """What the Smart Planner form remembers besides the tasks themselves (the topics are rebuilt from the tasks)."""
    model_config = ConfigDict(extra="forbid")
    subjects: list[StoredSubject] = Field(default_factory=list, max_length=12)
    experience: Optional[int] = Field(default=None, ge=1, le=4)
    obstacles: list[Literal[OBSTACLES]] = Field(default_factory=list, max_length=9)
    helps: list[Literal[HELPS]] = Field(default_factory=list, max_length=8)
    extra: str = Field(default="", max_length=600)

    @field_validator("extra")
    @classmethod
    def _e(cls, v: str) -> str:
        return " ".join(v.split())


class MoodEntry(BaseModel):
    """One optional daily check-in. Self-reported, never a diagnosis; the student can erase the whole log."""
    model_config = ConfigDict(extra="forbid")
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    mood: Optional[Literal[MOODS]] = None
    energy: Optional[Literal[LEVELS3]] = None
    stress: Optional[Literal[LEVELS3]] = None
    focus: Optional[Literal[FOCUS_LEVELS]] = None
    today_minutes: Optional[int] = Field(default=None, ge=0, le=720)


AVATARS = ("owl", "fox", "cat", "book", "star", "leaf", "moon", "sun")     # preset pictures only: no file upload, so nothing risky to store


class StudyProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(default="", max_length=100)
    phone: str = Field(default="", max_length=20)
    avatar: str = Field(default="", max_length=10)
    course: str = Field(default="", max_length=100)
    year_of_study: Optional[int] = Field(default=None, ge=1, le=8)
    subjects: list[str] = Field(default_factory=list, max_length=12)
    goal: str = Field(default="", max_length=300)
    weekly_goal_hours: Optional[float] = Field(default=None, ge=0, le=100)
    about_me: str = Field(default="", max_length=500)
    strengths: list[str] = Field(default_factory=list, max_length=8)
    struggles: list[str] = Field(default_factory=list, max_length=8)
    education_level: Optional[Literal[EDUCATION_LEVELS]] = None
    plan_form: dict = Field(default_factory=dict)
    mood_log: list[dict] = Field(default_factory=list, max_length=90)

    @field_validator("plan_form")
    @classmethod
    def _plan_form(cls, v: dict) -> dict:
        return StoredForm(**v).model_dump() if v else {}

    @field_validator("mood_log")
    @classmethod
    def _mood_log(cls, v: list) -> list:
        out = {}
        for e in v:
            m = MoodEntry(**e).model_dump(exclude_none=True)
            out[m["date"]] = m                      # one entry per day, the newest wins
        return [out[k] for k in sorted(out)][-90:]

    @field_validator("course", "goal", "about_me", "full_name")
    @classmethod
    def _tidy(cls, v: str) -> str:
        return " ".join(v.split())

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        v = " ".join(v.split())
        if v and not re.fullmatch(r"\+?[0-9][0-9 ()\-]{5,18}", v):
            raise ValueError("Phone number can only have digits, spaces, brackets, + and -.")
        return v

    @field_validator("avatar")
    @classmethod
    def _avatar(cls, v: str) -> str:
        if v and v not in AVATARS:
            raise ValueError("Choose one of the pictures in the list.")
        return v

    @field_validator("subjects", "strengths", "struggles")
    @classmethod
    def _items(cls, v: list) -> list:
        out = []
        for s in v:
            s = " ".join(str(s).split())[:60]
            if s and s not in out:
                out.append(s)
        return out


def profile_from(data: Optional[dict]) -> StudyProfile:
    """Stored profile; anything invalid falls back to its default field by field (one bad field never wipes the rest)."""
    data = dict(data or {})
    try:
        return StudyProfile(**data)
    except Exception:
        clean = {}
        for k, v in data.items():
            try:
                StudyProfile(**{k: v})
                clean[k] = v
            except Exception:
                continue
        try:
            return StudyProfile(**clean)
        except Exception:
            return StudyProfile()
