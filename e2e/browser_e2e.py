"""
End-to-end browser test for MindSync (Playwright + Chromium) - the seven-page MindSync (Smart Planner scenarios 1-16; My Tasks, Studio, Profile, Settings in e2e/browser_e2e_seven_pages.py).

It drives the REAL pages against a REAL running backend, the way a student would click through them. Scenarios:
   1 one subject, one topic            2 six subjects, many topics (one shared time budget)      3 not enough time (honest verdict)
   4 returning student (form kept)     5 finishing a study block (dashboard + roadmap agree)      6 deadline change (no duplicates)
   7 a missed block (re-plan offer)    8 account: save, reload, log out and in, second user isolated
   9 offline fallback (no AI key: rules wording, nothing waits for a model)                      10 phone layout, no sideways scroll
  11 keyboard only                     12 daily check-in (tired / stress high -> lighter plan)    13 toolkit chosen for you
  14 settings change the plan + dark theme                15 profile is accurate                  16 seven pages only, old addresses work

Run (backend on :8000 and the frontend on :5173 must already be running):
    pip install playwright && playwright install chromium
    python e2e/browser_e2e.py [screenshot_folder]

Every check prints PASS or FAIL; the script exits with code 1 if anything failed.
"""
import json
import os
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

FRONT, BACK = "http://localhost:5173", "http://localhost:8000"
SHOTS = Path(sys.argv[1] if len(sys.argv) > 1 else "e2e_screenshots")
SHOTS.mkdir(parents=True, exist_ok=True)
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(("PASS  " if ok else "FAIL  ") + name + (f"  [{detail}]" if detail else ""))


def eventually(pg, cond, timeout_ms=20000):
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


# ------------------------------------------------------------------ helpers that fill the form like a student
def open_form(pg):
    pg.goto(FRONT + "/planner?tab=form")
    pg.wait_for_selector("text=Loading your form", state="detached", timeout=20000)
    pg.wait_for_selector("button:has-text('Study Plan')", timeout=10000)


def subject(pg, i, name):
    while pg.locator(".sf-subject").count() <= i:
        pg.get_by_role("button", name="Add another subject").click()
    pg.locator(".sf-subject").nth(i).get_by_label("Subject name").fill(name)


def topic(pg, s, t, name, kind="Homework", when="In 1 week", progress="Not started", details=None, understanding=None, difficulty=None):
    sc = pg.locator(".sf-subject").nth(s)
    while sc.locator(".sf-topic").count() <= t:
        sc.get_by_role("button", name="Add another topic").click()
    tc = sc.locator(".sf-topic").nth(t)
    tc.get_by_label("Topic or task name").fill(name)
    chip = lambda legend, label: tc.locator("fieldset", has=tc.page.locator("legend", has_text=legend)).get_by_role("button", name=label, exact=True)
    chip("What kind of work", kind).click()
    if when:
        tc.get_by_role("button", name=when, exact=True).click()
    if progress:
        chip("How much is already finished", progress).click()
    for label, value in (details or {}).items():
        tc.get_by_label(label).fill(str(value))
    if understanding:
        chip("How well do you understand", understanding).click()
    if difficulty:
        chip("How difficult", difficulty).click()


def minutes_per_day(pg, m):
    pg.get_by_label("Minutes per day").fill(str(m))


def build(pg):
    pg.get_by_role("button", name="Study Plan").click()      # "Create My Study Plan" or "Update My Study Plan"
    return eventually(pg, lambda: pg.locator("text=Your study roadmap").count() > 0, 30000)


def guest_state(pg):
    return pg.evaluate("() => JSON.parse(localStorage.getItem('mindsync_guest_v1') || '{}')")


def plan_minutes_by_day(pg):
    st = guest_state(pg)
    plan = st.get("plan") or {"days": []}
    return {d["date"]: sum(s["minutes"] for s in d["sessions"] if s["status"] != "skipped") for d in plan["days"]}


def overflow(pg):
    return pg.evaluate("document.documentElement.scrollWidth - window.innerWidth")


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()

        def ctx(w=1280, h=900, **kw):
            # E2E_TIMEZONE (for example Europe/Copenhagen) pins the browser's time zone. Late in the local evening a plan correctly has nothing left for
            # today, and several scenarios below start by studying "today's" first block, so run them in a time zone where it is not late.
            if os.environ.get("E2E_TIMEZONE"):
                kw.setdefault("timezone_id", os.environ["E2E_TIMEZONE"])
            c = b.new_context(viewport={"width": w, "height": h}, **kw)
            pg = c.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("console", lambda m: errs.append(m.text) if m.type == "error" and "ERR_TUNNEL" not in m.text and "net::" not in m.text and "429" not in m.text else None)
            pg.errs = errs
            return c, pg

        # ================= 1. one subject, one topic =================
        c, pg = ctx()
        open_form(pg)
        check("1  The form opens on My Study Form for a new student and asks nothing else first", pg.locator("button:has-text('Create My Study Plan')").count() == 1)
        pg.screenshot(path=str(SHOTS / "01_form_empty.png"), full_page=True)
        subject(pg, 0, "Mathematics")
        topic(pg, 0, 0, "Quadratic equations", "Examination", "In 1 week", "Not started", {"How many chapters or topics does it cover?": 4}, "A little", "Difficult")
        ok = build(pg)
        check("1  One subject + one topic -> one button -> a roadmap", ok)
        pg.wait_for_timeout(1500)
        pg.screenshot(path=str(SHOTS / "02_roadmap_one_topic.png"), full_page=True)
        st = guest_state(pg)
        check("1  The topic is saved as a task under its subject", len(st["tasks"]) == 1 and st["tasks"][0]["category"] == "Mathematics" and st["tasks"][0]["meta"]["subject"] == "Mathematics")
        check("1  The roadmap shows a first step, today's block and the next 7 days", pg.locator(".rm-kicker").count() == 1 and pg.locator("#rm-days-t").count() == 1)
        check("1  The weekly calendar is part of the same page", pg.locator("#cal-h").count() == 1)
        check("1  How to study this topic: subject-specific guidance with an honest label", pg.locator("summary:has-text('How to study this topic')").count() == 1)
        pg.locator("summary:has-text('How to study this topic')").first.click()
        pg.wait_for_timeout(300)
        txt = pg.locator(".rm-guide-wrap").first.inner_text()
        check("1  The guidance covers what to understand, practice, mistakes and how to check", all(w in txt for w in ("What to understand", "Common mistakes", "Check your understanding", "If you get stuck")))
        check("1  The guidance says it is written by rules and has not read the course material", "not read your course material" in txt)
        pg.screenshot(path=str(SHOTS / "03_guidance_open.png"), full_page=True)
        check("1  No browser errors on the planner", not pg.errs, str(pg.errs[:2]))
        c.close()

        # ================= 2. six subjects, many topics =================
        c, pg = ctx()
        open_form(pg)
        names = ["Mathematics", "Python Programming", "Database Systems", "Computer Networks", "English", "Business Management"]
        kinds = ["Examination", "Programming project", "Assignment", "Homework", "Research report", "Presentation"]
        for i, n in enumerate(names):
            subject(pg, i, n)
            topic(pg, i, 0, f"{n} main work", kinds[i], "In 2 weeks", "Not started", None)
            topic(pg, i, 1, f"{n} practice", "Homework", "In 1 week", None, {"How many questions?": 10})
        minutes_per_day(pg, 180)
        ok = build(pg)
        pg.wait_for_timeout(1500)
        per_day = plan_minutes_by_day(pg)
        st = guest_state(pg)
        check("2  Six subjects with twelve topics are all saved", ok and len(st["tasks"]) == 12 and len({t["category"] for t in st["tasks"]}) == 6, f"{len(st['tasks'])} tasks")
        check("2  One shared time budget: no day goes over 180 minutes", per_day and max(per_day.values()) <= 180, f"max {max(per_day.values()) if per_day else None}")
        subj_cards = pg.locator(".rm-subject").count()
        check("2  The roadmap groups the topics into six subject cards", subj_cards == 6, str(subj_cards))
        pg.screenshot(path=str(SHOTS / "04_roadmap_six_subjects.png"), full_page=True)
        c.close()

        # ================= 3. insufficient time =================
        c, pg = ctx()
        open_form(pg)
        subject(pg, 0, "Mathematics")
        topic(pg, 0, 0, "Everything for the exam", "Examination", "In 3 days", "Not started", {"How many chapters or topics does it cover?": 12}, "Not yet", "Very difficult")
        minutes_per_day(pg, 30)
        build(pg)
        pg.wait_for_timeout(1200)
        check("3  Not enough time: the verdict says it does not fit, in words", pg.locator(".rm-glance .pill", has_text="Does not fit").count() == 1)
        check("3  It warns honestly instead of pretending", pg.locator("text=Honest warning").count() == 1)
        c.close()

        # ================= 4. returning student =================
        c, pg = ctx()
        open_form(pg)
        subject(pg, 0, "Physics")
        topic(pg, 0, 0, "Waves", "Homework", "In 1 week", None, {"How many questions?": 8}, "Fairly well", "Medium")
        pg.get_by_role("button", name="I get distracted easily").click()
        pg.get_by_role("button", name="Flash cards").click()
        minutes_per_day(pg, 75)
        build(pg)
        pg.reload(); pg.wait_for_timeout(1500)
        open_form(pg)
        check("4  Coming back: the subject and topic are still in the form", pg.locator(".sf-subject").first.get_by_label("Subject name").input_value() == "Physics" and pg.locator(".sf-topic").first.get_by_label("Topic or task name").input_value() == "Waves")
        check("4  Coming back: the button now says Update My Study Plan", pg.locator("button:has-text('Update My Study Plan')").count() == 1)
        pg.locator(".sf-topic").first.locator("summary").click()
        check("4  Coming back: answers (minutes, obstacles, what helps, understanding, follow-up) are kept",
              pg.get_by_label("Minutes per day").input_value() == "75"
              and pg.get_by_role("button", name="I get distracted easily").get_attribute("aria-pressed") == "true"
              and pg.get_by_role("button", name="Flash cards").get_attribute("aria-pressed") == "true"
              and pg.locator(".sf-topic").first.get_by_role("button", name="Fairly well", exact=True).get_attribute("aria-pressed") == "true"
              and pg.locator(".sf-topic").first.get_by_label("How many questions?").input_value() == "8")
        before = guest_state(pg)["tasks"][0]["meta"]["likely"]
        pg.get_by_role("button", name="Update My Study Plan").click(); pg.wait_for_selector("text=Your study roadmap", timeout=30000)
        st = guest_state(pg)
        check("4  Pressing Update again changes nothing and creates no duplicate", len(st["tasks"]) == 1 and st["tasks"][0]["meta"]["likely"] == before)
        c.close()

        # ================= 1b. hostile text is shown as plain text =================
        c, pg = ctx()
        dialogs = []
        pg.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        open_form(pg)
        subject(pg, 0, "<b>Maths</b>")
        topic(pg, 0, 0, "<img src=x onerror=alert(1)>Chapter", "Homework", "In 1 week", None, {"How many questions?": 5})
        build(pg); pg.wait_for_timeout(1500)
        check("1b Markup typed into the form is shown as text, never run", not dialogs and pg.locator("main img[src='x']").count() == 0 and pg.locator("main b:has-text('Maths')").count() == 0)
        c.close()

        # ================= 5. finishing a block + 12. dashboard sync =================
        c, pg = ctx()
        open_form(pg)
        subject(pg, 0, "Mathematics")
        topic(pg, 0, 0, "Algebra", "Homework", "In 1 week", None, {"How many questions?": 12})
        subject(pg, 1, "English")
        topic(pg, 1, 0, "Essay plan", "Assignment", "In 2 weeks", "Not started")
        build(pg)
        pg.wait_for_timeout(1200)
        pg.locator(".today .block").first.get_by_role("button", name="I did this").click()
        pg.wait_for_selector(".modal", timeout=5000)
        pg.screenshot(path=str(SHOTS / "05_session_feedback.png"))
        pg.locator(".modal button[type=submit]").click()
        pg.wait_for_timeout(2500)
        sessions = guest_state(pg)["taskSessions"]
        check("5  Finishing a block saves a study session", len(sessions) == 1 and sessions[0]["actual_minutes"] > 0, str(sessions[:1]))
        pg.goto(FRONT + "/dashboard"); pg.wait_for_timeout(2500)
        txt = pg.inner_text("main")
        check("5  Dashboard shows the time that was just studied", "Studied today" in txt and any(w in txt for w in ("Studied this week",)) and sessions[0]["actual_minutes"] > 0)
        check("5  Dashboard shows progress for both subjects", pg.locator("#dx-sub-h").count() == 1 and "Mathematics" in txt and "English" in txt)
        check("5  Dashboard earns the first achievement from the real session", pg.locator(".dx-ach li.earned").count() >= 1)
        check("5  Dashboard shows today's check-in strip empty state honestly", "daily check-in" in txt.lower())
        pg.screenshot(path=str(SHOTS / "06_dashboard.png"), full_page=True)
        c.close()

        # ================= 6. deadline change =================
        c, pg = ctx()
        open_form(pg)
        subject(pg, 0, "Chemistry")
        topic(pg, 0, 0, "Lab report", "Research report", "In 2 weeks", "Not started", {"How many words are required?": 1500})
        build(pg)
        pg.wait_for_timeout(800)
        old_deadline = guest_state(pg)["tasks"][0]["deadline"]
        old_last = max(d for d, m in plan_minutes_by_day(pg).items() if m)
        open_form(pg)
        pg.locator(".sf-topic").first.get_by_role("button", name="In 3 days", exact=True).click()
        pg.get_by_role("button", name="Update My Study Plan").click(); pg.wait_for_selector("text=Your study roadmap", timeout=30000); pg.wait_for_timeout(800)
        st = guest_state(pg)
        new_last = max(d for d, m in plan_minutes_by_day(pg).items() if m)
        check("6  Changing a deadline updates the same task (no duplicate)", len(st["tasks"]) == 1 and st["tasks"][0]["deadline"] != old_deadline)
        check("6  The plan now ends earlier, before the new deadline", new_last < old_last and new_last <= (date.today() + timedelta(days=3)).isoformat(), f"{old_last} -> {new_last}")
        c.close()

        # ================= 7. missed block =================
        c, pg = ctx()
        open_form(pg)
        subject(pg, 0, "History")
        topic(pg, 0, 0, "Revolutions", "Examination", "In 1 week", "Not started", {"How many chapters or topics does it cover?": 3})
        build(pg)
        pg.wait_for_timeout(800)
        pg.evaluate("""() => { const k='mindsync_guest_v1'; const d=JSON.parse(localStorage.getItem(k));
            // the first two days with blocks become "yesterday" and "the day before": two days of planned work that never happened
            const iso = (n) => new Date(Date.now() - n * 86400000).toISOString().slice(0, 10);
            d.plan.days.filter(x => x.sessions.length).slice(0, 2).forEach((day, i) => { day.date = iso(i + 1); });
            localStorage.setItem(k, JSON.stringify(d)); }""")
        pg.goto(FRONT + "/planner?tab=roadmap"); eventually(pg, lambda: pg.locator(".replan").count() >= 1, 20000)
        check("7  A block left undone from yesterday makes MindSync offer an updated plan", pg.locator(".replan").count() >= 1, pg.inner_text(".replan")[:120] if pg.locator(".replan").count() else "none")
        if pg.locator(".replan").count():
            pg.locator(".replan").first.get_by_role("button", name="Update my plan").click(); pg.wait_for_timeout(2500)
            check("7  Accepting the offer re-plans and the offer disappears", pg.locator(".replan").count() == 0)
        c.close()

        # ================= 8. account: register, persistence, isolation =================
        c, pg = ctx()
        email, pw = f"e2e-{uuid.uuid4().hex[:8]}@example.com", "Study-pass-12345"
        pg.goto(FRONT + "/register"); pg.wait_for_timeout(500)
        pg.fill("input >> nth=0", "E2E Student"); pg.fill("input[type=email]", email)
        for i in pg.locator("input[type=password]").all():
            i.fill(pw)
        pg.click("button[type=submit]")
        pg.wait_for_url("**/dashboard", timeout=60000)
        open_form(pg)
        subject(pg, 0, "Mathematics")
        topic(pg, 0, 0, "Calculus limits", "Examination", "In 1 week", "A little", {"How many chapters or topics does it cover?": 5}, "Not yet")
        subject(pg, 1, "Python Programming")
        topic(pg, 1, 0, "Course project", "Programming project", "In 2 weeks", "Halfway", {"How many features are left to build?": 4})
        pg.get_by_role("button", name="Tired", exact=True).click()
        pg.get_by_role("button", name="Low", exact=True).first.click()
        ok = build(pg)
        check("8  A registered student builds a plan (saved on the server)", ok)
        pg.screenshot(path=str(SHOTS / "07_account_roadmap.png"), full_page=True)
        pg.reload(); pg.wait_for_timeout(2500)
        open_form(pg)
        eventually(pg, lambda: pg.locator(".sf-subject").count() == 2, 15000)
        check("8  After a reload the form is restored from the database", pg.locator(".sf-subject").count() == 2 and pg.locator(".sf-subject").nth(1).get_by_label("Subject name").input_value() == "Python Programming")
        check("8  The project follow-up answer was kept", pg.locator(".sf-subject").nth(1).locator(".sf-topic").first.get_by_label("How many features are left to build?").input_value() == "4")
        pg.goto(FRONT + "/settings"); pg.wait_for_timeout(1500)
        pg.get_by_role("button", name="Log out").first.click() if pg.get_by_role("button", name="Log out").count() else pg.click("text=Log out")
        pg.wait_for_timeout(1500)
        pg.goto(FRONT + "/login"); pg.wait_for_timeout(400)
        pg.fill("input[type=email]", email); pg.fill("input[type=password]", pw); pg.click("button[type=submit]")
        pg.wait_for_url("**/dashboard", timeout=60000)
        open_form(pg)
        eventually(pg, lambda: pg.locator(".sf-subject").count() == 2, 15000)
        check("8  After logging out and in again the plan form is still there", pg.locator(".sf-subject").count() == 2, f"{pg.url} subjects={pg.locator('.sf-subject').count()} {pg.locator('.sf-intro').inner_text()[:300]!r}")
        c2, pg2 = ctx()
        email2 = f"e2e-{uuid.uuid4().hex[:8]}@example.com"
        pg2.goto(FRONT + "/register"); pg2.wait_for_timeout(500)
        pg2.fill("input >> nth=0", "Other Student"); pg2.fill("input[type=email]", email2)
        for i in pg2.locator("input[type=password]").all():
            i.fill(pw)
        pg2.click("button[type=submit]"); pg2.wait_for_url("**/dashboard", timeout=60000)
        open_form(pg2)
        check("8  A second student sees an empty form: users are isolated", pg2.locator(".sf-subject").count() == 1 and pg2.locator(".sf-subject").first.get_by_label("Subject name").input_value() == "")
        pg2.goto(FRONT + "/planner?tab=roadmap"); pg2.wait_for_timeout(2000)
        check("8  ... and an empty roadmap", pg2.locator("text=Your roadmap will appear here").count() == 1)
        c2.close()
        # profile + toolkit + dashboard for the account
        pg.goto(FRONT + "/profile"); pg.wait_for_timeout(2500)
        txt = pg.inner_text("main")
        check("15 Profile shows the subjects from the form with correct counts", "Mathematics" in txt and "Python Programming" in txt and "1 open topic" in txt)
        pg.goto(FRONT + "/dashboard"); pg.wait_for_timeout(2500)
        txt = pg.inner_text("main")
        check("12 Dashboard (account) shows subject progress, a next deadline and the check-in strip", "Progress by subject" in txt and "Your next deadline" in txt and pg.locator(".dx-moods li").count() == 1)
        c.close()

        # ================= 9. offline fallback =================
        c, pg = ctx()
        reqs = []
        pg.on("request", lambda r: reqs.append(r.url))
        open_form(pg)
        subject(pg, 0, "Economics")
        topic(pg, 0, 0, "Supply and demand", "Examination", "In 1 week", "Not started", {"How many chapters or topics does it cover?": 3})
        build(pg)
        pg.wait_for_timeout(1500)
        pg.locator("summary:has-text('Why this plan')").click(); pg.wait_for_timeout(2000)
        txt = pg.inner_text(".rm-why")
        check("9  With no AI key the plan is written by rules, and says so", "Rules" in txt or "rules" in txt)
        check("9  No request went to any outside AI service from the browser", not [u for u in reqs if "openai" in u or "googleapis.com/v1" in u])
        check("9  The plan form itself never used a language model (no /understand call)", not [u for u in reqs if u.endswith("/understand")])
        c.close()

        # ================= 10. phone =================
        c, pg = ctx(390, 844)
        open_form(pg)
        check("10 Phone: the empty form does not scroll sideways", overflow(pg) <= 1)
        subject(pg, 0, "Mathematics")
        topic(pg, 0, 0, "Functions", "Examination", "In 1 week", "Not started", {"How many chapters or topics does it cover?": 4})
        check("10 Phone: the filled form does not scroll sideways", overflow(pg) <= 1, str(overflow(pg)))
        pg.screenshot(path=str(SHOTS / "08_phone_form.png"), full_page=True)
        build(pg); pg.wait_for_timeout(1500)
        check("10 Phone: the roadmap does not scroll sideways", overflow(pg) <= 1, str(overflow(pg)))
        pg.screenshot(path=str(SHOTS / "09_phone_roadmap.png"), full_page=True)
        for path in ("/dashboard", "/toolkit", "/settings", "/profile"):
            pg.goto(FRONT + path); pg.wait_for_timeout(1500)
            check(f"10 Phone: {path} does not scroll sideways", overflow(pg) <= 1, str(overflow(pg)))
        c.close()

        # ================= 11. keyboard only =================
        c, pg = ctx()
        open_form(pg)
        pg.get_by_label("Subject name").first.focus()
        pg.keyboard.type("Biology")
        pg.keyboard.press("Tab"); pg.keyboard.press("Tab")        # experience select, then topic name
        focused = pg.evaluate("document.activeElement && document.activeElement.id")
        pg.get_by_label("Topic or task name").first.focus()
        pg.keyboard.type("Cells")
        # reach the exam chip with Tab and press it with Space
        pg.keyboard.press("Tab")
        label = pg.evaluate("document.activeElement.innerText")
        check("11 Keyboard: Tab moves from the topic name to the first type button", "Examination" in label, label)
        pg.keyboard.press("Space")
        check("11 Keyboard: Space presses it (aria-pressed becomes true)", pg.get_by_role("button", name="Examination", exact=True).first.get_attribute("aria-pressed") == "true")
        pg.get_by_role("button", name="In 1 week", exact=True).first.focus(); pg.keyboard.press("Enter")
        pg.get_by_role("button", name="Not started", exact=True).first.focus(); pg.keyboard.press("Enter")
        pg.get_by_label("How many chapters or topics does it cover?").fill("2")
        pg.get_by_role("button", name="Create My Study Plan").focus(); pg.keyboard.press("Enter")
        check("11 Keyboard: Enter on the main button builds the plan", eventually(pg, lambda: pg.locator("text=Your study roadmap").count() > 0, 30000))
        focus_ok = pg.evaluate("() => { const e = document.querySelector('button.sf-chip, .tabs button'); return !!e; }")
        pg.locator("[role=tab]").first.focus(); pg.keyboard.press("Tab")
        check("11 Keyboard: focus can move along the Smart Planner tabs", pg.evaluate("document.activeElement.getAttribute('role') === 'tab'"))
        c.close()

        # ================= 12. daily check-in changes the plan =================
        c, pg = ctx()
        open_form(pg)
        subject(pg, 0, "Mathematics")
        topic(pg, 0, 0, "Revision", "Examination", "In 1 week", "Not started", {"How many chapters or topics does it cover?": 10})
        minutes_per_day(pg, 60)
        build(pg); pg.wait_for_timeout(1000)
        normal_today = plan_minutes_by_day(pg).get(date.today().isoformat(), 0)
        pg.locator(".rm-checkin summary").click()
        pg.locator(".rm-checkin").get_by_role("button", name="Stressed", exact=True).click()
        pg.locator(".rm-checkin").get_by_role("button", name="High", exact=True).nth(1).click()
        pg.locator(".rm-checkin").get_by_role("button", name="Save my check-in").click(); pg.wait_for_timeout(3000)
        gentle_today = plan_minutes_by_day(pg).get(date.today().isoformat(), 0)
        txt = pg.inner_text("main")
        check("12 High stress today makes today's plan lighter", gentle_today < normal_today or normal_today == 0, f"{normal_today} -> {gentle_today}")
        check("12 The roadmap says so in a kind, non-medical way", "stress is high" in txt.lower() and "not medical advice" in txt.lower())
        check("12 Check-in is saved once for the day", len(guest_state(pg)["profile"]["mood_log"]) == 1)
        c.close()

        # ================= 13. toolkit personalised =================
        c, pg = ctx()
        open_form(pg)
        subject(pg, 0, "Mathematics")
        topic(pg, 0, 0, "Functions", "Examination", "In 1 week", "Not started", {"How many chapters or topics does it cover?": 4})
        pg.get_by_role("button", name="I put things off").click()
        build(pg); pg.wait_for_timeout(1000)
        pg.goto(FRONT + "/toolkit"); pg.wait_for_timeout(2500)
        txt = pg.inner_text("main")
        check("13 Toolkit has a 'Chosen for you' section built from the form", pg.locator("#foryou-h").count() == 1)
        check("13 It explains why (you put things off / exam work)", "you put things off" in txt and "examination" in txt.lower())
        pg.screenshot(path=str(SHOTS / "10_toolkit.png"), full_page=True)

        # ================= 14. settings change the plan + dark theme =================
        pg.goto(FRONT + "/settings"); pg.wait_for_timeout(1500)
        pg.get_by_label("Best time of day").select_option("evening"); pg.wait_for_timeout(1500)
        pg.get_by_label("Light or dark").select_option("dark"); pg.wait_for_timeout(1000)
        check("14 Dark theme applies at once and is remembered", pg.evaluate("document.documentElement.dataset.theme") == "dark")
        pg.goto(FRONT + "/planner?tab=roadmap"); pg.wait_for_timeout(2500)
        check("14 ... also after navigating to another page", pg.evaluate("document.documentElement.dataset.theme") == "dark")
        pg.screenshot(path=str(SHOTS / "11_dark_roadmap.png"), full_page=False)
        pg.goto(FRONT + "/settings"); pg.wait_for_timeout(1500)
        pg.screenshot(path=str(SHOTS / "12_settings_dark.png"), full_page=True)
        pg.get_by_label("Light or dark").select_option("light"); pg.wait_for_timeout(800)
        pg.goto(FRONT + "/settings"); pg.wait_for_timeout(1200)
        pg.screenshot(path=str(SHOTS / "12_settings.png"), full_page=True)
        pg.get_by_label("Minutes on a weekday").fill("30"); pg.wait_for_timeout(1800)
        pg.goto(FRONT + "/planner?tab=roadmap"); pg.wait_for_timeout(3000)
        check("14 Changing study minutes in Settings makes the planner offer an update", pg.locator(".replan").count() >= 1 or "tight" in pg.inner_text("main").lower() or "does not fit" in pg.inner_text("main").lower())
        c.close()

        # ================= 15. profile (guest) =================
        c, pg = ctx()
        open_form(pg)
        subject(pg, 0, "Mathematics")
        topic(pg, 0, 0, "Functions", "Homework", "In 1 week", None, {"How many questions?": 6})
        topic(pg, 0, 1, "Graphs", "Homework", "In 2 weeks", None, {"How many questions?": 6})
        pg.get_by_role("button", name="Intermediate").first.click()
        build(pg); pg.wait_for_timeout(800)
        pg.goto(FRONT + "/profile"); pg.wait_for_timeout(2500)
        txt = pg.inner_text("main")
        check("15 Profile (guest) lists the subject with two open topics", "Mathematics" in txt and "2 open topics" in txt)
        check("15 Profile explains that guest data stays in this browser", "browser" in txt.lower())
        pg.get_by_label("Level of study").select_option("undergraduate"); pg.wait_for_timeout(1500)
        check("15 Profile saves the level of study", guest_state(pg)["profile"].get("education_level") == "undergraduate")
        pg.screenshot(path=str(SHOTS / "13_profile.png"), full_page=True)
        c.close()

        # ================= 16. seven pages only =================
        c, pg = ctx()
        pg.goto(FRONT + "/dashboard"); pg.wait_for_timeout(1500)
        links = [a.inner_text().strip().split("\n")[0] for a in pg.locator("aside.sidebar nav a, aside.sidebar a").all()]
        SEVEN = ["Smart Planner", "My Tasks", "Dashboard", "Student Toolkit", "AI Learning Studio", "Settings", "My Profile"]
        main_links = [l for l in links if l in SEVEN]
        check("16 The menu has exactly the seven main pages", main_links == SEVEN, str(links))
        for old, expect in (("/wellbeing", "tab=wellbeing"), ("/analytics", "tab=history")):
            pg.goto(FRONT + old); pg.wait_for_timeout(1200)
            check(f"16 Old address {old} still lands on the right page", expect in pg.url, pg.url)
        pg.goto(FRONT + "/planner?tab=focus"); pg.wait_for_timeout(1200)
        check("16 Old planner tab names (focus) still work", pg.locator("[role=tab][aria-selected=true]").inner_text() == "Study Session")
        c.close()

        b.close()
    failed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(failed)} / {len(results)} browser checks passed")
    if failed:
        print("FAILED:")
        for n in failed:
            print("  -", n)
        sys.exit(1)


if __name__ == "__main__":
    main()
