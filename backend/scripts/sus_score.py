"""
Score System Usability Scale (SUS) questionnaires.

Put one row per participant in docs/usability_results.csv with columns
participant,q1,q2,...,q10 (each answer 1-5), plus optional columns
time_task1_sec ... time_task5_sec and completed_tasks (0-5). Then run:

    python -m scripts.sus_score

SUS scoring: odd questions (1,3,5,7,9): score = answer - 1.
             even questions (2,4,6,8,10): score = 5 - answer.
             SUS = (sum of the ten scores) x 2.5  -> 0..100.
Average SUS is about 68; 80+ is excellent.
"""
import csv
import statistics
import sys
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parents[2] / "docs" / "usability_results.csv"
OUT = Path(__file__).resolve().parents[2] / "docs" / "usability_summary.md"


def sus(row: dict) -> float:
    total = 0
    for i in range(1, 11):
        a = int(row[f"q{i}"])
        if not 1 <= a <= 5:
            raise ValueError(f"{row.get('participant')}: q{i} must be 1-5")
        total += (a - 1) if i % 2 == 1 else (5 - a)
    return total * 2.5


def grade(score: float) -> str:
    if score >= 80.3: return "Excellent (A)"
    if score >= 68: return "Good / above average"
    if score >= 51: return "OK / below average"
    return "Poor"


def main() -> int:
    if not CSV_PATH.exists():
        print(f"Create {CSV_PATH} first (copy usability_results_template.csv).")
        return 2
    rows = [r for r in csv.DictReader(CSV_PATH.open(encoding="utf-8")) if r.get("participant") and r.get("q1")]
    if not rows:
        print("No filled-in participant rows found yet.")
        return 2
    scores = [sus(r) for r in rows]
    mean = statistics.mean(scores)
    lines = ["# Usability results (System Usability Scale)", "",
             f"Participants: **{len(scores)}**  |  Mean SUS: **{mean:.1f}** ({grade(mean)})  |  "
             f"Median: {statistics.median(scores):.1f}  |  Min-Max: {min(scores):.1f}-{max(scores):.1f}", "",
             "| Participant | SUS score |", "|---|---|"]
    lines += [f"| {r['participant']} | {s:.1f} |" for r, s in zip(rows, scores)]
    done = [int(r["completed_tasks"]) for r in rows if r.get("completed_tasks", "").strip().isdigit()]
    if done:
        lines += ["", f"Task completion: mean {statistics.mean(done):.1f} of 5 tasks per participant "
                      f"({100 * statistics.mean(done) / 5:.0f}% overall)."]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
