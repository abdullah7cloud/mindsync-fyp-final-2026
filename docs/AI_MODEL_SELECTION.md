# AI model selection (as of 29 October 2026)

## What the language model is used for, and what it is not

MindSync is a hybrid system. The language model only does language work: it turns a student's free-text description into structured task fields, asks clarifying questions, explains a plan in plain words, and writes the weekly review wording. It never calculates a schedule, never decides feasibility and never changes stored data by itself. Those jobs belong to deterministic code (the scheduler, the ranking rules, the trained wellbeing model, the history calibration) and every model answer passes a validation layer before the student sees it.

The language model is an externally pretrained model. I did not train it. The wellbeing model and the task-fit scoring are the locally trained parts.

## Options compared

Prices are from the providers' own pages, fetched on 29 October 2026, in US dollars per million tokens (input / output), standard tier.

| Option | Input / output | Structured output | Privacy note | Verdict |
|---|---|---|---|---|
| OpenAI gpt-6-luna | 0.10 / 0.50 | Yes, strict JSON schema on Chat Completions and Responses | API data is not used for training by default (check the account's data controls) | Chosen as the default |
| OpenAI gpt-6.1-terra | 1.00 / 5.00 | Yes | Same | Better quality, ten times the price; keep as an env option |
| Google Gemini 3.1 Flash-Lite | 0.25 / 1.50 | Yes | The free tier may use content to improve Google products, so it is unsuitable for student text | Alternative, not implemented |
| Google Gemini 3.5 Flash-Lite | 0.30 / 2.50 | Yes | Same | Alternative, not implemented |
| GPT-4o mini and Gemini 2.5 Flash (named in the original project brief) | not listed | n/a | n/a | Not on the current pricing pages, so they cannot be recommended as a current choice |

Sources: OpenAI pricing page (https://developers.openai.com/api/docs/pricing), OpenAI Structured Outputs guide (https://developers.openai.com/api/docs/guides/structured-outputs), Google Gemini API pricing page (checked earlier the same day).

## Decision

Default model: `gpt-6-luna`, called through the Chat Completions endpoint with a strict `json_schema` response format. The model name is an environment setting, so a stronger or different model can be switched on without code changes. A mock provider and a rule-based local fallback exist, so the application works with no key at all and every test runs offline.

## Request settings (checked against OpenAI's pages on 29 October 2026)

OpenAI's model page lists `gpt-6-luna` for Chat Completions and Structured Outputs, with reasoning effort values none, low, medium (default), high, xhigh and max. At the default the model reasons first, which adds billed output tokens and delay and can use up the output cap. MindSync only extracts task fields and words explanations, so it sends `reasoning_effort: "none"` (setting `AI_REASONING_EFFORT`, blank = send nothing). It sends no `temperature`, `top_p` or penalties. Output is capped with `max_completion_tokens` (900) and the whole call, retries included, gives up after 10 seconds (`AI_TOTAL_DEADLINE_SECONDS`; each attempt 8 s, `AI_TIMEOUT_SECONDS`), so a slow provider delays a screen by at most 10 s before the rules answer; an answer cut off by the cap is discarded. Not verified: the pages did not say whether reasoning tokens count against `max_completion_tokens`, so this is handled by asking for none and by discarding truncated answers. A community report describes occasional extra message items from this model in the Responses API; MindSync uses Chat Completions, where that report does not apply, and any unparsable answer falls back to the rules anyway.

## Cost estimate (arithmetic, not a measurement)

A typical call sends about 1,500 input tokens and returns about 600 output tokens: 1,500 x 0.10 / 1,000,000 + 600 x 0.50 / 1,000,000 = 0.00015 + 0.0003 = about 0.00045 dollars, so roughly 2,200 calls per dollar. With the built-in cap of 40 AI calls per student per day, one very active student would cost at most about 0.018 dollars per day. A global monthly cap (default 5 dollars, set in the environment) stops all AI calls when reached. Real usage is recorded in the `ai_usage` table so the true cost can be read later.

## Safeguards

The key lives only in `backend/.env`. It is never sent to the browser. No purchase, subscription or billing change is made by the code or by me; the student creates the key and should set a spending limit in the OpenAI account. Only the task text the student typed and a few numbers (energy, daily hours, deadline dates) are sent. No e-mail address, name, password or wellbeing answers are sent.
