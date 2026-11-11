# Intelligence evaluation (measured)

Generated 2026-10-29 by `scripts/intelligence_eval.py` against the running servers. Daily capacity 120 min, no buffer, one task at a time, time-zone and settings identical for both versions.

| Case | Current version: kind | Workload low-likely-high (min) | Status | Steps | Session lengths | Older version: workload | Older steps |
|---|---|---|---|---|---|---|---|
| programming-large | Programming | 210-270-390 | on_track | 5 | 15, 20, 25, 30, 35, 50 | 210-270-390 | 5 |
| programming-small | Programming | 110-140-205 | tight | 5 | 10, 15, 20, 30, 45 | 150-195-280 | 5 |
| maths-large | Exam preparation | 280-360-520 | on_track | 4 | 15, 20, 25, 30, 35 | 110-140-205 | 4 |
| maths-small | Exam preparation | 115-145-210 | tight | 4 | 15, 20, 45 | 150-195-280 | 4 |
| report-large | Writing | 980-1265-1830 | tight | 5 | 25, 30, 35, 40, 45, 60, 85 | 980-1265-1830 | 5 |
| report-small | Writing | 165-210-305 | on_track | 5 | 10, 15, 20, 25, 30, 40, 45 | 165-210-305 | 5 |
| presentation-large | Presentation | 180-235-340 | on_track | 3 | 10, 15, 20, 25, 35 | 105-135-195 | 3 |
| presentation-small | Presentation | 100-130-190 | on_track | 3 | 20, 25, 35, 50 | 205-265-385 | 3 |
| reading-large | Reading | 250-320-465 | on_track | 3 | 15, 25, 35, 40 | 250-320-465 | 3 |
| reading-small | Reading | 15-20-30 | on_track | 1 | 10 | 35-45-65 | 2 |

## Ordering checks (large must need more than small, same type of work)

| Type of work | Current: large vs small | Older: large vs small |
|---|---|---|
| programming | PASS (270 vs 140 min) | PASS (270 vs 195 min) |
| maths | PASS (360 vs 145 min) | FAIL (140 vs 195 min) |
| report | PASS (1265 vs 210 min) | PASS (1265 vs 210 min) |
| presentation | PASS (235 vs 130 min) | FAIL (135 vs 265 min) |
| reading | PASS (320 vs 20 min) | PASS (320 vs 45 min) |

Distinct step sequences across the ten cases (current version): 6 of 10.

## Plan shape per case (current version)

- **programming-large** — “I have to build a Python Flask login page with user registration and unit tests, due in 5 days.” → Programming; steps: Plan the design > Build it > Fix problems > Test it > Tidy and document; 9 study blocks; verdict comfortable.
- **programming-small** — “Fix a small bug in my Python script, due tomorrow.” → Programming; steps: Plan the design > Build it > Fix problems > Test it > Tidy and document; 6 study blocks; verdict tight.
- **maths-large** — “Maths exam in 10 days covering calculus chapters 1 to 6. I find integration really hard.” → Exam preparation; steps: Understand the topics > Practise recalling > Do practice questions > Review again after a gap; 13 study blocks; verdict comfortable.
- **maths-small** — “Short algebra quiz tomorrow, mostly revision.” → Exam preparation; steps: Understand the topics > Practise recalling > Do practice questions > Review again after a gap; 5 study blocks; verdict tight.
- **report-large** — “3000 word research report on climate policy with 10 references due in 14 days.” → Writing; steps: Research and take notes > Make an outline > Write the first draft > Check references > Edit and proofread; 30 study blocks; verdict tight.
- **report-small** — “500 word reflection due in 3 days.” → Writing; steps: Research and take notes > Make an outline > Write the first draft > Check references > Edit and proofread; 8 study blocks; verdict comfortable.
- **presentation-large** — “10 minute group presentation on machine learning ethics in 6 days, I have to make the slides and practise.” → Presentation; steps: Gather the content > Prepare the slides > Rehearse aloud; 10 study blocks; verdict comfortable.
- **presentation-small** — “5 slide presentation due in 2 days.” → Presentation; steps: Gather the content > Prepare the slides > Rehearse aloud; 4 study blocks; verdict comfortable.
- **reading-large** — “Read chapters 4 to 6 of the economics textbook, about 90 pages, by next Friday.” → Reading; steps: Skim first > Read for understanding > Analyse in detail; 10 study blocks; verdict comfortable.
- **reading-small** — “Read a 6 page article by tomorrow.” → Reading; steps: Read for understanding; 2 study blocks; verdict comfortable.
