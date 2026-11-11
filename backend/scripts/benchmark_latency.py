"""
Latency benchmark for the contract's "sub-3-second end-to-end API latency" target.

Two modes:

  python -m scripts.benchmark_latency engine
      Times only the local ranking engine (heuristic + trained model) in
      memory. No server or database needed.

  python -m scripts.benchmark_latency api [--base http://127.0.0.1:8000] [--runs 50]
      End-to-end test against the RUNNING backend: registers a throw-away
      test user, creates tasks, logs an energy check-in, then calls
      GET /recommend repeatedly and reports min / median / p95 / max in ms
      and whether p95 is under 3000 ms. Results are saved to
      ../docs/latency_results.md for Chapter 4.
"""
import argparse
import statistics
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

TARGET_MS = 3000.0
OUT = Path(__file__).resolve().parents[2] / "docs" / "latency_results.md"


def summarise(samples_ms: list[float]) -> dict:
    s = sorted(samples_ms)
    p95 = s[min(len(s) - 1, int(round(0.95 * (len(s) - 1))))]
    return {
        "runs": len(s),
        "min_ms": round(s[0], 3),
        "median_ms": round(statistics.median(s), 3),
        "p95_ms": round(p95, 3),
        "max_ms": round(s[-1], 3),
        "under_target": p95 < TARGET_MS,
    }


def engine_benchmark(n_tasks: int, runs: int = 200) -> dict:
    from app.heuristic import ScorableTask, rank_tasks
    from app.ml import predictor

    now = datetime.now(timezone.utc)
    tasks = [
        ScorableTask(id=str(i), title=f"task {i}", difficulty=1 + i % 5,
                     deadline=now + timedelta(hours=(i * 7) % 500 - 20))
        for i in range(n_tasks)
    ]
    samples = []
    for _ in range(runs):
        t0 = time.perf_counter()
        rank_tasks(tasks, energy_level=3, recent_energy_levels=[4, 3, 3], now=now,
                   ml_scorer=predictor.task_fit_scorer, ml_weight=0.3)
        samples.append((time.perf_counter() - t0) * 1000)
    return summarise(samples)


def _time_calls(call, runs: int) -> dict:
    samples = []
    for _ in range(runs):
        t0 = time.perf_counter()
        call()
        samples.append((time.perf_counter() - t0) * 1000)
    return summarise(samples)


def api_benchmark(base: str, runs: int) -> dict:
    """
    End-to-end timings (HTTP -> validation -> authentication -> database -> JSON) for the main endpoints,
    then a small concurrency test (several students at the same moment).
    Returns {endpoint name: summary}.
    """
    import httpx
    from concurrent.futures import ThreadPoolExecutor

    email = f"bench-{uuid.uuid4().hex[:10]}@example.com"
    password = "Benchmark-pass-123"
    results: dict[str, dict] = {}
    with httpx.Client(base_url=base, timeout=60.0) as c:   # setup (Argon2 sign-up) may be slow on a busy laptop
        r = c.post("/auth/register", json={"email": email, "password": password, "display_name": "Bench"})
        r.raise_for_status()
        headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        for i in range(20):
            c.post("/tasks", headers=headers, json={
                "title": f"Benchmark task {i}", "difficulty": 1 + i % 5,
                "deadline": (datetime.now(timezone.utc) + timedelta(hours=10 + i * 9)).isoformat(),
            }).raise_for_status()
        c.post("/energy-checkins", headers=headers, json={"energy_level": 3}).raise_for_status()

        def get(path):
            return lambda: c.get(path, headers=headers).raise_for_status()

        print("Single-user timings ...", flush=True)
        results["GET /recommend (20 tasks)"] = _time_calls(get("/recommend"), runs)
        results["GET /tasks (20 tasks)"] = _time_calls(get("/tasks"), runs)
        plan = {"category": "Computer Science", "energy": 3, "topics": [{"title": "Python basics"}, {"title": "SQL joins"}]}
        results["POST /planner/plan (2 topics)"] = _time_calls(
            lambda: c.post("/planner/plan", headers=headers, json=plan).raise_for_status(), runs)
        info = c.get("/wellbeing/model").json()
        if info.get("available"):
            answers = {q["name"]: (q["min"] if q["type"] == "number" else q["options"][0]["value"]) for q in info["questions"]}
            # the server allows 20 assessments per user per hour, so stay below that
            results["POST /wellbeing/assess (trained model)"] = _time_calls(
                lambda: c.post("/wellbeing/assess", headers=headers, json={"answers": answers}).raise_for_status(), min(runs, 15))

        # Smart Planner endpoints. With no AI key the "understand" step uses the local rules, so these numbers are the deterministic
        # part of the system only; the time of a real language-model call depends on the provider and is NOT measured here.
        def dstr(days):
            return (datetime.now(timezone.utc) + timedelta(days=days)).date().isoformat()
        drafts = [{"ref": f"d{i}", "title": f"Benchmark essay {i}", "details": "Write 1500 words with references", "deadline_date": dstr(5 + i),
                   "deadline_hour": 20, "felt_hard": 3} for i in range(3)]
        results["POST /assist/understand (local rules)"] = _time_calls(
            lambda: c.post("/assist/understand", headers=headers, json={"text": "Stats exam in 10 days. Also a 1,500 word report due next Friday."}).raise_for_status(), runs)
        results["POST /assist/evaluate (3 drafts + 20 saved tasks)"] = _time_calls(
            lambda: c.post("/assist/evaluate", headers=headers, json={"drafts": drafts}).raise_for_status(), runs)
        results["GET /assist/state (plan, today, replan check)"] = _time_calls(get("/assist/state"), runs)
        results["GET /assist/dashboard"] = _time_calls(get("/assist/dashboard"), runs)
        ses = {"status": "done", "actual_minutes": 25, "felt_difficulty": 3}
        results["POST /assist/session (feedback learning)"] = _time_calls(
            lambda: c.post("/assist/session", headers=headers, json=ses).raise_for_status(), runs)
        gstate = {"now": datetime.now(timezone.utc).isoformat(), "settings": {}, "history": {"outcomes": [], "sessions": []},
                  "tasks": [{"id": f"g{i}", "title": f"Guest task {i}", "difficulty": 1 + i % 5,
                             "deadline": (datetime.now(timezone.utc) + timedelta(days=3 + i)).isoformat()} for i in range(10)]}
        results["POST /demo/assist/plan (guest, 10 tasks)"] = _time_calls(
            lambda: c.post("/demo/assist/plan", json={"state": gstate}).raise_for_status(), runs)

        # My Tasks, reminders and the AI Learning Studio (sample pack: no AI is ever called by any of these)
        c.post("/assist/accept", headers=headers, json={"drafts": drafts}).raise_for_status()
        results["GET /roadmap (whole saved roadmap)"] = _time_calls(get("/roadmap"), runs)
        results["GET /reminders (daily + deadline, in-app)"] = _time_calls(get("/reminders"), runs)
        results["POST /roadmap/replan/preview (nothing saved)"] = _time_calls(lambda: c.post("/roadmap/replan/preview", headers=headers).raise_for_status(), runs)
        grm = {"today": dstr(0), "time": "09:00", "name": "", "settings": {}, "tasks": [],
               "blocks": [{"id": f"b{i}", "task_id": None, "day": dstr(i % 10), "position": i, "minutes": 45, "actual_minutes": 0, "break_after": 5, "label": "Study",
                           "method": "", "status": "planned", "title": f"Block {i}", "subject": "Maths", "manual": False} for i in range(60)]}
        results["POST /demo/assist/roadmap (guest, 60 blocks)"] = _time_calls(lambda: c.post("/demo/assist/roadmap", json=grm).raise_for_status(), runs)
        pid = c.post("/studio/sample", headers=headers).json()["pack"]["id"]
        results["GET /studio/packs"] = _time_calls(get("/studio/packs"), runs)
        results["POST /studio/packs/{id}/quiz (10 questions)"] = _time_calls(
            lambda: c.post(f"/studio/packs/{pid}/quiz", headers=headers, json={"count": 10, "difficulty": "mixed"}).raise_for_status(), runs)
        results["GET /studio/summary (Dashboard)"] = _time_calls(get("/studio/summary"), runs)

        # Concurrency: 10 students at once, each asking for a recommendation 10 times.
        # A failed or timed-out request is counted and reported (not allowed to crash the whole benchmark),
        # because "does the server stay responsive under parallel use?" is exactly what this step measures.
        errors: list[str] = []

        def student(_):
            out = []
            with httpx.Client(base_url=base, timeout=15.0) as cc:
                for _ in range(10):
                    t0 = time.perf_counter()
                    try:
                        cc.get("/recommend", headers=headers).raise_for_status()
                        out.append((time.perf_counter() - t0) * 1000)
                    except Exception as exc:   # timeout, connection reset, HTTP error
                        errors.append(f"{type(exc).__name__} after {(time.perf_counter() - t0) * 1000:.0f} ms")
            return out
        print("Concurrency step: 10 students x 10 requests ...", flush=True)
        with ThreadPoolExecutor(max_workers=10) as ex:
            flat = [x for chunk in ex.map(student, range(10)) for x in chunk]
        if flat:
            results["GET /recommend, 10 students at once (100 requests)"] = summarise(flat)
        if errors:
            print(f"WARNING: {len(errors)} of 100 concurrent requests failed: {sorted(set(errors))[:5]}", flush=True)
            results["_concurrency_errors"] = {"count": len(errors), "examples": sorted(set(errors))[:5]}
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["engine", "api"])
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--runs", type=int, default=50)
    args = ap.parse_args()

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    if args.mode == "engine":
        lines = [f"### Ranking engine only (heuristic + trained model), {stamp}", "",
                 "| Tasks | Median ms | p95 ms | Max ms |", "|---|---|---|---|"]
        for n in (10, 100, 1000):
            r = engine_benchmark(n)
            lines.append(f"| {n} | {r['median_ms']} | {r['p95_ms']} | {r['max_ms']} |")
        text = "\n".join(lines)
    else:
        res = api_benchmark(args.base, args.runs)
        lines = [f"### End-to-end API latency, {stamp}", "",
                 f"Server: {args.base}. Target: p95 under {TARGET_MS:.0f} ms.", "",
                 "| Endpoint | Requests | Min ms | Median ms | p95 ms | Max ms | Result |", "|---|---|---|---|---|---|---|"]
        failed = res.pop("_concurrency_errors", None)
        for name, r in res.items():
            lines.append(f"| {name} | {r['runs']} | {r['min_ms']} | {r['median_ms']} | {r['p95_ms']} | {r['max_ms']} | "
                         f"{'PASS' if r['under_target'] else 'FAIL'} |")
        if failed:
            lines += ["", f"**{failed['count']} of the 100 concurrent requests failed** (examples: {failed['examples']}). This is a finding, not a pass."]
        text = "\n".join(lines)
    print(text)
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(text + "\n\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
