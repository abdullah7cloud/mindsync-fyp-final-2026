"""
Rule-based fallbacks for every language-model feature. They use the same inputs and return the same shapes as the model path,
so the screens work identically offline; the screen shows a small label ("rules" or "AI") so nobody is misled about which one wrote what.
"""
import re
from datetime import date, datetime
from typing import Optional

from app.taskaware import analysis as A
from app.taskaware import questions as Q
from app.taskaware import taxonomy as T

from .dates import parse_deadline


_STARTS_TASK = re.compile(r"^(?:(?:and|also|plus|then|oh)\b[ ,]*)*(?:another\b|i(?:'ve| have| need| must| want| got)\b|(?:my|a|an|the)\s|(?:read|write|finish|submit|revise|study|prepare|build|do|complete|fix|make|learn|practise|practice)\b)", re.I)
_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
_AND_TASK = re.compile(r",?\s+and\s+(?=(?:another|a|an|my|i(?:'ve| have| need| must| got)|(?:read|write|finish|submit|revise|study|prepare|build|complete|fix)\b))", re.I)


def _looks_like_task(chunk: str) -> bool:
    """A sentence or clause is a new task only if it starts like one AND has a date or a recognised kind of work."""
    if len(chunk.split()) < 3 or not _STARTS_TASK.match(chunk.strip()):
        return False
    try:
        if parse_deadline(chunk, date.today())[0] is not None:
            return True
    except Exception:                                               # noqa: BLE001 - a date we cannot read is just 'no date'
        pass
    return bool(A.classify(clean_title(chunk), chunk)[2])


def _has_own_task(chunk: str) -> bool:
    """A comma piece that has its own date AND its own recognised kind of work is a task of its own ("..., 500 word reflection tomorrow")."""
    if len(chunk.split()) < 3:
        return False
    try:
        dated = parse_deadline(chunk, date.today())[0] is not None
    except Exception:                                               # noqa: BLE001
        dated = False
    return dated and bool(A.classify(clean_title(chunk), chunk)[2])


def _split_tasks(text: str) -> list:
    parts = [p.strip(" -•*\t") for p in re.split(r"[\n;]+", text) if p.strip(" -•*\t")]
    if len(parts) == 1 and len(parts[0]) > 160:                     # one long sentence listing several things with "and then"/"also"
        parts = [p.strip() for p in re.split(r"\b(?:and then|also|plus)\b", parts[0]) if p.strip()]
    # one line with several sentences or ", and a ..." clauses: split only where the next piece really starts a task
    out = []
    for part in parts:
        pieces = []
        for sent in _SENTENCE.split(part):
            clauses = []
            for cl in _AND_TASK.split(sent):
                for sub in re.split(r",\s+", cl):
                    if clauses and not _has_own_task(sub):
                        clauses[-1] += ", " + sub
                    else:
                        clauses.append(sub)
            for clause in clauses:
                if pieces and not _looks_like_task(clause) and not _has_own_task(clause):
                    pieces[-1] = pieces[-1] + (" " if pieces[-1].endswith((".", "!", "?")) else ", ") + clause.strip()
                else:
                    pieces.append(clause.strip())
        out.extend(pieces)
    return [p for p in out if p][:6]


_LEAD = re.compile(r"^(?:(?:oh,? )?(?:and|also|plus|then)\b[ ,]*)+", re.I)
_I_HAVE = re.compile(r"^(?:i(?:'ve| have| need| must| want| got)(?: got)?(?: to)?|i'm (?:working on|doing)|need to|have to|must)\s+", re.I)
_CUT = re.compile(r"\s+(?:and (?:i|it|we|then)\b|but\b|because\b|so that\b)|[,;:!?](?!\d)|\.(?:\s+[A-Z]|$)|\s+in \d+\s+(?:days?|weeks?)\b|\s+(?:due|by|before|until|next|this|tomorrow|today|tonight)\b", re.I)


def clean_title(chunk: str) -> str:
    """'Also I have a stats exam in 10 days and I do not know chapter 5' -> 'Stats exam'. Keeps the words, drops the filler."""
    t = chunk.strip()
    for _ in range(2):
        t = _LEAD.sub("", t)
        t = _I_HAVE.sub("", t)
    t = re.sub(r"^(?:a|an|the|my|some)\s+", "", t, flags=re.I)
    t = _CUT.split(t, maxsplit=1)[0].strip(" ,-")
    t = t or chunk.strip()
    return (t[:1].upper() + t[1:])[:200]


def understand_local(text: str, fields: dict, today: date) -> dict:
    """Free text + optional structured fields -> tasks and questions, with no model."""
    tasks = []
    chunks = _split_tasks(text) if text.strip() else []
    if fields.get("title") and not chunks:
        chunks = [fields["title"]]
    for i, chunk in enumerate(chunks):
        dd, hh = parse_deadline(chunk, today)
        title = clean_title(chunk)
        details = chunk.strip() if title.lower() != chunk.strip().lower() else ""
        t = {"title": fields.get("title") if (i == 0 and fields.get("title")) else title,
             "details": details, "kind": fields.get("kind") if fields.get("kind") in T.KINDS else None,
             "deadline_date": dd, "deadline_hour": hh, "size": fields.get("size"), "felt_hard": fields.get("felt_hard"),
             "low": None, "likely": None, "high": None, "subtasks": []}
        if i == 0:
            if fields.get("deadline_date") is not None:
                t["deadline_date"], t["deadline_hour"] = fields["deadline_date"], fields.get("deadline_hour")
        tasks.append(t)
    questions = []
    if tasks:
        t0 = tasks[0]
        a = A.analyse(t0["title"], t0["details"], {k: v for k, v in (("kind", t0["kind"]), ("size", t0["size"])) if v})
        qs = Q.next_questions(a, answers={}, skipped=set(), skill=None, has_deadline=t0["deadline_date"] is not None, has_hours=True)
        for q in qs[:3]:
            questions.append({"id": q.id, "text": q.text, "why": q.why, "type": q.type,
                              "options": [{"value": v, "label": l} for v, l in q.options], "placeholder": q.placeholder})
    summary = (f"I found {len(tasks)} task{'s' if len(tasks) != 1 else ''}." if tasks else "I could not find a task in that text.")
    return {"tasks": tasks, "questions": questions, "summary": summary}


def _hm(m: int) -> str:
    h, mm = divmod(int(m), 60)
    return f"{h} h {mm} min" if h and mm else f"{h} h" if h else f"{mm} min"


def narrate_local(facts: dict) -> dict:
    level = facts.get("level")
    if level == "empty":
        return {"headline": "Nothing to plan yet.", "what_first": "Add a task to get started.", "why": "", "risks": [], "tips": []}
    head = {"comfortable": "Your plan fits, with room to spare.", "tight": "Your plan fits, but it is tight.",
            "infeasible": "This does not fit in the time you have."}[level]
    first = (facts.get("today") or [None])[0] or (facts.get("first_session"))
    if first:
        when = "Today" if facts.get("today") else "Next"
        what_first = f"{when}, start with “{first['title']}”: {first['stage']}, {first['minutes']} minutes."
    else:
        what_first = "There is nothing planned for today; the next session is on your calendar."
    tasks = facts.get("tasks") or []
    why = ""
    if first and tasks:
        mine = next((t for t in tasks if t["title"] == first["title"]), None)
        earliest = min(tasks, key=lambda t: t["deadline"]) if tasks else None
        if mine and earliest and mine["title"] == earliest["title"]:
            why = "It is the task whose deadline comes first, so it gets the earliest time."
        elif mine:
            why = (f"Its deadline needs the work to start now, and it is hard for you ({mine['difficulty_for_you']:.1f} out of 5), "
                   "so it goes early in the day while you are fresh.") if mine["difficulty_for_you"] >= 3.5 else \
                  "Starting it now keeps the later days lighter."
        if facts.get("energy") is not None and facts["energy"] <= 2:
            why += " Because your energy is low today, the easier work comes first and the day is shorter."
    risks = []
    if level == "infeasible":
        risks.append(f"About {_hm(facts['shortfall_minutes'])} of work would be left over after the deadlines.")
    if level != "infeasible" and not facts.get("fits_at_high"):
        risks.append(f"If every task takes the longer end of its range, you would be about {_hm(facts['high_shortfall'])} short.")
    if facts.get("buffer_used"):
        risks.append("The safety buffer before your deadlines had to be used up to make this fit.")
    for t in tasks:
        if t["status"] == "late":
            risks.append(f"“{t['title']}” cannot be finished before its deadline with the current settings.")
            break
    tips = []
    if first and first.get("method"):
        tips.append(first["method"])
    if facts.get("break_note"):
        tips.append(facts["break_note"])
    if level == "infeasible" and facts.get("alternatives"):
        tips.append(facts["alternatives"][0]["text"])
    return {"headline": head, "what_first": what_first, "why": why.strip(), "risks": risks[:3], "tips": tips[:3]}


_INTENTS = [
    ("tired", r"\b(tired|exhaust|drain|burn(ed|t)? ?out|no energy|can'?t cope|overwhelm|stress)"),
    ("why_first", r"\bwhy\b.*\b(first|this|order|start)\b|\bwhy (is|are|do)\b"),
    ("fits", r"\b(finish|on time|enough time|manage|make it|fit|possible|realistic|behind)\b"),
    ("today", r"\b(today|now|next|what should|what do i)\b"),
    ("hours", r"\b(how long|how many (hours|minutes)|how much time)\b"),
    ("focus", r"\b(focus|distract|procrastinat|stuck|motivat|start(ing)?|can'?t begin)\b"),
]


def answer_local(question: str, facts: dict) -> dict:
    q = (question or "").lower()
    intent = next((n for n, rx in _INTENTS if re.search(rx, q)), None)
    level = facts.get("level")
    today = facts.get("today") or []
    if intent == "tired":
        return {"answer": "That sounds heavy, and it is fine to slow down. I can make today lighter: shorter blocks and the easiest work first, "
                          "and I can show you what moves to later days. If this feeling is staying, talking to someone you trust or your student support service is a good idea.",
                "follow_ups": ["Lighten my plan", "Show me the Toolkit"], "suggest_action": "replan"}
    if intent == "fits":
        if level == "infeasible":
            alt = (facts.get("alternatives") or [{}])[0].get("text", "")
            return {"answer": f"Not as things stand: about {_hm(facts['shortfall_minutes'])} would be left over. {alt}".strip(), "follow_ups": [], "suggest_action": "none"}
        if level == "tight":
            return {"answer": "It fits, but with little slack. If a task takes longer than expected you could slip, so protecting your planned sessions matters.", "follow_ups": [], "suggest_action": "none"}
        if level == "comfortable":
            return {"answer": "Yes, it fits with room to spare if you keep to the planned sessions.", "follow_ups": [], "suggest_action": "none"}
    if intent in ("today",) and today:
        s = today[0]
        return {"answer": f"Start with “{s['title']}”: {s['stage']}, {s['minutes']} minutes. {len(today)} block{'s' if len(today) != 1 else ''} planned today.", "follow_ups": [], "suggest_action": "none"}
    if intent == "why_first":
        n = narrate_local(facts)
        return {"answer": n["why"] or n["what_first"], "follow_ups": [], "suggest_action": "none"}
    if intent == "hours":
        return {"answer": f"All remaining work adds up to about {_hm(facts.get('total_minutes', 0))}; you have about {_hm(facts.get('capacity_minutes', 0))} of study time before the deadlines.", "follow_ups": [], "suggest_action": "none"}
    if intent == "focus":
        return {"answer": "Try the smallest possible start: ten minutes on the first step of today's first block, then decide whether to continue. The Toolkit has more ideas, with their limits.",
                "follow_ups": [], "suggest_action": "open_toolkit"}
    n = narrate_local(facts)
    return {"answer": (n["headline"] + " " + n["what_first"]).strip() + " (The AI assistant is not available for open questions right now, so this is a summary of your plan.)",
            "follow_ups": [], "suggest_action": "none"}


def review_local(stats: dict) -> dict:
    s = stats
    if not s.get("sessions") and not s.get("tasks_completed"):
        return {"summary": "There is not enough data this week to review. Log a study session or finish a task and the review will fill in.",
                "went_well": [], "to_improve": [], "next_week": ["Add your tasks in the Smart Planner and do one planned block."]}
    went, improve, nxt = [], [], []
    summary = (f"This week you studied {_hm(s['minutes_studied'])} in {s['sessions']} session{'s' if s['sessions'] != 1 else ''} and finished "
               f"{s['tasks_completed']} task{'s' if s['tasks_completed'] != 1 else ''}.")
    if s.get("completion_rate") is not None and s["completion_rate"] >= 0.8:
        went.append(f"You finished {round(s['completion_rate'] * 100)}% of the sessions you started.")
    if s.get("avg_focus") is not None and s["avg_focus"] >= 3.5:
        went.append(f"Your focus ratings averaged {s['avg_focus']:.1f} out of 5.")
    if s.get("plan_adherence") is not None and s["plan_adherence"] >= 0.7:
        went.append(f"You did {round(s['plan_adherence'] * 100)}% of the planned minutes.")
    if s.get("plan_adherence") is not None and s["plan_adherence"] < 0.5:
        improve.append(f"Only {round(s['plan_adherence'] * 100)}% of the planned minutes were done. Shorter plans may suit this week better.")
        nxt.append("Lower your daily minutes a little in Settings and aim to keep every planned block.")
    if s.get("avg_focus") is not None and s["avg_focus"] < 2.8:
        improve.append(f"Focus ratings were low ({s['avg_focus']:.1f} out of 5). Shorter blocks or a different time of day might help.")
    if s.get("estimate_ratio") and abs(s["estimate_ratio"] - 1) > 0.25:
        word = "longer" if s["estimate_ratio"] > 1 else "shorter"
        improve.append(f"Tasks took about {round(abs(s['estimate_ratio'] - 1) * 100)}% {word} than estimated; the planner now takes that into account.")
    if s.get("goal_hours") and s.get("minutes_studied") is not None:
        pct = round(100 * s["minutes_studied"] / (s["goal_hours"] * 60))
        (went if pct >= 100 else improve).append(f"You reached {pct}% of your weekly goal of {s['goal_hours']:g} hours.")
    if not nxt:
        nxt.append("Keep your next planned block small and start it at the same time each day.")
    return {"summary": summary, "went_well": went[:3], "to_improve": improve[:3], "next_week": nxt[:3]}
