"""Strict JSON schemas sent to the model, and the validators that check what comes back (the model's word is never trusted)."""
from datetime import date, timedelta
from typing import Optional

from app.taskaware import taxonomy as T

from .sanitize import _BAD_OUTPUT, _INJ, clean_text, numbers_supported, safe_output_text

KINDS = sorted(T.KINDS)
SIZES = ["tiny", "small", "medium", "large", "huge"]
ACTIONS = ["none", "replan", "add_break", "open_toolkit", "check_in"]


def _obj(props: dict) -> dict:
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


_S, _I = {"type": "string"}, {"type": "integer"}
_NI, _NS = {"type": ["integer", "null"]}, {"type": ["string", "null"]}

UNDERSTAND_SCHEMA = _obj({
    "tasks": {"type": "array", "items": _obj({
        "title": _S, "details": _S, "kind": {"type": "string", "enum": KINDS}, "deadline_date": _NS, "deadline_hour": _NI,
        "size": {"type": ["string", "null"], "enum": SIZES + [None]}, "felt_hard": _NI,
        "estimate_low_minutes": _NI, "estimate_likely_minutes": _NI, "estimate_high_minutes": _NI,
        "subtasks": {"type": "array", "items": _obj({"title": _S, "share_percent": _I, "how": _S})}})},
    "questions": {"type": "array", "items": _obj({"id": _S, "text": _S, "why": _S})},
    "summary": _S})

NARRATE_SCHEMA = _obj({"headline": _S, "what_first": _S, "why": _S, "risks": {"type": "array", "items": _S},
                       "tips": {"type": "array", "items": _S}})
ANSWER_SCHEMA = _obj({"answer": _S, "follow_ups": {"type": "array", "items": _S},
                      "suggest_action": {"type": "string", "enum": ACTIONS}})
REVIEW_SCHEMA = _obj({"summary": _S, "went_well": {"type": "array", "items": _S}, "to_improve": {"type": "array", "items": _S},
                      "next_week": {"type": "array", "items": _S}})


class Invalid(ValueError):
    pass


def _int_or_none(v, lo: int, hi: int) -> Optional[int]:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    v = int(v)
    return v if lo <= v <= hi else None


def _foreign(text: str, student_text: str) -> bool:
    """True when the MODEL wrote a link, markup, a key-like string or an instruction-like phrase that the STUDENT did not type."""
    mine = student_text or ""
    return bool((_BAD_OUTPUT.search(text) and not _BAD_OUTPUT.search(mine)) or (_INJ.search(text) and not _INJ.search(mine)))


def validate_understand(raw: dict, today: date, student_text: str = "") -> dict:
    if not isinstance(raw, dict) or not isinstance(raw.get("tasks"), list):
        raise Invalid("tasks missing")
    tasks = []
    for t in raw["tasks"][:6]:
        if not isinstance(t, dict):
            continue
        title = clean_text(t.get("title"), 200)
        if not title or _foreign(title, student_text) or _foreign(str(t.get("details") or ""), student_text):
            continue
        kind = t.get("kind") if t.get("kind") in T.KINDS else "general"
        dd = None
        if isinstance(t.get("deadline_date"), str):
            try:
                d = date.fromisoformat(t["deadline_date"][:10])
                dd = d if today <= d <= today + timedelta(days=730) else None
            except ValueError:
                dd = None
        low, likely, high = (_int_or_none(t.get(k), 5, 6000) for k in ("estimate_low_minutes", "estimate_likely_minutes", "estimate_high_minutes"))
        if not (low and likely and high and low <= likely <= high):
            low = likely = high = None
        subs = []
        for s in (t.get("subtasks") or [])[:8]:
            try:
                st = safe_output_text(s.get("title"), 120)
                how = safe_output_text(s.get("how") or "-", 300)
                sp = _int_or_none(s.get("share_percent"), 1, 100)
            except (ValueError, AttributeError):
                subs = []
                break
            if sp is None:
                subs = []
                break
            subs.append({"title": st, "share_percent": sp, "how": "" if how == "-" else how})
        if not 3 <= len(subs) <= 8:
            subs = []
        tasks.append({"title": title, "details": clean_text(t.get("details"), 1000), "kind": kind, "deadline_date": dd,
                      "deadline_hour": _int_or_none(t.get("deadline_hour"), 0, 23) if dd else None,
                      "size": t.get("size") if t.get("size") in SIZES else None, "felt_hard": _int_or_none(t.get("felt_hard"), 1, 5),
                      "low": low, "likely": likely, "high": high, "subtasks": subs})
    if not tasks:
        raise Invalid("no usable task")
    qs = []
    for q in (raw.get("questions") or [])[:3]:
        try:
            qs.append({"id": clean_text(q.get("id"), 30) or f"q{len(qs) + 1}", "text": safe_output_text(q.get("text"), 220),
                       "why": safe_output_text(q.get("why") or "It helps me plan better.", 220)})
        except (ValueError, AttributeError):
            continue
    try:
        summary = safe_output_text(raw.get("summary") or "", 400)
    except ValueError:
        summary = ""
    return {"tasks": tasks, "questions": qs, "summary": summary}


def _items(v, n: int, each: int) -> list:
    out = []
    for x in (v or [])[:n]:
        out.append(safe_output_text(x, each))
    return out


def validate_narrate(raw: dict, facts) -> dict:
    try:
        out = {"headline": safe_output_text(raw.get("headline"), 140), "what_first": safe_output_text(raw.get("what_first"), 320),
               "why": safe_output_text(raw.get("why"), 420), "risks": _items(raw.get("risks"), 3, 220), "tips": _items(raw.get("tips"), 3, 220)}
    except (ValueError, AttributeError, TypeError) as e:
        raise Invalid(str(e))
    joined = " ".join([out["headline"], out["what_first"], out["why"], *out["risks"], *out["tips"]])
    if not numbers_supported(joined, facts):
        raise Invalid("number not in facts")
    return out


def validate_answer(raw: dict, facts) -> dict:
    try:
        out = {"answer": safe_output_text(raw.get("answer"), 800), "follow_ups": _items(raw.get("follow_ups"), 3, 120),
               "suggest_action": raw.get("suggest_action") if raw.get("suggest_action") in ACTIONS else "none"}
    except (ValueError, AttributeError, TypeError) as e:
        raise Invalid(str(e))
    if not numbers_supported(out["answer"], facts):
        raise Invalid("number not in facts")
    return out


def validate_review(raw: dict, facts) -> dict:
    try:
        out = {"summary": safe_output_text(raw.get("summary"), 560), "went_well": _items(raw.get("went_well"), 3, 220),
               "to_improve": _items(raw.get("to_improve"), 3, 220), "next_week": _items(raw.get("next_week"), 3, 220)}
    except (ValueError, AttributeError, TypeError) as e:
        raise Invalid(str(e))
    joined = " ".join([out["summary"], *out["went_well"], *out["to_improve"], *out["next_week"]])
    if not numbers_supported(joined, facts):
        raise Invalid("number not in facts")
    return out
