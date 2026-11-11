# Keeping the report accurate (word count must stay between 8,000 and 10,000)

> Superseded by `REPORT_REPLACEMENTS.md` (31 exact replacements, net -91 words, counted by script). This file keeps the reasoning.

The only report text available to the build was `docs/MindSync_Report_Draft_Chapters_1-6.docx` (about 8,450 words as exported). If your Turnitin version is a different, longer text, check it for the same statements. **Replace sentences; do not add paragraphs** - the report is already near the 10,000-word limit. Every replacement below is the same length or shorter.

## Statements in the draft that no longer match the software

| Draft says | What is true now | Replacement (same size or shorter) |
|---|---|---|
| Objective 3: "integrate an LLM API to generate natural-language justifications" | An OpenAI model is optional, used only for reading free text and wording explanations, the weekly review and answers about the plan. | "...and integrate an optional LLM API for natural-language wording, with validation, spending limits and an offline fallback." |
| "an AI study coach and an AI task-breakdown helper (both with offline fallbacks)... an optional ambient sound player" | The coach and breakdown helper were replaced by one plan assistant and the Smart Planner; the music player was removed. | "...a Smart Planner that understands free-text tasks, an assistant that answers questions about the plan, a focus timer and an energy-trend chart." |
| "The Gemini API key is sent in an HTTP header" ; table row "OpenAI gpt-4o-mini, Gemini 2.5 Flash" | One provider only: OpenAI Chat Completions (`gpt-6-luna`, checked 29 Oct 2026), key only in the backend `.env`, sent as a Bearer header. There is no Gemini and no backup provider. | "The OpenAI key is read from `.env` on the server and sent only in an HTTP header." / table: "OpenAI (optional; gpt-6-luna), scikit-learn (offline training only)". |
| "tries the preferred provider, then the backup provider, then ... three-second timeout per attempt" | One provider; 8 s per attempt, 10 s in total, then the rule-based answer. | "Each AI call is tried once with retries inside a 10-second limit and otherwise falls back to the rule-based answer." |
| "Both features are limited to 30 calls per user per 10 minutes" | 40 calls per student per day, 5 USD per month for the whole app, guests never reach the model, student can switch it off. | "AI calls are limited to 40 per student per day and 5 US dollars per month." |
| "pytest suite of 63 tests" and the test-file table | 338 backend tests, 140 frontend tests, 162 browser checks, 95 security checks (all in `UPGRADE_21_SUMMARY.md`). | Quote the figures from your own laptop logs (`_update_backup\logs`). |
| "95th-percentile end-to-end latency of 90 ms ... excludes the LLM call" | Still true that the deterministic path is far below 3 s. With a key, a language-model call is bounded by the 10-second limit; the 3-second target applies to the deterministic path (ranking, evaluation, state), which is where the plan and its numbers come from. | Keep the sentence, add: "AI-assisted calls are bounded at 10 s and fall back to rules." Use your own laptop benchmark numbers. |
| Anything saying MindSync is "AI-powered" or "predicts burnout" | The planner is rules plus per-student calibration. The wellbeing model reproduces its dataset's scoring rule and is not a diagnosis. The task-fit model uses simulated data and is off by default. | "...a rule-based planner supported by locally trained models and an optional language model." |

## Claims you may safely make (each has evidence in `docs/`)

- Works fully offline with no key; the screen labels whether a text was written by rules or by the AI.
- The language model never decides minutes, order, deadlines or whether a plan fits.
- 95 / 95 live security checks mapped to OWASP Top 10 categories; Argon2id; every query scoped to the logged-in student.
- 0 axe-core WCAG 2.0/2.1 A and AA violations on 16 page states (automated only).
- Two previous versions compared on identical inputs, with the two ordering errors that were found and fixed (`UPGRADE_21_INTELLIGENCE.md`).

## Claims you must not make

- That estimates are accurate for real students (no validation study yet).
- That OpenAI, real e-mail delivery, or the app on your laptop were tested by this build (they were not).
- That the wellbeing model predicts burnout or stress in real people.
- That the app is "WCAG compliant" (only an automated audit was done).
- Usability or SUS results (no participants yet).
