### AI integration test against a local stand-in for OpenAI, 2026-10-29 04:38

**18 / 18 checks passed.** This tests MindSync's side only; no real OpenAI call was made.

| Check | Result |
|---|---|
| normal: HTTP 200 and the answer says it came from the AI | PASS |
| normal: two tasks with validated fields | PASS |
| request: strict json_schema, reasoning_effort none, bearer sent, token cap set | PASS |
| privacy: nothing about the account (e-mail, name) was sent to the provider | PASS |
| student text is delimited as data | PASS |
| usage is recorded with tokens and cost (1500 in / 600 out at 0.10/0.50 per M = 0.00045) | PASS |
| injection: a model answer that obeys the hostile text is rejected and the rules answer instead | PASS |
| injection: the assistant answer containing a URL/system prompt is rejected | PASS |
| HTTP 500: falls back to rules, student still gets tasks | PASS |
| non-JSON: falls back to rules, student still gets tasks | PASS |
| refusal: falls back to rules, student still gets tasks | PASS |
| truncated answer: falls back to rules, student still gets tasks | PASS |
| 401 bad key: falls back to rules, student still gets tasks | PASS |
| slow provider: gives up within the total deadline (6 s here) and uses the rules | PASS |
| daily cap: after the cap the provider is no longer called and the rules answer | PASS |
| student switched AI off: provider is not called at all | PASS |
| guest: never reaches the provider by default | PASS |
| the API key never appears in usage, models status or openapi | PASS |

### AI integration test against a local stand-in for OpenAI, 2026-10-29 05:01

**18 / 18 checks passed.** This tests MindSync's side only; no real OpenAI call was made.

| Check | Result |
|---|---|
| normal: HTTP 200 and the answer says it came from the AI | PASS |
| normal: two tasks with validated fields | PASS |
| request: strict json_schema, reasoning_effort none, bearer sent, token cap set | PASS |
| privacy: nothing about the account (e-mail, name) was sent to the provider | PASS |
| student text is delimited as data | PASS |
| usage is recorded with tokens and cost (1500 in / 600 out at 0.10/0.50 per M = 0.00045) | PASS |
| injection: a model answer that obeys the hostile text is rejected and the rules answer instead | PASS |
| injection: the assistant answer containing a URL/system prompt is rejected | PASS |
| HTTP 500: falls back to rules, student still gets tasks | PASS |
| non-JSON: falls back to rules, student still gets tasks | PASS |
| refusal: falls back to rules, student still gets tasks | PASS |
| truncated answer: falls back to rules, student still gets tasks | PASS |
| 401 bad key: falls back to rules, student still gets tasks | PASS |
| slow provider: gives up within the total deadline (6 s here) and uses the rules | PASS |
| daily cap: after the cap the provider is no longer called and the rules answer | PASS |
| student switched AI off: provider is not called at all | PASS |
| guest: never reaches the provider by default | PASS |
| the API key never appears in usage, models status or openapi | PASS |

### AI integration test against a local stand-in for OpenAI, 2026-10-29 05:08

**18 / 18 checks passed.** This tests MindSync's side only; no real OpenAI call was made.

| Check | Result |
|---|---|
| normal: HTTP 200 and the answer says it came from the AI | PASS |
| normal: two tasks with validated fields | PASS |
| request: strict json_schema, reasoning_effort none, bearer sent, token cap set | PASS |
| privacy: nothing about the account (e-mail, name) was sent to the provider | PASS |
| student text is delimited as data | PASS |
| usage is recorded with tokens and cost (1500 in / 600 out at 0.10/0.50 per M = 0.00045) | PASS |
| injection: a model answer that obeys the hostile text is rejected and the rules answer instead | PASS |
| injection: the assistant answer containing a URL/system prompt is rejected | PASS |
| HTTP 500: falls back to rules, student still gets tasks | PASS |
| non-JSON: falls back to rules, student still gets tasks | PASS |
| refusal: falls back to rules, student still gets tasks | PASS |
| truncated answer: falls back to rules, student still gets tasks | PASS |
| 401 bad key: falls back to rules, student still gets tasks | PASS |
| slow provider: gives up within the total deadline (6 s here) and uses the rules | PASS |
| daily cap: after the cap the provider is no longer called and the rules answer | PASS |
| student switched AI off: provider is not called at all | PASS |
| guest: never reaches the provider by default | PASS |
| the API key never appears in usage, models status or openapi | PASS |

