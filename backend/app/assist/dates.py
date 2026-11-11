"""
A small, careful reader for dates in plain English ("by Friday", "in 10 days", "12 Nov", "tomorrow 5pm").
It is used only by the local fallback. If it is not sure, it returns None and the planner asks the student instead of
guessing. Pure functions: the caller supplies today's date.
"""
import re
from datetime import date, timedelta
from typing import Optional

_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
_MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
_WORDNUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            "eleven": 11, "twelve": 12, "fourteen": 14, "fifteen": 15, "twenty": 20, "thirty": 30}


def _num(s: str) -> Optional[int]:
    s = s.lower()
    return int(s) if s.isdigit() else _WORDNUM.get(s)


def _hour(text: str) -> Optional[int]:
    m = re.search(r"\b(?:at|by|before)?\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", text)
    if m:
        h = int(m.group(1)) % 12 + (12 if m.group(3) == "pm" else 0)
        return h if 0 <= h <= 23 else None
    m = re.search(r"\b(?:at|by)\s*(\d{1,2}):(\d{2})\b", text)
    if m and int(m.group(1)) <= 23:
        return int(m.group(1))
    if re.search(r"\bnoon\b|\bmidday\b", text):
        return 12
    if re.search(r"\bmidnight\b|\bend of (?:the )?day\b|\beod\b", text):
        return 23
    return None


def parse_deadline(text: str, today: date) -> tuple[Optional[date], Optional[int]]:
    """Return (date, hour) or (None, None). The date is never earlier than today."""
    t = " " + re.sub(r"\s+", " ", text.lower()) + " "
    hour = _hour(t)
    found: Optional[date] = None

    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", t)
    if m:
        try:
            found = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            found = None
    if found is None:
        m = re.search(r"\bin (\w+) (day|days|week|weeks)\b", t)
        if m and _num(m.group(1)):
            n = _num(m.group(1)) * (7 if m.group(2).startswith("week") else 1)
            found = today + timedelta(days=n)
    if found is None:
        m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)? (?:of )?(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", t)
        mon_first = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* (\d{1,2})(?:st|nd|rd|th)?\b", t)
        d = mo = None
        if m:
            d, mo = int(m.group(1)), _MONTHS[m.group(2)]
        elif mon_first:
            d, mo = int(mon_first.group(2)), _MONTHS[mon_first.group(1)]
        if d and mo:
            for yr in (today.year, today.year + 1):
                try:
                    cand = date(yr, mo, d)
                except ValueError:
                    continue
                if cand >= today:
                    found = cand
                    break
    if found is None:
        m = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", t)      # day/month (UK order, as the project's users are in the UK/DK)
        if m:
            d, mo = int(m.group(1)), int(m.group(2))
            yr = int(m.group(3)) if m.group(3) else None
            if yr is not None and yr < 100:
                yr += 2000
            for y in ([yr] if yr else [today.year, today.year + 1]):
                try:
                    cand = date(y, mo, d)
                except ValueError:
                    continue
                if cand >= today:
                    found = cand
                    break
    if found is None:
        if re.search(r"\btoday\b|\btonight\b", t):
            found = today
        elif re.search(r"\btomorrow\b", t):
            found = today + timedelta(days=1)
        elif re.search(r"\bnext week\b", t):
            found = today + timedelta(days=7)
        elif re.search(r"\bend of (?:the )?week\b", t):
            found = today + timedelta(days=(4 - today.weekday()) % 7)
    if found is None:
        for i, name in enumerate(_DAYS):
            # the full name is enough; a 3-letter form ("fri") only counts after a cue word, so "I sat down" is not a date
            m = re.search(rf"\b(next )?{name}\b", t) or re.search(rf"\b(?:by|on|due|before|this|next)\s+(?:(next)\s+)?{name[:3]}\b", t)
            if m:
                delta = (i - today.weekday()) % 7 or 7
                if m.lastindex and m.group(1):
                    delta += 7
                found = today + timedelta(days=delta)
                break
    if found is not None and found < today:
        found = None
    return found, (hour if found is not None else None)
