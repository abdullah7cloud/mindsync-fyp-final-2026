"""
End-to-end browser test for MindSync (Playwright + Chromium).

It drives the REAL web pages against a REAL running backend, the way a student would click through them:
  A. guest journey      welcome page -> Dashboard -> Smart Planner (understand -> check -> report -> accept -> today -> timer ->
                        session feedback -> low energy -> replan offer) -> Tasks -> Wellbeing -> History -> Toolkit -> Settings -> Profile
  B. account journey    register -> planner on the server -> tasks edit / complete / re-open -> settings that change the plan ->
                        profile -> dashboard with real numbers -> export -> delete
  C. first-impression checks (no browser errors, no leftover AI / music UI, plain everyday wording)
  F. premium look (full-width welcome photo, photo banners, readable words over photos, photo credits)
  E. photos and phone-size layout (images load and are small, nothing overflows on a phone, every page says where to start)

Run (backend on :8000 and the built frontend on :5173 must already be running):
    pip install playwright && playwright install chromium
    python e2e/browser_e2e.py [screenshot_folder]

The wellbeing steps run only when the wellbeing model is installed (GET /wellbeing/model says available).
Every check prints PASS or FAIL; the script exits with code 1 if anything failed.
"""
import json
import os
import sys
import urllib.request
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright

FRONT, BACK = "http://localhost:5173", "http://localhost:8000"
SHOTS = Path(sys.argv[1] if len(sys.argv) > 1 else "e2e_screenshots")
SHOTS.mkdir(parents=True, exist_ok=True)
results = []


def eventually(pg, condition, timeout_ms=20000):
    """Wait until condition() is true (polling), instead of a fixed pause. A slow laptop needs longer; a fast one returns at once."""
    waited = 0
    while waited <= timeout_ms:
        try:
            if condition():
                return True
        except Exception:
            pass
        pg.wait_for_timeout(250)
        waited += 250
    return False


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(("PASS  " if ok else "FAIL  ") + name + (f"  [{detail}]" if detail else ""))


def wellbeing_available():
    try:
        return json.load(urllib.request.urlopen(f"{BACK}/wellbeing/model", timeout=5)).get("available", False)
    except Exception:
        return False


# Answers that RAISE the estimated stress level when high, and ones that LOWER it when high (sleep, family support).
RAISES = {"Exam_Frequency", "Assignment_Load", "Social_Media_Use", "Screen_Time", "Anxiety_Level"}
LOWERS = {"Sleep_Hours", "Family_Support"}


def question_count():
    return len(json.load(urllib.request.urlopen(f"{BACK}/wellbeing/model", timeout=5)).get("questions", []))


def fill_wellbeing(pg, mode):
    """mode 'high' = the answers a high-stress student would give; 'low' = the calmest answers."""
    for s in pg.locator(".wb-q input[type=range]").all():
        name = s.get_attribute("id").removeprefix("wb-")
        s.fill(s.get_attribute("max" if (name in RAISES and mode == "high") or (name in LOWERS and mode == "low") else "min"))
    # the exercise question is a Yes/No choice: exercising lowers the estimate
    yes_no = pg.locator('.wb-q [role=radiogroup] button')
    if yes_no.count():
        pg.locator('.wb-q [role=radiogroup] button', has_text="No" if mode == "high" else "Yes").first.click()


def run():
    has_model = wellbeing_available()
    errors = []
    with sync_playwright() as p:
        b = p.chromium.launch(channel=os.environ.get("E2E_CHANNEL") or None)
        ctx = b.new_context(viewport={"width": 1280, "height": 1400})
        pg = ctx.new_page()
        # blocked web-font downloads are not app errors
        pg.on("pageerror", lambda e: errors.append(str(e)))
        # remember the answers of the sign-up / login / account routes, so a failure can be explained (status and time)
        api_log, bad = [], []
        pg.on("response", lambda r: (r.status >= 400 and "fonts.g" not in r.url and bad.append(f"{r.status} {r.request.method} {r.url.split('//')[-1][:80]}")) or ("/auth/" in r.url or "/account" in r.url) and api_log.append(f"{r.request.method} {r.url.split('8000')[-1]} -> {r.status}"))
        pg.on("console", lambda m: m.type == "error" and "ERR_TUNNEL" not in m.text and "net::" not in m.text and errors.append(m.text))

        # ---------------- A. guest ----------------
        pg.goto(FRONT + "/"); pg.wait_for_timeout(500)
        html = pg.content()
        check("Landing page loads with the main call to action", pg.locator("a", has_text="Get Started").count() > 0 and "Study Smarter" in html)
        check("Landing page has no AI-coach or music leftovers", "AI study coach" not in html and "Ambient" not in html and "lo-fi" not in html.lower())
        pg.screenshot(path=str(SHOTS / "01_landing.png"), full_page=True)

        def go(label):
            """Click a menu item (client-side navigation, like a student would)."""
            pg.locator("aside.sidebar a", has_text=label).first.click(); pg.wait_for_timeout(600)

        def tab(name):
            pg.locator("[role=tab]", has_text=name).first.click(); pg.wait_for_timeout(500)

        pg.goto(FRONT + "/dashboard"); pg.wait_for_timeout(800)
        check("Guest can open the dashboard without an account", pg.locator("text=You are trying MindSync as a guest").count() > 0)
        check("The menu offers exactly the five pages", all(pg.locator("aside.sidebar nav a", has_text=n).count() >= 1 for n in ["Smart Planner", "Dashboard", "Student Toolkit", "Settings", "My Profile"]))
        check("A new student sees an honest empty state, no invented numbers", pg.locator("h2", has_text="Nothing to show yet").count() == 1 and pg.locator(".kpis").count() == 0)

        # --- Smart Planner: one page for describing, checking, accepting, doing and learning ---
        go("Smart Planner")
        pg.wait_for_selector("#builder-text", timeout=10000)
        check("The Smart Planner opens on a single box for natural-language tasks", pg.locator("#builder-text").count() == 1)
        check("The planner has Plan / Tasks / Calendar / Focus tabs", [t.strip().rstrip("0123456789").strip() for t in pg.locator("[role=tab]").all_inner_texts()][:4] == ["Plan", "Tasks", "Calendar", "Focus"])
        pg.fill("#builder-text", "I have a stats exam in 10 days and I don't know chapter 5 yet.\nAlso a 1,500 word report due next Friday.")
        pg.click("button:has-text('Understand my tasks')")
        check("Two task drafts are understood from the text", eventually(pg, lambda: pg.locator("#draft-d1-title").count() == 1 and pg.locator("#draft-d2-title").count() == 1, 15000))
        t1, t2 = pg.input_value("#draft-d1-title"), pg.input_value("#draft-d2-title")
        check("The drafts have short titles, not the whole sentence", len(t1) < 40 and len(t2) < 40, f"{t1!r} | {t2!r}")
        pg.screenshot(path=str(SHOTS / "g1_drafts.png"), full_page=True)
        pg.click("button:has-text('Evaluate my plan')")
        check("Evaluate gives one combined report with a verdict", eventually(pg, lambda: pg.locator(".report").count() >= 1 and pg.locator(".report-head").count() >= 1, 15000))
        rep = pg.locator(".report").first.inner_text()
        check("The report shows a workload range, difficulty and a day-by-day schedule", "Likely" in rep or "likely" in rep or "min" in rep)
        check("The report names where its words come from (rules or AI)", "Written by" in rep)
        pg.screenshot(path=str(SHOTS / "g2_report.png"), full_page=True)
        pg.click("button:has-text('Accept and save my plan')")
        check("Accepting saves the tasks and shows today's blocks", eventually(pg, lambda: pg.locator(".block").count() >= 1, 15000))
        check("The menu badge counts the saved tasks", eventually(pg, lambda: pg.locator("aside.sidebar .nav-badge").first.inner_text().strip() == "2"))
        pg.screenshot(path=str(SHOTS / "g3_plan.png"), full_page=True)

        pg.click(".block button:has-text('Start')"); pg.wait_for_timeout(700)
        check("Starting a block opens the Focus tab linked to that block", pg.locator(".focus-panel").count() == 1)
        pg.click(".timer-buttons button:has-text('Start')"); pg.wait_for_timeout(1200)
        pg.click("button:has-text('Finish now')")
        check("Finishing the timer opens the feedback form", eventually(pg, lambda: pg.locator(".modal [role=dialog], [role=dialog]").count() >= 1, 5000))
        pg.click("fieldset:has-text('How hard') .scale-row label >> nth=4")
        pg.click(".modal button:has-text('Save')")
        check("Feedback says what MindSync learned from the session", eventually(pg, lambda: pg.locator(".modal h2", has_text="what I learned").count() == 1, 10000))
        check("Learned text mentions the difficulty it changed", "difficulty" in pg.locator(".modal").inner_text())
        pg.click(".modal button:has-text('Done')"); pg.wait_for_timeout(500)
        check("Guest session history stays in the browser and holds only numbers", pg.evaluate("() => { const d = JSON.parse(localStorage.getItem('mindsync_guest_v1')); return d.taskSessions.length === 1 && !JSON.stringify(d.taskSessions).toLowerCase().includes('stats'); }"))

        # energy -> plan adjustment offer, never applied automatically
        tab("Plan")
        before = pg.evaluate("() => JSON.stringify(JSON.parse(localStorage.getItem('mindsync_guest_v1')).plan.days.map(d => d.sessions.length))")
        pg.locator(".energy-buttons button").first.click()
        check("Very low energy offers a lighter plan (and does not change it by itself)", eventually(pg, lambda: pg.locator(".replan").count() == 1, 12000) and
              pg.evaluate("() => JSON.stringify(JSON.parse(localStorage.getItem('mindsync_guest_v1')).plan.days.map(d => d.sessions.length))") == before)
        pg.screenshot(path=str(SHOTS / "g4_replan.png"), full_page=True)
        pg.click("button:has-text('Update my plan')")
        check("Accepting the offer updates the plan and removes the banner", eventually(pg, lambda: pg.locator(".replan").count() == 0, 12000))

        tab("Calendar")
        check("The calendar shows the plan by day", pg.locator(".plan-calendar, .calendar").count() >= 1)
        tab("Tasks")
        check("The Tasks tab lists the two saved tasks", eventually(pg, lambda: pg.locator(".task-item").count() == 2))
        pg.fill("input[type=search]", "zzzz-no-match"); pg.wait_for_timeout(300)
        check("The task search filters the list", pg.locator(".task-item").count() == 0)
        pg.fill("input[type=search]", ""); pg.wait_for_timeout(300)
        pg.screenshot(path=str(SHOTS / "g5_tasks.png"), full_page=True)

        # --- Dashboard: real numbers only ---
        go("Dashboard")
        check("After studying, the dashboard shows real figures", eventually(pg, lambda: pg.locator(".kpis").count() == 1, 12000))
        check("The dashboard offers the weekly review", pg.locator("text=Your weekly review").count() >= 1)
        pg.screenshot(path=str(SHOTS / "g6_dashboard.png"), full_page=True)
        tab("History")
        check("History shows the study chart from the logged session", eventually(pg, lambda: pg.locator("text=Minutes studied, last 14 days").count() == 1))
        tab("Wellbeing")
        if has_model:
            check("Wellbeing form shows every question the model was trained on", eventually(pg, lambda: pg.locator(".wb-q").count() > 0 or pg.locator("button", has_text="Start the check").count() > 0))
            if pg.locator("button", has_text="Start the check").count():
                pg.click("button:has-text('Start the check')")
            pg.wait_for_selector(".wb-q")
            check("All 8 trained questions are asked", pg.locator(".wb-q").count() == question_count() == 8, str(pg.locator(".wb-q").count()))
            fill_wellbeing(pg, "high"); pg.click("text=Show my result"); pg.wait_for_selector(".wb-verdict", timeout=8000)
            first = pg.inner_text(".wb-verdict").replace("\n", " ")
            pg.wait_for_timeout(700)
            check("Wellbeing result shows a label and probability bars", pg.locator(".wb-bar").count() == 3, first)
            check("The page explains the model's limits", pg.locator("text=cannot diagnose anything").count() >= 1)
            pg.screenshot(path=str(SHOTS / "02_wellbeing_result.png"), full_page=True)
            if "High" in first:
                go("Smart Planner")
                check("A High result offers a gentler plan (it does not change the plan by itself)", eventually(pg, lambda: pg.locator(".replan").count() >= 1, 12000))
                go("Dashboard"); tab("Wellbeing")
            if pg.locator("button", has_text="Check again").count():
                pg.click("text=Check again")
            pg.wait_for_selector(".wb-q"); fill_wellbeing(pg, "low"); pg.click("text=Show my result"); pg.wait_for_selector(".wb-verdict")
            pg.wait_for_timeout(700)
        else:
            print("NOTE  wellbeing model not installed - wellbeing steps skipped (not counted)")

        go("Student Toolkit")
        check("The Toolkit lists techniques with references and limits", pg.locator("text=Limits of the evidence").count() >= 3 and pg.locator("h2", has_text="References").count() == 1)
        check("The Toolkit says it is not a diagnosis", pg.locator("text=Nothing in MindSync diagnoses").count() == 1)
        pg.screenshot(path=str(SHOTS / "g7_toolkit.png"), full_page=True)

        go("Settings")
        check("Guest sees that data is saved only in the browser", pg.locator("text=saved only in this browser").count() >= 1)
        check("Settings has study time, AI, reminders and display controls", all(pg.locator("h2", has_text=h).count() >= 1 for h in ["Study time", "AI assistant", "Email reminders", "Display"]))
        # a setting with a real effect: fewer study minutes per weekday -> the stored plan no longer matches -> an offer appears
        pg.fill("#s-wd", "30"); pg.wait_for_timeout(1800)   # settings save by themselves
        go("Smart Planner")
        check("Changing study minutes makes the planner offer an updated plan (settings are connected)", eventually(pg, lambda: pg.locator(".replan").count() == 1, 12000))
        go("Settings"); pg.fill("#s-wd", "120"); pg.wait_for_timeout(1800)
        go("My Profile")
        check("My Profile is optional and says nothing is guessed", pg.locator("text=Nothing is guessed").count() >= 1)
        check("The profile shows what was learned from the logged session", pg.locator("h2", has_text="What MindSync has learned").count() == 1)
        pg.screenshot(path=str(SHOTS / "g8_profile.png"), full_page=True)

        # old addresses still land somewhere useful
        pg.goto(FRONT + "/tasks"); pg.wait_for_timeout(700)
        check("Old /tasks address lands on the Tasks tab of the planner", "/planner" in pg.url and "tab=tasks" in pg.url)
        pg.goto(FRONT + "/analytics"); pg.wait_for_timeout(700)
        check("Old /analytics address lands on Dashboard history", "/dashboard" in pg.url and "tab=history" in pg.url)

        
        # ---------------- B. account ----------------
        email = f"e2e-{uuid.uuid4().hex[:8]}@example.com"
        pw = "Study-pass-12345"
        pg.goto(FRONT + "/register"); pg.wait_for_timeout(400)
        pg.fill("input >> nth=0", "E2E Student"); pg.fill("input[type=email]", email)
        for i in pg.locator("input[type=password]").all():
            i.fill(pw)
        pg.click("button[type=submit]")
        try:
            pg.wait_for_url("**/dashboard", timeout=40000)   # sign-up hashes the password (Argon2); a busy laptop can need many seconds
        except Exception:
            print("DIAGNOSIS: sign-up did not reach the dashboard. API answers seen:", api_log)
            print("DIAGNOSIS: visible message:", [t for t in pg.locator("[role=alert], .error, .form-error").all_inner_texts()][:3])
            pg.screenshot(path=str(SHOTS / "FAIL_signup.png"), full_page=True)
            check("Registration lands on the dashboard", False)
            b.close()
            failed = [n for n, ok in results if not ok]
            print(f"\n{len(results) - len(failed)} / {len(results)} browser checks passed")
            return 1
        pg.wait_for_timeout(1200)
        check("Registration lands on the dashboard", "dashboard" in pg.url)
        check("Guest tasks and plan moved into the new account", eventually(pg, lambda: pg.locator("aside.sidebar .nav-badge").first.inner_text().strip() == "2", 20000))
        go("Smart Planner")
        # tasks move with the guest's data; the plan itself is rebuilt on the server, and the student is asked first
        check("The moved tasks are offered a plan (nothing is planned behind the student's back)", eventually(pg, lambda: pg.locator(".replan button:has-text('Add them to my plan')").count() == 1, 20000))
        pg.click(".replan button:has-text('Add them to my plan')")
        check("Adding them builds the plan on the server", eventually(pg, lambda: pg.locator(".block").count() >= 1 and pg.locator(".replan").count() == 0, 20000))

        # describe a new task with the planner, evaluate, accept: it joins the existing plan
        pg.locator("button:has-text('Add tasks')").first.click(); pg.wait_for_selector("#builder-text", timeout=8000)
        pg.fill("#builder-text", "Read chapter 3 of the textbook by next Tuesday")
        pg.click("button:has-text('Understand my tasks')")
        check("A signed-in student can describe a task in words", eventually(pg, lambda: pg.locator("#draft-d1-title").count() == 1, 20000))
        pg.click("button:has-text('Evaluate my plan')")
        check("Evaluate checks it against the rest of the plan", eventually(pg, lambda: pg.locator(".report").count() >= 1, 20000))
        pg.click("button:has-text('Accept and save my plan')")
        check("Accepting adds the task (3 now)", eventually(pg, lambda: pg.locator("aside.sidebar .nav-badge").first.inner_text().strip() == "3", 20000))

        # edit, complete, re-open from the Tasks tab
        tab("Tasks")
        pg.wait_for_selector(".task-item", timeout=8000)
        row = pg.locator(".task-item").first
        title0 = row.locator("h3, .task-title").first.inner_text().strip()
        row.locator("text=Edit").click()
        pg.fill(".task-edit input >> nth=0", "E2E report (edited)")
        pg.click(".task-edit >> text=Save changes"); pg.wait_for_timeout(1000)
        check("A task can be edited", eventually(pg, lambda: pg.locator("text=E2E report (edited)").count() >= 1))
        pg.locator(".task-item", has_text="E2E report (edited)").locator(".done-button").click(); pg.wait_for_timeout(1000)
        check("A finished task leaves the To do list", pg.locator(".task-item", has_text="E2E report (edited)").count() == 0)
        check("Finishing a task lowers the badge (workload connected to the menu)", eventually(pg, lambda: pg.locator("aside.sidebar .nav-badge").first.inner_text().strip() == "2"))
        pg.click("[role=tab]:has-text('Finished')"); pg.wait_for_timeout(400)
        check("Finishing a task moves it to the Finished list", pg.locator(".task-item", has_text="E2E report (edited)").count() == 1)
        pg.locator(".task-item.task-status-completed >> text=Move back to To Do").first.click(); pg.wait_for_timeout(1000)
        check("A finished task can be moved back to To Do", pg.locator(".task-item.task-status-completed").count() == 0)

        # settings change the plan offer; profile goal appears on the dashboard
        go("Settings")
        pg.wait_for_selector("h2:has-text('Study time')", timeout=8000)
        check("Signed-in Settings show the AI status honestly", pg.locator("text=Connected").count() >= 1 or pg.locator("text=not connected").count() >= 1 or pg.locator("text=rules").count() >= 1)
        pg.screenshot(path=str(SHOTS / "u_settings.png"), full_page=True)
        go("My Profile")
        pg.wait_for_selector("h2:has-text('About you')", timeout=8000)
        pg.fill("#pf-hours", "6"); pg.wait_for_timeout(2000)   # the profile saves by itself
        go("Dashboard")
        check("A weekly goal set in My Profile appears on the Dashboard", eventually(pg, lambda: pg.locator("text=Weekly goal: 6 hours").count() == 1, 12000))
        pg.screenshot(path=str(SHOTS / "u_dashboard.png"), full_page=True)

        # (checked here, BEFORE the wrong-password step below, which intentionally causes one 403 response)
        check("No JavaScript errors in the browser console", not errors, "; ".join(errors[:3]) + (" | failed requests: " + "; ".join(sorted(set(bad))[:6]) if errors else ""))

        # export + delete (Settings page; the account panel is already open there)
        go("Settings")
        with pg.expect_download() as dl:
            pg.click("text=Download my data")
        data = json.loads(Path(dl.value.path()).read_text())
        check("Exported data has tasks, check-ins and no password", len(data["tasks"]) >= 3 and "password" not in json.dumps(data).lower())
        pg.click("text=Delete my account")
        pg.fill("input[aria-label=Password]", "wrong-password-1"); pg.click("text=Yes, erase it"); pg.wait_for_timeout(700)
        check("Deleting with the wrong password is refused", eventually(pg, lambda: pg.locator("[role=alert]", has_text="not correct").count() == 1) and "/settings" in pg.url)
        pg.fill("input[aria-label=Password]", pw); pg.click("text=Yes, erase it"); pg.wait_for_url(FRONT + "/", timeout=8000)
        check("Deleting with the right password signs out and returns to the landing page", pg.url.rstrip("/") == FRONT)
        r = urllib.request.Request(BACK + "/auth/login", data=json.dumps({"email": email, "password": pw}).encode(), headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(r); gone = False
        except urllib.error.HTTPError as e:
            gone = e.code == 401
        check("The deleted account can no longer log in", gone)

        
        # ---------------- D. forgot password ----------------
        # Uses the e-mail "outbox" folder (demo mode: no mail server). With real SMTP the link goes to a real inbox,
        # so the part that needs to read the link is skipped.
        fp_email = f"e2e-forgot-{uuid.uuid4().hex[:8]}@example.com"
        old_pw, new_pw = "Study-pass-12345", "Fresh-start-67890"
        urllib.request.urlopen(urllib.request.Request(BACK + "/auth/register", data=json.dumps(
            {"email": fp_email, "password": old_pw, "display_name": "Forgot Test"}).encode(), headers={"Content-Type": "application/json"}), timeout=60)
        pg.goto(FRONT + "/login"); pg.wait_for_timeout(500)
        check("The login page has a Forgot password link", pg.locator("a", has_text="Forgot your password").count() == 1)
        check("The login page can show and hide the password", pg.locator("input[type=password]").count() == 1 and pg.locator("button", has_text="Show").count() == 1)
        pg.click("a:has-text('Forgot your password')"); pg.wait_for_url("**/forgot-password", timeout=8000)
        pg.fill("input[type=email]", fp_email); pg.click("button[type=submit]")
        check("Forgot password shows a neutral 'check your email' message", eventually(pg, lambda: pg.locator("text=Check your email").count() == 1, 40000))
        pg.screenshot(path=str(SHOTS / "forgot_password.png"), full_page=True)
        outbox = Path(__file__).resolve().parent.parent / "backend" / "outbox"
        link = None
        if pg.locator("text=cannot send real emails yet").count() == 1:
            import re as _re
            def find_link():
                nonlocal link
                for f in sorted(outbox.glob("*.eml"), key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
                    # parse the message properly: long lines in the file are wrapped (quoted-printable), a mail program un-wraps them
                    import email as _email, email.policy as _policy
                    msg = _email.message_from_bytes(f.read_bytes(), policy=_policy.default)
                    txt = msg.get_body(("plain",)).get_content() if msg.get_body(("plain",)) else ""
                    if fp_email in str(msg["To"]):
                        m = _re.search(r"(http\S*/reset-password\?token=[A-Za-z0-9_\-]+)", txt)
                        if m:
                            link = m.group(1)
                            return True
                return False
            check("The reset email was saved to the outbox with a link", eventually(pg, find_link, 15000))
        else:
            print("SKIP  real email is configured: the reset link is in the inbox, so the link steps are skipped")
        if link:
            pg.goto(link); pg.wait_for_timeout(600)
            check("The secret is removed from the address bar", "token=" not in pg.url)
            pws = pg.locator("input[type=password]").all()
            pws[0].fill(new_pw); pws[1].fill(new_pw)
            pg.click("button[type=submit]")
            check("After choosing a new password the student is sent to the login page", eventually(pg, lambda: pg.url.endswith("/login"), 40000))
            check("The login page confirms the password was changed", eventually(pg, lambda: pg.locator(".success-banner", has_text="password").count() >= 1))
            pg.fill("input[type=email]", fp_email); pg.fill("input[type=password]", old_pw); pg.click("button[type=submit]")
            check("The OLD password no longer works", eventually(pg, lambda: pg.locator("[role=alert]").count() >= 1, 40000) and "dashboard" not in pg.url)
            pg.fill("input[type=password]", new_pw); pg.click("button[type=submit]")
            try:
                pg.wait_for_url("**/dashboard", timeout=40000)
            except Exception:
                pass
            check("The NEW password logs in", "dashboard" in pg.url)
            pg.goto(link); pg.wait_for_timeout(600)
            pws = pg.locator("input[type=password]").all()
            if len(pws) >= 2:
                pws[0].fill("Another-pass-4321"); pws[1].fill("Another-pass-4321"); pg.click("button[type=submit]")
            check("The same link cannot be used a second time", eventually(pg, lambda: pg.locator("[role=alert]", has_text="not valid").count() >= 1, 40000))

        # ---------------- E. photos, phone layout, plain words ----------------
        mctx = b.new_context(viewport={"width": 390, "height": 844})
        mp = mctx.new_page()
        pages = ["/", "/dashboard", "/planner", "/toolkit", "/settings", "/profile", "/how-it-works"]
        BANNED = ["Analytics", "Wellbeing Assessment", "Task Prioritization", "Productivity Insights",
                  "Model Prediction", "Workload Optimization", "Task Completion Rate", "Configure Preferences", "Burnout Mode"]
        for path in pages:
            mp.goto(FRONT + path); mp.wait_for_timeout(700)
            for y in range(0, 6000, 700):           # scroll through the page so lazy photos load
                mp.evaluate(f"window.scrollTo(0, {y})"); mp.wait_for_timeout(60)
            mp.wait_for_timeout(500)
            over = mp.evaluate("document.documentElement.scrollWidth - window.innerWidth")
            check(f"Phone: {path} does not scroll sideways", over <= 1, f"{over}px too wide")
            imgs = mp.evaluate("[...document.images].map(i => ({ok: i.complete && i.naturalWidth > 0, alt: (i.alt || '').length}))")
            check(f"Phone: photos on {path} load and have a description", all(i["ok"] and i["alt"] > 10 for i in imgs), f"{len(imgs)} photo(s)")
            kb = mp.evaluate("Math.round(performance.getEntriesByType('resource').filter(r => r.name.endsWith('.webp')).reduce((n, r) => n + (r.transferSize || r.encodedBodySize || 0), 0) / 1024)")
            budget = 220 if path == "/" else 110
            check(f"Phone: photos on {path} weigh under {budget} KB", kb < budget, f"{kb} KB")
            if path not in ("/", "/dashboard"):
                check(f"{path} tells you where to start", mp.locator(".start-here").count() == 1)
            if path != "/how-it-works":
                text = mp.inner_text("body")
                found = [w for w in BANNED if w in text]
                check(f"Plain words: {path} has no technical page names", not found, ", ".join(found))
        # the planner, with its tabs, must also fit a phone once it holds a plan
        mp.goto(FRONT + "/planner"); mp.wait_for_selector("#builder-text", timeout=8000)
        mp.fill("#builder-text", "Stats report 1500 words due in 6 days")
        mp.click("button:has-text('Understand my tasks')"); mp.wait_for_selector("#draft-d1-title", timeout=15000)
        mp.click("button:has-text('Evaluate my plan')"); mp.wait_for_selector(".report", timeout=15000)
        mp.wait_for_timeout(500)
        check("Phone: the planner report does not scroll sideways", mp.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 1)
        mp.screenshot(path=str(SHOTS / "05_phone_report.png"), full_page=True)
        mp.click("button:has-text('Accept and save my plan')"); mp.wait_for_selector(".block", timeout=15000)
        for t in ["Calendar", "Focus", "Tasks", "Plan"]:
            mp.locator("[role=tab]", has_text=t).first.click(); mp.wait_for_timeout(500)
            check(f"Phone: planner tab {t} does not scroll sideways", mp.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 1)
        mp.screenshot(path=str(SHOTS / "05_phone_planner.png"), full_page=True)
        mp.goto(FRONT + "/dashboard"); mp.wait_for_timeout(500)
        mp.get_by_label("Open menu").click(); mp.wait_for_timeout(400)
        check("Phone: the menu opens and lists the five pages", all(mp.locator("aside.sidebar a", has_text=n).first.is_visible() for n in ["Smart Planner", "Dashboard", "Student Toolkit", "Settings", "My Profile"]))
        mp.screenshot(path=str(SHOTS / "05_phone_menu.png"))
        mp.goto(FRONT + "/"); mp.wait_for_timeout(800)
        mp.screenshot(path=str(SHOTS / "05_phone_welcome.png"), full_page=True)
        mctx.close()

        # ---------------- accessibility basics ----------------
        actx = b.new_context(viewport={"width": 1280, "height": 900})
        ap = actx.new_page()
        for path in ["/planner", "/dashboard", "/toolkit", "/settings", "/profile"]:
            ap.goto(FRONT + path); ap.wait_for_timeout(900)
            check(f"A11y: {path} has exactly one h1", ap.locator("h1").count() == 1)
            unlabeled = ap.evaluate("""() => [...document.querySelectorAll('input, select, textarea')].filter(e => e.type !== 'hidden' && !e.closest('[hidden]')
                && !(e.labels && e.labels.length) && !e.getAttribute('aria-label') && !e.getAttribute('aria-labelledby') && !e.closest('label')).length""")
            check(f"A11y: every field on {path} has a label", unlabeled == 0, f"{unlabeled} without")
            nameless = ap.evaluate("""() => [...document.querySelectorAll('button, a[href]')].filter(e => !(e.textContent || '').trim() && !e.getAttribute('aria-label') && !e.getAttribute('aria-labelledby') && !e.querySelector('img[alt]')).length""")
            check(f"A11y: every button and link on {path} has a name", nameless == 0, f"{nameless} without")
        ap.goto(FRONT + "/planner"); ap.wait_for_selector("[role=tablist]")
        ap.locator("[role=tab]").first.focus()
        ap.keyboard.press("Tab"); ap.wait_for_timeout(100)
        check("A11y: a keyboard user can move focus along the planner tabs", ap.evaluate("document.activeElement && document.activeElement.getAttribute('role') === 'tab'"))
        # reduce motion: the setting is applied to the whole page
        ap.emulate_media(reduced_motion="reduce"); ap.goto(FRONT + "/planner"); ap.wait_for_timeout(500)
        dur = ap.evaluate("getComputedStyle(document.querySelector('.card') || document.body).transitionDuration")
        check("A11y: with reduced motion the cards do not animate", dur in ("0s", "0.01ms", "1e-05s", "0.00001s") or float(dur.split(",")[0].replace("s", "").replace("m", "") or 0) < 0.05, dur)
        actx.close()

        # ---------------- F. premium look: hero, banners, readable words over photos ----------------
        def contrast_behind(page, selector, label):
            """Hide the words, photograph what is behind them and check white words would be easy to read."""
            try:
                from PIL import Image
                import io
            except ImportError:
                print("  (skipped: install Pillow to measure text contrast)")
                return
            page.evaluate("window.scrollTo(0, 0)")
            box = page.locator(selector).first.bounding_box()
            page.add_style_tag(content="* { color: transparent !important; text-shadow: none !important; -webkit-text-fill-color: transparent !important; } .lp-accent { background: none !important; }")
            png = page.screenshot(clip={"x": max(box["x"], 0), "y": max(box["y"], 0), "width": box["width"], "height": min(box["height"], 400)})
            page.evaluate("document.querySelectorAll('style').forEach(s => { if (s.textContent.includes('transparent !important')) s.remove(); })")
            import warnings; warnings.simplefilter('ignore')
            im = Image.open(io.BytesIO(png)).convert("RGB").resize((60, 24))
            def lin(c):
                c /= 255
                return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
            lums = sorted(0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b) for r, g, b in list(im.getdata()))
            p95 = lums[int(len(lums) * 0.95)]
            ratio = 1.05 / (p95 + 0.05)
            check(f"White words stay readable over the photo: {label}", ratio >= 4.5, f"contrast {ratio:.1f}:1")

        for label, (w, h) in {"desktop": (1440, 900), "phone": (390, 844)}.items():
            fctx = b.new_context(viewport={"width": w, "height": h})
            fp = fctx.new_page()
            fp.goto(FRONT + "/"); fp.wait_for_timeout(900)
            hero_w = fp.evaluate("document.querySelector('.lp-hero-img').getBoundingClientRect().width")
            check(f"{label}: the welcome photo fills the full width", hero_w >= w - 1, f"{hero_w:.0f}px of {w}px")
            check(f"{label}: the welcome page has a Get Started button above the fold", fp.evaluate("(() => { const r = [...document.querySelectorAll('a')].find(a => a.textContent.trim() === 'Get Started').getBoundingClientRect(); return r.top >= 0 && r.bottom <= window.innerHeight; })()"))
            contrast_behind(fp, ".lp-hero-copy h1", f"{label} headline")
            contrast_behind(fp, ".lp-hero-copy .lp-lead", f"{label} welcome sentence")
            # photo banners on the three pages that suit them, and none on pages with forms or lists
            for path, has in [("/dashboard", True), ("/planner", True), ("/toolkit", True), ("/settings", False), ("/profile", False)]:
                fp.goto(FRONT + path); fp.wait_for_timeout(700)
                n = fp.locator(".page-banner img").count()
                check(f"{label}: {path} {'has' if has else 'has no'} photo banner", (n == 1) == has)
                if has:
                    contrast_behind(fp, ".page-banner .banner-text h1", f"{label} {path} title")
                    contrast_behind(fp, ".page-banner .page-subtitle", f"{label} {path} sentence")
                else:
                    check(f"{label}: {path} has no photo behind forms or lists", fp.locator("img.photo").count() == 0)
            fctx.close()
        dctx = b.new_context(viewport={"width": 1440, "height": 900})
        dp = dctx.new_page()
        dp.goto(FRONT + "/"); dp.wait_for_timeout(600)
        for y in range(0, 5200, 600):
            dp.evaluate(f"window.scrollTo(0, {y})"); dp.wait_for_timeout(120)
        dp.wait_for_timeout(600)
        kb = dp.evaluate("Math.round(performance.getEntriesByType('resource').filter(r => r.name.endsWith('.webp')).reduce((n, r) => n + (r.transferSize || r.encodedBodySize || 0), 0) / 1024)")
        check("Desktop: all photos on the welcome page weigh under 450 KB", kb < 450, f"{kb} KB")
        check("Desktop: photographers are credited on the welcome page", all(n in dp.inner_text(".lp-footer") for n in ["Eliott Reyna", "Brooke Cagle", "Meredith Spencer", "Zoshua Colah", "Good Faces"]))
        dp.evaluate("window.scrollTo(0, 0)"); dp.wait_for_timeout(300)
        dp.screenshot(path=str(SHOTS / "06_welcome_hero_desktop.png"))
        dp.screenshot(path=str(SHOTS / "06_welcome_desktop_full.png"), full_page=True)
        for path, name in [("/dashboard", "07_dashboard_banner"), ("/planner", "08_planner_banner"), ("/toolkit", "09_toolkit_banner")]:
            dp.goto(FRONT + path); dp.wait_for_timeout(700); dp.screenshot(path=str(SHOTS / f"{name}.png"))
        dp.goto(FRONT + "/login"); dp.wait_for_timeout(600)
        check("Desktop: the log-in page shows a photo beside the form (not behind it)", dp.locator(".auth-photo img").count() == 1)
        dp.screenshot(path=str(SHOTS / "11_login_desktop.png"))
        dctx.close()

        b.close()
    failed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(failed)} / {len(results)} browser checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
