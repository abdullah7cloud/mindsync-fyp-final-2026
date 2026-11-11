"""
What kinds of academic work exist, how each is usually done, and how to recognise them in text.

Two levels:
  * a KIND is the type of task (programming, mathematics, writing, exam preparation, ...). A task can have
    several kinds at once ("a Python project with a written report").
  * a WORK type is one step inside a kind (debugging, outlining, active recall, rehearsing ...). Work types
    become the stages of a plan, each with its own study method and session length.

The recognition lexicon is a weighted phrase list, not a trained model: there is no labelled corpus of
student tasks to train on, and training on invented data would be fabricated evidence (see
docs/TASK_AWARE_ENGINE.md). When the words give weak evidence the engine says "unknown" and asks.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Work:
    id: str
    label: str
    method: str                 # what to actually do in this stage (generic: never claims to know the content)
    deep: bool                  # needs sustained concentration (counts towards the daily deep-work limit)
    session: tuple              # (shortest, ideal, longest) minutes of one focus block
    breaks: bool = True         # False: short or administrative work that needs no scheduled break


WORKS = {w.id: w for w in [
    # programming
    Work("prog_design", "Plan the design", "Write down the inputs, outputs and the main parts, then sketch how they fit together before writing code.", True, (25, 40, 60)),
    Work("prog_implement", "Build it", "Build one small working piece at a time. Run it after every piece instead of writing everything first.", True, (45, 75, 120)),
    Work("prog_debug", "Fix problems", "Reproduce each problem, change one thing at a time and re-run. Keep a short note of what you tried.", True, (30, 50, 75)),
    Work("prog_test", "Test it", "Write tests for the normal case, the edge cases and bad input, then run all of them.", True, (25, 35, 50)),
    Work("prog_docs", "Tidy and document", "Clean up names, add comments where the reason is not obvious, and update the README.", False, (20, 30, 45)),
    # mathematics
    Work("math_concept", "Understand the ideas", "Read the definition, then explain it in your own words and check it against one worked example.", True, (25, 40, 50)),
    Work("math_examples", "Study worked examples", "Cover the solution, try each step yourself, then compare with the worked answer.", True, (25, 35, 45)),
    Work("math_practice", "Solve problems yourself", "Do problems without looking at the solution first. Mark which ones you got stuck on.", True, (30, 45, 60)),
    Work("math_review", "Review your mistakes", "Go through every wrong answer and write down why it went wrong and the rule that fixes it.", True, (20, 25, 35)),
    # writing
    Work("write_research", "Research and take notes", "Collect sources and write each note with its reference straight away.", True, (30, 45, 60)),
    Work("write_outline", "Make an outline", "List the main points in order, one sentence each, and what evidence supports each point.", True, (20, 30, 40)),
    Work("write_draft", "Write the first draft", "Write without editing. Follow the outline and leave gaps marked instead of stopping.", True, (40, 50, 75)),
    Work("write_refs", "Check references", "Check every citation in the text has an entry in the reference list in the required style.", False, (20, 25, 40)),
    Work("write_edit", "Edit and proofread", "Read it aloud, cut repetition, check the argument against the question, then check spelling.", True, (25, 30, 45)),
    # exam preparation
    Work("exam_concepts", "Understand the topics", "Go topic by topic from your notes and fill the gaps you find. Close the notes and explain each topic.", True, (30, 40, 50)),
    Work("exam_recall", "Practise recalling", "Close your notes, write what you remember, then check and mark the gaps. Repeat the gaps.", True, (20, 30, 40)),
    Work("exam_practice", "Do practice questions", "Answer past questions under time pressure, then mark them and note the types you lose marks on.", True, (40, 60, 90)),
    Work("exam_spaced", "Review again after a gap", "Return to earlier topics after a day or more and test yourself again.", False, (15, 20, 30)),
    # reading
    Work("read_scan", "Skim first", "Read the headings, introduction, conclusion and any summary boxes to see the structure.", False, (10, 15, 25)),
    Work("read_comprehend", "Read for understanding", "Read in sections and stop at the end of each to say the main point in one sentence.", True, (20, 30, 45)),
    Work("read_analyse", "Analyse in detail", "Re-read the important parts, write notes on the argument, evidence and weaknesses.", True, (30, 40, 55)),
    # presentation
    Work("pres_research", "Gather the content", "List what the audience needs to know, then collect the key facts and examples.", True, (30, 40, 60)),
    Work("pres_materials", "Prepare the slides", "Put one idea on each slide. Keep text short and use visuals where they help.", True, (30, 45, 60)),
    Work("pres_rehearse", "Rehearse aloud", "Present out loud with a timer, then fix the parts where you hesitated.", False, (15, 20, 30)),
    # data analysis
    Work("data_prepare", "Prepare the data", "Check the columns and missing values, clean what must be cleaned and note what you changed.", True, (30, 45, 60)),
    Work("data_analyse", "Run the analysis", "Run each analysis, check the result is sensible and save the output.", True, (35, 50, 75)),
    Work("data_interpret", "Interpret and report", "Say in plain words what each result means and what it does not show.", True, (25, 35, 50)),
    # small jobs and unknown work
    Work("admin_do", "Get it done", "Do it in one go. If it will take longer than planned, write down what is left.", False, (5, 15, 30), breaks=False),
    Work("general_work", "Work on the task", "Split the task into two or three clear parts, then work on one part at a time.", True, (25, 40, 60)),
]}

# (work id, share of the total effort) in the order the work is normally done
KINDS = {
    "programming": dict(label="Programming", skill="programming", base=480, deep_limit=240, stages=[
        ("prog_design", .12), ("prog_implement", .46), ("prog_debug", .20), ("prog_test", .14), ("prog_docs", .08)]),
    "mathematics": dict(label="Mathematics", skill="mathematics", base=150, deep_limit=210, stages=[
        ("math_concept", .22), ("math_examples", .23), ("math_practice", .40), ("math_review", .15)]),
    "writing": dict(label="Writing", skill="academic writing", base=420, deep_limit=240, stages=[
        ("write_research", .28), ("write_outline", .08), ("write_draft", .34), ("write_refs", .07), ("write_edit", .23)]),
    "exam": dict(label="Exam preparation", skill="this subject", base=480, deep_limit=210, stages=[
        ("exam_concepts", .32), ("exam_recall", .25), ("exam_practice", .30), ("exam_spaced", .13)]),
    "reading": dict(label="Reading", skill="reading academic texts", base=75, deep_limit=240, stages=[
        ("read_scan", .12), ("read_comprehend", .55), ("read_analyse", .33)]),
    "presentation": dict(label="Presentation", skill="presenting", base=240, deep_limit=240, stages=[
        ("pres_research", .30), ("pres_materials", .40), ("pres_rehearse", .30)]),
    "data": dict(label="Data analysis", skill="data analysis", base=300, deep_limit=240, stages=[
        ("data_prepare", .28), ("data_analyse", .42), ("data_interpret", .30)]),
    "admin": dict(label="Quick admin job", skill="this kind of task", base=25, deep_limit=240, stages=[("admin_do", 1.0)]),
    "general": dict(label="General study task", skill="this kind of task", base=180, deep_limit=240, stages=[("general_work", 1.0)]),
}

# Inherent difficulty of each kind on a 1-5 scale before scope and technical cues are looked at.
KIND_BASE_DIFFICULTY = {"programming": 3.0, "mathematics": 3.4, "writing": 3.0, "exam": 3.4, "reading": 2.0,
                        "presentation": 2.4, "data": 3.0, "admin": 1.0, "general": 2.8}

# Weighted evidence phrases. A phrase matches whole words. Weights are how strongly the phrase alone points to
# the kind (0-1); several phrases combine as 1 - product(1 - weight).
LEXICON = {
    "programming": {"python": .8, "java": .8, "javascript": .8, "typescript": .8, "c++": .85, "c#": .85, "html": .5, "css": .4,
                    "code": .7, "coding": .85, "program": .5, "programming": .9, "software": .7, "app": .4, "website": .55,
                    "api": .6, "function": .35, "bug": .8, "bugs": .8, "debug": .95, "debugging": .95, "algorithm": .6,
                    "implement": .6, "implementation": .5, "compile": .7, "github": .7, "git": .5, "backend": .8,
                    "frontend": .8, "react": .8, "flask": .85, "django": .85, "fastapi": .9, "web app": .8, "script": .55,
                    "unit test": .85, "unit tests": .85, "refactor": .8, "class": .25, "database": .35, "mobile app": .7,
                    "game": .3, "oop": .7, "recursion": .5, "sorting": .4, "data structure": .6, "data structures": .6},
    "mathematics": {"maths": .9, "math": .9, "mathematics": .95, "calculus": .95, "algebra": .95, "geometry": .9,
                    "trigonometry": .95, "equation": .7, "equations": .7, "derivative": .85, "derivatives": .85,
                    "integral": .85, "integrals": .85, "integration": .6, "differentiation": .85, "proof": .6, "proofs": .6,
                    "theorem": .8, "matrix": .7, "matrices": .75, "vectors": .6, "linear algebra": .95, "discrete": .6,
                    "probability": .8, "problem set": .6, "limits": .35, "sequences": .45, "logarithm": .8},
    "writing": {"essay": .95, "report": .75, "dissertation": .95, "thesis": .9, "paper": .35, "article": .3, "literature review": .95,
                "reflection": .7, "cover letter": .8, "write": .55, "writing": .75, "draft": .5, "referencing": .85,
                "citations": .8, "bibliography": .85, "case study": .6, "coursework": .35, "proposal": .7, "abstract": .4,
                "lab report": .9, "blog": .6, "assignment": .25, "critique": .7, "annotated bibliography": .95},
    "exam": {"exam": .95, "exams": .95, "examination": .95, "revision": .8, "revise": .85, "mock": .5, "midterm": .9,
             "final exam": .95, "quiz": .6, "past paper": .95, "past papers": .95, "flashcards": .8, "study for": .6,
             "test": .35, "resit": .85, "mock exam": .95, "prepare for": .15, "multiple choice": .6},
    "reading": {"read": .75, "reading": .8, "chapter": .55, "chapters": .55, "textbook": .65, "lecture notes": .55,
                "skim": .8, "book": .35, "reading list": .85, "journal": .45, "pages": .15, "review the notes": .5,
                "go through the notes": .5, "notes": .2},
    "presentation": {"presentation": .95, "slides": .85, "present": .55, "pitch": .8, "slide deck": .95, "powerpoint": .9,
                     "talk": .35, "seminar": .5, "speech": .75, "demo": .3, "viva": .45, "poster": .6, "rehearse": .8},
    "data": {"dataset": .75, "data analysis": .95, "excel": .7, "power bi": .9, "tableau": .9, "spss": .95, "pandas": .8,
             "visualisation": .7, "visualization": .7, "statistical analysis": .9, "survey data": .85, "chart": .4,
             "charts": .45, "spreadsheet": .75, "sql query": .6, "regression": .55, "statistics": .5, "data": .3, "r studio": .9},
    "admin": {"email": .8, "emails": .8, "form": .6, "register": .5, "book": .15, "print": .6, "submit": .45, "upload": .45,
              "tidy": .6, "organise": .5, "organize": .5, "backup": .6, "back up": .6, "sign up": .6, "fill in": .7,
              "pay": .6, "appointment": .8, "timetable": .6, "reply": .7, "admin": .9, "rename": .6, "download": .5},
}
# Words that change what an ambiguous word means. "unit test" is software, not an exam.
BLOCK_FOR = {("exam", "test"): ("unit test", "unit tests", "test case", "test cases", "write tests", "testing")}

# Cues for how big a task is when no number is given.
SIZE_CUES = {
    "tiny": ("quick", "tiny", "minor", "five minutes", "5 minutes", "briefly", "a few lines", "one email", "short email"),
    "small": ("short", "small", "simple", "fix", "bug", "debug", "typo", "exercise", "worksheet", "one question", "one problem", "single", "lecture", "intro", "introduction",
              "basic", "basics", "section", "easy"),
    "large": ("project", "coursework", "portfolio", "system", "application", "platform", "whole", "entire", "full",
              "complete", "final", "multiple", "several", "capstone", "end-to-end", "full-stack"),
    "huge": ("dissertation", "thesis", "final year", "capstone project", "final year project", "year-long"),
}
# Cues that raise or lower the intrinsic difficulty.
HARD_CUES = ("advanced", "algorithm", "machine learning", "neural", "recursion", "concurrency", "distributed", "proof", "prove",
             "theorem", "optimis", "optimiz", "regression", "differential", "eigen", "complexity", "cryptograph", "compiler",
             "multithread", "dynamic programming", "security", "scalab", "deep learning", "statistical", "critical analysis")
EASY_CUES = ("basic", "basics", "intro", "introduction", "beginner", "simple", "overview", "revision of", "recap", "setup",
             "install", "getting started", "tutorial", "easy")

SIZE_MULT = {"tiny": .12, "small": .3, "medium": 1.0, "large": 2.5, "huge": 8.0}
SIZE_ORDER = ["tiny", "small", "medium", "large", "huge"]

# Minutes per counted unit, by kind. (words/pages are handled separately for writing.)
UNIT_MINUTES = {
    ("writing", "word"): 0.21, ("writing", "page"): 58.0,
    ("reading", "page"): 3.5, ("reading", "chapter"): 40.0, ("reading", "paper"): 55.0, ("reading", "article"): 45.0,
    ("mathematics", "question"): 14.0, ("mathematics", "problem"): 14.0, ("mathematics", "exercise"): 14.0,
    ("exam", "topic"): 75.0, ("exam", "chapter"): 60.0, ("exam", "lecture"): 35.0, ("exam", "module"): 120.0,
    ("presentation", "slide"): 26.0, ("presentation", "talk_minute"): 24.0,
    ("programming", "feature"): 90.0, ("programming", "function"): 45.0, ("programming", "module"): 120.0,
    ("programming", "endpoint"): 60.0, ("programming", "class"): 60.0, ("programming", "page"): 75.0,
    ("data", "question"): 50.0, ("data", "chart"): 30.0, ("data", "table"): 30.0, ("data", "analysis"): 60.0,
}
UNIT_WORDS = {"word": "word", "words": "word", "page": "page", "pages": "page", "slide": "slide", "slides": "slide",
              "question": "question", "questions": "question", "problem": "problem", "problems": "problem",
              "exercise": "exercise", "exercises": "exercise", "chapter": "chapter", "chapters": "chapter",
              "feature": "feature", "features": "feature", "module": "module", "modules": "module",
              "topic": "topic", "topics": "topic", "function": "function", "functions": "function",
              "lecture": "lecture", "lectures": "lecture", "paper": "paper", "papers": "paper",
              "article": "article", "articles": "article", "endpoint": "endpoint", "endpoints": "endpoint",
              "class": "class", "classes": "class", "chart": "chart", "charts": "chart", "table": "table",
              "tables": "table", "analysis": "analysis", "analyses": "analysis",
              "minute": "talk_minute", "minutes": "talk_minute", "min": "talk_minute", "mins": "talk_minute"}
