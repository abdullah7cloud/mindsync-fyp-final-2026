"""
Study Planner.

The student chooses a category (e.g. "Computer Science") and lists what they
want to learn ("Python basics", "Power BI", "SQL joins" ...). MindSync then

  1. rates each topic: difficulty 1-5 and a time estimate, using simple RULES
     (a table of well-known topics plus keywords such as "basics" / "advanced").
     The rules are shown to the student ("why this rating") and the student can
     override any rating with a slider - an override is never re-rated;
  2. builds a timed plan of focus blocks and breaks that depends on the
     student's energy ("mode"):
         low (1-2)     15 min focus / 10 min break, only easy topics (Burnout Mode idea)
         normal (3-4)  20-25 min focus /  5 min break, easy topic first to warm up (3), hard first (4)
         high (5)      45 min focus / 10 min break, hardest topic first
     Two hard blocks are never placed back to back, a long break follows every 4th block,
     and a short review closes the session;
  3. optionally lowers the mode when the latest wellbeing check (trained model) shows
     a Medium or High stress risk: High -> low mode, Medium -> at most normal 20/5.

The plan is plain deterministic code (instant, testable, explainable). No external
AI service is used and nothing here is stored: the dashboard keeps the plan on
screen and can turn the topics into normal tasks.
"""
import math
import re
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from app.auth import get_current_user
from app.models import User

router = APIRouter(prefix="/planner", tags=["study planner"])

MAX_TOPICS = 15
HARD_FROM = 4          # difficulty >= 4 counts as "hard"
MAX_BLOCKS_PER_TOPIC = 6
MAX_TOTAL_BLOCKS = 24
DEFAULT_MINUTES = {1: 20, 2: 30, 3: 45, 4: 60, 5: 90}


# ---------- schemas ----------
class TopicIn(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    difficulty: Optional[int] = Field(default=None, ge=1, le=5)   # set => student's own rating
    minutes: Optional[int] = Field(default=None, ge=10, le=240)

    @field_validator("title")
    @classmethod
    def _clean(cls, v: str) -> str:
        v = re.sub(r"\s+", " ", v).strip()
        if not v:
            raise ValueError("Topic cannot be blank")
        return v


class PlanRequest(BaseModel):
    category: str = Field(default="General", max_length=40)
    topics: list[TopicIn] = Field(min_length=1, max_length=MAX_TOPICS)
    energy: int = Field(default=3, ge=1, le=5)
    available_minutes: Optional[int] = Field(default=None, ge=20, le=600)
    # Latest wellbeing-check result (guests send it from the browser; accounts may send it too).
    stress_risk: Optional[Literal["Low", "Medium", "High"]] = None

    @field_validator("category")
    @classmethod
    def _cat(cls, v: str) -> str:
        return re.sub(r"\s+", " ", v).strip() or "General"

    @field_validator("topics")
    @classmethod
    def _unique(cls, v: list[TopicIn]) -> list[TopicIn]:
        seen, out = set(), []
        for t in v:
            key = t.title.lower()
            if key not in seen:
                seen.add(key)
                out.append(t)
        return out


class RatedTopic(BaseModel):
    title: str
    difficulty: int
    minutes: int
    source: Literal["student", "offline_rules"]
    reason: str = ""


class PlanItem(BaseModel):
    kind: Literal["study", "break", "long_break", "review"]
    topic: Optional[str] = None
    difficulty: Optional[int] = None
    minutes: int
    start_minute: int            # minutes from the start of the session
    label: str


class PlanResponse(BaseModel):
    category: str
    mode: Literal["low", "normal", "high"]
    block_minutes: int
    break_minutes: int
    topics: list[RatedTopic]
    plan: list[PlanItem]
    deferred: list[str]          # topics not scheduled now (too hard for this mode, or no time left)
    deferred_reason: str = ""
    study_minutes: int
    total_minutes: int
    rating_source: Literal["student", "offline_rules", "mixed"]
    note: str = ""


# ---------- offline difficulty rules ----------
# Whole-phrase matches for common university topics (difficulty, typical minutes).
_KNOWN = {
    "html": 1, "css": 2, "git": 2, "github": 2, "excel": 2, "javascript basics": 2, "python basics": 2,
    "python": 3, "java": 3, "c++": 4, "c": 4, "sql": 3, "sql joins": 3, "power bi": 3, "tableau": 3,
    "pandas": 3, "numpy": 3, "react": 3, "node": 3, "fastapi": 3, "docker": 3, "linux": 3, "networking": 3,
    "data structures": 4, "algorithms": 4, "big o": 4, "dax": 4, "statistics": 3, "probability": 4,
    "calculus": 4, "linear algebra": 4, "machine learning": 4, "deep learning": 5, "neural networks": 5,
    "cryptography": 5, "operating systems": 4, "compilers": 5, "recursion": 4, "pointers": 4,
}
_EASIER = ("basic", "basics", "intro", "introduction", "overview", "beginner", "fundamental", "fundamentals",
           "getting started", "what is", "revision", "recap", "terminology", "setup", "install")
_HARDER = ("advanced", "optimi", "proof", "prove", "theory", "theorem", "derivation", "algorithm",
           "concurrency", "distributed", "complexity", "recursion", "pointer", "architecture", "deep",
           "neural", "cryptograph", "formal", "dynamic programming", "graph", "tree", "regression",
           "probabilistic", "compiler")


def offline_rate(title: str) -> tuple[int, int, str]:
    """(difficulty 1-5, minutes, reason). Pure keyword rules - no AI, no network."""
    low = title.lower().strip()
    base, reason = 3, "Medium by default"
    # longest known phrase contained in the title wins
    hits = [k for k in _KNOWN if re.search(rf"(?<![\w+]){re.escape(k)}(?![\w+])", low)]
    if hits:
        best = max(hits, key=len)
        base, reason = _KNOWN[best], f"'{best}' is usually {'easy' if _KNOWN[best] <= 2 else 'medium' if _KNOWN[best] == 3 else 'hard'}"
        low = low.replace(best, " ")      # the matched phrase already carries its own level; do not count its words twice
    adj = 0
    easier = [w for w in _EASIER if w in low]
    harder = [w for w in _HARDER if w in low]
    if easier:
        adj -= 1
        reason += f"; '{easier[0]}' makes it easier"
    if harder:
        adj += 1
        reason += f"; '{harder[0]}' makes it harder"
    if len(low.split()) >= 7:
        adj += 1
        reason += "; long topic = more to cover"
    d = max(1, min(5, base + adj))
    return d, DEFAULT_MINUTES[d], reason


# ---------- rating the topics ----------
def rate_topics(topics: list[TopicIn]) -> list[RatedTopic]:
    """Fill in missing ratings with the offline rules. A rating the student set is always kept."""
    rated = []
    for t in topics:
        if t.difficulty is not None:
            rated.append(RatedTopic(title=t.title, difficulty=t.difficulty,
                                    minutes=t.minutes or DEFAULT_MINUTES[t.difficulty],
                                    source="student", reason="Your own rating"))
        else:
            d, mins, why = offline_rate(t.title)
            rated.append(RatedTopic(title=t.title, difficulty=d, minutes=t.minutes or mins,
                                    source="offline_rules", reason=why))
    return rated


# ---------- the plan (pure, deterministic) ----------
def mode_for(energy: int) -> tuple[str, int, int, int]:
    """(mode, block minutes, break minutes, long break minutes)."""
    if energy <= 2:
        return "low", 15, 10, 20
    if energy == 3:
        return "normal", 20, 5, 20
    if energy == 4:
        return "normal", 25, 5, 20
    return "high", 45, 10, 30


def build_plan(category: str, topics: list[RatedTopic], energy: int, available_minutes: Optional[int]) -> dict:
    mode, block, brk, long_brk = mode_for(energy)

    # 1. which topics fit this mode (Burnout/low mode: only easy topics, never zero)
    deferred: list[str] = []
    reason = ""
    usable = list(topics)
    if mode == "low":
        usable = [t for t in topics if t.difficulty <= 2]
        if not usable:
            easiest = min(topics, key=lambda t: t.difficulty)
            usable = [easiest.model_copy(update={"minutes": min(easiest.minutes, block)})]
            reason = "Everything is hard for a low-energy day, so only one gentle starter block of the easiest topic is planned."
        else:
            reason = "Low energy: harder topics are saved for a day you feel better."
        deferred = [t.title for t in topics if t.title not in {u.title for u in usable}]

    # 2. split topics into blocks (a long topic becomes several parts)
    by_title = {t.title: t for t in usable}
    total_parts = {t.title: min(MAX_BLOCKS_PER_TOPIC, max(1, math.ceil(t.minutes / block))) for t in usable}
    remaining = dict(total_parts)

    def part_len(title: str, index: int) -> int:
        n = total_parts[title]
        if index < n - 1:
            return block
        return max(10, min(block, by_title[title].minutes - (n - 1) * block))

    def pick(prev: Optional[str], count_done: int) -> Optional[str]:
        cands = [x for x, n in remaining.items() if n > 0]
        if not cands:
            return None
        prev_hard = prev is not None and by_title[prev].difficulty >= HARD_FROM
        if prev is not None and not prev_hard and remaining.get(prev, 0) > 0:
            # keep going with an easy/medium topic until it is done - but only while enough light blocks stay
            # in reserve to separate the hard blocks that are still waiting
            hard_left = sum(n for x, n in remaining.items() if by_title[x].difficulty >= HARD_FROM)
            light_left = sum(n for x, n in remaining.items() if by_title[x].difficulty < HARD_FROM)
            if light_left - 1 >= max(0, hard_left - 1):
                return prev
        pool = cands
        if prev_hard:                                    # never two hard blocks in a row if avoidable
            pool = [c for c in cands if by_title[c].difficulty < HARD_FROM] or cands
        if prev is not None and len(pool) > 1:           # and avoid the same topic twice in a row
            pool = [c for c in pool if c != prev] or pool
        if count_done == 0:
            # first block: warm up with the easiest topic, unless energy is good -> hardest first
            key = (lambda c: -by_title[c].difficulty) if energy >= 4 else (lambda c: by_title[c].difficulty)
        else:
            # then alternate: after a hard block go lighter, after a light block go to the hardest left
            key = (lambda c: by_title[c].difficulty) if prev_hard else (lambda c: -by_title[c].difficulty)
        return sorted(pool, key=lambda c: (key(c), c))[0]

    # 3. lay the blocks out in time, fitting the time the student has (if given)
    items: list[PlanItem] = []
    clock = 0
    done = 0
    prev: Optional[str] = None
    while done < MAX_TOTAL_BLOCKS:
        title = pick(prev, done)
        if title is None:
            break
        t = by_title[title]
        part = part_len(title, total_parts[title] - remaining[title])
        gap = 0 if not items else (long_brk if done % 4 == 0 else brk)
        if available_minutes is not None:
            part = min(part, available_minutes - clock - gap)
            if part < 10:
                break
        if gap:
            long = done % 4 == 0
            items.append(PlanItem(kind="long_break" if long else "break", minutes=gap, start_minute=clock,
                                  label="Long break - walk, water, no phone" if long else "Short break - stand up, stretch"))
            clock += gap
        index = total_parts[title] - remaining[title] + 1
        label = t.title if total_parts[title] == 1 else f"{t.title} (part {index} of {total_parts[title]})"
        items.append(PlanItem(kind="study", topic=t.title, difficulty=t.difficulty, minutes=part,
                              start_minute=clock, label=label))
        clock += part
        remaining[title] -= 1
        done += 1
        prev = title
    unscheduled = [x for x, n in remaining.items() if n > 0]

    # 4. closing review (needs 2+ topics scheduled and a bit of time)
    scheduled_topics = {i.topic for i in items if i.kind == "study"}
    if len(scheduled_topics) >= 2:
        rev = min(block, 15)
        gap = brk
        if available_minutes is None or clock + gap + rev <= available_minutes:
            items.append(PlanItem(kind="break", minutes=gap, start_minute=clock, label="Short break - stand up, stretch"))
            clock += gap
            items.append(PlanItem(kind="review", minutes=rev, start_minute=clock,
                                  label="Quick review - say each topic out loud from memory"))
            clock += rev

    if unscheduled:
        deferred += [u for u in unscheduled if u not in deferred]
        if not reason:
            reason = "Not everything fits in the time you have, so the rest is left for the next session."
    study = sum(i.minutes for i in items if i.kind in ("study", "review"))
    return {
        "mode": mode, "block_minutes": block, "break_minutes": brk, "plan": items, "deferred": deferred,
        "deferred_reason": reason, "study_minutes": study, "total_minutes": clock,
    }


def effective_energy(energy: int, stress_risk: Optional[str]) -> int:
    """
    Combine the energy check-in with the wellbeing result: a High stress risk caps the plan at the
    gentle low-energy mode, a Medium risk caps it at normal 20/5. Low risk changes nothing.
    """
    if stress_risk == "High":
        return min(energy, 2)
    if stress_risk == "Medium":
        return min(energy, 3)
    return energy


def make_plan(payload: PlanRequest) -> PlanResponse:
    rated = rate_topics(payload.topics)
    energy = effective_energy(payload.energy, payload.stress_risk)
    built = build_plan(payload.category, rated, energy, payload.available_minutes)
    sources = {t.source for t in rated}
    src = sources.pop() if len(sources) == 1 else "mixed"
    notes = []
    if energy != payload.energy:
        notes.append(f"Your wellbeing check estimated a {payload.stress_risk} stress level, so the plan is gentler than your energy alone would give.")
    if any(t.source == "offline_rules" for t in rated):
        notes.append("Difficulty ratings are quick rule-based estimates - change any slider if you know better.")
    return PlanResponse(category=payload.category, topics=rated, rating_source=src, note=" ".join(notes), **built)


# ---------- route (logged-in users) ----------
@router.post("/plan", response_model=PlanResponse)
async def plan(payload: PlanRequest, current_user: User = Depends(get_current_user)) -> PlanResponse:
    return make_plan(payload)
