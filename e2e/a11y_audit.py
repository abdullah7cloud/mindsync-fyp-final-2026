"""
Accessibility audit (automated part) - axe-core in a real Chromium, against the running app.

    python e2e/a11y_audit.py          (backend :8000 and the frontend :5173 must be running; needs: pip install playwright)

Runs axe-core (WCAG 2.0/2.1 A and AA rules) on every page and on the main states of the Smart Planner, at desktop and phone
size, and a keyboard-only check. Prints every violation (rule, impact, element) and writes docs/accessibility_results.md.
Automated rules find roughly a third of real accessibility problems; a screen-reader pass by a person is still needed and is
listed as not done.
"""
import json
import os
import sys
import urllib.request
import uuid
from datetime import date, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

FRONT = "http://localhost:5173"
AXE = (Path(__file__).parent / "vendor" / "axe.min.js").read_text(encoding="utf-8")
TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]
rows, violations = [], []


def run_axe(pg, label):
    pg.wait_for_timeout(500)                      # let entrance animations finish so colours are final
    pg.evaluate(AXE)
    res = pg.evaluate("(tags) => axe.run(document, {runOnly: {type: 'tag', values: tags}})", TAGS)
    v = res["violations"]
    rows.append((label, len(v), len(res["passes"]), len(res.get("incomplete", []))))
    for item in v:
        for node in item["nodes"][:3]:
            violations.append((label, item["id"], item["impact"], node["target"][0] if node["target"] else "", item["help"]))
    print(f"{'OK  ' if not v else 'FAIL'} {label}: {len(v)} violations, {len(res['passes'])} rules passed")


BACK = "http://localhost:8000"


def api_call(path, body=None, token=None):
    req = urllib.request.Request(BACK + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})})
    return json.load(urllib.request.urlopen(req))


def make_account():
    """A throw-away signed-in student with a saved plan, so My Tasks, the Dashboard and the Studio show real content."""
    tok = api_call("/auth/register", {"email": f"a11y{uuid.uuid4().hex[:8]}@example.com", "display_name": "Axe Student", "password": "Study-pass-1"})["access_token"]
    d = lambda n: (date.today() + timedelta(days=n)).isoformat()
    api_call("/assist/plan-form", {"subjects": [{"id": "s1", "name": "Mathematics", "topics": [{"id": "m1", "name": "Quadratic equations", "type": "exam", "progress": "none", "deadline": d(9), "understanding": 2}]},
             {"id": "s2", "name": "Python Programming", "topics": [{"id": "p1", "name": "Loops practice", "type": "homework", "deadline": d(12)}]}], "availability": {"daily_minutes": 120}}, tok)
    api_call("/studio/sample", {}, tok)
    return tok


def fill_form(pg):
    pg.wait_for_selector("text=Loading your form", state="detached", timeout=15000)
    pg.get_by_label("Subject name").first.fill("Mathematics")
    pg.get_by_label("Topic or task name").first.fill("Quadratic equations")
    pg.get_by_role("button", name="Examination").first.click()
    pg.get_by_role("button", name="In 1 week").first.click()
    pg.get_by_role("button", name="Not started").first.click()
    pg.get_by_label("How many chapters or topics does it cover?").first.fill("4")


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(channel=os.environ.get("E2E_CHANNEL") or None)   # E2E_CHANNEL=chrome uses the installed Chrome
        themes = [t for t in os.environ.get("E2E_THEMES", "light,dark").split(",") if t]
        for name, vp, theme in [(f"{d} {t}", v, t) for t in themes for d, v in (("desktop", {"width": 1280, "height": 900}), ("phone", {"width": 390, "height": 844}))]:
            ctx = b.new_context(viewport=vp, color_scheme=theme)
            pg = ctx.new_page()
            for path in ("/", "/login", "/register", "/how-it-works", "/forgot-password"):
                pg.goto(FRONT + path); pg.wait_for_timeout(700)
                run_axe(pg, f"{name} {path}")
            for path in ("/dashboard", "/toolkit", "/settings", "/profile"):
                pg.goto(FRONT + path); pg.wait_for_timeout(900)
                run_axe(pg, f"{name} guest {path}")
            pg.goto(FRONT + "/planner?tab=form"); pg.wait_for_selector("text=Create My Study Plan", timeout=10000)
            run_axe(pg, f"{name} planner form (empty)")
            fill_form(pg)
            run_axe(pg, f"{name} planner form (filled)")
            pg.get_by_role("button", name="Create My Study Plan").click(); pg.wait_for_selector("text=Your study roadmap", timeout=20000); pg.wait_for_timeout(800)
            run_axe(pg, f"{name} planner roadmap")
            pg.locator("summary", has_text="How to study this topic").first.click(); pg.wait_for_timeout(300)
            run_axe(pg, f"{name} planner roadmap (guidance open)")
            pg.locator("[role=tab]", has_text="Study Session").first.click(); pg.wait_for_timeout(700)
            run_axe(pg, f"{name} planner study session")
            for path in ("/dashboard", "/toolkit", "/profile", "/settings"):
                pg.goto(FRONT + path); pg.wait_for_timeout(1500)
                run_axe(pg, f"{name} with data {path}")
            # the two new pages as a guest, then every page signed in with a saved roadmap, a sample pack and a finished block
            for path in ("/tasks", "/studio"):
                pg.goto(FRONT + path); pg.wait_for_timeout(1500)
                run_axe(pg, f"{name} guest {path}")
            tok = make_account()
            pg.goto(FRONT + "/login"); pg.evaluate("t => localStorage.setItem('mindsync_token', t)", tok)
            pg.goto(FRONT + "/tasks"); pg.wait_for_selector("text=Day ", timeout=15000); pg.wait_for_timeout(600)
            run_axe(pg, f"{name} account My Tasks (Today)")
            for tab in ("Tomorrow", "Full Roadmap", "Completed", "Overdue"):
                t = pg.get_by_role("tab", name=tab)
                if t.count():
                    t.first.click(); pg.wait_for_timeout(500)
                    run_axe(pg, f"{name} account My Tasks ({tab})")
            pg.get_by_role("tab", name="Today").first.click(); pg.wait_for_timeout(300)
            if pg.get_by_role("button", name="Done").count():
                pg.get_by_role("button", name="Done").first.click(); pg.wait_for_selector("text=How did it go?", timeout=8000); pg.wait_for_timeout(400)
                run_axe(pg, f"{name} account My Tasks (confirm Done form)")
                pg.get_by_role("button", name="Save My Progress").click(); pg.wait_for_timeout(1200)
            pg.goto(FRONT + "/studio"); pg.wait_for_timeout(1500)
            run_axe(pg, f"{name} account Studio (library)")
            pg.get_by_role("button", name="Open", exact=True).first.click() if pg.get_by_role("button", name="Open", exact=True).count() else pg.get_by_role("button", name="Try a Sample Learning Pack").click()
            pg.wait_for_selector("text=Lesson 1", timeout=10000); pg.wait_for_timeout(600)
            run_axe(pg, f"{name} account Studio (pack, Learn tab)")
            for tab in ("Quiz", "Flashcards", "Revise", "Progress"):
                t = pg.get_by_role("tab", name=tab)
                if t.count():
                    t.first.click(); pg.wait_for_timeout(600)
                    run_axe(pg, f"{name} account Studio ({tab})")
            for path in ("/dashboard", "/profile", "/settings", "/toolkit"):
                pg.goto(FRONT + path); pg.wait_for_timeout(1800)
                run_axe(pg, f"{name} account {path}")
            # every colour theme, readable contrast and larger text, on the pages that use the colours most
            pg.goto(FRONT + "/settings"); pg.wait_for_timeout(1200)
            for accent in ("Purple", "Green", "Pink", "Neutral"):
                pg.get_by_role("radio", name=accent).check(force=True); pg.wait_for_timeout(500)
                for path in ("/settings", "/tasks", "/dashboard"):
                    pg.goto(FRONT + path); pg.wait_for_timeout(1500)
                    run_axe(pg, f"{name} colour theme {accent} {path}")
                pg.goto(FRONT + "/settings"); pg.wait_for_timeout(800)
            pg.get_by_role("radio", name="Blue").check(force=True)
            pg.get_by_label("Text size").select_option("larger"); pg.wait_for_timeout(400)
            pg.get_by_label("Readable contrast").check(force=True) if pg.get_by_label("Readable contrast").count() else None
            pg.wait_for_timeout(500)
            for path in ("/settings", "/tasks", "/studio", "/profile"):
                pg.goto(FRONT + path); pg.wait_for_timeout(1500)
                run_axe(pg, f"{name} larger text + readable contrast {path}")
            ctx.close()
        # keyboard only: the welcome page's main action can be reached and activated with Tab and Enter
        ctx = b.new_context(viewport={"width": 1280, "height": 900})
        pg = ctx.new_page(); pg.goto(FRONT + "/"); pg.wait_for_timeout(600)
        reached = False
        for _ in range(25):
            pg.keyboard.press("Tab")
            txt = pg.evaluate("() => document.activeElement && document.activeElement.innerText || ''")
            if "Get Started" in txt or "Get started" in txt:
                reached = True
                break
        focus_visible = pg.evaluate("() => { const e = document.activeElement; if (!e) return false; const s = getComputedStyle(e); return s.outlineStyle !== 'none' || s.boxShadow !== 'none'; }")
        print(("OK  " if reached else "FAIL") + " keyboard: the welcome page's Get Started button is reachable with Tab")
        print(("OK  " if focus_visible else "FAIL") + " keyboard: the focused control has a visible focus style")
        lang = pg.evaluate("() => document.documentElement.lang")
        print(("OK  " if lang else "FAIL") + f" html lang attribute = {lang!r}")
        b.close()
    total = sum(r[1] for r in rows)
    out = Path(__file__).resolve().parents[1] / "docs" / "accessibility_results.md"
    lines = ["# Accessibility audit (automated, measured)", "",
             f"Run {date.today().isoformat()} - axe-core (WCAG 2.0/2.1 A and AA) in Chromium via `e2e/a11y_audit.py`. {total} violations over {len(rows)} page states.", "",
             "| Page state | Violations | Rules passed |", "|---|---|---|"]
    lines += [f"| {l} | {v} | {ps} |" for l, v, ps, _ in rows]
    lines += ["", f"Keyboard: Get Started reachable by Tab = {reached}; visible focus style = {focus_visible}; html lang = {lang!r}.", ""]
    if violations:
        lines += ["## Violations", "", "| State | Rule | Impact | Element | Help |", "|---|---|---|---|---|"]
        lines += [f"| {a} | {b_} | {c} | `{d}` | {e} |" for a, b_, c, d, e in violations]
    lines += ["", "Not covered by this script and not done: a screen-reader walk-through (NVDA/VoiceOver), zoom to 400 %, and a test with real users who use assistive technology."]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n{total} violations -> {out}")
    return 1 if total or not reached else 0


if __name__ == "__main__":
    sys.exit(main())
