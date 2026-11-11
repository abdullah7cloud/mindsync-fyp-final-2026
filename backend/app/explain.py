"""
Plain-English explanation of a recommendation.

Why this file exists
--------------------
A ranking is only useful if the student understands WHY a task is on top.
The explanation is built from the numbers the local models already computed
(deadline urgency, energy match, the trained model's probability), using fixed
sentence templates. It is therefore:

  * 100% local and offline - no external AI service is called, ever;
  * deterministic - the same input always gives the same text, so it can be
    unit-tested and defended in the viva;
  * honest - every claim in the sentence is read directly from a number
    (nothing is invented).
"""
from typing import Optional


def _deadline_phrase(deadline_score: float) -> str:
    # deadline_score is 1.0 when the task is overdue or due within 24 h and decays towards 0.
    if deadline_score >= 0.99:
        return "its deadline is very close (or already passed)"
    if deadline_score >= 0.5:
        return "its deadline is coming up soon"
    return "its deadline is still some way off"


def _energy_phrase(difficulty: int, energy: int, energy_match: float) -> str:
    if energy_match >= 0.99:
        return f"its difficulty ({difficulty}/5) exactly matches your energy ({energy}/5)"
    if energy_match >= 0.7:
        return f"its difficulty ({difficulty}/5) is close to your energy ({energy}/5)"
    if difficulty > energy:
        return f"it is harder ({difficulty}/5) than your current energy ({energy}/5), but it cannot wait"
    return f"it is easier ({difficulty}/5) than your current energy ({energy}/5), so it is a low-risk start"


def _hours(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} minutes"
    h, m = divmod(minutes, 60)
    return f"{h} hour{'s' if h != 1 else ''}" if m == 0 else f"{h} h {m} min"


def _effort_phrase(effort: int, breakdown: dict) -> str:
    text = f"It needs about {_hours(effort)} of work"
    if breakdown.get("effort_confidence") == "low":
        text += " (a rough guess: you have not told me much about it)"
    per_day = breakdown.get("hours_per_day_needed")
    if breakdown.get("pressure", 0) >= 0.7 and per_day and per_day != float("inf"):
        text += f", so you need to spend around {per_day:.1f} hours a day on it to finish on time"
    return text + "."


def explain_recommendation(
    top_title: Optional[str],
    top_difficulty: Optional[int],
    breakdown: dict,
    energy_level: int,
    burnout_mode: bool,
    burnout_reason: Optional[str] = None,
) -> str:
    """Build the sentence(s) shown under the top recommended task."""
    if top_title is None:
        if burnout_mode:
            return ("Burnout Mode is on, so only light tasks are shown, and you have none right now. "
                    "A proper break is a good use of time.")
        return "You have no pending tasks. Add one above to get a recommendation."

    parts = []
    if burnout_mode:
        why = ("your latest wellbeing check estimated a high stress level"
               if burnout_reason == "high_stress_risk" else "your latest energy check-in was low")
        parts.append(f"Burnout Mode is on because {why}, so only lighter tasks are suggested.")

    reasons = [
        _deadline_phrase(breakdown.get("deadline_score", 0.0)),
        _energy_phrase(top_difficulty or 3, energy_level, breakdown.get("energy_match_score", 0.0)),
    ]
    parts.append(f"'{top_title}' is first because {reasons[0]} and {reasons[1]}.")

    effort = breakdown.get("effort_minutes")
    if effort:
        parts.append(_effort_phrase(effort, breakdown))
    ml = breakdown.get("ml_score")
    if ml is not None:
        parts.append(f"The trained task-fit model estimates a {round(ml * 100)}% chance this is a good fit right now.")
    return " ".join(parts)
