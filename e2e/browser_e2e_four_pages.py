"""
End-to-end browser test for the four-page MindSync (Playwright + Chromium), added in update 26.

It drives the REAL pages against a REAL running backend (PostgreSQL) the way a student would.

  A  register -> exactly four pages in the menu, no old pages                     B  Study Planner: one form, plan, tasks
  C  Dashboard: numbers, progress bar, tick a task, overdue + deadlines          D  edit / delete a task, edit / delete a plan
  E  My Notebook: notes (create, save, edit, search, PDF, Word, delete)          F  My Documents (upload, view, download, rename, delete)
  G  AI Learning Zone: quiz from a Notebook document and from a direct upload, score, retry
  H  everything is still there after log out and log in                          I  account window: name, password, data download, delete
  J  phone layout: no sideways scroll on the four pages                          K  screenshots

Run (backend :8000 and frontend :5173 must be running; restart the backend first so the sign-up limiter is fresh):
    python e2e/browser_e2e_four_pages.py [screenshot_folder] [--ai-off]

With the backend started with the scripted AI stand-in (E2E_AI=mock) the AI paths are exercised; with --ai-off the test expects the
honest "not available" behaviour (offline plan made by the built-in engine, no fake quiz). This never calls a real AI service.
"""
import json
import os
import re
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
AI_OFF = "--ai-off" in sys.argv
FRONT, BACK = "http://localhost:5173", "http://localhost:8000"
SHOTS = Path(ARGS[0] if ARGS else "e2e_screenshots_four")
SHOTS.mkdir(parents=True, exist_ok=True)
import tempfile
FILES = Path(tempfile.gettempdir()) / "e2e_files"
results = []
PW = "Study-pass-1"
FOUR = ["Dashboard", "Study Planner", "AI Learning Zone", "My Notebook"]
PATHS = ["/dashboard", "/planner", "/ai-zone", "/notebook"]


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(("PASS  " if ok else "FAIL  ") + name + (f"  [{detail}]" if detail else ""))


def iso(n):
    return (date.today() + timedelta(days=n)).isoformat()


def register(pg, label="Abi Student"):
    email = f"four-{uuid.uuid4().hex[:8]}@example.com"
    pg.goto(FRONT + "/register")
    pg.get_by_label(re.compile(r"your name|name", re.I)).first.fill(label)
    pg.get_by_label(re.compile(r"email", re.I)).first.fill(email)
    pws = pg.locator('input[type="password"]')
    pws.nth(0).fill(PW)
    pws.nth(1).fill(PW)
    pg.get_by_role("button", name=re.compile(r"create|sign up|register", re.I)).first.click()
    pg.wait_for_url("**/dashboard", timeout=15000)
    return email


def login(pg, email, pw=PW):
    pg.goto(FRONT + "/login")
    pg.get_by_label(re.compile(r"email", re.I)).first.fill(email)
    pg.locator('input[type="password"]').first.fill(pw)
    pg.get_by_role("button", name=re.compile(r"^log in$", re.I)).click()
    pg.wait_for_url("**/dashboard", timeout=15000)


def num(pg, tid):
    return int(pg.get_by_test_id(tid).inner_text())


def no_sideways_scroll(pg):
    return pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


def run():
    p = sync_playwright().start()
    if True:
        br = p.chromium.launch(channel=os.environ.get("E2E_CHANNEL") or None)
        ctx = br.new_context(viewport={"width": 1280, "height": 900}, timezone_id="Europe/Copenhagen", accept_downloads=True)
        pg = ctx.new_page()
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        failed = []
        pg.on("requestfailed", lambda r: failed.append(f"{r.method} {r.url} {r.failure}"))
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" and "favicon" not in m.text and "Failed to load resource" not in m.text else None)
        pg.on("dialog", lambda d: d.accept())
        globals()["PG"] = pg

        # ------------------------------------------------------------------ A. register and the menu
        email = register(pg)
        check("A1 registering signs the student in and opens the Dashboard", pg.url.endswith("/dashboard"))
        nav = pg.get_by_role("navigation", name="Pages")
        labels = [t.strip() for t in nav.locator("a").all_inner_texts()]
        check("A2 the menu has the four pages, then My Profile and Settings", labels == FOUR + ["My Profile", "Settings"], str(labels))
        body = pg.locator("body").inner_text()
        check("A3 no old page names are visible", not re.search(r"Wellbeing|Analytics|Toolkit|My Tasks|Smart Planner|AI Learning Studio", body))
        check("A4 My Notebook shortcut is in the header", pg.locator("a.topbar-notebook").count() == 1)
        check("A5 empty dashboard shows 0 / 0 / 0 and 0%", (num(pg, "total"), num(pg, "completed"), num(pg, "remaining")) == (0, 0, 0)
              and pg.get_by_role("progressbar").get_attribute("aria-valuenow") == "0")
        pg.screenshot(path=str(SHOTS / "01_dashboard_empty.png"))
        pg.get_by_role("link", name="Create Study Plan").first.click()
        pg.wait_for_url("**/planner")
        check("A6 'Create Study Plan' button opens the Study Planner", True)

        # ------------------------------------------------------------------ B. Study Planner
        form = pg.locator("form.lt-form")
        fields = [l.strip() for l in form.locator("label").all_inner_texts()]
        check("B1 the form has the six fields", all(any(k in f for f in fields) for k in
              ["Subject Name", "Topic Name", "Learning Goal", "Target Completion Date"]) and pg.get_by_text("Current Mood").count() >= 1 and pg.get_by_text("Stress Level").count() >= 1, str(fields)[:200])
        moods = [t.strip() for t in pg.locator('fieldset:has-text("Current Mood") label').all_inner_texts()]
        stress = [t.strip() for t in pg.locator('fieldset:has-text("Stress Level") label').all_inner_texts()]
        check("B2 mood Good/Okay/Tired and stress Low/Medium/High", moods == ["Good", "Okay", "Tired"] and stress == ["Low", "Medium", "High"], f"{moods} {stress}")
        check("B3 one button 'Generate My Study Plan'", pg.get_by_role("button", name="Generate My Study Plan").count() == 1)
        check("B4 button is off until the form is filled", pg.get_by_role("button", name="Generate My Study Plan").is_disabled())
        pg.get_by_label("Subject Name").fill("Biology")
        pg.get_by_label(re.compile("Topic Name")).fill("Photosynthesis")
        pg.get_by_label(re.compile("Learning Goal")).fill("I find the Calvin cycle hard.")
        pg.get_by_label("Target Completion Date").fill(iso(6))
        pg.get_by_label("Tired").check(force=True)
        pg.get_by_label("High").check(force=True)
        pg.get_by_role("button", name="Generate My Study Plan").click()
        pg.get_by_text(re.compile("Your plan is ready")).wait_for(timeout=40000)
        card = pg.locator("article.lt-plan").first
        card_text = card.inner_text()
        if AI_OFF:
            check("B5 offline: plan made by the built-in engine and says so", "Made offline" in card_text and re.search(r"not switched on|offline", card_text, re.I), card_text[:160].replace("\n", " "))
        else:
            check("B5 online: plan made by the AI and says so", "Made by AI" in card_text, card_text[:160].replace("\n", " "))
        n_tasks = card.locator("li.lt-task").count()
        check("B6 roadmap (3+ steps) and 3+ tasks with dates and times", card.locator("ol.lt-road li").count() >= 3 and n_tasks >= 3, f"{n_tasks} tasks")
        pg.screenshot(path=str(SHOTS / "02_planner_plan.png"), full_page=True)

        # ------------------------------------------------------------------ C. Dashboard
        pg.goto(FRONT + "/dashboard")
        pg.get_by_test_id("total").wait_for()
        total, done0, rem0 = num(pg, "total"), num(pg, "completed"), num(pg, "remaining")
        check("C1 dashboard counts the new tasks", total == n_tasks and done0 == 0 and rem0 == n_tasks, f"{total}/{done0}/{rem0}")
        check("C2 upcoming deadline lists Biology", pg.get_by_role("heading", name="Upcoming deadlines").locator("xpath=..").inner_text().count("Biology") >= 1)
        first = pg.locator("ul[aria-label='Tasks to do'] input[type=checkbox]").first
        first.click()
        pg.wait_for_function("document.querySelector('[data-testid=completed]').innerText === '1'", timeout=8000)
        check("C3 ticking a task updates completed / remaining at once", (num(pg, "completed"), num(pg, "remaining")) == (1, n_tasks - 1))
        pct = int(pg.get_by_role("progressbar").get_attribute("aria-valuenow"))
        check("C4 the progress bar matches done/total", pct == round(100 * 1 / n_tasks) or abs(pct - 100 / n_tasks) < 1, f"{pct}%")
        pg.reload()
        pg.get_by_test_id("completed").wait_for()
        check("C5 the tick is still there after a reload", num(pg, "completed") == 1)
        pg.locator("details.lt-finished summary").click()
        pg.locator("ul[aria-label='Completed tasks'] input[type=checkbox]").first.click()
        pg.wait_for_function("document.querySelector('[data-testid=completed]').innerText === '0'", timeout=8000)
        check("C6 un-ticking works too", num(pg, "completed") == 0)
        pg.wait_for_timeout(700); pg.screenshot(path=str(SHOTS / "03_dashboard_with_tasks.png"), full_page=True)

        # ------------------------------------------------------------------ D. edit / delete task and plan
        pg.goto(FRONT + "/planner")
        card = pg.locator("article.lt-plan").first
        card.wait_for()
        card.locator("li.lt-task").first.get_by_role("button", name=re.compile("^Edit task")).click()
        ed = card.locator("li.lt-editing")
        ed.get_by_label(re.compile("Task")).first.fill("Read page 10 about chloroplasts")
        ed.get_by_role("button", name=re.compile("^Save")).click()
        pg.get_by_text("Read page 10 about chloroplasts").wait_for()
        check("D1 a task can be edited", True)
        card.locator("li.lt-task").nth(1).get_by_role("button", name=re.compile("^Delete task")).click()
        card.locator("li.lt-task").nth(1).get_by_role("button", name="Yes, delete").click()
        pg.wait_for_function(f"document.querySelectorAll('article.lt-plan li.lt-task').length === {n_tasks - 1}", timeout=8000)
        check("D2 a task can be deleted (with a confirm step)", True)
        card.get_by_role("button", name="Edit plan").click()
        ep = card.locator("form.lt-plan-edit")
        ep.get_by_label(re.compile("Subject")).first.fill("Biology 101")
        ep.get_by_role("button", name=re.compile("^Save")).click()
        pg.get_by_text("Biology 101").first.wait_for()
        check("D3 the plan can be edited", True)
        pg.reload()
        pg.get_by_text("Read page 10 about chloroplasts").wait_for()
        check("D4 the edits are saved", pg.get_by_text("Biology 101").count() >= 1 and pg.get_by_text("Read page 10 about chloroplasts").count() == 1)
        card = pg.locator("article.lt-plan").first
        card.get_by_role("button", name="Delete plan").click()
        card.get_by_role("button", name="Yes, delete plan").click()
        pg.get_by_text(re.compile("You have no study plans yet")).wait_for()
        check("D5 a plan can be deleted and its tasks go with it", True)
        pg.goto(FRONT + "/dashboard")
        pg.get_by_test_id("total").wait_for()
        check("D6 dashboard is back to zero", num(pg, "total") == 0)

        # a second plan, kept for the persistence test
        pg.goto(FRONT + "/planner")
        pg.get_by_label("Subject Name").fill("History")
        pg.get_by_label(re.compile("Topic Name")).fill("World War 1")
        pg.get_by_label("Target Completion Date").fill(iso(10))
        pg.get_by_role("button", name="Generate My Study Plan").click()
        pg.get_by_text(re.compile("Your plan is ready")).wait_for(timeout=40000)
        check("D7 a second plan can be made", pg.locator("article.lt-plan").count() == 1)

        # ------------------------------------------------------------------ E. My Notebook: notes
        pg.goto(FRONT + "/notebook")
        pg.get_by_role("tab", name="My Notes").wait_for()
        check("E1 Notebook has two sections", pg.get_by_role("tab", name="My Notes").count() == 1 and pg.get_by_role("tab", name="My Documents").count() == 1)
        pg.get_by_role("button", name="New note").click()
        pg.get_by_label("Title").fill("Calvin cycle summary")
        pg.get_by_label("Your note").fill("The Calvin cycle builds glucose.\nIt happens in the stroma.\nÅ ø æ – accents too.")
        pg.get_by_role("button", name="Save note").click()
        pg.get_by_text("Saved to your account.").wait_for()
        check("E2 a note can be created and saved", pg.locator("ul[aria-label='Notes'] li").count() == 1)
        pg.get_by_role("button", name="New note").click()
        pg.get_by_label("Title").fill("Exam dates")
        pg.get_by_label("Your note").fill("Biology exam is on Friday.")
        pg.get_by_role("button", name="Save note").click()
        pg.get_by_text("Saved to your account.").wait_for()
        pg.get_by_placeholder("Search my notes").fill("stroma")
        pg.wait_for_function("document.querySelectorAll(\"ul[aria-label='Notes'] li\").length === 1", timeout=5000)
        check("E3 search finds a note by words inside it", "Calvin cycle summary" in pg.locator("ul[aria-label='Notes']").inner_text())
        pg.get_by_placeholder("Search my notes").fill("zzzz")
        pg.get_by_text("No notes match your search.").wait_for()
        check("E4 search says so when nothing matches", True)
        pg.get_by_placeholder("Search my notes").fill("")
        pg.locator("ul[aria-label='Notes'] li").nth(1).wait_for()
        pg.get_by_role("button", name=re.compile("Calvin cycle summary")).click()
        expect(pg.get_by_label("Title")).to_have_value("Calvin cycle summary")
        pg.get_by_label("Your note").fill("The Calvin cycle builds glucose.\nIt happens in the stroma.\nEdited line.")
        check("E5 unsaved changes are shown", pg.get_by_text("You have changes that are not saved yet.").count() == 1)
        pg.get_by_role("button", name="Save note").click()
        pg.get_by_text("Saved to your account.").wait_for()
        with pg.expect_download() as dl:
            pg.get_by_role("button", name="Download PDF").click()
        data = Path(dl.value.path()).read_bytes()
        check("E6 note downloads as a real PDF", data[:5] == b"%PDF-" and dl.value.suggested_filename.endswith(".pdf"), dl.value.suggested_filename)
        with pg.expect_download() as dl:
            pg.get_by_role("button", name="Download Word").click()
        data = Path(dl.value.path()).read_bytes()
        check("E7 note downloads as a real Word file", data[:2] == b"PK" and dl.value.suggested_filename.endswith(".docx"), dl.value.suggested_filename)
        pg.get_by_role("button", name="New note").click()
        pg.get_by_role("button", name=re.compile("Exam dates")).click()
        pg.get_by_role("button", name="Delete note").click()
        pg.get_by_role("button", name="Yes, delete").click()
        pg.get_by_text("Note deleted.").wait_for()
        check("E8 a note can be deleted (with a confirm step)", pg.locator("ul[aria-label='Notes'] li").count() == 1)
        pg.screenshot(path=str(SHOTS / "04_notebook_notes.png"), full_page=True)

        # ------------------------------------------------------------------ F. My Documents
        pg.get_by_role("tab", name="My Documents").click()
        pg.wait_for_url("**/notebook?tab=documents")
        for f in ["photosynthesis.pdf", "lesson.docx", "notes.txt"]:
            pg.locator("input[type=file]").set_input_files(str(FILES / f))
            pg.get_by_text(f"“{f}” was saved to your account.").wait_for(timeout=15000)
        check("F1 PDF, Word and text files can be uploaded", pg.locator("ul[aria-label='My documents'] li").count() == 3)
        pg.locator("input[type=file]").set_input_files(str(FILES / "fake.pdf"))
        pg.get_by_role("alert").wait_for()
        check("F2 a fake file is refused with a plain message", True, pg.get_by_role("alert").inner_text()[:90])
        row = pg.locator("li.lt-doc", has_text="photosynthesis.pdf")
        row.get_by_role("button", name="View").click()
        pg.locator("iframe.lt-pdf").wait_for(timeout=10000)
        check("F3 a PDF opens inside the page", True)
        pg.get_by_role("button", name="Close").last.click()
        pg.locator("li.lt-doc", has_text="lesson.docx").get_by_role("button", name="View").click()
        pg.locator("pre.lt-doc-text").wait_for(timeout=10000)
        check("F4 a Word file shows its text", "Photosynthesis converts" in pg.locator("pre.lt-doc-text").inner_text())
        pg.get_by_role("button", name="Close").last.click()
        with pg.expect_download() as dl:
            row.get_by_role("button", name="Download").click()
        check("F5 a document downloads unchanged", Path(dl.value.path()).read_bytes() == (FILES / "photosynthesis.pdf").read_bytes())
        row = pg.locator("ul[aria-label='My documents'] li").first          # newest first: notes.txt
        row.get_by_role("button", name="Rename").click()
        row.get_by_label("New name").fill("Biology revision")
        row.get_by_role("button", name="Save name").click()
        pg.get_by_text("Biology revision.txt").wait_for()
        check("F6 a document can be renamed (file type kept)", True)
        row = pg.locator("li.lt-doc", has_text="Biology revision.txt")
        row.get_by_role("button", name="Delete").click()
        row.get_by_role("button", name="Yes, delete").click()
        pg.get_by_text(re.compile("Biology revision.txt” was deleted")).wait_for()
        check("F7 a document can be deleted (with a confirm step)", pg.locator("ul[aria-label='My documents'] li").count() == 2)
        pg.screenshot(path=str(SHOTS / "05_notebook_documents.png"), full_page=True)

        # ------------------------------------------------------------------ G. AI Learning Zone
        pg.locator("li.lt-doc", has_text="photosynthesis.pdf").get_by_role("link", name="Create Quiz").click()
        pg.wait_for_url(re.compile(r"/ai-zone\?document="))
        if AI_OFF:
            pg.get_by_text("The AI quiz is not available right now").wait_for(timeout=10000)
            check("G1 AI off: an honest 'not available' message, no fake quiz", pg.get_by_role("button", name="Generate Quiz").is_disabled())
            pg.screenshot(path=str(SHOTS / "06_ai_zone_off.png"), full_page=True)
        else:
            pg.get_by_text(re.compile("characters read")).wait_for(timeout=15000)
            check("G1 'Create Quiz' opens the AI Learning Zone with the document read", "photosynthesis.pdf" in pg.locator("p.lt-chosen").inner_text())
            pg.get_by_role("button", name="Generate Quiz").click()
            pg.get_by_text(re.compile(r"Question 1 of")).wait_for(timeout=40000)
            total_q = int(re.search(r"of (\d+)", pg.get_by_text(re.compile(r"Question 1 of")).inner_text()).group(1))
            check("G2 multiple-choice questions appear", total_q >= 5, f"{total_q} questions")
            for i in range(total_q):
                pg.locator("fieldset.st-options label").first.click()
                if i < total_q - 1:
                    pg.get_by_role("button", name="Next").click()
            pg.get_by_role("button", name="Finish and see my score").click()
            pg.get_by_role("heading", name=re.compile("Your score:")).wait_for(timeout=15000)
            check("G3 a final score and the correct answers with explanations", pg.locator("ol.st-review li").count() == total_q and pg.locator("ol.st-review .insight-note").count() >= 1)
            pg.screenshot(path=str(SHOTS / "06_ai_zone_score.png"), full_page=True)
            pg.get_by_role("button", name="Try the quiz again").click()
            pg.get_by_text(re.compile(r"Question 1 of")).wait_for(timeout=15000)
            check("G4 retry gives the quiz again", True)
            pg.goto(FRONT + "/ai-zone")
            pg.locator("input[type=file]").set_input_files(str(FILES / "lesson.docx"))
            pg.get_by_text(re.compile("characters read")).wait_for(timeout=15000)
            check("G5 a file can also be uploaded straight into the AI Learning Zone", True)

        # ------------------------------------------------------------------ H. persistence
        pg.get_by_role("button", name="Log out").first.click()
        pg.wait_for_url(re.compile(r"/login|/$"))
        check("H1 logging out leaves the app", True)
        pg.goto(FRONT + "/dashboard")
        pg.wait_for_url("**/login")
        check("H2 pages need a login", True)
        login(pg, email)
        pg.get_by_test_id("total").wait_for()
        check("H3 plan and tasks are still there", num(pg, "total") >= 3)
        pg.goto(FRONT + "/notebook")
        pg.get_by_text("Calvin cycle summary").wait_for()
        pg.get_by_role("button", name=re.compile("Calvin cycle summary")).click()
        check("H4 the note is still there with its text", "Edited line." in pg.get_by_label("Your note").input_value())
        pg.get_by_role("tab", name="My Documents").click()
        pg.get_by_text("photosynthesis.pdf").first.wait_for()
        check("H5 documents are still there", pg.locator("ul[aria-label='My documents'] li").count() == 2)

        # ------------------------------------------------------------------ I. account window
        pg.get_by_role("button", name="My account").first.click()
        dlg = pg.get_by_role("dialog")
        dlg.get_by_label("Name shown in MindSync").fill("Abi Renamed")
        dlg.get_by_role("button", name="Save name").click()
        dlg.get_by_text("Your name was saved.").wait_for()
        check("I1 name can be changed", True)
        dlg.get_by_label("Current password").fill(PW)
        dlg.get_by_label("New password", exact=True).fill("Newer-pass-2")
        dlg.get_by_label("New password again").fill("Newer-pass-2")
        dlg.get_by_role("button", name="Change password").click()
        dlg.get_by_text("Your password was changed.").wait_for()
        check("I2 password can be changed", True)
        with pg.expect_download() as dl:
            dlg.get_by_role("button", name="Download my data").click()
        exported = json.loads(Path(dl.value.path()).read_text())
        check("I3 data export contains plans, notes and document names", bool(exported.get("study_plans")) and bool(exported.get("notebook_notes")) and bool(exported.get("notebook_documents")), str(list(exported))[:120])
        dlg.get_by_role("button", name="Log out").click()
        pg.wait_for_url(re.compile(r"/login|/$"))
        login(pg, email, "Newer-pass-2")
        check("I4 the new password works", True)
        pg.get_by_role("button", name="My account").first.click()
        dlg = pg.get_by_role("dialog")
        dlg.get_by_role("button", name=re.compile("Delete my account")).click()
        dlg.get_by_label(re.compile("Type your password")).fill("Newer-pass-2")
        dlg.get_by_role("button", name="Yes, delete everything").click()
        pg.wait_for_url(re.compile(r"/login|/$"), timeout=15000)
        check("I5 the account can be deleted", True)
        pg.goto(FRONT + "/login")
        pg.get_by_label(re.compile(r"email", re.I)).first.fill(email)
        pg.locator('input[type="password"]').first.fill("Newer-pass-2")
        pg.get_by_role("button", name=re.compile(r"^log in$", re.I)).click()
        pg.get_by_role("alert").wait_for()
        check("I6 a deleted account cannot log in again", "/dashboard" not in pg.url)

        # ------------------------------------------------------------------ J. phone layout
        ph = br.new_context(viewport={"width": 390, "height": 800}, timezone_id="Europe/Copenhagen", is_mobile=True, has_touch=True)
        pp = ph.new_page()
        register(pp, "Phone Student")
        for path, name in zip(PATHS, FOUR):
            pp.goto(FRONT + path)
            pp.wait_for_load_state("networkidle")
            check(f"J {name} fits a phone (no sideways scroll)", no_sideways_scroll(pp))
            pp.screenshot(path=str(SHOTS / f"07_phone_{path.strip('/')}.png"))
        pp.goto(FRONT + "/dashboard")
        pp.get_by_role("button", name="Open menu").click()
        check("J5 phone menu opens with the four pages plus My Profile and Settings", pp.get_by_role("navigation", name="Pages").locator("a").count() == 6)
        pp.screenshot(path=str(SHOTS / "07_phone_menu.png"))

        own = [u for u in failed if not re.search(r"fonts\.(googleapis|gstatic)\.com", u) and not u.endswith("net::ERR_ABORTED")]  # cancelled loads (page left, empty 204 answers) are not failures      # web fonts may be blocked where the test runs
        check("K no browser errors and no failed requests on any page", not errors and not own, "; ".join(errors[:3] + own[:3]))
        br.close()
    p.stop()


if __name__ == "__main__":
    # a fake PDF (text renamed) for the "wrong file type" check
    (FILES / "fake.pdf").write_text("this is not really a pdf")
    try:
        run()
    except Exception as exc:                     # show where it stopped
        print("STOPPED:", str(exc).splitlines()[0])
        try:
            PG.screenshot(path=str(SHOTS / "stopped.png"), full_page=True)
            print("PAGE:", PG.url, "|", PG.locator("body").inner_text()[:600].replace("\n", " / "))
        except Exception:
            pass
        results.append(("run finished", False))
    bad = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(bad)} / {len(results)} checks passed")
    sys.exit(1 if bad else 0)
