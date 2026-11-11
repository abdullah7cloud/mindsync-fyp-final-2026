"""
Where does the slowdown under parallel use come from?  (Objective 4: performance testing.)

Sends the same number of requests at three endpoints that stress different layers, at 1, 2, 5 and 10 simultaneous
clients, and prints one table:

    /health      web server + event loop only (no database)
    /tasks       one database query with authentication
    /recommend   three queries + the ranking engine

If /health is slow under load the problem is the web server or the machine; if only /tasks and /recommend are slow
the problem is the database connection (pool) or the queries.

    python -m scripts.diagnose_concurrency [--base http://127.0.0.1:8000]
Needs the backend running. Creates one throw-away test account.
"""
import argparse
import statistics
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

OUT = Path(__file__).resolve().parents[2] / "docs" / "latency_results.md"
PER_CLIENT = 10
TIMEOUT = 20.0


def pct(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, int(round(p / 100 * (len(values) - 1))))]


def run_level(base, headers, path, clients):
    errors, times = [], []

    def worker(_):
        with httpx.Client(base_url=base, timeout=TIMEOUT) as c:
            for _ in range(PER_CLIENT):
                t0 = time.perf_counter()
                try:
                    c.get(path, headers=headers).raise_for_status()
                    times.append((time.perf_counter() - t0) * 1000)
                except Exception as exc:
                    errors.append(type(exc).__name__)
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=clients) as ex:
        list(ex.map(worker, range(clients)))
    wall = time.perf_counter() - t0
    n = clients * PER_CLIENT
    return {"clients": clients, "ok": len(times), "errors": len(errors),
            "median": round(statistics.median(times), 1) if times else None,
            "p95": round(pct(times, 95), 1) if times else None,
            "max": round(max(times), 1) if times else None,
            "throughput": round(len(times) / wall, 1)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    args = ap.parse_args()
    with httpx.Client(base_url=args.base, timeout=30) as c:
        r = c.post("/auth/register", json={"email": f"diag-{uuid.uuid4().hex[:10]}@example.com",
                                           "password": "Diagnose-pass-123", "display_name": "Diag"})
        r.raise_for_status()
        headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        for i in range(20):
            c.post("/tasks", headers=headers, json={"title": f"Diag task {i}", "difficulty": 1 + i % 5,
                   "deadline": (datetime.now(timezone.utc) + timedelta(hours=10 + 9 * i)).isoformat()}).raise_for_status()
        c.post("/energy-checkins", headers=headers, json={"energy_level": 3}).raise_for_status()
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"### Concurrency diagnosis, {stamp}", "", f"Server {args.base}. {PER_CLIENT} requests per client, timeout {TIMEOUT:.0f} s.", "",
             "| Endpoint | Clients | OK | Errors | Median ms | p95 ms | Max ms | Requests/s |", "|---|---|---|---|---|---|---|---|"]
    for path in ("/health", "/tasks", "/recommend"):
        for clients in (1, 2, 5, 10):
            print(f"{path} x {clients} clients ...", flush=True)
            r = run_level(args.base, headers, path, clients)
            lines.append(f"| {path} | {clients} | {r['ok']} | {r['errors']} | {r['median']} | {r['p95']} | {r['max']} | {r['throughput']} |")
    text = "\n".join(lines)
    print(text)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(text + "\n\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
