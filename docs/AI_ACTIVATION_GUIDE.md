# How to switch on AI later (free Google Gemini first, any provider later)

**Status today: AI is OFF unless you add your own key.** MindSync works fully without it. No key exists in any file of this project and nothing costs money by itself. This guide is for the day you decide to switch it on. You do not need to change any website code. (For the separate Update 27 AI preview, follow the section "Step by step: the AI preview (Update 27)" at the end.)

## What AI does in MindSync, in one paragraph you can say to your professor

"The student gives MindSync notes. The AI turns them into a learning pack **once**: lessons, quiz questions with answers and explanations, and flashcards. MindSync **saves that pack in PostgreSQL**. After that the student practises as often as they like, and MindSync marks the quizzes and schedules the flashcards itself, with **no further AI request**. AI is only called again when the student adds genuinely new material. The study plan itself (minutes, order, deadlines) is **never** decided by AI; it comes from MindSync's own rules."

## Five steps to switch it on (about 10 minutes)

1. **Get a free key.** Go to Google AI Studio (aistudio.google.com), sign in with your Google account and choose "Get API key". You do not need a credit card for the free tier. Copy the key. Treat it like a password.
2. **Check the model name and your free allowance.** In AI Studio look at the rate-limit page for your project. Google changes model names and free limits from time to time. When this guide was updated (30 October 2026) Google's pricing page listed `gemini-3.5-flash-lite` with free input and output tokens. It is the recommended model for this project: it is free, fast, thinks only a little by default (so the answer is not cut short), and its free daily allowance is larger than the bigger Flash models (reported as about 500 requests a day and 10 a minute per project; AI Studio shows your real numbers). `gemini-3.8-flash` and `gemini-3.6-flash` are also free but reported at only about 20 requests a day, which is too few for several students.
3. **Put the key in `backend\.env` only.** Open `backend\.env` in Notepad (double-click `edit-email-settings.bat` opens it, or open the file by hand). Add or change exactly these lines, with your key after the equals sign and no spaces or quotes:

   ```
   AI_PROVIDER=gemini
   GEMINI_API_KEY=paste-your-key-here
   GEMINI_MODEL=gemini-3.5-flash-lite
   ```

   Never type the key into the website, into a chat, into a report, or into any file that you upload or share. `backend\.env` is excluded from the ZIP and from GitHub on purpose.
4. **Restart the backend** (`restart-backend.bat`).
5. **Test with one tiny request.** Double-click `run-ai-smoke-test.bat`. It asks you to type YES before it sends anything, sends about 30 words, and tells you the provider, model, time taken and tokens used. It never prints your key. Then open **AI Learning Studio**: the grey "AI is not switched on yet" box turns into "AI is switched on (gemini)" and the form unlocks.

To switch it off again, set `AI_PROVIDER=off` and restart the backend. A key on its own never switches AI on: the line `AI_PROVIDER` must say so.

## Important: the free tier, privacy and Google's rules for Europe (checked 30 October 2026)

* **Free plan and your data.** Google's pricing page says content sent on the **free** plan may be used to improve Google's products, and that content on the paid plan is not. Google's "Gemini API Additional Terms" add that for people in the European Economic Area (which includes Denmark), Switzerland and the United Kingdom the paid-plan data terms also apply to the unpaid quota. Rules can change, so read the terms yourself before you rely on this. In every case, tell students not to upload private, confidential or marked university material.
* **Free plan and real users in Europe.** The same terms say that when you make an app available to users in the EEA, Switzerland or the UK, you may use only **Paid Services**. So the free key is fine for **your own testing and for showing the project to your supervisor and examiners**, but it is not meant to be the key behind a live service used by other students in Denmark. If that ever happens, switch to a paid project first (see "Switching to a paid provider" below), and decide that with your supervisor. This is not legal advice. The terms (last updated 28 April 2026 on Google's page) do not say anything special about private demonstrations or university projects, so the safe reading is: your own testing is fine; letting other people use the app is not, unless the project is on a paid plan. The terms also say not to put sensitive, confidential or personal information into the free service, and that the service is for developers, not for consumer use.
* MindSync shows students a notice before they use AI: the Study Planner page says what is sent, and the AI Learning Zone asks for consent before a quiz is made.

## What protects you from surprise costs and misuse (all enforced on the server)

| Safeguard | Default | Where to change it (`backend\.env`) |
|---|---|---|
| Student must tick consent first | always | not changeable |
| Smallest and largest text | 300 and 24,000 characters (about 6,000 words) | `STUDIO_MIN_CHARS`, `STUDIO_MAX_CHARS` |
| Largest upload | 5 MB, PDFs up to 80 pages | `STUDIO_MAX_UPLOAD_MB`, `STUDIO_MAX_PDF_PAGES` |
| The same text is never made twice | always (duplicate guard on a fingerprint of the text; it opens the saved pack instead) | not changeable |
| One generation at a time per student, 45 seconds between attempts | 45 s | `STUDIO_COOLDOWN_SECONDS` |
| Attempts per student (failed ones count too) | 5 a day, 20 a month | `STUDIO_USER_DAILY_ATTEMPTS`, `STUDIO_USER_MONTHLY_ATTEMPTS` |
| All students together | 40 a day (protects a free daily quota) | `STUDIO_GLOBAL_DAILY_ATTEMPTS` |
| Saved packs per student | 30 | `STUDIO_MAX_PACKS_PER_USER` |
| Time limit for the one AI request | 75 seconds, then it is abandoned | `STUDIO_TIMEOUT_SECONDS` |
| Output size limit | 9,000 tokens | `STUDIO_MAX_OUTPUT_TOKENS` |
| Monthly money budget (only matters on a paid plan) | 5 US dollars | `AI_MONTHLY_BUDGET_USD` |
| Free quota used up (HTTP 429 from Google) | MindSync stops, tells the student to try later, and does **not** retry | automatic |
| Keys | only in `backend\.env`, never sent to the browser, never in the export, never in logs | automatic |

Practising (quizzes, flashcards, progress, revision reminders) never calls AI, so it has no limits and no cost.

## What MindSync does with what the AI sends back

The AI's answer is treated as untrusted. MindSync checks every item before saving it: it must be plain text, links and markup are removed or the item is dropped, multiple-choice questions need four different options and a valid right answer, and the question must share real words with the student's own notes (so invented material is dropped). A pack needs at least 2 lessons, 6 questions and 6 flashcards or it is refused and nothing is shown as if it worked. The student's notes are sent as data inside a fixed instruction, and the instruction tells the model to ignore instructions inside the notes (prompt-injection defence).

## Switching to a paid provider later (no website changes)

* **Paid Gemini:** keep `AI_PROVIDER=gemini`, enable billing in your Google AI Studio project, then fill in the two price lines from Google's pricing page so the budget limit is accurate: `GEMINI_PRICE_IN_PER_M=` and `GEMINI_PRICE_OUT_PER_M=` (US dollars per million tokens).
* **OpenAI:** set `AI_PROVIDER=openai`, `OPENAI_API_KEY=...`, `OPENAI_MODEL=...` (check the current model name and price first) and the `AI_PRICE_IN_PER_M` / `AI_PRICE_OUT_PER_M` lines.
* **Either, whichever has a key:** `AI_PROVIDER=auto` (Gemini first, then OpenAI).
* **Another company:** add one small class in `backend/app/ai/provider.py` with the same `complete_json` method. Everything else (limits, saving, quizzes, pages) stays the same, because the rest of MindSync only talks to that one method.

## Future premium plans (prepared, not built)

`backend/app/studio/pack.py` has `tier_of()` and `limits_for()`. Today every student is on the free tier. A later premium tier would only need `tier_of()` to return "premium" for paying students, which multiplies the allowances above by `STUDIO_PREMIUM_MULTIPLIER` (default 5). **There is no payment, subscription or card code in MindSync, on purpose.**

## Honest limits of what has been tested

* Until you run the real test below, the Gemini and OpenAI code was tested **only against pretend servers** (mock responses, including errors, quota, timeouts, refusals and hostile output). It has **not** been tested against the real Gemini service, because no key exists yet and nothing paid or live was to be used. The first real test is `run-ai-smoke-test.bat`, and then making one real pack. Expect to adjust the model name if Google has renamed it.
* The quality of a real pack (how good the questions are) is unknown until you try it. MindSync can reject bad output, but it cannot make a weak model write good questions.
* Do not claim in the report that AI is active until you have run the smoke test and made a real pack.


## What is sent to the AI service, and what is not (updated 30 October 2026)

* **Study Planner:** the subject, the topic, the target date, today's date, the text in the notes box, and plain limits (most minutes per day, most minutes per task). **The mood and stress answers are never sent, not even as words.** MindSync turns them into the limits itself and checks the AI's plan against the same limits afterwards. If a student types "I feel stressed" in the notes box, that sentence is the student's own text and is sent. The Study Planner page now shows a short notice that says exactly this (added in Update 27 with the owner's approval).
* **AI Learning Zone:** the text of the chosen document (up to 24,000 characters). Nothing else. Please do not use private or sensitive material on the free plan.
* **Never sent:** name, e-mail address, password, login token, account data, other plans, notes or documents.

## Expected cost and how to keep it at zero

* **Free Gemini plan: 0 US dollars.** No card is needed. If the daily free allowance is used up, Google answers "429"; MindSync stops, does not retry, and uses the built-in planner (or tells the student the quiz is unavailable until tomorrow).
* **If you ever enable billing** for the project, the paid price of `gemini-3.5-flash-lite` on Google's pricing page was 0.30 dollars per million input tokens and 2.50 dollars per million output tokens (30 October 2026). Rough worst cases (arithmetic, not a measurement): one study plan about 0.004 dollars; one quiz from a very long document about 0.024 dollars. With the built-in limits (5 quizzes per student per day, 40 quizzes per day for everyone, 40 AI calls per student per day, 5 dollars a month budget once the two price lines in `backend\.env` are filled in) the most MindSync can spend is about 1 dollar a day, and the monthly budget stops it at 5 dollars.
* **Two ways to be completely safe:** (1) never enable billing in Google AI Studio, then Google cannot charge you at all; (2) set `AI_PROVIDER=off`, which stops every AI call at once.
* Practising a quiz again (retry) and marking it never calls the AI, so retries cost nothing.

## Step by step: the AI preview (Update 27)

The AI preview is a separate copy (folder `MindSync_preview_ai`, website on port 5181, backend on port 8101, its own SQLite database). It cannot touch your real MindSync, PostgreSQL or the first preview. The files are `MindSync_update27_ai.zip`, `PREVIEW-MINDSYNC-27-AI.bat` and `ADD-OR-TEST-GEMINI-KEY.bat`; put all three in your Downloads folder.

1. Double-click `PREVIEW-MINDSYNC-27-AI.bat`. It checks the ZIP fingerprint, builds the preview, starts it with AI **off** (no key yet) and opens http://localhost:5181.
2. Create your free key at aistudio.google.com/apikey (sign in, "Create API key", choose or create a project; **do not add a card and do not enable billing**).
3. Close the two black windows. Double-click `ADD-OR-TEST-GEMINI-KEY.bat` and press 1. Notepad opens the preview's settings file. On the last line type your key right after `GEMINI_API_KEY=` (no spaces, no quote marks), press Ctrl+S, close Notepad. Never paste the key anywhere else.
4. Double-click `ADD-OR-TEST-GEMINI-KEY.bat`, press 2, and type YES when asked. This sends ONE tiny question and prints OK, the model and the time. It never prints the key.
5. Double-click `PREVIEW-MINDSYNC-27-AI.bat` again. It says "AI KEY: found (hidden)". Make a study plan: the page says whether the AI or the built-in planner made it. Upload a short, non-private document in the AI Learning Zone and make one quiz.
6. To stop: close the two black windows. To switch the AI off again: delete everything after `GEMINI_API_KEY=` in the same file.
