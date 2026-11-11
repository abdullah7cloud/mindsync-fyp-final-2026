# Latency results

_Ranking-engine numbers below were measured on the development sandbox; re-run run-benchmark.bat on your laptop for the figures to quote in Chapter 4._

### Ranking engine only (heuristic + trained model), 2026-10-05 16:44

| Tasks | Median ms | p95 ms | Max ms |
|---|---|---|---|
| 10 | 0.073 | 0.173 | 0.294 |
| 100 | 1.345 | 1.489 | 1.684 |
| 1000 | 7.986 | 9.682 | 29.196 |

### Ranking engine only (heuristic + trained model), 2026-10-05 16:51

| Tasks | Median ms | p95 ms | Max ms |
|---|---|---|---|
| 10 | 0.064 | 0.195 | 0.752 |
| 100 | 0.615 | 1.847 | 2.864 |
| 1000 | 24.869 | 86.712 | 183.157 |

### End-to-end GET /recommend, 2026-10-05 16:51

Server: http://127.0.0.1:8000, 50 requests, 20 pending tasks.

| Min ms | Median ms | p95 ms | Max ms | Target | Result |
|---|---|---|---|---|---|
| 23.751 | 34.604 | 90.205 | 147.007 | < 3000 p95 | PASS |

### Ranking engine only (heuristic + trained model), 2026-10-21 15:40

| Tasks | Median ms | p95 ms | Max ms |
|---|---|---|---|
| 10 | 0.202 | 2.245 | 10.972 |
| 100 | 3.044 | 10.206 | 57.965 |
| 1000 | 41.645 | 109.045 | 333.419 |

### Ranking engine only (heuristic + trained model), 2026-10-21 15:51

| Tasks | Median ms | p95 ms | Max ms |
|---|---|---|---|
| 10 | 0.226 | 2.09 | 14.754 |
| 100 | 4.612 | 14.256 | 50.031 |
| 1000 | 33.967 | 85.354 | 234.475 |

### Ranking engine only (heuristic + trained model), 2026-10-21 16:09

| Tasks | Median ms | p95 ms | Max ms |
|---|---|---|---|
| 10 | 0.231 | 0.897 | 4.657 |
| 100 | 4.124 | 15.757 | 51.713 |
| 1000 | 35.004 | 61.58 | 141.068 |

### End-to-end API latency, 2026-10-21 16:09

Server: http://127.0.0.1:8000. Target: p95 under 3000 ms.

| Endpoint | Requests | Min ms | Median ms | p95 ms | Max ms | Result |
|---|---|---|---|---|---|---|
| GET /recommend (20 tasks) | 50 | 42.128 | 73.813 | 267.363 | 789.424 | PASS |
| GET /tasks (20 tasks) | 50 | 21.925 | 60.739 | 150.817 | 218.792 | PASS |
| POST /planner/plan (2 topics) | 50 | 6.632 | 51.727 | 854.5 | 2211.546 | PASS |
| POST /wellbeing/assess (trained model) | 15 | 13.539 | 92.692 | 197.801 | 2143.718 | PASS |
| GET /recommend, 10 students at once (100 requests) | 97 | 105.407 | 1952.327 | 12825.587 | 14630.801 | FAIL |

**3 of the 100 concurrent requests failed** (examples: ['ReadTimeout after 15006 ms', 'ReadTimeout after 15008 ms', 'ReadTimeout after 15020 ms']). This is a finding, not a pass.

### Concurrency diagnosis, 2026-10-21 16:13

Server http://127.0.0.1:8000. 10 requests per client, timeout 20 s.

| Endpoint | Clients | OK | Errors | Median ms | p95 ms | Max ms | Requests/s |
|---|---|---|---|---|---|---|---|
| /health | 1 | 10 | 0 | 20.0 | 416.8 | 416.8 | 15.3 |
| /health | 2 | 20 | 0 | 23.2 | 36.6 | 38.9 | 66.8 |
| /health | 5 | 50 | 0 | 45.0 | 110.4 | 118.1 | 84.4 |
| /health | 10 | 100 | 0 | 85.5 | 219.4 | 281.5 | 79.8 |
| /tasks | 1 | 10 | 0 | 27.7 | 51.1 | 51.1 | 30.1 |
| /tasks | 2 | 20 | 0 | 78.9 | 139.6 | 190.5 | 21.5 |
| /tasks | 5 | 50 | 0 | 434.6 | 1787.0 | 1827.5 | 7.6 |
| /tasks | 10 | 100 | 0 | 750.8 | 9814.7 | 10942.9 | 3.8 |
| /recommend | 1 | 10 | 0 | 115.6 | 751.0 | 751.0 | 3.6 |
| /recommend | 2 | 20 | 0 | 60.8 | 2369.0 | 2519.4 | 4.8 |
| /recommend | 5 | 50 | 0 | 480.6 | 4043.5 | 4675.2 | 5.4 |
| /recommend | 10 | 100 | 0 | 2178.6 | 9015.2 | 12099.5 | 3.1 |

### Ranking engine only (heuristic + trained model), 2026-10-21 16:25

| Tasks | Median ms | p95 ms | Max ms |
|---|---|---|---|
| 10 | 0.238 | 0.833 | 6.713 |
| 100 | 4.853 | 11.805 | 31.374 |
| 1000 | 36.1 | 76.593 | 155.487 |

### Status and reading guide (written 21 Oct 2026)

* The "10 students at once" row in the second-to-last End-to-end table above is a **FAIL measured on the student's laptop** (median 1,952 ms, p95 12,826 ms, 3 of 100 requests timed out at 15 s). It stays here as a finding: it was not hidden or re-run until it looked good.
* Cause found with `run-diagnose-db.bat`: a new PostgreSQL connection took about 360 ms on this Windows laptop, and memory was 95% used (0.37 of 7.7 GB free). Opening 10 connections in advance cut the p95 of 10 parallel database queries from 449 ms to 97 ms.
* Fixes installed: connection pool opened at start-up (update 9); Argon2id hashing moved to worker threads so sign-up/login no longer freeze other requests (update 10; proven by `test_hashing_does_not_block_the_event_loop`).
* **Post-fix re-run done (PostgreSQL running, laptop):** run 1 at 21:02 - 10 students at once, 100/100 requests succeeded, p95 2,948 ms, slowest request 4,307 ms (p95 only narrowly under the 3 s target; slowest request over it). Run 2 at 21:33 - 100/100 succeeded, p95 1,663 ms, slowest 2,999 ms. Both tables are appended further down by the benchmark script. The laptop is still short of memory, so these numbers move between runs; quote both, not only the better one. Not tested: more than 10 simultaneous users.

### End-to-end API latency, 2026-10-21, BUILD ENVIRONMENT (Linux, SQLite, fast machine: NOT the target laptop)

| Endpoint | Requests | Median ms | p95 ms | Result |
|---|---|---|---|---|
| GET /recommend (20 tasks) | 30 | 5.84 | 7.8 | PASS |
| GET /tasks (20 tasks) | 30 | 4.05 | 4.4 | PASS |
| POST /planner/plan (2 topics) | 30 | 3.45 | 5.0 | PASS |
| POST /wellbeing/assess (real model) | 15 | 6.29 | 6.9 | PASS |
| GET /recommend, 10 students at once (100 requests) | 100 | 56.7 | 84.8 | PASS |

Do not quote the table above as a laptop result; it shows only that the code itself is fast and does not fail under 10 parallel users when the database is fast.
### Ranking engine only (heuristic + trained model), 2026-10-21 21:02

| Tasks | Median ms | p95 ms | Max ms |
|---|---|---|---|
| 10 | 0.198 | 1.254 | 5.939 |
| 100 | 3.571 | 11.282 | 26.013 |
| 1000 | 30.436 | 50.184 | 125.116 |

### End-to-end API latency, 2026-10-21 21:02

Server: http://127.0.0.1:8000. Target: p95 under 3000 ms.

| Endpoint | Requests | Min ms | Median ms | p95 ms | Max ms | Result |
|---|---|---|---|---|---|---|
| GET /recommend (20 tasks) | 50 | 63.871 | 116.868 | 189.116 | 222.046 | PASS |
| GET /tasks (20 tasks) | 50 | 41.142 | 73.219 | 130.82 | 286.829 | PASS |
| POST /planner/plan (2 topics) | 50 | 37.822 | 63.721 | 107.343 | 161.156 | PASS |
| POST /wellbeing/assess (trained model) | 15 | 58.794 | 87.736 | 177.184 | 216.107 | PASS |
| GET /recommend, 10 students at once (100 requests) | 100 | 218.939 | 1476.291 | 2947.604 | 4306.835 | PASS |

### Ranking engine only (heuristic + trained model), 2026-10-21 21:32

| Tasks | Median ms | p95 ms | Max ms |
|---|---|---|---|
| 10 | 0.227 | 1.063 | 4.989 |
| 100 | 2.701 | 6.583 | 30.81 |
| 1000 | 25.289 | 43.667 | 117.134 |

### End-to-end API latency, 2026-10-21 21:33

Server: http://127.0.0.1:8000. Target: p95 under 3000 ms.

| Endpoint | Requests | Min ms | Median ms | p95 ms | Max ms | Result |
|---|---|---|---|---|---|---|
| GET /recommend (20 tasks) | 50 | 49.608 | 90.942 | 153.3 | 190.252 | PASS |
| GET /tasks (20 tasks) | 50 | 32.159 | 59.842 | 141.761 | 206.858 | PASS |
| POST /planner/plan (2 topics) | 50 | 24.403 | 45.777 | 97.074 | 116.157 | PASS |
| POST /wellbeing/assess (trained model) | 15 | 54.287 | 74.906 | 140.17 | 219.161 | PASS |
| GET /recommend, 10 students at once (100 requests) | 100 | 142.91 | 933.344 | 1662.999 | 2998.723 | PASS |

### End-to-end API latency, 2026-10-29 04:19 - BUILD ENVIRONMENT (Linux, SQLite): not the laptop

Server: http://127.0.0.1:8000. Target: p95 under 3000 ms.

| Endpoint | Requests | Min ms | Median ms | p95 ms | Max ms | Result |
|---|---|---|---|---|---|---|
| GET /recommend (20 tasks) | 50 | 16.256 | 26.291 | 35.392 | 41.67 | PASS |
| GET /tasks (20 tasks) | 50 | 2.95 | 3.707 | 4.735 | 7.203 | PASS |
| POST /planner/plan (2 topics) | 50 | 2.905 | 3.679 | 4.992 | 6.975 | PASS |
| POST /wellbeing/assess (trained model) | 15 | 6.128 | 7.492 | 9.985 | 10.564 | PASS |
| POST /assist/understand (local rules) | 50 | 13.781 | 16.901 | 21.896 | 54.949 | PASS |
| POST /assist/evaluate (3 drafts + 20 saved tasks) | 50 | 18.692 | 21.189 | 30.496 | 72.762 | PASS |
| GET /assist/state (plan, today, replan check) | 50 | 11.531 | 13.495 | 18.694 | 20.931 | PASS |
| GET /assist/dashboard | 50 | 13.961 | 17.291 | 24.172 | 30.689 | PASS |
| POST /assist/session (feedback learning) | 50 | 13.441 | 15.545 | 19.655 | 24.272 | PASS |
| POST /demo/assist/plan (guest, 10 tasks) | 50 | 9.353 | 12.885 | 13.98 | 21.071 | PASS |
| GET /recommend, 10 students at once (100 requests) | 100 | 35.059 | 249.185 | 307.173 | 368.473 | PASS |

### Ranking engine only (heuristic + trained model), 2026-10-29 05:01

| Tasks | Median ms | p95 ms | Max ms |
|---|---|---|---|
| 10 | 0.06 | 0.11 | 0.377 |
| 100 | 0.634 | 0.891 | 2.447 |
| 1000 | 7.209 | 8.562 | 11.492 |

### End-to-end API latency, 2026-10-29 05:01 - BUILD ENVIRONMENT (Linux, SQLite): not the laptop

Server: http://127.0.0.1:8000. Target: p95 under 3000 ms.

| Endpoint | Requests | Min ms | Median ms | p95 ms | Max ms | Result |
|---|---|---|---|---|---|---|
| GET /recommend (20 tasks) | 50 | 20.018 | 22.212 | 30.62 | 40.748 | PASS |
| GET /tasks (20 tasks) | 50 | 3.298 | 3.998 | 4.601 | 4.997 | PASS |
| POST /planner/plan (2 topics) | 50 | 2.891 | 3.484 | 4.445 | 5.36 | PASS |
| POST /wellbeing/assess (trained model) | 15 | 6.216 | 7.338 | 8.33 | 8.467 | PASS |
| POST /assist/understand (local rules) | 50 | 14.452 | 18.968 | 28.286 | 118.983 | PASS |
| POST /assist/evaluate (3 drafts + 20 saved tasks) | 50 | 19.783 | 22.171 | 30.218 | 61.616 | PASS |
| GET /assist/state (plan, today, replan check) | 50 | 13.458 | 16.375 | 19.446 | 22.163 | PASS |
| GET /assist/dashboard | 50 | 14.366 | 18.539 | 24.917 | 26.794 | PASS |
| POST /assist/session (feedback learning) | 50 | 13.57 | 18.392 | 23.418 | 32.43 | PASS |
| POST /demo/assist/plan (guest, 10 tasks) | 50 | 10.368 | 13.159 | 16.92 | 25.666 | PASS |
| GET /recommend, 10 students at once (100 requests) | 100 | 23.873 | 247.912 | 310.646 | 356.289 | PASS |

### End-to-end API latency, 2026-10-29 05:24 - BUILD ENVIRONMENT (Linux, PostgreSQL 16.15 over localhost): not the laptop

Server: http://127.0.0.1:8000. Target: p95 under 3000 ms.

| Endpoint | Requests | Min ms | Median ms | p95 ms | Max ms | Result |
|---|---|---|---|---|---|---|
| GET /recommend (20 tasks) | 50 | 21.49 | 29.2 | 39.21 | 46.142 | PASS |
| GET /tasks (20 tasks) | 50 | 4.473 | 5.455 | 6.473 | 11.906 | PASS |
| POST /planner/plan (2 topics) | 50 | 3.357 | 3.896 | 5.075 | 5.96 | PASS |
| POST /wellbeing/assess (trained model) | 15 | 7.5 | 9.319 | 12.376 | 12.534 | PASS |
| POST /assist/understand (local rules) | 50 | 11.962 | 15.389 | 21.313 | 123.119 | PASS |
| POST /assist/evaluate (3 drafts + 20 saved tasks) | 50 | 20.697 | 31.097 | 39.51 | 95.634 | PASS |
| GET /assist/state (plan, today, replan check) | 50 | 15.514 | 19.793 | 30.669 | 42.995 | PASS |
| GET /assist/dashboard | 50 | 17.085 | 23.479 | 28.379 | 31.333 | PASS |
| POST /assist/session (feedback learning) | 50 | 12.794 | 17.117 | 22.057 | 28.355 | PASS |
| POST /demo/assist/plan (guest, 10 tasks) | 50 | 10.632 | 12.425 | 17.28 | 18.065 | PASS |
| GET /recommend, 10 students at once (100 requests) | 100 | 40.371 | 215.458 | 403.568 | 518.931 | PASS |

### End-to-end API latency, 2026-10-29 18:00

Server: http://127.0.0.1:8000. Target: p95 under 3000 ms.

| Endpoint | Requests | Min ms | Median ms | p95 ms | Max ms | Result |
|---|---|---|---|---|---|---|
| GET /recommend (20 tasks) | 30 | 21.248 | 23.052 | 30.736 | 33.648 | PASS |
| GET /tasks (20 tasks) | 30 | 3.608 | 4.627 | 5.366 | 5.444 | PASS |
| POST /planner/plan (2 topics) | 30 | 3.125 | 3.341 | 4.916 | 7.468 | PASS |
| POST /wellbeing/assess (trained model) | 15 | 5.821 | 6.769 | 7.74 | 8.26 | PASS |
| POST /assist/understand (local rules) | 30 | 9.768 | 11.086 | 15.445 | 16.725 | PASS |
| POST /assist/evaluate (3 drafts + 20 saved tasks) | 30 | 20.216 | 22.345 | 32.634 | 69.51 | PASS |
| GET /assist/state (plan, today, replan check) | 30 | 12.07 | 13.607 | 16.998 | 18.718 | PASS |
| GET /assist/dashboard | 30 | 13.91 | 16.325 | 21.322 | 21.461 | PASS |
| POST /assist/session (feedback learning) | 30 | 11.236 | 12.909 | 15.378 | 17.287 | PASS |
| POST /demo/assist/plan (guest, 10 tasks) | 30 | 10.675 | 12.007 | 17.289 | 19.233 | PASS |
| GET /roadmap (whole saved roadmap) | 30 | 12.48 | 14.898 | 19.854 | 22.322 | PASS |
| GET /reminders (daily + deadline, in-app) | 30 | 12.292 | 13.903 | 17.177 | 19.304 | PASS |
| POST /roadmap/replan/preview (nothing saved) | 30 | 18.634 | 19.859 | 22.514 | 23.892 | PASS |
| POST /demo/assist/roadmap (guest, 60 blocks) | 30 | 2.66 | 2.928 | 4.259 | 4.899 | PASS |
| GET /studio/packs | 30 | 6.222 | 7.503 | 9.58 | 10.079 | PASS |
| POST /studio/packs/{id}/quiz (10 questions) | 30 | 4.911 | 5.463 | 6.425 | 8.848 | PASS |
| GET /studio/summary (Dashboard) | 30 | 5.254 | 6.404 | 7.961 | 8.874 | PASS |
| GET /recommend, 10 students at once (100 requests) | 100 | 60.524 | 241.247 | 312.994 | 614.954 | PASS |

### End-to-end API latency, 2026-10-29 19:09

Server: http://127.0.0.1:8000. Target: p95 under 3000 ms.

| Endpoint | Requests | Min ms | Median ms | p95 ms | Max ms | Result |
|---|---|---|---|---|---|---|
| GET /recommend (20 tasks) | 50 | 21.128 | 23.763 | 36.669 | 40.548 | PASS |
| GET /tasks (20 tasks) | 50 | 3.673 | 4.358 | 5.812 | 8.314 | PASS |
| POST /planner/plan (2 topics) | 50 | 3.12 | 3.559 | 4.98 | 7.005 | PASS |
| POST /wellbeing/assess (trained model) | 15 | 5.674 | 6.175 | 7.782 | 13.012 | PASS |
| POST /assist/understand (local rules) | 50 | 10.159 | 11.736 | 15.996 | 18.992 | PASS |
| POST /assist/evaluate (3 drafts + 20 saved tasks) | 50 | 20.34 | 23.324 | 33.177 | 69.702 | PASS |
| GET /assist/state (plan, today, replan check) | 50 | 11.863 | 12.772 | 17.049 | 17.335 | PASS |
| GET /assist/dashboard | 50 | 13.149 | 14.592 | 17.496 | 18.035 | PASS |
| POST /assist/session (feedback learning) | 50 | 11.759 | 12.689 | 15.809 | 17.902 | PASS |
| POST /demo/assist/plan (guest, 10 tasks) | 50 | 11.463 | 12.022 | 16.279 | 19.269 | PASS |
| GET /roadmap (whole saved roadmap) | 50 | 12.266 | 13.398 | 18.124 | 19.817 | PASS |
| GET /reminders (daily + deadline, in-app) | 50 | 11.966 | 13.342 | 16.647 | 18.227 | PASS |
| POST /roadmap/replan/preview (nothing saved) | 50 | 18.325 | 20.076 | 30.264 | 32.503 | PASS |
| POST /demo/assist/roadmap (guest, 60 blocks) | 50 | 2.668 | 3.112 | 4.149 | 5.564 | PASS |
| GET /studio/packs | 50 | 6.336 | 7.391 | 10.063 | 13.826 | PASS |
| POST /studio/packs/{id}/quiz (10 questions) | 50 | 4.502 | 5.027 | 7.294 | 7.79 | PASS |
| GET /studio/summary (Dashboard) | 50 | 5.073 | 5.608 | 7.066 | 7.803 | PASS |
| GET /recommend, 10 students at once (100 requests) | 100 | 47.406 | 220.635 | 315.674 | 638.915 | PASS |

