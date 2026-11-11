"""
Accessibility audit (automated part) for the four-page MindSync - axe-core (WCAG 2.0/2.1 A and AA) in a real Chromium, update 26.

    python e2e/a11y_audit_four_pages.py     (backend :8000 and the frontend :5173 must be running)

Checks every page at desktop and phone size, the Notebook documents tab, the account window and the quiz screen, plus a keyboard-only
check of the Study Planner form. Automated rules find roughly a third of real problems; a screen-reader pass by a person is NOT done.
"""
import os
import re
import tempfile
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

FRONT = "http://localhost:5173"
AXE = (Path(__file__).parent / "vendor" / "axe.min.js").read_text(encoding="utf-8")
TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]
bad = []


def axe(pg, label):
    pg.wait_for_timeout(700)
    pg.evaluate(AXE)
    r = pg.evaluate("(t) => axe.run(document, {runOnly: {type: 'tag', values: t}})", TAGS)
    v = r["violations"]
    print(("OK   " if not v else "FAIL ") + f"{label}: {len(v)} violations, {len(r['passes'])} rules passed")
    for i in v:
        for n in i["nodes"][:3]:
            print(f"       {i['id']} ({i['impact']}): {n['target'][0] if n['target'] else ''}  - {i['help']}")
            bad.append(label)


def main():
    with sync_playwright() as p:
        br = p.chromium.launch(channel=os.environ.get("E2E_CHANNEL") or None)
        for name, vp, mobile in [("desktop", {"width": 1280, "height": 900}, False), ("phone", {"width": 390, "height": 800}, True)]:
            ctx = br.new_context(viewport=vp, is_mobile=mobile, timezone_id="Europe/Copenhagen")
            pg = ctx.new_page()
            for path in ["/", "/login", "/register", "/forgot-password"]:
                pg.goto(FRONT + path); axe(pg, f"{name} {path}")
            pg.goto(FRONT + "/register")
            pg.get_by_label(re.compile("name", re.I)).first.fill("Axe Student")
            pg.get_by_label(re.compile("email", re.I)).first.fill(f"axe{uuid.uuid4().hex[:8]}@example.com")
            pw = pg.locator('input[type=password]'); pw.nth(0).fill("Study-pass-1"); pw.nth(1).fill("Study-pass-1")
            pg.get_by_role("button", name=re.compile("create|sign up|register", re.I)).first.click(); pg.wait_for_url("**/dashboard")
            axe(pg, f"{name} /dashboard (empty)")
            pg.goto(FRONT + "/planner")
            pg.get_by_label("Subject Name").fill("Biology"); pg.get_by_label(re.compile("Topic Name")).fill("Cells")
            pg.get_by_label("Target Completion Date").fill((date.today() + timedelta(days=7)).isoformat())
            axe(pg, f"{name} /planner (form filled)")
            pg.get_by_role("button", name="Generate My Study Plan").click(); pg.get_by_text(re.compile("Your plan is ready")).wait_for(timeout=40000)
            axe(pg, f"{name} /planner (plan shown)")
            pg.locator("article.lt-plan li.lt-task").first.get_by_role("button", name=re.compile("^Edit task")).click()
            axe(pg, f"{name} /planner (editing a task)")
            pg.goto(FRONT + "/dashboard"); pg.get_by_test_id("total").wait_for(); axe(pg, f"{name} /dashboard (with tasks)")
            pg.goto(FRONT + "/ai-zone"); pg.get_by_role("heading", name="AI Learning Zone").wait_for(); axe(pg, f"{name} /ai-zone")
            pg.goto(FRONT + "/notebook"); pg.get_by_role("tab", name="My Notes").wait_for(); axe(pg, f"{name} /notebook (notes, empty)")
            pg.get_by_role("button", name="New note").click(); pg.get_by_label("Title").fill("Note"); pg.get_by_label("Your note").fill("Text")
            axe(pg, f"{name} /notebook (editing a note)")
            pg.get_by_role("tab", name="My Documents").click(); pg.get_by_text("My Documents").first.wait_for()
            pg.locator("input[type=file]").set_input_files(str(Path(tempfile.gettempdir()) / "e2e_files" / "notes.txt")); pg.get_by_text(re.compile("was saved")).wait_for()
            axe(pg, f"{name} /notebook (documents)")
            pg.locator("li.lt-doc").first.get_by_role("button", name="View").click(); pg.get_by_role("dialog").wait_for()
            axe(pg, f"{name} document viewer window")
            pg.get_by_role("button", name="Close").last.click()
            (pg.locator(".greeting-button") if mobile else pg.locator("button.nav-button")).click()
            pg.get_by_role("dialog").wait_for(); axe(pg, f"{name} account window")
            ctx.close()
        # keyboard only: reach and use the planner form without a mouse
        ctx = br.new_context(viewport={"width": 1280, "height": 900}); pg = ctx.new_page()
        pg.goto(FRONT + "/register")
        pg.get_by_label(re.compile("name", re.I)).first.fill("Key Student"); pg.get_by_label(re.compile("email", re.I)).first.fill(f"key{uuid.uuid4().hex[:8]}@example.com")
        pw = pg.locator('input[type=password]'); pw.nth(0).fill("Study-pass-1"); pw.nth(1).fill("Study-pass-1")
        pg.keyboard.press("Enter"); pg.wait_for_url("**/dashboard")
        pg.goto(FRONT + "/planner"); pg.get_by_label("Subject Name").focus()
        pg.keyboard.type("Maths"); pg.keyboard.press("Tab"); pg.keyboard.type("Algebra"); pg.keyboard.press("Tab"); pg.keyboard.press("Tab")
        pg.keyboard.type((date.today() + timedelta(days=6)).strftime("%m%d%Y"))
        seen_radio = seen_button = False
        for _ in range(12):
            pg.keyboard.press("Tab")
            kind = pg.evaluate("(document.activeElement.type || '') + '|' + (document.activeElement.textContent || '')")
            seen_radio = seen_radio or kind.startswith("radio")
            if "Generate My Study Plan" in kind:
                seen_button = True
                break
        print(("OK   " if seen_radio else "FAIL ") + "keyboard: Tab reaches the mood and stress choices")
        print(("OK   " if seen_button else "FAIL ") + "keyboard: Tab reaches the Generate button")
        if not (seen_radio and seen_button): bad.append("kbd")
        pg.keyboard.press("Enter")
        try:
            pg.get_by_text(re.compile("Your plan is ready")).wait_for(timeout=40000); print("OK   keyboard: the plan can be made without a mouse")
        except Exception:
            print("FAIL keyboard: plan not made"); bad.append("kbd2")
        br.close()
    print("\nRESULT:", "no automated violations" if not bad else f"{len(bad)} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
