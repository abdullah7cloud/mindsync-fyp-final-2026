"""
Intelligence evaluation: ten realistic task descriptions through the current MindSync and (optionally) through an
older MindSync backend started on another port, on identical inputs. Writes docs/intelligence_results.md.

    python scripts/intelligence_eval.py [--new http://localhost:8000] [--old http://localhost:8001]

Everything printed is measured from the running servers; nothing is typed in by hand. The old server is optional.
"""
import argparse
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import httpx

CASES = [
    # (name, family, text, days_left, plain title/details for the old engine)
    ("programming-large", "programming", "I have to build a Python Flask login page with user registration and unit tests, due in 5 days.", 5),
    ("programming-small", "programming", "Fix a small bug in my Python script, due tomorrow.", 1),
    ("maths-large", "maths exam", "Maths exam in 10 days covering calculus chapters 1 to 6. I find integration really hard.", 10),
    ("maths-small", "maths exam", "Short algebra quiz tomorrow, mostly revision.", 1),
    ("report-large", "research report", "3000 word research report on climate policy with 10 references due in 14 days.", 14),
    ("report-small", "research report", "500 word reflection due in 3 days.", 3),
    ("presentation-large", "presentation", "10 minute group presentation on machine learning ethics in 6 days, I have to make the slides and practise.", 6),
    ("presentation-small", "presentation", "5 slide presentation due in 2 days.", 2),
    ("reading-large", "reading", "Read chapters 4 to 6 of the economics textbook, about 90 pages, by next Friday.", None),
    ("reading-small", "reading", "Read a 6 page article by tomorrow.", 1),
]
DAILY = 120


def new_run(base, text):
    c = httpx.Client(base_url=base, timeout=60)
    tok = c.post("/auth/register", json={"email": f"ieval-{time.time_ns()}@example.com", "password": "Intel-pass-12345",
                                          "display_name": "Eval"}).json()["access_token"]
    h = {"Authorization": "Bearer " + tok}
    c.put("/settings", headers=h, json={"weekday_minutes": DAILY, "weekend_minutes": DAILY, "buffer_days": 0})
    u = c.post("/assist/understand", headers=h, json={"text": text}).json()
    d = u["tasks"][0]
    draft = {"ref": "d1", "title": d["title"], "details": d.get("details", ""), "deadline_date": d["deadline_date"],
             "deadline_hour": d.get("deadline_hour"), "felt_hard": d.get("felt_hard"), "kind": d.get("kind")}
    ev = c.post("/assist/evaluate", headers=h, json={"drafts": [draft]}).json()
    rep = ev["report"]
    t = rep["tasks"][0]
    sess = sorted({s["minutes"] for dd in rep["schedule"]["days"] for s in dd["sessions"]})
    return {"title": d["title"], "deadline": d["deadline_date"], "kind": t["kind_label"], "likely": t["workload"]["likely"],
            "low": t["workload"]["low"], "high": t["workload"]["high"], "status": t["status"], "verdict": rep["verdict"]["level"],
            "steps": [s["label"] for s in t["steps"]], "sessions": sess,
            "blocks": sum(len(dd["sessions"]) for dd in rep["schedule"]["days"]),
            "difficulty": t["difficulty"]["intrinsic"]}


def old_run(base, title, details, deadline):
    c = httpx.Client(base_url=base, timeout=60)
    today = date.today()
    body = {"title": title, "details": details, "deadline": deadline, "today": today.isoformat(), "daily_minutes": DAILY, "energy": 3}
    r = c.post("/demo/smart/plan", json=body).json()
    if r.get("status") == "needs_info":
        r = c.post("/demo/smart/plan", json=dict(body, skipped=[q["id"] for q in r["questions"]])).json()
    w = r["workload"]
    sch = r["schedule"]
    days = sch.get("days") if isinstance(sch, dict) else sch
    sess = sorted({s.get("minutes") for d in days for s in d.get("sessions", [])}) if days and isinstance(days[0], dict) and "sessions" in days[0] else []
    return {"kind": (r["understanding"]["kinds"][0]["label"] if r.get("understanding") else "?"), "likely": w["likely"],
            "low": w["low"], "high": w["high"], "steps": [s.get("label") for s in w.get("stages", [])], "sessions": sess}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", default="http://localhost:8000")
    ap.add_argument("--old", default="")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[2] / "docs" / "intelligence_results.md"))
    a = ap.parse_args()
    rows = []
    for name, fam, text, days in CASES:
        n = new_run(a.new, text)
        dl = n["deadline"]
        o = None
        if a.old:
            try:
                o = old_run(a.old, n["title"], text, dl)
            except Exception as e:                      # noqa: BLE001 - report, do not hide
                o = {"error": str(e)}
        rows.append((name, fam, text, n, o))
        print(f"{name:20} new: {n['kind']:18} {n['low']}-{n['likely']}-{n['high']} min  status={n['status']} steps={len(n['steps'])} sessions={n['sessions']}")
        if o and "likely" in o:
            print(f"{'':20} old: {o['kind']:18} {o['low']}-{o['likely']}-{o['high']} min  steps={len(o['steps'])} sessions={o['sessions']}")
    # shape checks that do not depend on exact numbers
    by = {r[0]: r for r in rows}
    checks = []
    for fam in ("programming", "maths", "report", "presentation", "reading"):
        big = next(r for r in rows if r[0].startswith(fam) and r[0].endswith("large"))
        small = next(r for r in rows if r[0].startswith(fam) and r[0].endswith("small"))
        checks.append((fam, big[3]["likely"] > small[3]["likely"], big[3]["likely"], small[3]["likely"]))
        if big[4] and small[4] and "likely" in big[4] and "likely" in small[4]:
            checks[-1] += (big[4]["likely"] > small[4]["likely"], big[4]["likely"], small[4]["likely"])
    kinds_distinct = len({tuple(r[3]["steps"]) for r in rows})
    lines = ["# Intelligence evaluation (measured)", "",
             f"Generated {date.today().isoformat()} by `scripts/intelligence_eval.py` against the running servers. "
             f"Daily capacity {DAILY} min, no buffer, one task at a time, time-zone and settings identical for both versions.", "",
             "| Case | Current version: kind | Workload low-likely-high (min) | Status | Steps | Session lengths |"
             + (" Older version: workload | Older steps |" if a.old else ""),
             "|---|---|---|---|---|---|" + ("---|---|" if a.old else "")]
    for name, fam, text, n, o in rows:
        line = f"| {name} | {n['kind']} | {n['low']}-{n['likely']}-{n['high']} | {n['status']} | {len(n['steps'])} | {', '.join(map(str, n['sessions']))} |"
        if a.old:
            line += (f" {o['low']}-{o['likely']}-{o['high']} | {len(o['steps'])} |" if o and 'likely' in o else " n/a | n/a |")
        lines.append(line)
    lines += ["", "## Ordering checks (large must need more than small, same type of work)", "",
              "| Type of work | Current: large vs small | Older: large vs small |", "|---|---|---|"]
    for c in checks:
        cur = f"{'PASS' if c[1] else 'FAIL'} ({c[2]} vs {c[3]} min)"
        old = (f"{'PASS' if c[4] else 'FAIL'} ({c[5]} vs {c[6]} min)" if len(c) > 4 else "not run")
        lines.append(f"| {c[0]} | {cur} | {old} |")
    lines += ["", f"Distinct step sequences across the ten cases (current version): {kinds_distinct} of 10.", "",
              "## Plan shape per case (current version)", ""]
    for name, fam, text, n, o in rows:
        lines += [f"- **{name}** — “{text}” → {n['kind']}; steps: {' > '.join(n['steps'])}; {n['blocks']} study blocks; verdict {n['verdict']}."]
    Path(a.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    failed = [c for c in checks if not c[1]]
    print("\nordering checks failed:", [c[0] for c in failed] or "none")
    print("written", a.out)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
