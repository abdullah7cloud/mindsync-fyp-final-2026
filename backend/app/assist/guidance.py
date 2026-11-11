"""
Study guidance for each topic: WHAT to understand, WHY it matters, the FIRST step, an approach, exercises, common mistakes and how to check
understanding. Pure rule-based text (no network, no language model), so it works offline and in milliseconds.

Honest label: this is written from the TYPE of work, the subject's name and the student's own answers (progress, understanding, days left).
It has NOT read the student's lecture notes or assignment brief, and it says so. An optional language-model layer may later rephrase it,
but nothing in the plan depends on that.
"""
from typing import Optional

from .formplan import PROGRESS_LABELS, TASK_TYPE_LABELS, _subject_kind, _type_from_kind

NOTE = ("Written by MindSync’s built-in rules from your task type, subject name and answers. It has not read your course material, "
        "so check it against your brief or lecture notes.")

# ---- per task type: the general shape of good study
BASE = {
    "exam": {
        "understand": "The main ideas of each chapter well enough to explain them without your notes, and the kinds of questions your exam asks.",
        "why": "Exams reward recalling and applying ideas under time pressure, not just recognising them on a page.",
        "first": "List the chapters or topics the exam covers, then mark each one green (confident), amber (shaky) or red (not yet).",
        "approach": ["Start with the red topics while your energy is best.", "Close the book and write what you remember, then check the gaps.",
                     "Finish each block by testing yourself, not by re-reading."],
        "exercises": ["Answer two past-paper questions per topic under a timer.", "Make 10 question cards per chapter and test yourself."],
        "mistakes": ["Re-reading notes instead of testing yourself.", "Leaving the hardest topics to the last night.", "Skipping past papers."],
        "check": "Explain each topic aloud in two minutes without notes. Whatever you cannot explain goes back on the list.",
        "stuck": "Pick one small question from that topic and solve it; look up only the step you are missing, then try a similar question.",
        "review": "Short review of each topic after 1 day, 3 days and a week; the last day before the exam is for light review only.",
    },
    "assignment": {
        "understand": "Exactly what the brief asks for, how marks are given, and the one or two ideas the assignment is really testing.",
        "why": "Most lost marks come from answering a slightly different question than the one set.",
        "first": "Read the brief and marking criteria, then write the task in your own words in two sentences.",
        "approach": ["Break the brief into parts and give each part a mini-deadline.", "Draft a rough version of every part early, then improve it.",
                     "Keep the final day for checking against the criteria."],
        "exercises": ["Tick the marking criteria one by one against your draft.", "Ask: could a classmate follow my work without me explaining it?"],
        "mistakes": ["Perfecting one part while others are empty.", "Starting late and skipping the check against the criteria."],
        "check": "Read the criteria line by line and point to where your work meets each one.",
        "stuck": "Write down what is unclear as a question, then check the brief, lecture notes, or ask your lecturer in office hours.",
        "review": "Read it aloud once after a break; fresh eyes catch more mistakes.",
    },
    "project": {
        "understand": "The smallest working version of the project (the core features) and how the parts connect.",
        "why": "A small thing that works is worth more than a big thing that almost works, and it shows your understanding.",
        "first": "Write the list of features, then choose the smallest set that makes a working version.",
        "approach": ["Build the core first and run it after every small step.", "Add features one at a time; commit or save after each one.",
                     "Test and fix before adding anything new; leave documentation time at the end."],
        "exercises": ["Write three test cases for the feature you are building.", "Explain how each part works to a friend (or to a rubber duck)."],
        "mistakes": ["Adding features before the core works.", "Leaving testing and the write-up to the last day.", "Not saving working versions."],
        "check": "Can you run it from scratch and show every required feature working? Can you explain each file or function?",
        "stuck": "Make the problem smaller: reproduce it in the tiniest example, read the error message line by line, then search that message.",
        "review": "Re-run everything from a clean start and re-read the requirements before you submit.",
    },
    "report": {
        "understand": "Your question or argument, the evidence for it, and how each section supports it.",
        "why": "A report is marked on structure and evidence; a clear outline makes the writing much faster.",
        "first": "Write the question your report answers, then list the headings you will need under it.",
        "approach": ["Collect sources first and note why each is useful.", "Write the rough draft quickly, section by section, without polishing.",
                     "Use the last sessions for structure, referencing and proofreading."],
        "exercises": ["Write one summary sentence per section.", "Check every claim has a source or a result behind it."],
        "mistakes": ["Researching without writing anything down.", "Polishing the first page while later sections are empty.", "Leaving references to the end."],
        "check": "Read only the first sentence of each paragraph. Do they tell the whole argument in order?",
        "stuck": "Write badly on purpose for 10 minutes. A rough paragraph is easier to fix than a blank page.",
        "review": "Leave it overnight if you can, then proofread aloud and check the references and word count.",
    },
    "presentation": {
        "understand": "The one message you want the audience to remember, and the three points that support it.",
        "why": "Audiences remember a clear story, not a long list of facts.",
        "first": "Write your main message in one sentence, then list the three points behind it.",
        "approach": ["Plan the story before you open the slides.", "Keep each slide to one idea.", "Spend at least a third of your time rehearsing out loud."],
        "exercises": ["Time yourself from start to finish.", "Present once to a friend and ask what they remember."],
        "mistakes": ["Too much text on slides.", "Never practising out loud.", "Reading the slides instead of speaking."],
        "check": "Can you give the talk without reading, inside the time limit?",
        "stuck": "Say it out loud as if explaining to a friend, then write down what you said.",
        "review": "Run through it once more the day before, including the likely questions.",
    },
    "homework": {
        "understand": "The method the questions practise, not just the answers.",
        "why": "Homework is practice for exams; doing it for understanding pays back later.",
        "first": "Read all the questions, then start with the one you find easiest to build momentum.",
        "approach": ["Try each question on your own first.", "If stuck for 10 minutes, review the lecture example and try again.", "Check your answers and fix mistakes."],
        "exercises": ["Redo one question you got wrong without looking at the answer.", "Write a one-line rule for each type of question."],
        "mistakes": ["Copying solutions without trying first.", "Not checking the answers."],
        "check": "Can you solve a similar question without looking anything up?",
        "stuck": "Find the worked example in your notes that matches, follow it line by line, then change the numbers.",
        "review": "Look over your mistakes again before the next lecture.",
    },
    "revision": {
        "understand": "Which topics are weakest, and the core idea behind each.",
        "why": "Revision works best when it targets gaps, not what you already know.",
        "first": "Rate each topic honestly (confident / shaky / not yet) and start with the weakest.",
        "approach": ["Use active recall: questions, flash cards, and blank-page summaries.", "Space the topics out and come back to them.", "Mix topics in later sessions."],
        "exercises": ["Blank-page summary of each topic.", "Ten self-test questions per topic."],
        "mistakes": ["Highlighting without testing yourself.", "Only revising the topics you enjoy."],
        "check": "Pick a topic at random and explain it in two minutes.",
        "stuck": "Switch to a different topic for one block, then come back with fresh eyes.",
        "review": "A quick look back after 1 day, 3 days and 7 days.",
    },
    "reading": {
        "understand": "The main argument of the text and the two or three ideas you need from it.",
        "why": "Reading with a purpose is faster and you remember more.",
        "first": "Skim the headings, the introduction and the conclusion, and write one question you want answered.",
        "approach": ["Read in short blocks, then write two lines on what you just read.", "Mark only the important parts.", "Finish with a five-line summary in your own words."],
        "exercises": ["Write a 5-line summary.", "Write three questions the text answers."],
        "mistakes": ["Reading everything at the same speed.", "Highlighting most of the page."],
        "check": "Close the text and say what the author argues and why.",
        "stuck": "Skip to the summary or conclusion, then return to the hard part knowing where it leads.",
        "review": "Look at your summary the next day.",
    },
    "other": {
        "understand": "What “finished” looks like for this task, and the first small step that gets you moving.",
        "why": "A clear finish line makes it easier to start and easier to stop.",
        "first": "Write one sentence describing what a finished version looks like.",
        "approach": ["Break the task into 2–4 small steps.", "Do the easiest step first to build momentum.", "Check your work against your finish line."],
        "exercises": ["Tick off each small step."],
        "mistakes": ["Not defining when it is finished."],
        "check": "Does it match your sentence about what finished looks like?",
        "stuck": "Do just five minutes of the smallest step.",
        "review": "Read it again after a short break.",
    },
}

# ---- subject flavour (examples, exercises, typical mistakes) chosen by the subject/topic words
FLAVOURS = {
    "mathematics": {
        "examples": "Work through one example from your notes line by line, then do the same question with different numbers.",
        "exercises": ["Do 5 questions on the method, then 2 mixed questions.", "Re-solve a question you got wrong without looking at the solution."],
        "mistakes": ["Reading worked solutions instead of solving.", "Not checking units or the final answer."],
    },
    "programming": {
        "examples": "Run a small example from your lectures, then change one thing and predict what will happen before you run it.",
        "exercises": ["Write the function by hand before coding it.", "Add three tests, including one unusual case."],
        "mistakes": ["Copying code you cannot explain.", "Changing many things at once so you cannot find the bug."],
    },
    "data": {
        "examples": "Take one small dataset or table from the lectures and answer one question with it step by step.",
        "exercises": ["Write one query or analysis per concept.", "Explain what each result means in a sentence."],
        "mistakes": ["Running queries without saying what the result means.", "Not checking the data for gaps first."],
    },
    "writing": {
        "examples": "Choose one strong example paragraph (from a reading or marked sample) and notice how it makes a point and backs it up.",
        "exercises": ["Write one paragraph that states a point, gives evidence, and explains why it matters.", "Rewrite one sentence to make it shorter."],
        "mistakes": ["Describing instead of arguing.", "Quotes without explanation."],
    },
}

UNDERSTANDING_NOTE = {
    1: "You said you do not understand this yet, so start from the basics: read or watch one clear explanation first, before practice.",
    2: "You said you understand this a little, so spend the first block on the core idea, then practise on easy examples.",
    3: "You said you understand this fairly well, so spend less time on reading and more on questions.",
    4: "You said you understand this well, so keep the sessions for practice and for the hardest parts.",
}


def _flavour(kind: Optional[str], subject: str, name: str) -> Optional[dict]:
    k = _subject_kind(subject, name) or (kind if kind in FLAVOURS else None)
    return FLAVOURS.get(k or "")


def guide_for(*, name: str, subject: str, task_type: Optional[str], kind: Optional[str], progress: Optional[str],
              understanding: Optional[int], days_left: Optional[float], remaining_minutes: Optional[int],
              obstacles: Optional[list] = None, helps: Optional[list] = None, hard_topics: str = "") -> dict:
    t = task_type if task_type in BASE else _type_from_kind(kind)
    b = BASE.get(t, BASE["other"])
    fl = _flavour(kind, subject, name)
    steps = list(b["approach"])
    if understanding in UNDERSTANDING_NOTE:
        steps.insert(0, UNDERSTANDING_NOTE[understanding])
    if progress in ("half", "most"):
        steps.insert(0, f"You told me you are {PROGRESS_LABELS[progress].lower()}, so skip the planning stage and go straight to the unfinished parts.")
    if hard_topics:
        steps.append(f"You named “{hard_topics}” as hard, so give it your best-energy block.")
    if days_left is not None and days_left <= 2:
        steps.insert(0, "The deadline is very close: cover the essentials first and leave small improvements for later.")
    obs = set(obstacles or [])
    tips = []
    if "distracted" in obs:
        tips.append("Put your phone in another room and use short 25-minute blocks; jot distracting thoughts down to look at later.")
    if "procrastinate" in obs or "dont_know_where_to_start" in obs:
        tips.append("Start with a 5-minute timer on the first step above; getting started is the hardest part.")
    if "forget" in obs:
        tips.append("Test yourself the next day on what you studied today; spaced recall beats re-reading.")
    if "struggle_to_understand" in obs:
        tips.append("Look for one clear explanation or worked example first, then try a question on your own.")
    if "need_practice" in obs:
        tips.append("Add one extra practice question to the end of each block.")
    if "overwhelmed" in obs or "not_enough_time" in obs:
        tips.append("Do only the next block; the plan already holds the rest. Take the break that is planned.")
    helps = set(helps or [])
    ways = {"practice_questions": "practice questions", "solving_problems": "solving problems", "flashcards": "flash cards",
            "writing_summaries": "writing summaries", "building_projects": "building something small", "watching_explanations": "watching an explanation first",
            "reading_notes": "reading your notes"}
    liked = [ways[h] for h in ("practice_questions", "solving_problems", "flashcards", "writing_summaries", "building_projects", "watching_explanations", "reading_notes") if h in helps]
    if liked:
        tips.append("You said you learn best by " + ", ".join(liked[:3]) + ", so use that way in the first half of each block.")
    return {
        "name": name, "subject": subject, "type": t, "type_label": TASK_TYPE_LABELS.get(t, "Task"),
        "understand": b["understand"], "why": b["why"], "first_step": b["first"],
        "approach": steps, "example": fl["examples"] if fl else None,
        "exercises": (fl["exercises"] if fl else []) + b["exercises"],
        "mistakes": (fl["mistakes"] if fl else []) + b["mistakes"],
        "check": b["check"], "if_stuck": b["stuck"], "review": b["review"], "tips": tips,
        "remaining_minutes": remaining_minutes, "source": "rules", "note": NOTE,
    }


def guidance_for_core(core, limit: int = 12) -> list:
    """Guidance for the student's pending topics, most urgent first."""
    from . import core as C
    pf = (core.profile.plan_form if core.profile else None) or {}
    obstacles, helps = pf.get("obstacles") or [], pf.get("helps") or []
    out = []
    rows = sorted((r for r in core.tasks if r.status == "pending"), key=lambda r: r.deadline)[:limit]
    for r in rows:
        m = r.meta or {}
        days = (r.deadline - core.now).total_seconds() / 86400
        rem = C.remaining_of(m)[0] if m.get("likely") else None
        g = guide_for(name=r.title, subject=m.get("subject") or "My other tasks", task_type=m.get("task_type"), kind=m.get("kind"),
                      progress=m.get("progress"), understanding=m.get("grasp"), days_left=round(days, 1), remaining_minutes=rem,
                      obstacles=obstacles, helps=helps)
        g["task_id"] = r.id
        g["topic_id"] = m.get("topic_id")
        out.append(g)
    return out
