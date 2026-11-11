"""Cleaning of student text before it goes into a prompt, and checks on model text before it goes to a student."""
import json
import re
import unicodedata

_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿‪‫‬‭‮"), None)
_DELIM = re.compile(r"</?\s*student_text[^>]*>", re.I)

INJECTION_PATTERNS = [
    r"ignore (all |any |the )?(previous|prior|above|earlier) (instructions|rules|prompts?)",
    r"disregard (all |any |the )?(previous|prior|above|earlier)",
    r"you are now\b", r"\bsystem prompt\b", r"reveal (your|the) (instructions|prompt|rules)",
    r"\bdeveloper mode\b", r"\bjailbreak\b", r"act as (an? )?(unrestricted|different)",
    r"api[_ -]?key", r"\bpassword\b.*\b(send|show|print)\b",
]
_INJ = re.compile("|".join(INJECTION_PATTERNS), re.I)


def clean_text(value, max_len: int) -> str:
    """Plain text only: no control characters, no hidden characters, no fake delimiters, bounded length."""
    s = unicodedata.normalize("NFKC", str(value or "")).translate(_ZERO_WIDTH)
    s = "".join(ch for ch in s if ch in "\n\t" or unicodedata.category(ch)[0] != "C")
    s = _DELIM.sub(" ", s)
    s = "\n".join(" ".join(line.split()) for line in s.splitlines())
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    return s[:max_len]


def injection_suspected(text: str) -> bool:
    return bool(_INJ.search(text or ""))


def wrap_student_text(text: str) -> str:
    return f"<student_text>\n{text}\n</student_text>"


# ---------- model output checks
_NUM = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)?")


def numbers_in(text: str) -> list:
    return [t.replace(",", ".") for t in _NUM.findall(text or "")]


def allowed_numbers(facts) -> set:
    """Every number that appears in the facts we gave the model, plus minutes shown as hours."""
    raw = json.dumps(facts, ensure_ascii=False, default=str)
    allowed = set()
    for tok in numbers_in(raw):
        allowed.add(tok)
        try:
            f = float(tok)
        except ValueError:
            continue
        allowed.add(str(int(f)) if f == int(f) else f"{f:g}")
        allowed.add(f"{f:.1f}".rstrip("0").rstrip("."))
        if f >= 5:
            allowed.add(f"{f / 60:.1f}".rstrip("0").rstrip("."))
            allowed.add(str(int(round(f / 60))))
        allowed.add(tok.lstrip("0") or "0")
    allowed.update({"0", "1", "2", "3"})      # "1 session", "2 steps": counting words are harmless
    return allowed


def numbers_supported(text: str, facts) -> bool:
    ok = allowed_numbers(facts)
    for tok in numbers_in(text):
        norm = tok.rstrip("0").rstrip(".") if "." in tok else tok
        if tok not in ok and norm not in ok and tok.lstrip("0") not in ok:
            return False
    return True


_BAD_OUTPUT = re.compile(r"https?://|www\.|<[a-z/!][^>]*>|```|\bapi[_ -]?key\b|\bsk-[A-Za-z0-9]{8,}", re.I)


def safe_output_text(text: str, max_len: int) -> str:
    """Returns the cleaned text or raises ValueError when it contains links, markup or key-like strings."""
    t = clean_text(text, max_len + 1)
    if not t or len(t) > max_len:
        raise ValueError("empty or too long")
    if _BAD_OUTPUT.search(t):
        raise ValueError("unsafe content")
    return t
