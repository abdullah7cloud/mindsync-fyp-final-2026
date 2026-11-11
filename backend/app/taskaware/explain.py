"""
Step 6 - say why, in plain language.

Every sentence is filled from a number or fact the engine actually used. If something was not known, the sentence
says so instead of sounding sure. Templates only: no generated text, no invented requirements, and the plan never
claims to have read material the student did not supply.
"""
from . import difficulty as D
from . import taxonomy as T


def _hours(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} minutes"
    h, m = divmod(minutes, 60)
    if m == 0:
        return f"{h} hour{'s' if h != 1 else ''}"
    return f"{h} h {m} min"


def understanding(analysis) -> str:
    if not analysis.kind_known:
        return "I could not tell what kind of work this is from the words you gave, so I am treating it as a general study task."
    parts = []
    for km in analysis.kinds:
        ev = ", ".join(f"'{e}'" for e in km.evidence[:3])
        parts.append(f"{T.KINDS[km.kind]['label'].lower()} (because of {ev})" if ev else T.KINDS[km.kind]["label"].lower())
    text = "I read this as " + " plus ".join(parts) + "."
    if analysis.subjects:
        text += f" The subject is {T.KINDS[analysis.subjects[0]]['label'].lower()}."
    return text


def difficulty_text(diff: D.Difficulty, skill_label: str) -> str:
    base = f"For an average student this is {D.label(diff.intrinsic)} ({diff.intrinsic:.1f} out of 5)."
    if diff.skill_known:
        mine = f" For you it is {D.label(diff.personal)} ({diff.personal:.1f} out of 5)."
    else:
        mine = (f" I do not know your experience with {skill_label}, so for you it could be anywhere between "
                f"{D.label(diff.low)} and {D.label(diff.high)}.")
    why = " Reasons: " + "; ".join(diff.reasons) + "." if diff.reasons else ""
    return base + mine + why


def workload_text(w, analysis, cal: dict) -> str:
    if w.likely == 0:
        return "Nothing is left to plan: you said it is finished."
    basis = {"counts": "I used the amounts you gave (" + ", ".join(f"{int(n) if n == int(n) else n} {u}{'s' if n != 1 else ''}" for n, u in analysis.counts) + ")",
             "deliverables": f"I counted the {len(analysis.deliverables)} parts you listed",
             "size": f"I used the usual effort for a {analysis.size} {T.KINDS[analysis.primary]['label'].lower()} task"}[w.basis]
    text = f"About {_hours(w.likely)} of focused work in total (probably between {_hours(w.low)} and {_hours(w.high)}). {basis}."
    if w.already_done:
        text += f" You said about {int(round(w.already_done * 100))}% is already done, so that part is not planned again."
    return text


def history_text(cal: dict, kind_label: str) -> str:
    if cal["basis"] == "none":
        return "You have no finished tasks of this kind yet, so this is a general estimate. It will improve as you log how long tasks really take."
    ratio = cal["typical_ratio"]
    change = round((cal["factor"] - 1) * 100)
    scope = f"your last {cal['n']} {kind_label.lower()} task{'s' if cal['n'] != 1 else ''}" if cal["basis"] == "kind" else f"your last {cal['n']} tasks of all kinds"
    if abs(change) < 3:
        return f"Based on {scope}, your estimates have been about right, so I did not change this one."
    word = "longer" if change > 0 else "shorter"
    cautious = " Only a few results so far, so I changed it only part of the way." if cal["n"] < 5 else ""
    return (f"Based on {scope}, tasks took about {ratio:.1f} times my first estimate, so I made this estimate {abs(change)}% {word}."
            + cautious)


def uncertainty_list(analysis, skill, answers, skipped, has_deadline, hours_defaulted, history_n) -> list:
    out = []
    if not analysis.kind_known:
        out.append("The kind of work was not clear.")
    if not analysis.scope_known:
        out.append("I do not know exactly what has to be finished, so the size is a guess.")
    if skill is None and analysis.primary != "admin":
        out.append("I do not know how experienced you are, so the estimate range is wider.")
    if hours_defaulted:
        out.append("You did not say how much time you have each day, so I assumed 2 hours.")
    if not has_deadline:
        out.append("There is no deadline, so I cannot check that the plan fits.")
    if history_n == 0:
        out.append("There are no finished tasks of this kind to learn from yet.")
    for q in sorted(skipped):
        out.append(f"You skipped a question ({q}), so I used a default.")
    return out


def session_text(label: str, minutes: int, why: str, break_after: int) -> str:
    br = f" then a {break_after}-minute break" if break_after else " with no scheduled break"
    return f"{minutes} minutes ({why}){br}."
