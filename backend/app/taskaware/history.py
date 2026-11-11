"""
Step 4 - learn from what already happened (per student, per kind of work).

Two small statistical estimators, both explainable and both protected against reacting to one odd result:

1. Workload calibration. Every finished task gives a ratio actual / estimated. The estimate is multiplied by a
   shrunk, robust average of those ratios (computed on logs, each log capped at +-1 which is about 2.7x).
   With few outcomes the weight is small: n / (n + 3), so a single unusual task moves the estimate by at most
   about a quarter of its size.  The kind's own history is used when it has at least two outcomes; otherwise the
   student's history across all kinds is used with a much smaller weight n / (n + 6), and the explanation says so.

2. Preferred session length (per kind only). Sessions are grouped into length bands; a band is preferred only
   when it has enough sessions and a clearly better completion rate than the usual band. A preference found for
   reading is NEVER applied to programming.

The estimates are made against the model's RAW estimate (before calibration) so correcting the estimate does not
cancel the evidence that caused the correction.
"""
import math
from dataclasses import dataclass
from typing import Optional

LOG_CAP = 1.0
K_KIND = 3.0
K_GLOBAL = 6.0
MIN_FACTOR, MAX_FACTOR = 0.5, 2.5
BANDS = [(5, 20), (21, 35), (36, 55), (56, 90), (91, 240)]
MIN_SESSIONS_TOTAL = 6
MIN_SESSIONS_BAND = 3
MIN_RATE_GAIN = 0.15


@dataclass(frozen=True)
class Outcome:
    kind: str
    raw_minutes: float            # the engine's own estimate before calibration
    actual_minutes: float
    felt: Optional[int] = None    # how hard it felt 1-5 (optional)
    predicted_personal: Optional[float] = None


@dataclass(frozen=True)
class SessionRecord:
    kind: str
    minutes: int
    completed: bool
    focus: Optional[int] = None   # 1-5, optional


def _logs(outcomes: list) -> list:
    out = []
    for o in outcomes:
        if o.raw_minutes > 0 and o.actual_minutes > 0:
            out.append(max(-LOG_CAP, min(LOG_CAP, math.log(o.actual_minutes / o.raw_minutes))))
    return out


def _robust_location(logs: list) -> float:
    s = sorted(logs)
    n = len(s)
    if n == 0:
        return 0.0
    if n >= 5:                      # drop the single highest and lowest value
        s = s[1:-1]
        return sum(s) / len(s)
    if n >= 3:                      # median
        return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
    return sum(s) / n


def calibration(kind: str, outcomes: list) -> dict:
    """{'factor', 'basis': none|kind|all, 'n', 'typical_ratio'}"""
    mine = _logs([o for o in outcomes if o.kind == kind])
    if len(mine) >= 2:
        m, n, k, basis = _robust_location(mine), len(mine), K_KIND, "kind"
    else:
        allk = _logs(outcomes)
        if len(allk) >= 2:
            m, n, k, basis = _robust_location(allk), len(allk), K_GLOBAL, "all"
        elif len(mine) == 1:
            m, n, k, basis = mine[0], 1, K_KIND, "kind"
        else:
            return {"factor": 1.0, "basis": "none", "n": 0, "typical_ratio": 1.0}
    weight = n / (n + k)
    factor = max(MIN_FACTOR, min(MAX_FACTOR, math.exp(weight * m)))
    return {"factor": round(factor, 3), "basis": basis, "n": n, "typical_ratio": round(math.exp(m), 2)}


def _band(minutes: int) -> int:
    for i, (lo, hi) in enumerate(BANDS):
        if lo <= minutes <= hi:
            return i
    return len(BANDS) - 1


def _ok(s: SessionRecord) -> bool:
    return s.completed and (s.focus is None or s.focus >= 3)


def preferred_session(kind: str, sessions: list, baseline_minutes: int) -> Optional[dict]:
    """{'minutes', 'band', 'rate', 'baseline_rate', 'n'} or None when there is no clear preference for this kind."""
    mine = [s for s in sessions if s.kind == kind]
    if len(mine) < MIN_SESSIONS_TOTAL:
        return None
    by_band: dict[int, list] = {}
    for s in mine:
        by_band.setdefault(_band(s.minutes), []).append(s)

    def rate(items):
        return (sum(1 for s in items if _ok(s)) + 1) / (len(items) + 2)

    base_band = _band(baseline_minutes)
    base_items = by_band.get(base_band, [])
    base_rate = rate(base_items) if base_items else 0.5
    best_band, best_rate = None, 0.0
    for b, items in sorted(by_band.items()):
        if len(items) >= MIN_SESSIONS_BAND and rate(items) > best_rate:
            best_band, best_rate = b, rate(items)
    if best_band is None or best_band == base_band or best_rate - base_rate < MIN_RATE_GAIN:
        return None
    mins = sorted(s.minutes for s in by_band[best_band])
    median = mins[len(mins) // 2]
    return {"minutes": int(round(median / 5.0) * 5), "band": BANDS[best_band], "rate": round(best_rate, 2),
            "baseline_rate": round(base_rate, 2), "n": len(by_band[best_band])}
