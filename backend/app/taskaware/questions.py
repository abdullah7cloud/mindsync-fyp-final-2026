"""
Step 0 - ask instead of guessing.

If the text does not say enough, return the few questions whose answers would change the plan most, at most
three at a time. Nothing is asked twice: an answered or skipped question is never asked again, and a skipped one
simply widens the estimate range and is mentioned as an uncertainty.

Blocking questions (the plan would be a guess without them): the kind of work, what has to be finished, how
experienced the student is, the deadline, and - for big tasks - how much is already done. Not blocking (a default is
used and shown): study hours per day.
"""
from dataclasses import dataclass, field

from . import taxonomy as T

MAX_QUESTIONS = 3
CONTINUE_WORDS = ("complete", "finish", "continue", "rest of", "remaining", "left to", "working on", "carry on")

KIND_CHOICES = [("programming", "Programming / coding"), ("mathematics", "Maths problems"), ("writing", "Writing (essay, report)"),
                ("exam", "Exam revision"), ("reading", "Reading"), ("presentation", "Presentation"),
                ("data", "Data analysis"), ("admin", "A quick admin job")]
SKILL_CHOICES = [(1, "Complete beginner"), (2, "I know a little"), (3, "Comfortable"), (4, "Good"), (5, "Very experienced")]
PROGRESS_CHOICES = [("none", "Nothing yet"), ("some", "A little (about a quarter)"), ("half", "About half"), ("most", "Most of it")]
HOURS_CHOICES = [(30, "30 minutes"), (60, "1 hour"), (120, "2 hours"), (180, "3 hours"), (240, "4 hours")]

SCOPE_TEXT = {
    "programming": ("What kind of project is it, and which features must be finished? Put one feature on each line.", "A login page\nSave data to a file\nUnit tests"),
    "mathematics": ("Which topics or how many problems do you need to cover?", "Integration by parts, 12 problems"),
    "writing": ("What is the question or topic, and how long must it be?", "2,000 words on renewable energy policy"),
    "exam": ("Which topics does the exam cover? Put one topic on each line.", "Limits\nDerivatives\nIntegrals"),
    "reading": ("How many pages or chapters do you need to read?", "Chapters 3 and 4, about 40 pages"),
    "presentation": ("How many slides or minutes is it, and what is it about?", "10 slides on our group project"),
    "data": ("What questions must the analysis answer, and how big is the data?", "Compare sales by region; 5,000 rows"),
    "general": ("What exactly needs to be finished? List the main parts, one per line.", "First part\nSecond part"),
}


@dataclass
class Question:
    id: str
    text: str
    type: str                 # choice | text | date
    options: list = field(default_factory=list)      # [(value, label)]
    why: str = ""
    placeholder: str = ""
    blocking: bool = True


def next_questions(analysis, *, answers: dict, skipped: set, skill: int | None, has_deadline: bool, has_hours: bool) -> list:
    out: list[Question] = []

    def open_(qid):
        return qid not in answers and qid not in skipped

    kind = analysis.primary
    if not analysis.kind_known and open_("kind"):
        out.append(Question("kind", "What kind of work is this?", "choice", KIND_CHOICES,
                            "The title is too short for me to tell, and the plan is very different for each kind."))
    if not analysis.scope_known and open_("scope"):
        text, ph = SCOPE_TEXT.get(kind, SCOPE_TEXT["general"])
        out.append(Question("scope", text, "text", [], "Two tasks with the same title can need 2 hours or 20 hours.", ph))
    continuing = any(w in (analysis.title + " " + analysis.details).lower() for w in CONTINUE_WORDS)
    needs_progress = analysis.size in ("large", "huge") and not analysis.counts and (continuing or not analysis.scope_known)
    if needs_progress and open_("progress"):
        out.append(Question("progress", "How much have you already finished?", "choice", PROGRESS_CHOICES,
                            "Finished work does not need to be planned again."))
    if skill is None and kind != "admin" and open_("skill"):
        label = T.KINDS[analysis.skill_kind]["skill"]
        out.append(Question("skill", f"How experienced are you with {label}?", "choice", SKILL_CHOICES,
                            "The same task takes a beginner much longer than an experienced student."))
    if not has_deadline and open_("deadline"):
        out.append(Question("deadline", "When is it due?", "date", [], "I need the deadline to spread the work over the days you have."))
    order = {"kind": 0, "scope": 1, "progress": 2, "skill": 3, "deadline": 4}
    out.sort(key=lambda q: order[q.id])
    return out[:MAX_QUESTIONS]


def optional_hours_question() -> Question:
    return Question("daily_minutes", "How much time can you study on a normal day?", "choice", HOURS_CHOICES,
                    "Used to check the work fits before the deadline.", blocking=False)
