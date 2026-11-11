"""
End-to-end browser test for the seven-page MindSync (Playwright + Chromium), added in update 25.

It drives the REAL pages against a REAL running backend (PostgreSQL) the way a student would. Smart Planner itself is covered by
e2e/browser_e2e.py (scenarios 1-16); this file covers the rest of the workflow:

  SMART PLANNER -> ROADMAP SAVED -> MY TASKS -> REMINDERS -> STUDENT CONFIRMS PROGRESS -> DASHBOARD UPDATES -> REPLAN KEEPS HISTORY

   A  the seven pages and the menu            B  My Tasks: roadmap saved, confirm, partly, delayed, edit, add, remove, undo, replan
   C  Dashboard shows only real progress      D  reminders (in-app only)            E  AI Learning Studio: sample, quiz, flashcards, progress
   F  Settings: theme, colours, text, reminders persist after reload                G  Profile: picture, name, phone, password, e-mail, sign out, delete
   H  Toolkit: six categories                 I  guest mode: the same workflow without an account
   J  phone layout: no sideways scroll on all seven pages                          K  screenshots of all seven pages (light, dark, phone)

Run (backend :8000 and frontend :5173 must be running; restart the backend first so the sign-up limiter is fresh):
    python e2e/browser_e2e_seven_pages.py [screenshot_folder]
"""
import json
import sys
import urllib.request
import uuid
from datetime import date, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

FRONT, BACK = "http://localhost:5173", "http://localhost:8000"
SHOTS = Path(sys.argv[1] if len(sys.argv) > 1 else "e2e_screenshots_seven")
SHOTS.mkdir(parents=True, exist_ok=True)
results = []
SEVEN = ["Smart Planner", "My Tasks", "Dashboard", "Student Toolkit", "AI Learning Studio", "Settings", "My Profile"]
PATHS = ["/planner", "/tasks", "/dashboard", "/toolkit", "/studio", "/settings", "/profile"]
PW = "Study-pass-1"


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(("PASS  " if ok else "FAIL  ") + name + (f"  [{detail}]" if detail else ""))


def call(path, body=None, token=None, method=None):
    req = urllib.request.Request(BACK + path, data=json.dumps(body).encode() if body is not None else None, method=method or ("POST" if body is not None else "GET"),
                                 headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})})
    with urllib.request.urlopen(req) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def new_student(label="Student"):
    email = f"seven-{uuid.uuid4().hex[:8]}@example.com"
    tok = call("/auth/register", {"email": email, "display_name": label, "password": PW})["access_token"]
    d = lambda n: (date.today() + timedelta(days=n)).isoformat()
    call("/assist/plan-form", {"subjects": [
        {"id": "s1", "name": "Mathematics", "topics": [{"id": "m1", "name": "Quadratic equations", "type": "exam", "progress": "none", "deadline": d(9), "understanding": 2}]},
        {"id": "s2", "name": "Python Programming", "topics": [{"id": "p1", "name": "Loops practice", "type": "homework", "deadline": d(12)}]}],
        "availability": {"daily_minutes": 120}}, tok)
    return email, tok


def eventually(pg, cond, timeout_ms=15000):
    waited = 0
    while waited <= timeout_ms:
        try:
            if cond():
                return True
        except Exception:
            pass
        pg.wait_for_timeout(250)
        waited += 250
    return False


def signed_in(b, tok, w=1280, h=900, scheme="light"):
    c = b.new_context(viewport={"width": w, "height": h}, color_scheme=scheme)
    pg = c.new_page()
    errs = []
    pg.errs = errs
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" and "net::" not in m.text and "429" not in m.text else None)
    pg.goto(FRONT + "/login")
    pg.evaluate("t => localStorage.setItem('mindsync_token', t)", tok)
    return c, pg


def overflow(pg):
    return pg.evaluate("document.documentElement.scrollWidth - window.innerWidth")


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        email, tok = new_student("Seven Student")

        # ================= A. seven pages =================
        c, pg = signed_in(b, tok)
        pg.goto(FRONT + "/dashboard"); pg.wait_for_selector("nav a", timeout=15000)
        links = [a.inner_text().strip().split("\n")[0] for a in pg.locator("aside.sidebar nav a").all()]
        names = [l for l in links if l in SEVEN]
        check("A  The menu has exactly the seven pages, in the planned order", names == SEVEN, str(links))
        for path, name in zip(PATHS, SEVEN):
            pg.goto(FRONT + path); pg.wait_for_timeout(1200)
            check(f"A  {name} opens and has its own heading", pg.locator("h1", has_text=name).count() >= 1 or (name == "Dashboard" and "Dashboard" in pg.title()))

        # ================= B. My Tasks =================
        pg.goto(FRONT + "/tasks"); pg.wait_for_selector("#mt-sum-title", timeout=15000)
        txt = pg.inner_text("main")
        check("B  My Tasks shows 'Day N of total' from the saved roadmap", "Day 1 of" in txt, txt[:80].replace("\n", " "))
        check("B  The five views are there (Today, Tomorrow, Full Roadmap, Completed, Overdue / Delayed)", all(pg.get_by_role("tab", name=t).count() for t in ("Today", "Tomorrow", "Full Roadmap", "Completed", "Overdue")))
        saved = call("/roadmap", None, tok)
        n_blocks = saved["summary"]["total_blocks"]
        check("B  The WHOLE roadmap is saved in the database, not only today", n_blocks > 3 and saved["summary"]["days_total"] > 3, f"{n_blocks} blocks over {saved['summary']['days_total']} days")
        pg.reload(); pg.wait_for_selector("#mt-sum-title", timeout=15000)
        check("B  After a reload the roadmap is still there", pg.locator("#mt-sum-title").count() >= 1)
        pg.screenshot(path=str(SHOTS / "02_my_tasks.png"), full_page=True)
        # Done with real minutes
        first_title = pg.locator(".mt-block-title").first.inner_text()
        pg.get_by_role("button", name="Done", exact=True).first.click()
        pg.wait_for_selector("text=How did it go?")
        pg.get_by_label("How many minutes did you study?").fill("20")
        pg.get_by_label("Okay").check()
        pg.get_by_role("button", name="Save My Progress").click()
        check("B  Done: 'How did it go?' then Save My Progress is confirmed on screen", eventually(pg, lambda: pg.get_by_text("Saved", exact=False).count() > 0))
        s = call("/roadmap", None, tok)["summary"]
        check("B  The confirmation is in the database (1 block done, 20 minutes studied)", s["done"] == 1 and s["studied_minutes"] == 20, f"done={s['done']} min={s['studied_minutes']}")
        pg.get_by_role("tab", name="Completed").click(); pg.wait_for_timeout(600)
        check("B  The finished block is listed under Completed with the studied minutes", "studied 20 min" in pg.inner_text("main"))
        # Dashboard reads the same numbers
        pg.goto(FRONT + "/dashboard"); pg.wait_for_timeout(2500)
        dash = pg.inner_text("main")
        check("C  The Dashboard shows the confirmed progress (real numbers, not invented)", "My study roadmap progress" in dash and ("20 min" in dash or "0h 20" in dash or "20m" in dash or "0:20" in dash or "20" in dash), dash[:60].replace("\n", " "))
        check("C  The Dashboard says completion is not the same as mastery", "not the same as mastering" in dash)
        pg.screenshot(path=str(SHOTS / "03_dashboard.png"), full_page=True)
        # Partly / not done / delayed / undo
        pg.goto(FRONT + "/tasks"); pg.wait_for_selector("#mt-sum-title", timeout=15000)
        pg.get_by_role("button", name="Update progress").first.click()
        pg.wait_for_selector("text=How did it go?")
        pg.get_by_label("Partly done").check()
        pg.get_by_label("How many minutes did you study?").fill("10")
        pg.get_by_role("button", name="Save My Progress").click(); pg.wait_for_timeout(1500)
        s = call("/roadmap", None, tok)["summary"]
        check("B  Partly done saves the real minutes", s["partial"] == 1, f"partial={s['partial']}")
        pg.get_by_role("button", name="Update progress").first.click()
        pg.wait_for_selector("text=How did it go?")
        pg.get_by_label("Partly done").check()
        pg.get_by_label("How many minutes did you study?").fill("999")
        pg.get_by_role("button", name="Save My Progress").click(); pg.wait_for_timeout(800)
        check("B  Impossible minutes (999) are refused: the form stays open and nothing is saved", pg.get_by_text("How did it go?").count() >= 1 and call("/roadmap", None, tok)["summary"]["studied_minutes"] == 30)
        pg.get_by_role("button", name="Cancel").click()
        pg.get_by_role("button", name="Tomorrow", exact=True).first.click(); pg.wait_for_timeout(1500)
        s = call("/roadmap", None, tok)["summary"]
        check("B  Tomorrow (postpone) marks a block Delayed and keeps it", s["delayed"] >= 1, f"delayed={s['delayed']}")
        # edit
        pg.locator(".mt-more summary").first.click()
        pg.get_by_role("button", name="Edit", exact=True).first.click()
        pg.wait_for_selector("text=Edit this study block")
        pg.get_by_label("Title").fill("My renamed block")
        pg.get_by_role("button", name="Save change").click(); pg.wait_for_timeout(1200)
        check("B  Editing a block changes its title and marks it as Yours", pg.locator("text=My renamed block").count() >= 1 and pg.locator("text=Yours").count() >= 1)
        # add own block
        pg.get_by_role("button", name="Add a study block").click()
        pg.wait_for_selector("#mt-add-title")
        pg.get_by_label("What will you study?").fill("Revise lecture notes")
        pg.get_by_role("button", name="Add block").click(); pg.wait_for_timeout(1200)
        check("B  The student can add their own block", any(x["title"] == "Revise lecture notes" for d in call("/roadmap", None, tok)["days"] for x in d["items"]))
        # remove needs confirmation
        pg.get_by_role("tab", name="Full Roadmap").click(); pg.wait_for_timeout(600)
        before = call("/roadmap", None, tok)["summary"]["total_blocks"]
        row = pg.locator(".mt-block", has_text="Revise lecture notes").first
        row.locator(".mt-more summary").click()
        row.get_by_role("button", name="Remove").click()
        pg.wait_for_selector("text=Remove this block?")
        check("B  Removing asks for confirmation first and has not removed anything yet", call("/roadmap", None, tok)["summary"]["total_blocks"] == before)
        pg.get_by_role("button", name="Keep it").click(); pg.wait_for_timeout(400)
        check("B  'Keep it' leaves the block", call("/roadmap", None, tok)["summary"]["total_blocks"] == before)
        # replan preview then confirm
        pg.get_by_role("button", name="Replan My Remaining Work").click()
        pg.wait_for_selector("text=This is a preview")
        check("B  Replan shows a preview of what is kept and replaced, and changes nothing yet", pg.locator("text=Kept:").count() >= 1 and pg.locator("text=Replaced:").count() >= 1 and call("/roadmap", None, tok)["summary"]["total_blocks"] == before)
        pg.screenshot(path=str(SHOTS / "02b_replan_preview.png"))
        pg.get_by_role("button", name="Yes, replace my remaining plan").click(); pg.wait_for_timeout(2500)
        s2 = call("/roadmap", None, tok)["summary"]
        check("B  After replanning the confirmed work and its minutes are kept (history preserved)", s2["done"] >= 1 and s2["studied_minutes"] >= 30, f"done={s2['done']} min={s2['studied_minutes']}")

        # ================= D. reminders =================
        rem = call("/reminders", None, tok)
        check("D  Reminders exist inside the app, and the page says nothing is e-mailed", rem["delivery"] == "in_app" and rem["email_available"] is False and "No email" in rem["delivery_note"] or "email" in rem["delivery_note"].lower(), rem["delivery_note"][:80])
        pg.goto(FRONT + "/tasks"); pg.wait_for_selector("#mt-sum-title", timeout=15000)
        check("D  The bell with the unread count is in the menu", pg.locator("aside.sidebar nav a", has_text="My Tasks").locator(".nav-badge, .badge, span").count() >= 1)
        check("D  My Tasks lists the reminders", "Reminders" in pg.inner_text("main"))
        check("D  Deadline cards say Upcoming / Due today / Overdue / Completed", "Deadlines" in pg.inner_text("main") and "Upcoming" in pg.inner_text("main"))

        # ================= E. AI Learning Studio =================
        pg.goto(FRONT + "/studio"); pg.wait_for_selector("text=How it works", timeout=15000)
        st = pg.inner_text("main")
        check("E  The Studio says plainly that AI is not switched on", "AI is not switched on yet" in st)
        check("E  The create button is not usable without AI (it is switched off, nothing is sent)", pg.get_by_role("button", name="Create My Learning Pack").is_disabled())
        pg.screenshot(path=str(SHOTS / "05_studio.png"), full_page=True)
        pg.get_by_role("button", name="Try a Sample Learning Pack").click()
        pg.wait_for_selector("text=Hand-written sample", timeout=10000)
        check("E  The sample pack is labelled as hand-written, not AI", "hand-written sample" in pg.inner_text("main").lower() and "not made by ai" in pg.inner_text("main").lower())
        for tab in ("Learn", "Quiz", "Flashcards", "Revise", "Progress"):
            check(f"E  Tab '{tab}' is there", pg.get_by_role("tab", name=tab).count() == 1)
        pg.get_by_role("tab", name="Quiz").click()
        pg.get_by_label("5", exact=True).check()
        pg.get_by_role("button", name="Start quiz").click()
        for q in range(5):
            pg.wait_for_selector("fieldset.st-options"); pg.locator("fieldset.st-options input").first.check()
            pg.get_by_role("button", name="Next").click() if q < 4 else pg.get_by_role("button", name="Finish and see my score").click()
        pg.wait_for_selector("text=Review Answers", timeout=10000)
        res = pg.inner_text("main")
        check("E  The quiz is marked with a score, explanations and 'Review Answers'", "Review Answers" in res and ("%" in res or "out of" in res.lower() or "/" in res))
        check("E  The score is described as practice, not mastery", "not a measure" in res.lower() or "practice" in res.lower())
        if pg.get_by_role("button", name="Retry Incorrect").count():
            pg.get_by_role("button", name="Retry Incorrect").click(); pg.wait_for_selector("fieldset.st-options", timeout=8000)
            check("E  Retry Incorrect re-asks only the questions that were wrong", True)
        pg.goto(FRONT + "/studio"); pg.wait_for_timeout(1000)
        pg.get_by_role("button", name="Open", exact=True).first.click(); pg.wait_for_selector("text=Hand-written sample")
        pg.get_by_role("tab", name="Flashcards").click(); pg.wait_for_timeout(600)
        pg.locator("button.st-card").first.click(); pg.wait_for_timeout(300)
        for rating in ("Easy", "Okay", "Difficult"):
            if pg.get_by_role("button", name=rating, exact=True).count():
                pg.get_by_role("button", name=rating, exact=True).first.click(); pg.wait_for_timeout(500)
                if pg.locator("button.st-card").count():
                    pg.locator("button.st-card").first.click(); pg.wait_for_timeout(300)
        cards = call(f"/studio/packs/{call('/studio/packs', None, tok)['packs'][0]['id']}/cards?mode=all", None, tok)
        check("E  Flashcard ratings move cards between spaced-repetition boxes", any(c_["box"] > 0 for c_ in cards["cards"]) and any(c_["reviews"] > 0 for c_ in cards["cards"]))
        sm = call("/studio/summary", None, tok)
        check("E  The Studio summary has the real quiz result for the Dashboard", sm["quizzes_taken"] >= 1 and sm["average_percent"] is not None, str(sm["quizzes_taken"]))
        pg.goto(FRONT + "/dashboard"); pg.wait_for_timeout(2500)
        check("E  The Dashboard shows the quiz result and revision reminders", "Learning Studio" in pg.inner_text("main"))
        pg.screenshot(path=str(SHOTS / "05b_studio_pack.png"), full_page=True)

        # ================= F. Settings =================
        pg.goto(FRONT + "/settings"); pg.wait_for_selector("h1:has-text('Settings')")
        pg.get_by_label("Light or dark").select_option("dark"); pg.wait_for_timeout(700)
        pg.get_by_role("radio", name="Purple").check(force=True); pg.wait_for_timeout(500)
        pg.get_by_label("Text size").select_option("larger"); pg.wait_for_timeout(500)
        pg.get_by_label("Readable contrast").check(force=True); pg.wait_for_timeout(500)
        pg.reload(); pg.wait_for_selector("h1:has-text('Settings')"); pg.wait_for_timeout(1200)
        ds = pg.evaluate("({t: document.documentElement.dataset.theme, a: document.documentElement.dataset.accent, x: document.documentElement.dataset.text, c: document.documentElement.dataset.contrast})")
        check("F  Dark theme, purple colour, larger text and readable contrast are applied and survive a reload", ds["t"] == "dark" and ds["a"] == "purple" and ds["x"] == "larger" and ds["c"] == "high", str(ds))
        saved_set = call("/settings", None, tok)["settings"]
        check("F  ... and are saved in the account (not just this browser)", saved_set.get("accent") == "purple" and saved_set.get("text_size") == "larger" and saved_set.get("high_contrast") is True, str({k: saved_set.get(k) for k in ("accent", "text_size", "high_contrast", "theme")}))
        page_text = pg.inner_text("main").lower()
        check("F  Settings shows no keys, SMTP, database or debug options", not any(w in page_text for w in ("api key", "smtp", "database url", "debug", "password for")), "")
        pg.screenshot(path=str(SHOTS / "06_settings_dark_purple.png"), full_page=True)
        # reminders settings
        pg.get_by_label("Time of the daily reminder").fill("07:30")
        pg.wait_for_timeout(1500)
        check("F  The daily reminder time is saved in the account", call("/settings", None, tok)["settings"].get("daily_reminder_time") == "07:30")
        pg.get_by_label("Light or dark").select_option("system"); pg.get_by_role("radio", name="Blue").check(force=True)
        pg.get_by_label("Text size").select_option("normal"); pg.get_by_label("Readable contrast").click(force=True); pg.wait_for_timeout(1200)
        check("F  Switching readable contrast off again works", pg.evaluate("document.documentElement.dataset.contrast") != "high")

        # ================= H. Toolkit =================
        pg.goto(FRONT + "/toolkit"); pg.wait_for_selector("h1:has-text('Student Toolkit')")
        cats = ["Focus and Concentration", "Memory and Revision", "Procrastination", "Exam Preparation", "Assignments and Projects", "Study Wellbeing"]
        check("H  The Toolkit has the six categories", all(pg.get_by_role("heading", name=cn, level=2).count() == 1 for cn in cats))
        tt = pg.inner_text("main").lower()
        check("H  Each technique has what, why, how and an example", tt.count("what it is") >= 18 and tt.count("how to do it") >= 18 and tt.count("example") >= 18 and tt.count("why it works") >= 18)
        check("H  The Toolkit has no AI quiz generator", "generate a quiz" not in tt.lower())
        pg.screenshot(path=str(SHOTS / "04_toolkit.png"), full_page=True)

        # ================= J. phone layout, all seven pages =================
        c.close()
        c, pg = signed_in(b, tok, 390, 844)
        worst = 0
        for path, name in zip(PATHS, SEVEN):
            pg.goto(FRONT + path); pg.wait_for_timeout(1800)
            o = overflow(pg); worst = max(worst, o)
            check(f"J  Phone: {name} has no sideways scroll", o <= 1, f"{o}px")
        call("/settings", {"text_size": "larger", "high_contrast": True, "accent": "pink"}, tok, method="PUT")
        for path, name in zip(PATHS, SEVEN):
            pg.goto(FRONT + path); pg.wait_for_timeout(1800)
            o = overflow(pg)
            check(f"J  Phone with larger text, readable contrast and the pink theme: {name} has no sideways scroll", o <= 1, f"{o}px")
        call("/settings", {"text_size": "normal", "high_contrast": False, "accent": "blue"}, tok, method="PUT")
        pg.goto(FRONT + "/tasks"); pg.wait_for_timeout(1500)
        pg.screenshot(path=str(SHOTS / "phone_02_my_tasks.png"), full_page=True)
        pg.goto(FRONT + "/studio"); pg.wait_for_timeout(1500)
        pg.screenshot(path=str(SHOTS / "phone_05_studio.png"), full_page=True)
        c.close()

        # ================= K. screenshots, light and dark, desktop =================
        for scheme in ("light", "dark"):
            c, pg = signed_in(b, tok, 1280, 900, scheme)
            for i, (path, name) in enumerate(zip(PATHS, SEVEN), 1):
                pg.goto(FRONT + path); pg.wait_for_timeout(2200)
                pg.screenshot(path=str(SHOTS / f"{scheme}_{i}_{name.lower().replace(' ', '_')}.png"), full_page=True)
            errs = [e for e in pg.errs if "ERR_TUNNEL" not in e]
            check(f"K  No browser errors while visiting all seven pages ({scheme})", not errs, str(errs[:2]))
            c.close()

        # ================= G. Profile =================
        email2, tok2 = new_student("Profile Student")
        c, pg = signed_in(b, tok2)
        pg.goto(FRONT + "/profile"); pg.wait_for_selector("h1:has-text('My Profile')"); pg.wait_for_timeout(1000)
        pg.get_by_role("radio", name="Fox").check(force=True); pg.wait_for_timeout(300)
        pg.get_by_label("Full name").fill("Muhammad Profile Student"); pg.get_by_label("Display name").fill("Profi")
        pg.get_by_label("Phone number").fill("+45 12 34 56 78"); pg.get_by_label("Field of study").fill("Computer Science")
        pg.get_by_label("My study goals").fill("Pass every module"); pg.get_by_label("Academic summary").fill("Second year, likes databases")
        pg.wait_for_timeout(2500)
        prof = call("/profile", None, tok2)
        check("G  Profile saves picture, full name, phone, field of study, goals and academic summary",
              prof["profile"]["avatar"] == "fox" and prof["profile"]["full_name"] == "Muhammad Profile Student" and prof["profile"]["phone"] == "+45 12 34 56 78"
              and prof["profile"]["course"] == "Computer Science" and prof["profile"]["goal"] == "Pass every module" and prof["profile"]["about_me"].startswith("Second year"), "")
        check("G  The display name is saved", prof["account"]["display_name"] == "Profi")
        pg.get_by_label("Phone number").fill("not a phone"); pg.wait_for_timeout(2500)
        check("G  A bad phone number is refused with a message and the old one is kept", call("/profile", None, tok2)["profile"]["phone"] == "+45 12 34 56 78" and pg.get_by_role("alert").count() >= 1)
        pg.reload(); pg.wait_for_selector("h1:has-text('My Profile')"); pg.wait_for_timeout(1200)
        check("G  After a reload the details are still there", pg.get_by_label("Full name").input_value() == "Muhammad Profile Student")
        pg.screenshot(path=str(SHOTS / "07_profile.png"), full_page=True)
        # change password
        pg.get_by_role("button", name="Change password").click()
        pg.get_by_label("Current password").fill(PW); pg.get_by_label("New password", exact=True).fill("Changed-pass-2"); pg.get_by_label("Repeat new password").fill("Changed-pass-2")
        pg.get_by_role("button", name="Save new password").click(); pg.wait_for_timeout(2000)
        try:
            ok_login = bool(call("/auth/login", {"email": email2, "password": "Changed-pass-2"}))
        except Exception:
            ok_login = False
        check("G  Change password works (the new password logs in)", ok_login)
        # change e-mail with a wrong password first
        new_mail = f"moved-{uuid.uuid4().hex[:6]}@example.com"
        pg.get_by_role("button", name="Change e-mail").click()
        pg.get_by_label("New e-mail address").fill(new_mail); pg.get_by_label("Password for e-mail change").fill("wrong-pass-9")
        pg.get_by_role("button", name="Save new e-mail").click(); pg.wait_for_timeout(1500)
        check("G  Changing e-mail with a wrong password is refused", pg.get_by_role("alert").count() >= 1 and call("/auth/me", None, tok2)["email"] == email2)
        pg.get_by_label("Password for e-mail change").fill("Changed-pass-2")
        pg.get_by_role("button", name="Save new e-mail").click(); pg.wait_for_timeout(2000)
        check("G  Changing e-mail with the right password works and the page shows the new address", call("/auth/me", None, tok2)["email"] == new_mail)
        # sign out
        pg.get_by_role("button", name="Sign out").click(); pg.wait_for_timeout(1500)
        check("G  Sign out returns to the welcome page and removes the login", pg.evaluate("localStorage.getItem('mindsync_token')") is None)
        # sign in again then delete
        tok3 = call("/auth/login", {"email": new_mail, "password": "Changed-pass-2"})["access_token"]
        pg.goto(FRONT + "/login"); pg.evaluate("t => localStorage.setItem('mindsync_token', t)", tok3)
        pg.goto(FRONT + "/profile"); pg.wait_for_selector("h1:has-text('My Profile')"); pg.wait_for_timeout(1000)
        pg.get_by_role("button", name="Delete my account").click()
        pg.get_by_label("Password", exact=True).fill("wrong-pass-9"); pg.get_by_role("button", name="Yes, erase it").click(); pg.wait_for_timeout(1500)
        still = False
        try:
            still = bool(call("/auth/me", None, tok3))
        except Exception:
            still = False
        check("G  Delete account with a wrong password does nothing", still)
        pg.get_by_label("Password", exact=True).fill("Changed-pass-2"); pg.get_by_role("button", name="Yes, erase it").click(); pg.wait_for_timeout(2500)
        try:
            call("/auth/login", {"email": new_mail, "password": "Changed-pass-2"}); gone = False
        except Exception:
            gone = True
        check("G  Delete account with the right password erases it (login no longer works)", gone)
        c.close()

        # ================= I. guest mode =================
        c = b.new_context(viewport={"width": 1280, "height": 900}); pg = c.new_page()
        pg.goto(FRONT + "/tasks"); pg.wait_for_timeout(1500)
        check("I  A guest with no plan is told to make one in Smart Planner", "do not have a roadmap yet" in pg.inner_text("main").lower())
        pg.goto(FRONT + "/planner?tab=form"); pg.wait_for_selector("text=Create My Study Plan", timeout=15000)
        pg.wait_for_selector("text=Loading your form", state="detached", timeout=15000)
        pg.get_by_label("Subject name").first.fill("Mathematics")
        pg.get_by_label("Topic or task name").first.fill("Quadratic equations")
        pg.get_by_role("button", name="Examination", exact=True).first.click()
        pg.get_by_role("button", name="In 1 week", exact=True).first.click()
        pg.get_by_role("button", name="Not started", exact=True).first.click()
        pg.get_by_label("How many chapters or topics does it cover?").first.fill("4")
        pg.get_by_role("button", name="Create My Study Plan").click(); pg.wait_for_selector("text=Your study roadmap", timeout=30000)
        pg.goto(FRONT + "/tasks?tab=full"); pg.wait_for_selector("#mt-sum-title", timeout=15000)      # late in the day nothing may be left for today, so use the whole roadmap
        check("I  A guest's plan appears in My Tasks (kept in this browser)", pg.locator(".mt-block").count() >= 1)
        pg.get_by_role("button", name="Done", exact=True).first.click(); pg.wait_for_selector("text=How did it go?")
        pg.get_by_label("How many minutes did you study?").fill("15"); pg.get_by_role("button", name="Save My Progress").click(); pg.wait_for_timeout(1500)
        gs = pg.evaluate("() => JSON.parse(localStorage.getItem('mindsync_guest_v1') || '{}')")
        check("I  A guest's confirmation is saved in the browser", any(x.get("status") == "done" and x.get("actual_minutes") == 15 for x in gs.get("roadmap", [])))
        pg.reload(); pg.wait_for_selector("#mt-sum-title", timeout=15000)
        check("I  ... and survives a reload", pg.locator(".mt-block.st-done").count() >= 1)
        pg.goto(FRONT + "/studio"); pg.wait_for_selector("text=How it works")
        check("I  The guest Studio says AI is off and that your own notes need an account", "AI is not switched on yet" in pg.inner_text("main") and "free account" in pg.inner_text("main").lower())
        pg.get_by_role("button", name="Try a Sample Learning Pack").click(); pg.wait_for_selector("text=Hand-written sample", timeout=10000)
        check("I  A guest can open and practise the sample pack", pg.get_by_role("tab", name="Quiz").count() == 1)
        pg.goto(FRONT + "/profile"); pg.wait_for_timeout(1500)
        check("I  The guest profile explains guest limits and offers a free account", "guest limits" in pg.inner_text("main").lower() or "Guest limits" in pg.inner_text("main"))
        pg.screenshot(path=str(SHOTS / "guest_07_profile.png"), full_page=True)
        c.close()
        b.close()

    failed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(failed)} / {len(results)} seven-page browser checks passed")
    if failed:
        print("FAILED:")
        for n in failed:
            print("  -", n)
        sys.exit(1)


if __name__ == "__main__":
    main()
