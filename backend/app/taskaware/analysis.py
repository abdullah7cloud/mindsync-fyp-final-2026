"""
Step 1 - read the task text.

Finds (a) which kinds of work the text points to, with the words that were the evidence, (b) how big the task
looks (counts such as "2000 words", a list of deliverables, or size words such as "project"), and (c) technical
cues. It never assumes the kind can always be read from a short title: when the evidence is weak the kind is
reported as unknown with a low confidence, which makes the engine ask instead of guess.
"""
import re
from dataclasses import dataclass, field

from . import taxonomy as T

_NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
                 "ten": 10, "twelve": 12, "fifteen": 15, "twenty": 20}
_UNITS = "|".join(sorted(T.UNIT_WORDS, key=len, reverse=True))
_COUNT_RE = re.compile(rf"(?<![\w.])(\d+(?:[.,]\d+)?|{'|'.join(_NUMBER_WORDS)})\s*(k\b)?[\s-]*({_UNITS})\b", re.I)
# "chapters 1 to 6" (a numbered range after the unit) and "5 to 8 pages" (a range before it)
_RANGE_AFTER_RE = re.compile(rf"\b({_UNITS})\s+(\d+)\s*(?:to|through|-|–)\s*(\d+)\b", re.I)
_RANGE_BEFORE_RE = re.compile(rf"(?<![\w.])(\d+)\s*(?:to|-|–)\s*(\d+)\s*({_UNITS})\b", re.I)
_LEAD_I = re.compile(r"^(?:and\s+)?(?:i|we)\s+(?:also\s+)?(?:have|need|want|must|should|will|am going|have got)\s+to\s+", re.I)
_SPLIT_RE = re.compile(r"[\n;]+|(?:^|\s)(?:\d+[.)]|[-*•])\s+|,\s+|\s+and\s+|\s+then\s+|\s+(?:with|including|plus)\s+")
# a fragment that only says when it is due is not a piece of work
_WHEN_RE = re.compile(r"^(?:due|by|before|until|in\s+\d+\s+(?:days?|weeks?)|tomorrow|today|tonight|next\s+\w+|this\s+\w+|on\s+\w+day)\b", re.I)


@dataclass
class KindMatch:
    kind: str
    score: float
    evidence: list = field(default_factory=list)


@dataclass
class TaskAnalysis:
    title: str
    details: str
    kinds: list                      # [KindMatch] best first; ["general"] with low score when unknown
    kind_confidence: float
    kind_known: bool
    counts: list                     # [(number, unit)]
    deliverables: list               # list of short strings
    size: str                        # tiny|small|medium|large|huge
    size_source: str                 # answer|count|cue|default
    scope_known: bool
    hard_cues: list
    easy_cues: list
    words: int
    subjects: list = field(default_factory=list)   # e.g. 'mathematics' for a mathematics exam

    @property
    def primary(self) -> str:
        return self.kinds[0].kind

    @property
    def skill_kind(self) -> str:
        """The kind whose skill rating applies: the subject of an exam, otherwise the main kind."""
        return self.subjects[0] if self.subjects else self.kinds[0].kind


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def _find(phrase: str, text: str) -> bool:
    return re.search(rf"(?<![\w+#]){re.escape(phrase)}(?![\w+#])", text) is not None


def classify(title: str, details: str = "") -> tuple[list, float, bool]:
    """Returns (matches best-first, confidence of the best, whether any kind was recognised)."""
    t, d = _norm(title), _norm(details)
    scores: dict[str, list] = {}
    for kind, words in T.LEXICON.items():
        hits = []
        for phrase, w in words.items():
            in_title, in_details = _find(phrase, t), _find(phrase, d)
            if not (in_title or in_details):
                continue
            blocked = T.BLOCK_FOR.get((kind, phrase))
            if blocked and any(_find(b, t + " " + d) for b in blocked):
                continue
            hits.append((phrase, w if in_title else w * 0.7))
        if hits:
            prod = 1.0
            for _, w in hits:
                prod *= 1.0 - w
            scores[kind] = [round(1.0 - prod, 3), sorted(h[0] for h in hits)]
    # a quick admin word beats weak study words ("email my tutor about the exam" is still an email), but not strong ones
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1][0], kv[0]))
    if not ranked or ranked[0][1][0] < 0.4:
        top = ranked[0][1][0] if ranked else 0.0
        return [KindMatch("general", top, ranked[0][1][1] if ranked else [])], top, False
    best = ranked[0][1][0]
    matches = [KindMatch(k, v[0], v[1]) for k, v in ranked if v[0] >= 0.45 and v[0] >= 0.5 * best][:3]
    return matches, best, True


def extract_counts(text: str) -> list:
    out = []
    # ranges are read first and blanked out so "1 to 6" is not also read as "6 chapters" a second time
    def _range_after(m):
        a, b = int(m.group(2)), int(m.group(3))
        if 0 < b - a + 1 <= 200 and b > a:
            out.append((float(b - a + 1), T.UNIT_WORDS[m.group(1).lower()]))
        return " "
    def _range_before(m):
        a, b = float(m.group(1)), float(m.group(2))
        if 0 < a < b <= 100000:
            out.append(((a + b) / 2.0, T.UNIT_WORDS[m.group(3).lower()]))
        return " "
    text = _RANGE_AFTER_RE.sub(_range_after, text or "")
    text = _RANGE_BEFORE_RE.sub(_range_before, text)
    for m in _COUNT_RE.finditer(text):
        raw = m.group(1).lower()
        num = _NUMBER_WORDS.get(raw)
        if num is None:
            num = float(raw.replace(",", "."))
        if m.group(2):
            num *= 1000
        if 0 < num <= 100000:
            out.append((num, T.UNIT_WORDS[m.group(3).lower()]))
    return out


def extract_deliverables(details: str) -> list:
    """Items the student listed (one per line, numbered, or separated by commas / 'and')."""
    if not details:
        return []
    parts = [re.sub(r"^[\s\-*•\d.)]+", "", p).strip(" .") for p in _SPLIT_RE.split(details)]
    parts = [re.sub(r"^[A-Za-z ]{3,20}:\s+", "", p) for p in parts]      # "topics: limits" -> "limits"
    parts = [_LEAD_I.sub("", p) for p in parts]
    parts = [p for p in parts if not _WHEN_RE.match(p.strip())]                            # "I have to make the slides" -> "make the slides"
    items, seen = [], set()
    for p in parts:
        if 2 <= len(p) <= 120 and len(p.split()) >= 1 and p.lower() not in seen:
            seen.add(p.lower())
            items.append(p)
    return items[:12] if len(items) >= 2 else []


def infer_size(text: str, kind: str) -> tuple[str, bool]:
    """(size, found_a_cue). Checked from the biggest to the smallest cue so 'final year project' is not 'small'."""
    for size in ("huge", "large", "tiny", "small"):
        if any(_find(c, text) for c in T.SIZE_CUES[size]):
            return size, True
    if kind == "admin":
        return "tiny", True
    return "medium", False


def analyse(title: str, details: str = "", answers: dict | None = None) -> TaskAnalysis:
    answers = answers or {}
    # What the student typed in answer to the scope question counts as extra details.
    extra = " ".join(str(answers.get(k, "")) for k in ("scope",) if isinstance(answers.get(k), str))
    full_details = (details + "\n" + extra).strip()
    kinds, conf, known = classify(title, full_details)
    # an answer to "what kind of work is this?" overrides the guess
    chosen = answers.get("kind")
    if isinstance(chosen, str) and chosen in T.KINDS:
        kinds, conf, known = [KindMatch(chosen, 1.0, ["you told us"])], 1.0, True
    # "revise calculus for the exam": the exam is the work, mathematics is only the subject
    subjects = []
    if known and any(k.kind == "exam" for k in kinds) and len(kinds) > 1:
        subjects = [k.kind for k in kinds if k.kind in ("mathematics", "programming", "writing", "data")]
        kinds = [k for k in kinds if k.kind == "exam"]
    text = _norm(title + " " + full_details)
    counts = extract_counts(title + " " + full_details)
    deliverables = extract_deliverables(full_details)
    primary = kinds[0].kind
    size, cue = infer_size(text, primary)
    size_source = "cue" if cue else "default"
    if isinstance(answers.get("size"), str) and answers["size"] in T.SIZE_MULT:
        size, size_source, cue = answers["size"], "answer", True
    usable_counts = [c for c in counts if any((k.kind, c[1]) in T.UNIT_MINUTES for k in kinds)]
    if usable_counts and size_source != "answer":
        size_source = "count"
    words = len(re.findall(r"\w+", full_details))
    explicit_small = size in ("tiny", "small") and cue
    scope_known = bool(usable_counts) or len(deliverables) >= 2 or words >= 10 or size_source == "answer" or explicit_small \
        or primary == "admin"
    hard = [c for c in T.HARD_CUES if c in text]
    easy = [c for c in T.EASY_CUES if _find(c, text)]
    return TaskAnalysis(title=title.strip(), details=full_details, kinds=kinds, kind_confidence=round(conf, 3), kind_known=known,
                        counts=usable_counts, deliverables=deliverables, size=size, size_source=size_source,
                        scope_known=scope_known, hard_cues=hard, easy_cues=easy, words=words, subjects=subjects)
