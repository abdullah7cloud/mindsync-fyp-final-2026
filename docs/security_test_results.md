### Live security test, 2026-10-05 16:59 (http://127.0.0.1:8000)

**35 / 35 checks passed**

| OWASP category | Check | Result | Detail |
|---|---|---|---|
| A03 Injection | SQL injection in login e-mail rejected (no 200/500) | PASS | HTTP 422 |
| A03 Injection | SQL injection in login password does not log in | PASS | HTTP 401 |
| A03 Injection | SQL in task title stored as plain text, tables intact (parameterised queries) | PASS | HTTP 201/200 |
| A03 Injection | XSS payload returned as inert JSON text (not HTML) with nosniff | PASS | application/json |
| A01 Broken Access Control | User B cannot read user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot edit user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot delete user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User A's task unchanged after B's attempts | PASS |  |
| A01 Broken Access Control | /tasks refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /recommend refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /energy-checkins refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /auth/me refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | Mass assignment: client cannot set owner_id/id | PASS | HTTP 201 |
| A02 Cryptographic Failures | API never returns password or password_hash | PASS |  |
| A07 Auth Failures | Tampered JWT signature rejected | PASS | HTTP 401 |
| A07 Auth Failures | JWT with alg=none rejected | PASS | HTTP 401 |
| A07 Auth Failures | Duplicate registration gives a generic error | PASS | {"detail":"Registration failed"} |
| A07 Auth Failures | Weak/short password rejected (min 8) | PASS | HTTP 422 |
| A07 Auth Failures | Brute-force login locked out with HTTP 429 after repeated failures | PASS | codes [401, 401, 401, 401, 401, 429, 429] |
| A07 Auth Failures | Even the correct password is refused during lock-out | PASS | HTTP 429 |
| A04 Insecure Design | Validation rejects title 201 chars | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 99 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 0 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects empty title | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects bad deadline | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects description 2001 chars | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 0 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 6 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level -1 rejected | PASS | HTTP 422 |
| A04 Insecure Design | PATCH with null title rejected (no server error) | PASS | HTTP 422 |
| A04 Insecure Design | Malformed JSON gives 4xx, not a crash | PASS | HTTP 422 |
| A05 Misconfiguration | CORS refuses unknown origin | PASS |  |
| A05 Misconfiguration | Security headers present | PASS | {'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'no-referrer', 'cache-control': 'no-store'} |
| A05 Misconfiguration | Bad ID gives clean 422 without stack trace | PASS | HTTP 422 |
| LLM01 Prompt Injection | Hostile task title does not break /recommend; explanation source is valid | PASS | HTTP 200 |

### Live security test, 2026-10-05 17:14 (http://127.0.0.1:8000)

**42 / 42 checks passed**

| OWASP category | Check | Result | Detail |
|---|---|---|---|
| A03 Injection | SQL injection in login e-mail rejected (no 200/500) | PASS | HTTP 422 |
| A03 Injection | SQL injection in login password does not log in | PASS | HTTP 401 |
| A03 Injection | SQL in task title stored as plain text, tables intact (parameterised queries) | PASS | HTTP 201/200 |
| A03 Injection | XSS payload returned as inert JSON text (not HTML) with nosniff | PASS | application/json |
| A01 Broken Access Control | User B cannot read user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot edit user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot delete user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User A's task unchanged after B's attempts | PASS |  |
| A01 Broken Access Control | /tasks refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /recommend refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /energy-checkins refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /auth/me refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | Mass assignment: client cannot set owner_id/id | PASS | HTTP 201 |
| A02 Cryptographic Failures | API never returns password or password_hash | PASS |  |
| A07 Auth Failures | Tampered JWT signature rejected | PASS | HTTP 401 |
| A07 Auth Failures | JWT with alg=none rejected | PASS | HTTP 401 |
| A07 Auth Failures | Duplicate registration gives a generic error | PASS | {"detail":"Registration failed"} |
| A07 Auth Failures | Weak/short password rejected (min 8) | PASS | HTTP 422 |
| A07 Auth Failures | Brute-force login locked out with HTTP 429 after repeated failures | PASS | codes [401, 401, 401, 401, 401, 429, 429] |
| A07 Auth Failures | Even the correct password is refused during lock-out | PASS | HTTP 429 |
| A04 Insecure Design | Validation rejects title 201 chars | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 99 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 0 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects empty title | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects bad deadline | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects description 2001 chars | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 0 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 6 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level -1 rejected | PASS | HTTP 422 |
| A04 Insecure Design | PATCH with null title rejected (no server error) | PASS | HTTP 422 |
| A04 Insecure Design | Malformed JSON gives 4xx, not a crash | PASS | HTTP 422 |
| A05 Misconfiguration | CORS refuses unknown origin | PASS |  |
| A05 Misconfiguration | Security headers present | PASS | {'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'no-referrer', 'cache-control': 'no-store'} |
| A05 Misconfiguration | Bad ID gives clean 422 without stack trace | PASS | HTTP 422 |
| LLM01 Prompt Injection | Hostile task title does not break /recommend; explanation source is valid | PASS | HTTP 200 |
| LLM01 Prompt Injection | AI status endpoint works for logged-in user | PASS | HTTP 200 |
| LLM01 Prompt Injection | Hostile AI-coach message gets a safe reply with no link | PASS | HTTP 200 |
| A04 Insecure Design | AI-coach message over 500 chars rejected | PASS | HTTP 422 |
| A04 Insecure Design | Crisis wording gets the fixed supportive safety reply (no model call) | PASS | HTTP 200 |
| A01 Broken Access Control | User B cannot use AI breakdown on user A's task | PASS | HTTP 404 |
| A04 Insecure Design | AI breakdown returns 3-7 valid steps for own task | PASS | HTTP 200 |
| A01 Broken Access Control | AI coach refuses requests with no token | PASS | HTTP 401 |

### Live security test, 2026-10-21 06:35 (http://127.0.0.1:8000)

**46 / 46 checks passed**

| OWASP category | Check | Result | Detail |
|---|---|---|---|
| A03 Injection | SQL injection in login e-mail rejected (no 200/500) | PASS | HTTP 422 |
| A03 Injection | SQL injection in login password does not log in | PASS | HTTP 401 |
| A03 Injection | SQL in task title stored as plain text, tables intact (parameterised queries) | PASS | HTTP 201/200 |
| A03 Injection | XSS payload returned as inert JSON text (not HTML) with nosniff | PASS | application/json |
| A01 Broken Access Control | User B cannot read user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot edit user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot delete user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User A's task unchanged after B's attempts | PASS |  |
| A01 Broken Access Control | /tasks refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /recommend refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /energy-checkins refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /auth/me refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | Mass assignment: client cannot set owner_id/id | PASS | HTTP 201 |
| A02 Cryptographic Failures | API never returns password or password_hash | PASS |  |
| A07 Auth Failures | Tampered JWT signature rejected | PASS | HTTP 401 |
| A07 Auth Failures | JWT with alg=none rejected | PASS | HTTP 401 |
| A07 Auth Failures | Duplicate registration gets a clear 409 message (rate-limited) | PASS | {"detail":"An account with this email already exists. Please log in in |
| A07 Auth Failures | Password without a number is rejected with a readable reason | PASS | HTTP 422 |
| A07 Auth Failures | Weak/short password rejected (min 8) | PASS | HTTP 422 |
| A01 Broken Access Control | Email-alert settings need a login | PASS | HTTP 401 |
| A01 Broken Access Control | Deadline check-now needs a login | PASS | HTTP 401 |
| A03 Injection | Alert settings reject a non-boolean value | PASS | HTTP 422 |
| A01 Broken Access Control | Wellbeing assessment needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Wellbeing history needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Study planner (account route) needs a login | PASS | HTTP 401 |
| A03 Injection | Guest study planner rejects oversize / out-of-range input | PASS | HTTP 422 |
| A03 Injection | Planner returns data only (no HTML executed), topic text is just data | PASS | HTTP 200 |
| A07 Auth Failures | Brute-force login locked out with HTTP 429 after repeated failures | PASS | codes [401, 401, 401, 401, 401, 429, 429] |
| A07 Auth Failures | Even the correct password is refused during lock-out | PASS | HTTP 429 |
| A04 Insecure Design | Validation rejects title 201 chars | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 99 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 0 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects empty title | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects bad deadline | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects description 2001 chars | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 0 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 6 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level -1 rejected | PASS | HTTP 422 |
| A04 Insecure Design | PATCH with null title rejected (no server error) | PASS | HTTP 422 |
| A04 Insecure Design | Malformed JSON gives 4xx, not a crash | PASS | HTTP 422 |
| A05 Misconfiguration | CORS refuses unknown origin | PASS |  |
| A05 Misconfiguration | Security headers present | PASS | {'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'no-referrer', 'cache-control': 'no-store'} |
| A05 Misconfiguration | Bad ID gives clean 422 without stack trace | PASS | HTTP 422 |
| A03 Injection | Hostile task title does not break /recommend (explanation is built locally) | PASS | HTTP 200 |
| A04 Insecure Design | Models status reports that no external AI is used | PASS | HTTP 200 |
| A05 Misconfiguration | Removed cloud-AI routes no longer exist (404) | PASS | HTTP 404 |

### Live security test, 2026-10-21 15:39 (http://127.0.0.1:8000)

**46 / 46 checks passed**

| OWASP category | Check | Result | Detail |
|---|---|---|---|
| A03 Injection | SQL injection in login e-mail rejected (no 200/500) | PASS | HTTP 422 |
| A03 Injection | SQL injection in login password does not log in | PASS | HTTP 401 |
| A03 Injection | SQL in task title stored as plain text, tables intact (parameterised queries) | PASS | HTTP 201/200 |
| A03 Injection | XSS payload returned as inert JSON text (not HTML) with nosniff | PASS | application/json |
| A01 Broken Access Control | User B cannot read user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot edit user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot delete user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User A's task unchanged after B's attempts | PASS |  |
| A01 Broken Access Control | /tasks refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /recommend refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /energy-checkins refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /auth/me refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | Mass assignment: client cannot set owner_id/id | PASS | HTTP 201 |
| A02 Cryptographic Failures | API never returns password or password_hash | PASS |  |
| A07 Auth Failures | Tampered JWT signature rejected | PASS | HTTP 401 |
| A07 Auth Failures | JWT with alg=none rejected | PASS | HTTP 401 |
| A07 Auth Failures | Duplicate registration gets a clear 409 message (rate-limited) | PASS | {"detail":"An account with this email already exists. Please log in in |
| A07 Auth Failures | Password without a number is rejected with a readable reason | PASS | HTTP 422 |
| A07 Auth Failures | Weak/short password rejected (min 8) | PASS | HTTP 422 |
| A01 Broken Access Control | Email-alert settings need a login | PASS | HTTP 401 |
| A01 Broken Access Control | Deadline check-now needs a login | PASS | HTTP 401 |
| A03 Injection | Alert settings reject a non-boolean value | PASS | HTTP 422 |
| A01 Broken Access Control | Wellbeing assessment needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Wellbeing history needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Study planner (account route) needs a login | PASS | HTTP 401 |
| A03 Injection | Guest study planner rejects oversize / out-of-range input | PASS | HTTP 422 |
| A03 Injection | Planner returns data only (no HTML executed), topic text is just data | PASS | HTTP 200 |
| A07 Auth Failures | Brute-force login locked out with HTTP 429 after repeated failures | PASS | codes [401, 401, 401, 401, 401, 429, 429] |
| A07 Auth Failures | Even the correct password is refused during lock-out | PASS | HTTP 429 |
| A04 Insecure Design | Validation rejects title 201 chars | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 99 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 0 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects empty title | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects bad deadline | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects description 2001 chars | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 0 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 6 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level -1 rejected | PASS | HTTP 422 |
| A04 Insecure Design | PATCH with null title rejected (no server error) | PASS | HTTP 422 |
| A04 Insecure Design | Malformed JSON gives 4xx, not a crash | PASS | HTTP 422 |
| A05 Misconfiguration | CORS refuses unknown origin | PASS |  |
| A05 Misconfiguration | Security headers present | PASS | {'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'no-referrer', 'cache-control': 'no-store'} |
| A05 Misconfiguration | Bad ID gives clean 422 without stack trace | PASS | HTTP 422 |
| A03 Injection | Hostile task title does not break /recommend (explanation is built locally) | PASS | HTTP 200 |
| A04 Insecure Design | Models status reports that no external AI is used | PASS | HTTP 200 |
| A05 Misconfiguration | Removed cloud-AI routes no longer exist (404) | PASS | HTTP 404 |

### Live security test, 2026-10-21 21:01 (http://127.0.0.1:8000)

**51 / 51 checks passed**

| OWASP category | Check | Result | Detail |
|---|---|---|---|
| A03 Injection | SQL injection in login e-mail rejected (no 200/500) | PASS | HTTP 422 |
| A03 Injection | SQL injection in login password does not log in | PASS | HTTP 401 |
| A03 Injection | SQL in task title stored as plain text, tables intact (parameterised queries) | PASS | HTTP 201/200 |
| A03 Injection | XSS payload returned as inert JSON text (not HTML) with nosniff | PASS | application/json |
| A01 Broken Access Control | User B cannot read user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot edit user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot delete user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User A's task unchanged after B's attempts | PASS |  |
| A01 Broken Access Control | /tasks refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /recommend refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /energy-checkins refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /auth/me refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | Mass assignment: client cannot set owner_id/id | PASS | HTTP 201 |
| A02 Cryptographic Failures | API never returns password or password_hash | PASS |  |
| A07 Auth Failures | Tampered JWT signature rejected | PASS | HTTP 401 |
| A07 Auth Failures | JWT with alg=none rejected | PASS | HTTP 401 |
| A07 Auth Failures | Duplicate registration gets a clear 409 message (rate-limited) | PASS | {"detail":"An account with this email already exists. Please log in in |
| A07 Auth Failures | Password without a number is rejected with a readable reason | PASS | HTTP 422 |
| A07 Auth Failures | Weak/short password rejected (min 8) | PASS | HTTP 422 |
| A01 Broken Access Control | Email-alert settings need a login | PASS | HTTP 401 |
| A01 Broken Access Control | Deadline check-now needs a login | PASS | HTTP 401 |
| A03 Injection | Alert settings reject a non-boolean value | PASS | HTTP 422 |
| A01 Broken Access Control | Wellbeing assessment needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Wellbeing history needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Study planner (account route) needs a login | PASS | HTTP 401 |
| A03 Injection | Guest study planner rejects oversize / out-of-range input | PASS | HTTP 422 |
| A03 Injection | Planner returns data only (no HTML executed), topic text is just data | PASS | HTTP 200 |
| A07 Auth Failures | Brute-force login locked out with HTTP 429 after repeated failures | PASS | codes [401, 401, 401, 401, 401, 429, 429] |
| A07 Auth Failures | Even the correct password is refused during lock-out | PASS | HTTP 429 |
| A04 Insecure Design | Validation rejects title 201 chars | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 99 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 0 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects empty title | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects bad deadline | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects description 2001 chars | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 0 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 6 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level -1 rejected | PASS | HTTP 422 |
| A04 Insecure Design | PATCH with null title rejected (no server error) | PASS | HTTP 422 |
| A04 Insecure Design | Malformed JSON gives 4xx, not a crash | PASS | HTTP 422 |
| A05 Misconfiguration | CORS refuses unknown origin | PASS |  |
| A05 Misconfiguration | Security headers present | PASS | {'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'no-referrer', 'cache-control': 'no-store'} |
| A05 Misconfiguration | Bad ID gives clean 422 without stack trace | PASS | HTTP 422 |
| A03 Injection | Hostile task title does not break /recommend (explanation is built locally) | PASS | HTTP 200 |
| A04 Insecure Design | Models status reports that no external AI is used | PASS | HTTP 200 |
| A05 Misconfiguration | Removed cloud-AI routes no longer exist (404) | PASS | HTTP 404 |
| A04 Insecure Design | Valid wellbeing answers give a label and probabilities | PASS | HTTP 200 |
| A03 Injection | Wellbeing rejects unknown answer keys | PASS | HTTP 422 |
| A04 Insecure Design | Wellbeing rejects out-of-range numbers | PASS | HTTP 422 |
| A03 Injection | Wellbeing rejects text where a number is required | PASS | HTTP 422 |
| A01 Broken Access Control | User B does not see user A's wellbeing history | PASS | HTTP 200 |

### Live security test, 2026-10-22 01:47 (http://127.0.0.1:8000)

**60 / 60 checks passed**

| OWASP category | Check | Result | Detail |
|---|---|---|---|
| A03 Injection | SQL injection in login e-mail rejected (no 200/500) | PASS | HTTP 422 |
| A03 Injection | SQL injection in login password does not log in | PASS | HTTP 401 |
| A03 Injection | SQL in task title stored as plain text, tables intact (parameterised queries) | PASS | HTTP 201/200 |
| A03 Injection | XSS payload returned as inert JSON text (not HTML) with nosniff | PASS | application/json |
| A01 Broken Access Control | User B cannot read user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot edit user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot delete user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User A's task unchanged after B's attempts | PASS |  |
| A01 Broken Access Control | /tasks refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /recommend refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /energy-checkins refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /auth/me refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | Mass assignment: client cannot set owner_id/id | PASS | HTTP 201 |
| A02 Cryptographic Failures | API never returns password or password_hash | PASS |  |
| A07 Auth Failures | Tampered JWT signature rejected | PASS | HTTP 401 |
| A07 Auth Failures | JWT with alg=none rejected | PASS | HTTP 401 |
| A07 Auth Failures | Duplicate registration gets a clear 409 message (rate-limited) | PASS | {"detail":"An account with this email already exists. Please log in in |
| A07 Auth Failures | Password without a number is rejected with a readable reason | PASS | HTTP 422 |
| A07 Auth Failures | Weak/short password rejected (min 8) | PASS | HTTP 422 |
| A01 Broken Access Control | Email-alert settings need a login | PASS | HTTP 401 |
| A01 Broken Access Control | Deadline check-now needs a login | PASS | HTTP 401 |
| A03 Injection | Alert settings reject a non-boolean value | PASS | HTTP 422 |
| A01 Broken Access Control | Wellbeing assessment needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Wellbeing history needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Study planner (account route) needs a login | PASS | HTTP 401 |
| A03 Injection | Guest study planner rejects oversize / out-of-range input | PASS | HTTP 422 |
| A03 Injection | Planner returns data only (no HTML executed), topic text is just data | PASS | HTTP 200 |
| A07 Auth Failures | Brute-force login locked out with HTTP 429 after repeated failures | PASS | codes [401, 401, 401, 401, 401, 429, 429] |
| A07 Auth Failures | Even the correct password is refused during lock-out | PASS | HTTP 429 |
| A07 Auth Failures | Forgot-password gives the same answer for a registered and an unknown address (no account enumeration) | PASS | HTTP 200/200 |
| A02 Cryptographic Failures | The reset secret is never returned by the API (only e-mailed) | PASS |  |
| A03 Injection | SQL injection in the forgot-password e-mail field is rejected | PASS | HTTP 422 |
| A07 Auth Failures | A made-up reset token is refused | PASS | HTTP 400 |
| A07 Auth Failures | A too-short reset token is rejected by validation | PASS | HTTP 422 |
| A07 Auth Failures | A weak new password is rejected on reset | PASS | HTTP 422 |
| A04 Insecure Design | Repeated forgot-password requests for one address are rate limited (HTTP 429) | PASS | codes [200, 200, 200, 200, 200, 429, 429] |
| A01 Broken Access Control | Changing the password needs a login | PASS | HTTP 401 |
| A07 Auth Failures | Changing the password with a wrong current password is refused | PASS | HTTP 403 |
| A04 Insecure Design | Validation rejects title 201 chars | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 99 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 0 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects empty title | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects bad deadline | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects description 2001 chars | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 0 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 6 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level -1 rejected | PASS | HTTP 422 |
| A04 Insecure Design | PATCH with null title rejected (no server error) | PASS | HTTP 422 |
| A04 Insecure Design | Malformed JSON gives 4xx, not a crash | PASS | HTTP 422 |
| A05 Misconfiguration | CORS refuses unknown origin | PASS |  |
| A05 Misconfiguration | Security headers present | PASS | {'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'no-referrer', 'cache-control': 'no-store'} |
| A05 Misconfiguration | Bad ID gives clean 422 without stack trace | PASS | HTTP 422 |
| A03 Injection | Hostile task title does not break /recommend (explanation is built locally) | PASS | HTTP 200 |
| A04 Insecure Design | Models status reports that no external AI is used | PASS | HTTP 200 |
| A05 Misconfiguration | Removed cloud-AI routes no longer exist (404) | PASS | HTTP 404 |
| A04 Insecure Design | Valid wellbeing answers give a label and probabilities | PASS | HTTP 200 |
| A03 Injection | Wellbeing rejects unknown answer keys | PASS | HTTP 422 |
| A04 Insecure Design | Wellbeing rejects out-of-range numbers | PASS | HTTP 422 |
| A03 Injection | Wellbeing rejects text where a number is required | PASS | HTTP 422 |
| A01 Broken Access Control | User B does not see user A's wellbeing history | PASS | HTTP 200 |

### Live security test, 2026-10-29 04:18 (http://127.0.0.1:8000)

**95 / 95 checks passed**

| OWASP category | Check | Result | Detail |
|---|---|---|---|
| A03 Injection | SQL injection in login e-mail rejected (no 200/500) | PASS | HTTP 422 |
| A03 Injection | SQL injection in login password does not log in | PASS | HTTP 401 |
| A03 Injection | SQL in task title stored as plain text, tables intact (parameterised queries) | PASS | HTTP 201/200 |
| A03 Injection | XSS payload returned as inert JSON text (not HTML) with nosniff | PASS | application/json |
| A01 Broken Access Control | User B cannot read user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot edit user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot delete user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User A's task unchanged after B's attempts | PASS |  |
| A01 Broken Access Control | /tasks refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /recommend refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /energy-checkins refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /auth/me refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | Mass assignment: client cannot set owner_id/id | PASS | HTTP 201 |
| A02 Cryptographic Failures | API never returns password or password_hash | PASS |  |
| A07 Auth Failures | Tampered JWT signature rejected | PASS | HTTP 401 |
| A07 Auth Failures | JWT with alg=none rejected | PASS | HTTP 401 |
| A07 Auth Failures | Duplicate registration gets a clear 409 message (rate-limited) | PASS | {"detail":"An account with this email already exists. Please log in in |
| A07 Auth Failures | Password without a number is rejected with a readable reason | PASS | HTTP 422 |
| A07 Auth Failures | Weak/short password rejected (min 8) | PASS | HTTP 422 |
| A01 Broken Access Control | Email-alert settings need a login | PASS | HTTP 401 |
| A01 Broken Access Control | Deadline check-now needs a login | PASS | HTTP 401 |
| A03 Injection | Alert settings reject a non-boolean value | PASS | HTTP 422 |
| A01 Broken Access Control | Wellbeing assessment needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Wellbeing history needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Study planner (account route) needs a login | PASS | HTTP 401 |
| A03 Injection | Guest study planner rejects oversize / out-of-range input | PASS | HTTP 422 |
| A03 Injection | Planner returns data only (no HTML executed), topic text is just data | PASS | HTTP 200 |
| A07 Auth Failures | Brute-force login locked out with HTTP 429 after repeated failures | PASS | codes [401, 401, 401, 401, 401, 429, 429] |
| A07 Auth Failures | Even the correct password is refused during lock-out | PASS | HTTP 429 |
| A07 Auth Failures | Forgot-password gives the same answer for a registered and an unknown address (no account enumeration) | PASS | HTTP 200/200 |
| A02 Cryptographic Failures | The reset secret is never returned by the API (only e-mailed) | PASS |  |
| A03 Injection | SQL injection in the forgot-password e-mail field is rejected | PASS | HTTP 422 |
| A07 Auth Failures | A made-up reset token is refused | PASS | HTTP 400 |
| A07 Auth Failures | A too-short reset token is rejected by validation | PASS | HTTP 422 |
| A07 Auth Failures | A weak new password is rejected on reset | PASS | HTTP 422 |
| A04 Insecure Design | Repeated forgot-password requests for one address are rate limited (HTTP 429) | PASS | codes [200, 200, 200, 200, 200, 429, 429] |
| A01 Broken Access Control | Changing the password needs a login | PASS | HTTP 401 |
| A07 Auth Failures | Changing the password with a wrong current password is refused | PASS | HTTP 403 |
| A04 Insecure Design | Validation rejects title 201 chars | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 99 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 0 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects empty title | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects bad deadline | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects description 2001 chars | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 0 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 6 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level -1 rejected | PASS | HTTP 422 |
| A04 Insecure Design | PATCH with null title rejected (no server error) | PASS | HTTP 422 |
| A04 Insecure Design | Malformed JSON gives 4xx, not a crash | PASS | HTTP 422 |
| A05 Misconfiguration | CORS refuses unknown origin | PASS |  |
| A05 Misconfiguration | Security headers present | PASS | {'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'no-referrer', 'cache-control': 'no-store'} |
| A05 Misconfiguration | Bad ID gives clean 422 without stack trace | PASS | HTTP 422 |
| A03 Injection | Hostile task title does not break /recommend (explanation is built locally) | PASS | HTTP 200 |
| A04 Insecure Design | Models status states honestly whether an external language model is configured | PASS | HTTP 200 |
| A05 Misconfiguration | Removed cloud-AI routes no longer exist (404) | PASS | HTTP 404 |
| A04 Insecure Design | Valid wellbeing answers give a label and probabilities | PASS | HTTP 200 |
| A03 Injection | Wellbeing rejects unknown answer keys | PASS | HTTP 422 |
| A04 Insecure Design | Wellbeing rejects out-of-range numbers | PASS | HTTP 422 |
| A03 Injection | Wellbeing rejects text where a number is required | PASS | HTTP 422 |
| A01 Broken Access Control | User B does not see user A's wellbeing history | PASS | HTTP 200 |
| A01 Broken Access Control | GET /assist/state needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/understand needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/evaluate needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/accept needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/replan/apply needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/session needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/explain needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/ask needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/dashboard needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/review needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/usage needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/reminders needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /settings needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | PUT /settings needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /profile needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | PUT /profile needs a login | PASS | HTTP 401 |
| A04 Insecure Design | Settings reject an unknown field | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a 3-day study-time value out of range | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a made-up time zone | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a non-boolean AI switch | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a reminder lead time that is not offered | PASS | HTTP 422 |
| A04 Insecure Design | Profile rejects an oversize free-text field | PASS | HTTP 422 |
| A01 Broken Access Control | Profile rejects unknown fields (no mass assignment) | PASS | HTTP 422 |
| A01 Broken Access Control | User A cannot log a study session against user B's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User A cannot change the priority of user B's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B's planner state never contains user A's task titles | PASS |  |
| A03 Injection | Planner text with instructions and a script tag gives clean JSON and no leaked prompt | PASS | HTTP 200 |
| A04 Insecure Design | Planner rejects oversize text | PASS | HTTP 422 |
| A04 Insecure Design | Assistant rejects an oversize question | PASS | HTTP 422 |
| A04 Insecure Design | A study session of 100000 minutes is rejected | PASS | HTTP 422 |
| A04 Insecure Design | Guest state with 30 tasks is rejected (bounded input) | PASS | HTTP 422 |
| A04 Insecure Design | A forged guest clock 400 days ahead cannot give a wildly different 'today' | PASS | HTTP 200 |
| A04 Insecure Design | Guests never reach the language model by default | PASS | HTTP 200 |
| A09 Logging | AI usage (calls, tokens, cost) is recorded and visible to the student | PASS | HTTP 200 ['available', 'provider', 'model', 'student_allows', 'daily_cap'] |
| A02 Cryptographic Failures | No API key is ever returned by the usage endpoint | PASS |  |

### Live security test, 2026-10-29 05:01 (http://127.0.0.1:8000)

**95 / 95 checks passed**

| OWASP category | Check | Result | Detail |
|---|---|---|---|
| A03 Injection | SQL injection in login e-mail rejected (no 200/500) | PASS | HTTP 422 |
| A03 Injection | SQL injection in login password does not log in | PASS | HTTP 401 |
| A03 Injection | SQL in task title stored as plain text, tables intact (parameterised queries) | PASS | HTTP 201/200 |
| A03 Injection | XSS payload returned as inert JSON text (not HTML) with nosniff | PASS | application/json |
| A01 Broken Access Control | User B cannot read user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot edit user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot delete user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User A's task unchanged after B's attempts | PASS |  |
| A01 Broken Access Control | /tasks refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /recommend refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /energy-checkins refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /auth/me refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | Mass assignment: client cannot set owner_id/id | PASS | HTTP 201 |
| A02 Cryptographic Failures | API never returns password or password_hash | PASS |  |
| A07 Auth Failures | Tampered JWT signature rejected | PASS | HTTP 401 |
| A07 Auth Failures | JWT with alg=none rejected | PASS | HTTP 401 |
| A07 Auth Failures | Duplicate registration gets a clear 409 message (rate-limited) | PASS | {"detail":"An account with this email already exists. Please log in in |
| A07 Auth Failures | Password without a number is rejected with a readable reason | PASS | HTTP 422 |
| A07 Auth Failures | Weak/short password rejected (min 8) | PASS | HTTP 422 |
| A01 Broken Access Control | Email-alert settings need a login | PASS | HTTP 401 |
| A01 Broken Access Control | Deadline check-now needs a login | PASS | HTTP 401 |
| A03 Injection | Alert settings reject a non-boolean value | PASS | HTTP 422 |
| A01 Broken Access Control | Wellbeing assessment needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Wellbeing history needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Study planner (account route) needs a login | PASS | HTTP 401 |
| A03 Injection | Guest study planner rejects oversize / out-of-range input | PASS | HTTP 422 |
| A03 Injection | Planner returns data only (no HTML executed), topic text is just data | PASS | HTTP 200 |
| A07 Auth Failures | Brute-force login locked out with HTTP 429 after repeated failures | PASS | codes [401, 401, 401, 401, 401, 429, 429] |
| A07 Auth Failures | Even the correct password is refused during lock-out | PASS | HTTP 429 |
| A07 Auth Failures | Forgot-password gives the same answer for a registered and an unknown address (no account enumeration) | PASS | HTTP 200/200 |
| A02 Cryptographic Failures | The reset secret is never returned by the API (only e-mailed) | PASS |  |
| A03 Injection | SQL injection in the forgot-password e-mail field is rejected | PASS | HTTP 422 |
| A07 Auth Failures | A made-up reset token is refused | PASS | HTTP 400 |
| A07 Auth Failures | A too-short reset token is rejected by validation | PASS | HTTP 422 |
| A07 Auth Failures | A weak new password is rejected on reset | PASS | HTTP 422 |
| A04 Insecure Design | Repeated forgot-password requests for one address are rate limited (HTTP 429) | PASS | codes [200, 200, 200, 200, 200, 429, 429] |
| A01 Broken Access Control | Changing the password needs a login | PASS | HTTP 401 |
| A07 Auth Failures | Changing the password with a wrong current password is refused | PASS | HTTP 403 |
| A04 Insecure Design | Validation rejects title 201 chars | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 99 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 0 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects empty title | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects bad deadline | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects description 2001 chars | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 0 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 6 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level -1 rejected | PASS | HTTP 422 |
| A04 Insecure Design | PATCH with null title rejected (no server error) | PASS | HTTP 422 |
| A04 Insecure Design | Malformed JSON gives 4xx, not a crash | PASS | HTTP 422 |
| A05 Misconfiguration | CORS refuses unknown origin | PASS |  |
| A05 Misconfiguration | Security headers present | PASS | {'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'no-referrer', 'cache-control': 'no-store'} |
| A05 Misconfiguration | Bad ID gives clean 422 without stack trace | PASS | HTTP 422 |
| A03 Injection | Hostile task title does not break /recommend (explanation is built locally) | PASS | HTTP 200 |
| A04 Insecure Design | Models status states honestly whether an external language model is configured | PASS | HTTP 200 |
| A05 Misconfiguration | Removed cloud-AI routes no longer exist (404) | PASS | HTTP 404 |
| A04 Insecure Design | Valid wellbeing answers give a label and probabilities | PASS | HTTP 200 |
| A03 Injection | Wellbeing rejects unknown answer keys | PASS | HTTP 422 |
| A04 Insecure Design | Wellbeing rejects out-of-range numbers | PASS | HTTP 422 |
| A03 Injection | Wellbeing rejects text where a number is required | PASS | HTTP 422 |
| A01 Broken Access Control | User B does not see user A's wellbeing history | PASS | HTTP 200 |
| A01 Broken Access Control | GET /assist/state needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/understand needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/evaluate needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/accept needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/replan/apply needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/session needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/explain needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/ask needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/dashboard needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/review needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/usage needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/reminders needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /settings needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | PUT /settings needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /profile needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | PUT /profile needs a login | PASS | HTTP 401 |
| A04 Insecure Design | Settings reject an unknown field | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a 3-day study-time value out of range | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a made-up time zone | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a non-boolean AI switch | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a reminder lead time that is not offered | PASS | HTTP 422 |
| A04 Insecure Design | Profile rejects an oversize free-text field | PASS | HTTP 422 |
| A01 Broken Access Control | Profile rejects unknown fields (no mass assignment) | PASS | HTTP 422 |
| A01 Broken Access Control | User A cannot log a study session against user B's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User A cannot change the priority of user B's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B's planner state never contains user A's task titles | PASS |  |
| A03 Injection | Planner text with instructions and a script tag gives clean JSON and no leaked prompt | PASS | HTTP 200 |
| A04 Insecure Design | Planner rejects oversize text | PASS | HTTP 422 |
| A04 Insecure Design | Assistant rejects an oversize question | PASS | HTTP 422 |
| A04 Insecure Design | A study session of 100000 minutes is rejected | PASS | HTTP 422 |
| A04 Insecure Design | Guest state with 30 tasks is rejected (bounded input) | PASS | HTTP 422 |
| A04 Insecure Design | A forged guest clock 400 days ahead cannot give a wildly different 'today' | PASS | HTTP 200 |
| A04 Insecure Design | Guests never reach the language model by default | PASS | HTTP 200 |
| A09 Logging | AI usage (calls, tokens, cost) is recorded and visible to the student | PASS | HTTP 200 ['available', 'provider', 'model', 'student_allows', 'daily_cap'] |
| A02 Cryptographic Failures | No API key is ever returned by the usage endpoint | PASS |  |

### Live security test, 2026-10-29 05:10 (http://127.0.0.1:8000)

**95 / 95 checks passed**

| OWASP category | Check | Result | Detail |
|---|---|---|---|
| A03 Injection | SQL injection in login e-mail rejected (no 200/500) | PASS | HTTP 422 |
| A03 Injection | SQL injection in login password does not log in | PASS | HTTP 401 |
| A03 Injection | SQL in task title stored as plain text, tables intact (parameterised queries) | PASS | HTTP 201/200 |
| A03 Injection | XSS payload returned as inert JSON text (not HTML) with nosniff | PASS | application/json |
| A01 Broken Access Control | User B cannot read user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot edit user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot delete user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User A's task unchanged after B's attempts | PASS |  |
| A01 Broken Access Control | /tasks refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /recommend refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /energy-checkins refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /auth/me refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | Mass assignment: client cannot set owner_id/id | PASS | HTTP 201 |
| A02 Cryptographic Failures | API never returns password or password_hash | PASS |  |
| A07 Auth Failures | Tampered JWT signature rejected | PASS | HTTP 401 |
| A07 Auth Failures | JWT with alg=none rejected | PASS | HTTP 401 |
| A07 Auth Failures | Duplicate registration gets a clear 409 message (rate-limited) | PASS | {"detail":"An account with this email already exists. Please log in in |
| A07 Auth Failures | Password without a number is rejected with a readable reason | PASS | HTTP 422 |
| A07 Auth Failures | Weak/short password rejected (min 8) | PASS | HTTP 422 |
| A01 Broken Access Control | Email-alert settings need a login | PASS | HTTP 401 |
| A01 Broken Access Control | Deadline check-now needs a login | PASS | HTTP 401 |
| A03 Injection | Alert settings reject a non-boolean value | PASS | HTTP 422 |
| A01 Broken Access Control | Wellbeing assessment needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Wellbeing history needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Study planner (account route) needs a login | PASS | HTTP 401 |
| A03 Injection | Guest study planner rejects oversize / out-of-range input | PASS | HTTP 422 |
| A03 Injection | Planner returns data only (no HTML executed), topic text is just data | PASS | HTTP 200 |
| A07 Auth Failures | Brute-force login locked out with HTTP 429 after repeated failures | PASS | codes [401, 401, 401, 401, 401, 429, 429] |
| A07 Auth Failures | Even the correct password is refused during lock-out | PASS | HTTP 429 |
| A07 Auth Failures | Forgot-password gives the same answer for a registered and an unknown address (no account enumeration) | PASS | HTTP 200/200 |
| A02 Cryptographic Failures | The reset secret is never returned by the API (only e-mailed) | PASS |  |
| A03 Injection | SQL injection in the forgot-password e-mail field is rejected | PASS | HTTP 422 |
| A07 Auth Failures | A made-up reset token is refused | PASS | HTTP 400 |
| A07 Auth Failures | A too-short reset token is rejected by validation | PASS | HTTP 422 |
| A07 Auth Failures | A weak new password is rejected on reset | PASS | HTTP 422 |
| A04 Insecure Design | Repeated forgot-password requests for one address are rate limited (HTTP 429) | PASS | codes [200, 200, 200, 200, 200, 429, 429] |
| A01 Broken Access Control | Changing the password needs a login | PASS | HTTP 401 |
| A07 Auth Failures | Changing the password with a wrong current password is refused | PASS | HTTP 403 |
| A04 Insecure Design | Validation rejects title 201 chars | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 99 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 0 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects empty title | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects bad deadline | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects description 2001 chars | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 0 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 6 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level -1 rejected | PASS | HTTP 422 |
| A04 Insecure Design | PATCH with null title rejected (no server error) | PASS | HTTP 422 |
| A04 Insecure Design | Malformed JSON gives 4xx, not a crash | PASS | HTTP 422 |
| A05 Misconfiguration | CORS refuses unknown origin | PASS |  |
| A05 Misconfiguration | Security headers present | PASS | {'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'no-referrer', 'cache-control': 'no-store'} |
| A05 Misconfiguration | Bad ID gives clean 422 without stack trace | PASS | HTTP 422 |
| A03 Injection | Hostile task title does not break /recommend (explanation is built locally) | PASS | HTTP 200 |
| A04 Insecure Design | Models status states honestly whether an external language model is configured | PASS | HTTP 200 |
| A05 Misconfiguration | Removed cloud-AI routes no longer exist (404) | PASS | HTTP 404 |
| A04 Insecure Design | Valid wellbeing answers give a label and probabilities | PASS | HTTP 200 |
| A03 Injection | Wellbeing rejects unknown answer keys | PASS | HTTP 422 |
| A04 Insecure Design | Wellbeing rejects out-of-range numbers | PASS | HTTP 422 |
| A03 Injection | Wellbeing rejects text where a number is required | PASS | HTTP 422 |
| A01 Broken Access Control | User B does not see user A's wellbeing history | PASS | HTTP 200 |
| A01 Broken Access Control | GET /assist/state needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/understand needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/evaluate needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/accept needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/replan/apply needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/session needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/explain needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/ask needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/dashboard needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/review needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/usage needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/reminders needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /settings needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | PUT /settings needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /profile needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | PUT /profile needs a login | PASS | HTTP 401 |
| A04 Insecure Design | Settings reject an unknown field | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a 3-day study-time value out of range | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a made-up time zone | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a non-boolean AI switch | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a reminder lead time that is not offered | PASS | HTTP 422 |
| A04 Insecure Design | Profile rejects an oversize free-text field | PASS | HTTP 422 |
| A01 Broken Access Control | Profile rejects unknown fields (no mass assignment) | PASS | HTTP 422 |
| A01 Broken Access Control | User A cannot log a study session against user B's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User A cannot change the priority of user B's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B's planner state never contains user A's task titles | PASS |  |
| A03 Injection | Planner text with instructions and a script tag gives clean JSON and no leaked prompt | PASS | HTTP 200 |
| A04 Insecure Design | Planner rejects oversize text | PASS | HTTP 422 |
| A04 Insecure Design | Assistant rejects an oversize question | PASS | HTTP 422 |
| A04 Insecure Design | A study session of 100000 minutes is rejected | PASS | HTTP 422 |
| A04 Insecure Design | Guest state with 30 tasks is rejected (bounded input) | PASS | HTTP 422 |
| A04 Insecure Design | A forged guest clock 400 days ahead cannot give a wildly different 'today' | PASS | HTTP 200 |
| A04 Insecure Design | Guests never reach the language model by default | PASS | HTTP 200 |
| A09 Logging | AI usage (calls, tokens, cost) is recorded and visible to the student | PASS | HTTP 200 ['available', 'provider', 'model', 'student_allows', 'daily_cap'] |
| A02 Cryptographic Failures | No API key is ever returned by the usage endpoint | PASS |  |

### Live security test, 2026-10-29 05:24 (http://127.0.0.1:8000)

**95 / 95 checks passed**

| OWASP category | Check | Result | Detail |
|---|---|---|---|
| A03 Injection | SQL injection in login e-mail rejected (no 200/500) | PASS | HTTP 422 |
| A03 Injection | SQL injection in login password does not log in | PASS | HTTP 401 |
| A03 Injection | SQL in task title stored as plain text, tables intact (parameterised queries) | PASS | HTTP 201/200 |
| A03 Injection | XSS payload returned as inert JSON text (not HTML) with nosniff | PASS | application/json |
| A01 Broken Access Control | User B cannot read user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot edit user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot delete user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User A's task unchanged after B's attempts | PASS |  |
| A01 Broken Access Control | /tasks refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /recommend refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /energy-checkins refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /auth/me refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | Mass assignment: client cannot set owner_id/id | PASS | HTTP 201 |
| A02 Cryptographic Failures | API never returns password or password_hash | PASS |  |
| A07 Auth Failures | Tampered JWT signature rejected | PASS | HTTP 401 |
| A07 Auth Failures | JWT with alg=none rejected | PASS | HTTP 401 |
| A07 Auth Failures | Duplicate registration gets a clear 409 message (rate-limited) | PASS | {"detail":"An account with this email already exists. Please log in in |
| A07 Auth Failures | Password without a number is rejected with a readable reason | PASS | HTTP 422 |
| A07 Auth Failures | Weak/short password rejected (min 8) | PASS | HTTP 422 |
| A01 Broken Access Control | Email-alert settings need a login | PASS | HTTP 401 |
| A01 Broken Access Control | Deadline check-now needs a login | PASS | HTTP 401 |
| A03 Injection | Alert settings reject a non-boolean value | PASS | HTTP 422 |
| A01 Broken Access Control | Wellbeing assessment needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Wellbeing history needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Study planner (account route) needs a login | PASS | HTTP 401 |
| A03 Injection | Guest study planner rejects oversize / out-of-range input | PASS | HTTP 422 |
| A03 Injection | Planner returns data only (no HTML executed), topic text is just data | PASS | HTTP 200 |
| A07 Auth Failures | Brute-force login locked out with HTTP 429 after repeated failures | PASS | codes [401, 401, 401, 401, 401, 429, 429] |
| A07 Auth Failures | Even the correct password is refused during lock-out | PASS | HTTP 429 |
| A07 Auth Failures | Forgot-password gives the same answer for a registered and an unknown address (no account enumeration) | PASS | HTTP 200/200 |
| A02 Cryptographic Failures | The reset secret is never returned by the API (only e-mailed) | PASS |  |
| A03 Injection | SQL injection in the forgot-password e-mail field is rejected | PASS | HTTP 422 |
| A07 Auth Failures | A made-up reset token is refused | PASS | HTTP 400 |
| A07 Auth Failures | A too-short reset token is rejected by validation | PASS | HTTP 422 |
| A07 Auth Failures | A weak new password is rejected on reset | PASS | HTTP 422 |
| A04 Insecure Design | Repeated forgot-password requests for one address are rate limited (HTTP 429) | PASS | codes [200, 200, 200, 200, 200, 429, 429] |
| A01 Broken Access Control | Changing the password needs a login | PASS | HTTP 401 |
| A07 Auth Failures | Changing the password with a wrong current password is refused | PASS | HTTP 403 |
| A04 Insecure Design | Validation rejects title 201 chars | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 99 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 0 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects empty title | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects bad deadline | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects description 2001 chars | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 0 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 6 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level -1 rejected | PASS | HTTP 422 |
| A04 Insecure Design | PATCH with null title rejected (no server error) | PASS | HTTP 422 |
| A04 Insecure Design | Malformed JSON gives 4xx, not a crash | PASS | HTTP 422 |
| A05 Misconfiguration | CORS refuses unknown origin | PASS |  |
| A05 Misconfiguration | Security headers present | PASS | {'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'no-referrer', 'cache-control': 'no-store'} |
| A05 Misconfiguration | Bad ID gives clean 422 without stack trace | PASS | HTTP 422 |
| A03 Injection | Hostile task title does not break /recommend (explanation is built locally) | PASS | HTTP 200 |
| A04 Insecure Design | Models status states honestly whether an external language model is configured | PASS | HTTP 200 |
| A05 Misconfiguration | Removed cloud-AI routes no longer exist (404) | PASS | HTTP 404 |
| A04 Insecure Design | Valid wellbeing answers give a label and probabilities | PASS | HTTP 200 |
| A03 Injection | Wellbeing rejects unknown answer keys | PASS | HTTP 422 |
| A04 Insecure Design | Wellbeing rejects out-of-range numbers | PASS | HTTP 422 |
| A03 Injection | Wellbeing rejects text where a number is required | PASS | HTTP 422 |
| A01 Broken Access Control | User B does not see user A's wellbeing history | PASS | HTTP 200 |
| A01 Broken Access Control | GET /assist/state needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/understand needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/evaluate needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/accept needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/replan/apply needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/session needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/explain needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/ask needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/dashboard needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/review needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/usage needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/reminders needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /settings needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | PUT /settings needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /profile needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | PUT /profile needs a login | PASS | HTTP 401 |
| A04 Insecure Design | Settings reject an unknown field | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a 3-day study-time value out of range | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a made-up time zone | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a non-boolean AI switch | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a reminder lead time that is not offered | PASS | HTTP 422 |
| A04 Insecure Design | Profile rejects an oversize free-text field | PASS | HTTP 422 |
| A01 Broken Access Control | Profile rejects unknown fields (no mass assignment) | PASS | HTTP 422 |
| A01 Broken Access Control | User A cannot log a study session against user B's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User A cannot change the priority of user B's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B's planner state never contains user A's task titles | PASS |  |
| A03 Injection | Planner text with instructions and a script tag gives clean JSON and no leaked prompt | PASS | HTTP 200 |
| A04 Insecure Design | Planner rejects oversize text | PASS | HTTP 422 |
| A04 Insecure Design | Assistant rejects an oversize question | PASS | HTTP 422 |
| A04 Insecure Design | A study session of 100000 minutes is rejected | PASS | HTTP 422 |
| A04 Insecure Design | Guest state with 30 tasks is rejected (bounded input) | PASS | HTTP 422 |
| A04 Insecure Design | A forged guest clock 400 days ahead cannot give a wildly different 'today' | PASS | HTTP 200 |
| A04 Insecure Design | Guests never reach the language model by default | PASS | HTTP 200 |
| A09 Logging | AI usage (calls, tokens, cost) is recorded and visible to the student | PASS | HTTP 200 ['available', 'provider', 'model', 'student_allows', 'daily_cap'] |
| A02 Cryptographic Failures | No API key is ever returned by the usage endpoint | PASS |  |

### Live security test, 2026-10-29 16:32 (http://127.0.0.1:8000)

**94 / 95 checks passed**

| OWASP category | Check | Result | Detail |
|---|---|---|---|
| A03 Injection | SQL injection in login e-mail rejected (no 200/500) | PASS | HTTP 422 |
| A03 Injection | SQL injection in login password does not log in | PASS | HTTP 401 |
| A03 Injection | SQL in task title stored as plain text, tables intact (parameterised queries) | PASS | HTTP 201/200 |
| A03 Injection | XSS payload returned as inert JSON text (not HTML) with nosniff | PASS | application/json |
| A01 Broken Access Control | User B cannot read user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot edit user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot delete user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User A's task unchanged after B's attempts | PASS |  |
| A01 Broken Access Control | /tasks refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /recommend refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /energy-checkins refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /auth/me refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | Mass assignment: client cannot set owner_id/id | PASS | HTTP 201 |
| A02 Cryptographic Failures | API never returns password or password_hash | PASS |  |
| A07 Auth Failures | Tampered JWT signature rejected | PASS | HTTP 401 |
| A07 Auth Failures | JWT with alg=none rejected | PASS | HTTP 401 |
| A07 Auth Failures | Duplicate registration gets a clear 409 message (rate-limited) | PASS | {"detail":"An account with this email already exists. Please log in in |
| A07 Auth Failures | Password without a number is rejected with a readable reason | PASS | HTTP 422 |
| A07 Auth Failures | Weak/short password rejected (min 8) | PASS | HTTP 422 |
| A01 Broken Access Control | Email-alert settings need a login | PASS | HTTP 401 |
| A01 Broken Access Control | Deadline check-now needs a login | PASS | HTTP 401 |
| A03 Injection | Alert settings reject a non-boolean value | PASS | HTTP 422 |
| A01 Broken Access Control | Wellbeing assessment needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Wellbeing history needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Study planner (account route) needs a login | PASS | HTTP 401 |
| A03 Injection | Guest study planner rejects oversize / out-of-range input | PASS | HTTP 422 |
| A03 Injection | Planner returns data only (no HTML executed), topic text is just data | PASS | HTTP 200 |
| A07 Auth Failures | Brute-force login locked out with HTTP 429 after repeated failures | PASS | codes [401, 401, 401, 401, 401, 429, 429] |
| A07 Auth Failures | Even the correct password is refused during lock-out | PASS | HTTP 429 |
| A07 Auth Failures | Forgot-password gives the same answer for a registered and an unknown address (no account enumeration) | PASS | HTTP 200/200 |
| A02 Cryptographic Failures | The reset secret is never returned by the API (only e-mailed) | PASS |  |
| A03 Injection | SQL injection in the forgot-password e-mail field is rejected | PASS | HTTP 422 |
| A07 Auth Failures | A made-up reset token is refused | PASS | HTTP 400 |
| A07 Auth Failures | A too-short reset token is rejected by validation | PASS | HTTP 422 |
| A07 Auth Failures | A weak new password is rejected on reset | PASS | HTTP 422 |
| A04 Insecure Design | Repeated forgot-password requests for one address are rate limited (HTTP 429) | PASS | codes [200, 200, 200, 200, 200, 429, 429] |
| A01 Broken Access Control | Changing the password needs a login | PASS | HTTP 401 |
| A07 Auth Failures | Changing the password with a wrong current password is refused | PASS | HTTP 403 |
| A04 Insecure Design | Validation rejects title 201 chars | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 99 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 0 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects empty title | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects bad deadline | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects description 2001 chars | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 0 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 6 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level -1 rejected | PASS | HTTP 422 |
| A04 Insecure Design | PATCH with null title rejected (no server error) | PASS | HTTP 422 |
| A04 Insecure Design | Malformed JSON gives 4xx, not a crash | PASS | HTTP 422 |
| A05 Misconfiguration | CORS refuses unknown origin | PASS |  |
| A05 Misconfiguration | Security headers present | PASS | {'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'no-referrer', 'cache-control': 'no-store'} |
| A05 Misconfiguration | Bad ID gives clean 422 without stack trace | PASS | HTTP 422 |
| A03 Injection | Hostile task title does not break /recommend (explanation is built locally) | PASS | HTTP 200 |
| A04 Insecure Design | Models status states honestly whether an external language model is configured | PASS | HTTP 200 |
| A05 Misconfiguration | Removed cloud-AI routes no longer exist (404) | PASS | HTTP 404 |
| A04 Insecure Design | Valid wellbeing answers give a label and probabilities | PASS | HTTP 200 |
| A03 Injection | Wellbeing rejects unknown answer keys | PASS | HTTP 422 |
| A04 Insecure Design | Wellbeing rejects out-of-range numbers | PASS | HTTP 422 |
| A03 Injection | Wellbeing rejects text where a number is required | PASS | HTTP 422 |
| A01 Broken Access Control | User B does not see user A's wellbeing history | PASS | HTTP 200 |
| A01 Broken Access Control | GET /assist/state needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/understand needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/evaluate needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/accept needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/replan/apply needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/session needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/explain needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/ask needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/dashboard needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/review needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/usage needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/reminders needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /settings needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | PUT /settings needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /profile needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | PUT /profile needs a login | PASS | HTTP 401 |
| A04 Insecure Design | Settings reject an unknown field | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a 3-day study-time value out of range | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a made-up time zone | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a non-boolean AI switch | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a reminder lead time that is not offered | PASS | HTTP 422 |
| A04 Insecure Design | Profile rejects an oversize free-text field | PASS | HTTP 422 |
| A01 Broken Access Control | Profile rejects unknown fields (no mass assignment) | PASS | HTTP 422 |
| A01 Broken Access Control | User A cannot log a study session against user B's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User A cannot change the priority of user B's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B's planner state never contains user A's task titles | PASS |  |
| A03 Injection | Planner text with instructions and a script tag gives clean JSON and no leaked prompt | PASS | HTTP 200 |
| A04 Insecure Design | Planner rejects oversize text | PASS | HTTP 422 |
| A04 Insecure Design | Assistant rejects an oversize question | PASS | HTTP 422 |
| A04 Insecure Design | A study session of 100000 minutes is rejected | PASS | HTTP 422 |
| A04 Insecure Design | Guest state with 30 tasks is rejected (bounded input) | FAIL | HTTP 200 |
| A04 Insecure Design | A forged guest clock 400 days ahead cannot give a wildly different 'today' | PASS | HTTP 200 |
| A04 Insecure Design | Guests never reach the language model by default | PASS | HTTP 200 |
| A09 Logging | AI usage (calls, tokens, cost) is recorded and visible to the student | PASS | HTTP 200 ['available', 'provider', 'model', 'student_allows', 'daily_cap'] |
| A02 Cryptographic Failures | No API key is ever returned by the usage endpoint | PASS |  |

### Live security test, 2026-10-29 16:32 (http://127.0.0.1:8000)

**105 / 106 checks passed**

| OWASP category | Check | Result | Detail |
|---|---|---|---|
| A03 Injection | SQL injection in login e-mail rejected (no 200/500) | PASS | HTTP 422 |
| A03 Injection | SQL injection in login password does not log in | PASS | HTTP 401 |
| A03 Injection | SQL in task title stored as plain text, tables intact (parameterised queries) | PASS | HTTP 201/200 |
| A03 Injection | XSS payload returned as inert JSON text (not HTML) with nosniff | PASS | application/json |
| A01 Broken Access Control | User B cannot read user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot edit user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot delete user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User A's task unchanged after B's attempts | PASS |  |
| A01 Broken Access Control | /tasks refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /recommend refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /energy-checkins refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /auth/me refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | Mass assignment: client cannot set owner_id/id | PASS | HTTP 201 |
| A02 Cryptographic Failures | API never returns password or password_hash | PASS |  |
| A07 Auth Failures | Tampered JWT signature rejected | PASS | HTTP 401 |
| A07 Auth Failures | JWT with alg=none rejected | PASS | HTTP 401 |
| A07 Auth Failures | Duplicate registration gets a clear 409 message (rate-limited) | PASS | {"detail":"An account with this email already exists. Please log in in |
| A07 Auth Failures | Password without a number is rejected with a readable reason | PASS | HTTP 422 |
| A07 Auth Failures | Weak/short password rejected (min 8) | PASS | HTTP 422 |
| A01 Broken Access Control | Email-alert settings need a login | PASS | HTTP 401 |
| A01 Broken Access Control | Deadline check-now needs a login | PASS | HTTP 401 |
| A03 Injection | Alert settings reject a non-boolean value | PASS | HTTP 422 |
| A01 Broken Access Control | Wellbeing assessment needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Wellbeing history needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Study planner (account route) needs a login | PASS | HTTP 401 |
| A03 Injection | Guest study planner rejects oversize / out-of-range input | PASS | HTTP 422 |
| A03 Injection | Planner returns data only (no HTML executed), topic text is just data | PASS | HTTP 200 |
| A07 Auth Failures | Brute-force login locked out with HTTP 429 after repeated failures | PASS | codes [401, 401, 401, 401, 401, 429, 429] |
| A07 Auth Failures | Even the correct password is refused during lock-out | PASS | HTTP 429 |
| A07 Auth Failures | Forgot-password gives the same answer for a registered and an unknown address (no account enumeration) | PASS | HTTP 200/200 |
| A02 Cryptographic Failures | The reset secret is never returned by the API (only e-mailed) | PASS |  |
| A03 Injection | SQL injection in the forgot-password e-mail field is rejected | PASS | HTTP 422 |
| A07 Auth Failures | A made-up reset token is refused | PASS | HTTP 400 |
| A07 Auth Failures | A too-short reset token is rejected by validation | PASS | HTTP 422 |
| A07 Auth Failures | A weak new password is rejected on reset | PASS | HTTP 422 |
| A04 Insecure Design | Repeated forgot-password requests for one address are rate limited (HTTP 429) | PASS | codes [200, 200, 200, 200, 200, 429, 429] |
| A01 Broken Access Control | Changing the password needs a login | PASS | HTTP 401 |
| A07 Auth Failures | Changing the password with a wrong current password is refused | PASS | HTTP 403 |
| A04 Insecure Design | Validation rejects title 201 chars | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 99 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 0 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects empty title | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects bad deadline | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects description 2001 chars | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 0 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 6 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level -1 rejected | PASS | HTTP 422 |
| A04 Insecure Design | PATCH with null title rejected (no server error) | PASS | HTTP 422 |
| A04 Insecure Design | Malformed JSON gives 4xx, not a crash | PASS | HTTP 422 |
| A05 Misconfiguration | CORS refuses unknown origin | PASS |  |
| A05 Misconfiguration | Security headers present | PASS | {'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'no-referrer', 'cache-control': 'no-store'} |
| A05 Misconfiguration | Bad ID gives clean 422 without stack trace | PASS | HTTP 422 |
| A03 Injection | Hostile task title does not break /recommend (explanation is built locally) | PASS | HTTP 200 |
| A04 Insecure Design | Models status states honestly whether an external language model is configured | PASS | HTTP 200 |
| A05 Misconfiguration | Removed cloud-AI routes no longer exist (404) | PASS | HTTP 404 |
| A04 Insecure Design | Valid wellbeing answers give a label and probabilities | PASS | HTTP 200 |
| A03 Injection | Wellbeing rejects unknown answer keys | PASS | HTTP 422 |
| A04 Insecure Design | Wellbeing rejects out-of-range numbers | PASS | HTTP 422 |
| A03 Injection | Wellbeing rejects text where a number is required | PASS | HTTP 422 |
| A01 Broken Access Control | User B does not see user A's wellbeing history | PASS | HTTP 200 |
| A01 Broken Access Control | GET /assist/state needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/understand needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/evaluate needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/accept needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/replan/apply needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/session needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/explain needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/ask needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/dashboard needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/review needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/usage needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/reminders needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /settings needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | PUT /settings needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /profile needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | PUT /profile needs a login | PASS | HTTP 401 |
| A04 Insecure Design | Settings reject an unknown field | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a 3-day study-time value out of range | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a made-up time zone | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a non-boolean AI switch | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a reminder lead time that is not offered | PASS | HTTP 422 |
| A04 Insecure Design | Profile rejects an oversize free-text field | PASS | HTTP 422 |
| A01 Broken Access Control | Profile rejects unknown fields (no mass assignment) | PASS | HTTP 422 |
| A01 Broken Access Control | User A cannot log a study session against user B's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User A cannot change the priority of user B's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B's planner state never contains user A's task titles | PASS |  |
| A03 Injection | Planner text with instructions and a script tag gives clean JSON and no leaked prompt | PASS | HTTP 200 |
| A04 Insecure Design | Planner rejects oversize text | PASS | HTTP 422 |
| A04 Insecure Design | Assistant rejects an oversize question | PASS | HTTP 422 |
| A04 Insecure Design | A study session of 100000 minutes is rejected | PASS | HTTP 422 |
| A04 Insecure Design | Guest state with 61 tasks is rejected (bounded input; the limit is 60) | PASS | HTTP 422 |
| A04 Insecure Design | A forged guest clock 400 days ahead cannot give a wildly different 'today' | PASS | HTTP 200 |
| A04 Insecure Design | Guests never reach the language model by default | PASS | HTTP 200 |
| A01 Broken Access Control | The form endpoint needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Reading the saved form needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | The study guidance needs a login | PASS | HTTP 401 |
| A04 Insecure Design | The form rejects an unknown field (no mass assignment) | PASS | HTTP 422 |
| A04 Insecure Design | The form rejects 41 topics (limit 40) | PASS | HTTP 422 |
| A04 Insecure Design | The form rejects an invented task type | PASS | HTTP 422 |
| A04 Insecure Design | The form rejects 100000 minutes a day | PASS | HTTP 422 |
| A01 Broken Access Control | A form topic naming another student's task id changes nothing of theirs (IDOR) | PASS | HTTP 200 |
| A01 Broken Access Control | Deleting by id through the form cannot delete another student's task (IDOR) | PASS | HTTP 200 |
| A03 Injection | Hostile text in the form is stored as plain text, never as markup, and never reaches a model | FAIL | HTTP 200 |
| A04 Insecure Design | The guest form twin rejects 41 topics too | PASS | HTTP 422 |
| A09 Logging | AI usage (calls, tokens, cost) is recorded and visible to the student | PASS | HTTP 200 ['available', 'provider', 'model', 'student_allows', 'daily_cap'] |
| A02 Cryptographic Failures | No API key is ever returned by the usage endpoint | PASS |  |

### Live security test, 2026-10-29 16:33 (http://127.0.0.1:8000)

**106 / 106 checks passed**

| OWASP category | Check | Result | Detail |
|---|---|---|---|
| A03 Injection | SQL injection in login e-mail rejected (no 200/500) | PASS | HTTP 422 |
| A03 Injection | SQL injection in login password does not log in | PASS | HTTP 401 |
| A03 Injection | SQL in task title stored as plain text, tables intact (parameterised queries) | PASS | HTTP 201/200 |
| A03 Injection | XSS payload returned as inert JSON text (not HTML) with nosniff | PASS | application/json |
| A01 Broken Access Control | User B cannot read user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot edit user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot delete user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User A's task unchanged after B's attempts | PASS |  |
| A01 Broken Access Control | /tasks refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /recommend refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /energy-checkins refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /auth/me refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | Mass assignment: client cannot set owner_id/id | PASS | HTTP 201 |
| A02 Cryptographic Failures | API never returns password or password_hash | PASS |  |
| A07 Auth Failures | Tampered JWT signature rejected | PASS | HTTP 401 |
| A07 Auth Failures | JWT with alg=none rejected | PASS | HTTP 401 |
| A07 Auth Failures | Duplicate registration gets a clear 409 message (rate-limited) | PASS | {"detail":"An account with this email already exists. Please log in in |
| A07 Auth Failures | Password without a number is rejected with a readable reason | PASS | HTTP 422 |
| A07 Auth Failures | Weak/short password rejected (min 8) | PASS | HTTP 422 |
| A01 Broken Access Control | Email-alert settings need a login | PASS | HTTP 401 |
| A01 Broken Access Control | Deadline check-now needs a login | PASS | HTTP 401 |
| A03 Injection | Alert settings reject a non-boolean value | PASS | HTTP 422 |
| A01 Broken Access Control | Wellbeing assessment needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Wellbeing history needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Study planner (account route) needs a login | PASS | HTTP 401 |
| A03 Injection | Guest study planner rejects oversize / out-of-range input | PASS | HTTP 422 |
| A03 Injection | Planner returns data only (no HTML executed), topic text is just data | PASS | HTTP 200 |
| A07 Auth Failures | Brute-force login locked out with HTTP 429 after repeated failures | PASS | codes [401, 401, 401, 401, 401, 429, 429] |
| A07 Auth Failures | Even the correct password is refused during lock-out | PASS | HTTP 429 |
| A07 Auth Failures | Forgot-password gives the same answer for a registered and an unknown address (no account enumeration) | PASS | HTTP 200/200 |
| A02 Cryptographic Failures | The reset secret is never returned by the API (only e-mailed) | PASS |  |
| A03 Injection | SQL injection in the forgot-password e-mail field is rejected | PASS | HTTP 422 |
| A07 Auth Failures | A made-up reset token is refused | PASS | HTTP 400 |
| A07 Auth Failures | A too-short reset token is rejected by validation | PASS | HTTP 422 |
| A07 Auth Failures | A weak new password is rejected on reset | PASS | HTTP 422 |
| A04 Insecure Design | Repeated forgot-password requests for one address are rate limited (HTTP 429) | PASS | codes [200, 200, 200, 200, 200, 429, 429] |
| A01 Broken Access Control | Changing the password needs a login | PASS | HTTP 401 |
| A07 Auth Failures | Changing the password with a wrong current password is refused | PASS | HTTP 403 |
| A04 Insecure Design | Validation rejects title 201 chars | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 99 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 0 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects empty title | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects bad deadline | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects description 2001 chars | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 0 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 6 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level -1 rejected | PASS | HTTP 422 |
| A04 Insecure Design | PATCH with null title rejected (no server error) | PASS | HTTP 422 |
| A04 Insecure Design | Malformed JSON gives 4xx, not a crash | PASS | HTTP 422 |
| A05 Misconfiguration | CORS refuses unknown origin | PASS |  |
| A05 Misconfiguration | Security headers present | PASS | {'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'no-referrer', 'cache-control': 'no-store'} |
| A05 Misconfiguration | Bad ID gives clean 422 without stack trace | PASS | HTTP 422 |
| A03 Injection | Hostile task title does not break /recommend (explanation is built locally) | PASS | HTTP 200 |
| A04 Insecure Design | Models status states honestly whether an external language model is configured | PASS | HTTP 200 |
| A05 Misconfiguration | Removed cloud-AI routes no longer exist (404) | PASS | HTTP 404 |
| A04 Insecure Design | Valid wellbeing answers give a label and probabilities | PASS | HTTP 200 |
| A03 Injection | Wellbeing rejects unknown answer keys | PASS | HTTP 422 |
| A04 Insecure Design | Wellbeing rejects out-of-range numbers | PASS | HTTP 422 |
| A03 Injection | Wellbeing rejects text where a number is required | PASS | HTTP 422 |
| A01 Broken Access Control | User B does not see user A's wellbeing history | PASS | HTTP 200 |
| A01 Broken Access Control | GET /assist/state needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/understand needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/evaluate needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/accept needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/replan/apply needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/session needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/explain needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/ask needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/dashboard needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/review needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/usage needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/reminders needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /settings needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | PUT /settings needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /profile needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | PUT /profile needs a login | PASS | HTTP 401 |
| A04 Insecure Design | Settings reject an unknown field | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a 3-day study-time value out of range | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a made-up time zone | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a non-boolean AI switch | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a reminder lead time that is not offered | PASS | HTTP 422 |
| A04 Insecure Design | Profile rejects an oversize free-text field | PASS | HTTP 422 |
| A01 Broken Access Control | Profile rejects unknown fields (no mass assignment) | PASS | HTTP 422 |
| A01 Broken Access Control | User A cannot log a study session against user B's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User A cannot change the priority of user B's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B's planner state never contains user A's task titles | PASS |  |
| A03 Injection | Planner text with instructions and a script tag gives clean JSON and no leaked prompt | PASS | HTTP 200 |
| A04 Insecure Design | Planner rejects oversize text | PASS | HTTP 422 |
| A04 Insecure Design | Assistant rejects an oversize question | PASS | HTTP 422 |
| A04 Insecure Design | A study session of 100000 minutes is rejected | PASS | HTTP 422 |
| A04 Insecure Design | Guest state with 61 tasks is rejected (bounded input; the limit is 60) | PASS | HTTP 422 |
| A04 Insecure Design | A forged guest clock 400 days ahead cannot give a wildly different 'today' | PASS | HTTP 200 |
| A04 Insecure Design | Guests never reach the language model by default | PASS | HTTP 200 |
| A01 Broken Access Control | The form endpoint needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Reading the saved form needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | The study guidance needs a login | PASS | HTTP 401 |
| A04 Insecure Design | The form rejects an unknown field (no mass assignment) | PASS | HTTP 422 |
| A04 Insecure Design | The form rejects 41 topics (limit 40) | PASS | HTTP 422 |
| A04 Insecure Design | The form rejects an invented task type | PASS | HTTP 422 |
| A04 Insecure Design | The form rejects 100000 minutes a day | PASS | HTTP 422 |
| A01 Broken Access Control | A form topic naming another student's task id changes nothing of theirs (IDOR) | PASS | HTTP 200 |
| A01 Broken Access Control | Deleting by id through the form cannot delete another student's task (IDOR) | PASS | HTTP 200 |
| A03 Injection | Hostile text in the form is kept as inert data: JSON only, nosniff, and shown by the page as plain text (see the browser test) | PASS | HTTP 200 |
| A04 Insecure Design | The guest form twin rejects 41 topics too | PASS | HTTP 422 |
| A09 Logging | AI usage (calls, tokens, cost) is recorded and visible to the student | PASS | HTTP 200 ['available', 'provider', 'model', 'student_allows', 'daily_cap'] |
| A02 Cryptographic Failures | No API key is ever returned by the usage endpoint | PASS |  |

### Live security test, 2026-10-29 17:59 (http://127.0.0.1:8000)

**158 / 159 checks passed**

| OWASP category | Check | Result | Detail |
|---|---|---|---|
| A03 Injection | SQL injection in login e-mail rejected (no 200/500) | PASS | HTTP 422 |
| A03 Injection | SQL injection in login password does not log in | PASS | HTTP 401 |
| A03 Injection | SQL in task title stored as plain text, tables intact (parameterised queries) | PASS | HTTP 201/200 |
| A03 Injection | XSS payload returned as inert JSON text (not HTML) with nosniff | PASS | application/json |
| A01 Broken Access Control | User B cannot read user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot edit user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot delete user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User A's task unchanged after B's attempts | PASS |  |
| A01 Broken Access Control | /tasks refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /recommend refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /energy-checkins refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /auth/me refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | Mass assignment: client cannot set owner_id/id | PASS | HTTP 201 |
| A02 Cryptographic Failures | API never returns password or password_hash | PASS |  |
| A07 Auth Failures | Tampered JWT signature rejected | PASS | HTTP 401 |
| A07 Auth Failures | JWT with alg=none rejected | PASS | HTTP 401 |
| A07 Auth Failures | Duplicate registration gets a clear 409 message (rate-limited) | PASS | {"detail":"An account with this email already exists. Please log in in |
| A07 Auth Failures | Password without a number is rejected with a readable reason | PASS | HTTP 422 |
| A07 Auth Failures | Weak/short password rejected (min 8) | PASS | HTTP 422 |
| A01 Broken Access Control | Email-alert settings need a login | PASS | HTTP 401 |
| A01 Broken Access Control | Deadline check-now needs a login | PASS | HTTP 401 |
| A03 Injection | Alert settings reject a non-boolean value | PASS | HTTP 422 |
| A01 Broken Access Control | Wellbeing assessment needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Wellbeing history needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Study planner (account route) needs a login | PASS | HTTP 401 |
| A03 Injection | Guest study planner rejects oversize / out-of-range input | PASS | HTTP 422 |
| A03 Injection | Planner returns data only (no HTML executed), topic text is just data | PASS | HTTP 200 |
| A07 Auth Failures | Brute-force login locked out with HTTP 429 after repeated failures | PASS | codes [401, 401, 401, 401, 401, 429, 429] |
| A07 Auth Failures | Even the correct password is refused during lock-out | PASS | HTTP 429 |
| A07 Auth Failures | Forgot-password gives the same answer for a registered and an unknown address (no account enumeration) | PASS | HTTP 200/200 |
| A02 Cryptographic Failures | The reset secret is never returned by the API (only e-mailed) | PASS |  |
| A03 Injection | SQL injection in the forgot-password e-mail field is rejected | PASS | HTTP 422 |
| A07 Auth Failures | A made-up reset token is refused | PASS | HTTP 400 |
| A07 Auth Failures | A too-short reset token is rejected by validation | PASS | HTTP 422 |
| A07 Auth Failures | A weak new password is rejected on reset | PASS | HTTP 422 |
| A04 Insecure Design | Repeated forgot-password requests for one address are rate limited (HTTP 429) | PASS | codes [200, 200, 200, 200, 200, 429, 429] |
| A01 Broken Access Control | Changing the password needs a login | PASS | HTTP 401 |
| A07 Auth Failures | Changing the password with a wrong current password is refused | PASS | HTTP 403 |
| A04 Insecure Design | Validation rejects title 201 chars | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 99 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 0 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects empty title | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects bad deadline | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects description 2001 chars | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 0 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 6 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level -1 rejected | PASS | HTTP 422 |
| A04 Insecure Design | PATCH with null title rejected (no server error) | PASS | HTTP 422 |
| A04 Insecure Design | Malformed JSON gives 4xx, not a crash | PASS | HTTP 422 |
| A05 Misconfiguration | CORS refuses unknown origin | PASS |  |
| A05 Misconfiguration | Security headers present | PASS | {'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'no-referrer', 'cache-control': 'no-store'} |
| A05 Misconfiguration | Bad ID gives clean 422 without stack trace | PASS | HTTP 422 |
| A03 Injection | Hostile task title does not break /recommend (explanation is built locally) | PASS | HTTP 200 |
| A04 Insecure Design | Models status states honestly whether an external language model is configured | PASS | HTTP 200 |
| A05 Misconfiguration | Removed cloud-AI routes no longer exist (404) | PASS | HTTP 404 |
| A04 Insecure Design | Valid wellbeing answers give a label and probabilities | PASS | HTTP 200 |
| A03 Injection | Wellbeing rejects unknown answer keys | PASS | HTTP 422 |
| A04 Insecure Design | Wellbeing rejects out-of-range numbers | PASS | HTTP 422 |
| A03 Injection | Wellbeing rejects text where a number is required | PASS | HTTP 422 |
| A01 Broken Access Control | User B does not see user A's wellbeing history | PASS | HTTP 200 |
| A01 Broken Access Control | GET /assist/state needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/understand needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/evaluate needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/accept needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/replan/apply needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/session needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/explain needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/ask needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/dashboard needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/review needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/usage needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/reminders needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /settings needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | PUT /settings needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /profile needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | PUT /profile needs a login | PASS | HTTP 401 |
| A04 Insecure Design | Settings reject an unknown field | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a 3-day study-time value out of range | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a made-up time zone | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a non-boolean AI switch | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a reminder lead time that is not offered | PASS | HTTP 422 |
| A04 Insecure Design | Profile rejects an oversize free-text field | PASS | HTTP 422 |
| A01 Broken Access Control | Profile rejects unknown fields (no mass assignment) | PASS | HTTP 422 |
| A01 Broken Access Control | User A cannot log a study session against user B's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User A cannot change the priority of user B's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B's planner state never contains user A's task titles | PASS |  |
| A03 Injection | Planner text with instructions and a script tag gives clean JSON and no leaked prompt | PASS | HTTP 200 |
| A04 Insecure Design | Planner rejects oversize text | PASS | HTTP 422 |
| A04 Insecure Design | Assistant rejects an oversize question | PASS | HTTP 422 |
| A04 Insecure Design | A study session of 100000 minutes is rejected | PASS | HTTP 422 |
| A04 Insecure Design | Guest state with 61 tasks is rejected (bounded input; the limit is 60) | PASS | HTTP 422 |
| A04 Insecure Design | A forged guest clock 400 days ahead cannot give a wildly different 'today' | PASS | HTTP 200 |
| A04 Insecure Design | Guests never reach the language model by default | PASS | HTTP 200 |
| A01 Broken Access Control | The form endpoint needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Reading the saved form needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | The study guidance needs a login | PASS | HTTP 401 |
| A04 Insecure Design | The form rejects an unknown field (no mass assignment) | PASS | HTTP 422 |
| A04 Insecure Design | The form rejects 41 topics (limit 40) | PASS | HTTP 422 |
| A04 Insecure Design | The form rejects an invented task type | PASS | HTTP 422 |
| A04 Insecure Design | The form rejects 100000 minutes a day | PASS | HTTP 422 |
| A01 Broken Access Control | A form topic naming another student's task id changes nothing of theirs (IDOR) | PASS | HTTP 200 |
| A01 Broken Access Control | Deleting by id through the form cannot delete another student's task (IDOR) | PASS | HTTP 200 |
| A03 Injection | Hostile text in the form is kept as inert data: JSON only, nosniff, and shown by the page as plain text (see the browser test) | PASS | HTTP 200 |
| A04 Insecure Design | The guest form twin rejects 41 topics too | PASS | HTTP 422 |
| A09 Logging | AI usage (calls, tokens, cost) is recorded and visible to the student | PASS | HTTP 200 ['available', 'provider', 'model', 'student_allows', 'daily_cap'] |
| A02 Cryptographic Failures | No API key is ever returned by the usage endpoint | PASS |  |
| A01 Broken Access Control | GET /roadmap needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /roadmap/history needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /roadmap/replan/preview needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /reminders needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /reminders/read-all needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /studio/status needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /studio/packs needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /studio/sample needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /studio/summary needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /account/email needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | User B cannot POST another student's roadmap block (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot POST another student's roadmap block (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot POST another student's roadmap block (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot PATCH another student's roadmap block (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot DELETE another student's roadmap block (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | A's roadmap block is unchanged after B's attempts | PASS |  |
| A03 Injection | Roadmap confirm rejects bad input ['done', -5] | PASS | HTTP 422 |
| A03 Injection | Roadmap confirm rejects bad input ['done', 99999] | PASS | HTTP 422 |
| A03 Injection | Roadmap confirm rejects bad input ['hacked'] | PASS | HTTP 422 |
| A03 Injection | Roadmap confirm rejects bad input ['done', 'x'] | PASS | HTTP 422 |
| A03 Injection | Markup in a block title is kept as inert JSON text with nosniff | PASS | HTTP 200 |
| A04 Insecure Design | Removing a block needs explicit confirmation (?confirm=true) | PASS | HTTP 422 |
| A04 Insecure Design | Replan cannot be applied without explicit confirmation | PASS | HTTP 422 |
| A04 Insecure Design | A study block cannot be added in the past | PASS | HTTP 422 |
| A04 Insecure Design | The guest roadmap twin rejects 1600 blocks | PASS | HTTP 422 |
| A02 Cryptographic Failures | Reminders carry no password, token or e-mail address | PASS | HTTP 200 |
| A01 Broken Access Control | Marking an unknown reminder read is a clean 404 | PASS | HTTP 404 |
| A05 Misconfiguration | Studio status says AI is off and never shows a key | PASS | HTTP 200 |
| A04 Insecure Design | Creating a pack while AI is off is refused honestly (no fake pack, no cost) | PASS | HTTP 409 |
| A04 Insecure Design | The hand-written sample pack can be opened without AI | PASS | HTTP 200 |
| A01 Broken Access Control | User B cannot GET A's learning pack (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot GET A's learning pack (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot GET A's learning pack (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot DELETE A's learning pack (IDOR) | PASS | HTTP 404 |
| A02 Cryptographic Failures | A quiz sent to the browser never contains the right answers | PASS | HTTP 200 |
| A01 Broken Access Control | User B cannot submit answers to A's pack | PASS | HTTP 404 |
| A03 Injection | Quiz request with bad input [7] is rejected | PASS | HTTP 422 |
| A03 Injection | Quiz request with bad input [5, 'impossible'] is rejected | PASS | HTTP 422 |
| A03 Injection | Quiz request with bad input [5, 1] is rejected | PASS | HTTP 422 |
| A04 Insecure Design | Deleting a pack needs explicit confirmation | PASS | HTTP 422 |
| A08 Integrity | Upload of a .exe renamed .pdf is refused (no 200, no 500) | PASS | HTTP 422 |
| A08 Integrity | Upload of a script is refused (no 200, no 500) | PASS | HTTP 422 |
| A08 Integrity | Upload of a path-traversal name is refused (no 200, no 500) | FAIL | HTTP 200 |
| A08 Integrity | Upload of an empty file is refused (no 200, no 500) | PASS | HTTP 422 |
| A08 Integrity | Upload of a fake docx that is not a zip is refused (no 200, no 500) | PASS | HTTP 422 |
| A04 Insecure Design | A file over the size limit is refused before it is read | PASS | HTTP 422 |
| A04 Insecure Design | A normal text file is read as plain text only | PASS | HTTP 200 |
| A03 Injection | Profile rejects a markup avatar and a letters-only phone number | PASS | HTTP 422 |
| A03 Injection | Profile text is stored as plain JSON text | PASS | HTTP 200 |
| A07 Auth Failures | E-mail change with a wrong password is refused | PASS | HTTP 403 |
| A07 Auth Failures | E-mail change to an address that is taken is refused with a neutral message | PASS | HTTP 409 |
| A03 Injection | E-mail change rejects an invalid address | PASS | HTTP 422 |
| A02 Cryptographic Failures | The data export includes the new roadmap and Studio data but no password hash or API key | PASS | HTTP 200 |

### Live security test, 2026-10-29 17:59 (http://127.0.0.1:8000)

**159 / 159 checks passed**

| OWASP category | Check | Result | Detail |
|---|---|---|---|
| A03 Injection | SQL injection in login e-mail rejected (no 200/500) | PASS | HTTP 422 |
| A03 Injection | SQL injection in login password does not log in | PASS | HTTP 401 |
| A03 Injection | SQL in task title stored as plain text, tables intact (parameterised queries) | PASS | HTTP 201/200 |
| A03 Injection | XSS payload returned as inert JSON text (not HTML) with nosniff | PASS | application/json |
| A01 Broken Access Control | User B cannot read user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot edit user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot delete user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User A's task unchanged after B's attempts | PASS |  |
| A01 Broken Access Control | /tasks refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /recommend refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /energy-checkins refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /auth/me refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | Mass assignment: client cannot set owner_id/id | PASS | HTTP 201 |
| A02 Cryptographic Failures | API never returns password or password_hash | PASS |  |
| A07 Auth Failures | Tampered JWT signature rejected | PASS | HTTP 401 |
| A07 Auth Failures | JWT with alg=none rejected | PASS | HTTP 401 |
| A07 Auth Failures | Duplicate registration gets a clear 409 message (rate-limited) | PASS | {"detail":"An account with this email already exists. Please log in in |
| A07 Auth Failures | Password without a number is rejected with a readable reason | PASS | HTTP 422 |
| A07 Auth Failures | Weak/short password rejected (min 8) | PASS | HTTP 422 |
| A01 Broken Access Control | Email-alert settings need a login | PASS | HTTP 401 |
| A01 Broken Access Control | Deadline check-now needs a login | PASS | HTTP 401 |
| A03 Injection | Alert settings reject a non-boolean value | PASS | HTTP 422 |
| A01 Broken Access Control | Wellbeing assessment needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Wellbeing history needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Study planner (account route) needs a login | PASS | HTTP 401 |
| A03 Injection | Guest study planner rejects oversize / out-of-range input | PASS | HTTP 422 |
| A03 Injection | Planner returns data only (no HTML executed), topic text is just data | PASS | HTTP 200 |
| A07 Auth Failures | Brute-force login locked out with HTTP 429 after repeated failures | PASS | codes [401, 401, 401, 401, 401, 429, 429] |
| A07 Auth Failures | Even the correct password is refused during lock-out | PASS | HTTP 429 |
| A07 Auth Failures | Forgot-password gives the same answer for a registered and an unknown address (no account enumeration) | PASS | HTTP 200/200 |
| A02 Cryptographic Failures | The reset secret is never returned by the API (only e-mailed) | PASS |  |
| A03 Injection | SQL injection in the forgot-password e-mail field is rejected | PASS | HTTP 422 |
| A07 Auth Failures | A made-up reset token is refused | PASS | HTTP 400 |
| A07 Auth Failures | A too-short reset token is rejected by validation | PASS | HTTP 422 |
| A07 Auth Failures | A weak new password is rejected on reset | PASS | HTTP 422 |
| A04 Insecure Design | Repeated forgot-password requests for one address are rate limited (HTTP 429) | PASS | codes [200, 200, 200, 200, 200, 429, 429] |
| A01 Broken Access Control | Changing the password needs a login | PASS | HTTP 401 |
| A07 Auth Failures | Changing the password with a wrong current password is refused | PASS | HTTP 403 |
| A04 Insecure Design | Validation rejects title 201 chars | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 99 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 0 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects empty title | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects bad deadline | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects description 2001 chars | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 0 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 6 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level -1 rejected | PASS | HTTP 422 |
| A04 Insecure Design | PATCH with null title rejected (no server error) | PASS | HTTP 422 |
| A04 Insecure Design | Malformed JSON gives 4xx, not a crash | PASS | HTTP 422 |
| A05 Misconfiguration | CORS refuses unknown origin | PASS |  |
| A05 Misconfiguration | Security headers present | PASS | {'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'no-referrer', 'cache-control': 'no-store'} |
| A05 Misconfiguration | Bad ID gives clean 422 without stack trace | PASS | HTTP 422 |
| A03 Injection | Hostile task title does not break /recommend (explanation is built locally) | PASS | HTTP 200 |
| A04 Insecure Design | Models status states honestly whether an external language model is configured | PASS | HTTP 200 |
| A05 Misconfiguration | Removed cloud-AI routes no longer exist (404) | PASS | HTTP 404 |
| A04 Insecure Design | Valid wellbeing answers give a label and probabilities | PASS | HTTP 200 |
| A03 Injection | Wellbeing rejects unknown answer keys | PASS | HTTP 422 |
| A04 Insecure Design | Wellbeing rejects out-of-range numbers | PASS | HTTP 422 |
| A03 Injection | Wellbeing rejects text where a number is required | PASS | HTTP 422 |
| A01 Broken Access Control | User B does not see user A's wellbeing history | PASS | HTTP 200 |
| A01 Broken Access Control | GET /assist/state needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/understand needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/evaluate needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/accept needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/replan/apply needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/session needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/explain needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/ask needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/dashboard needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/review needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/usage needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/reminders needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /settings needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | PUT /settings needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /profile needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | PUT /profile needs a login | PASS | HTTP 401 |
| A04 Insecure Design | Settings reject an unknown field | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a 3-day study-time value out of range | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a made-up time zone | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a non-boolean AI switch | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a reminder lead time that is not offered | PASS | HTTP 422 |
| A04 Insecure Design | Profile rejects an oversize free-text field | PASS | HTTP 422 |
| A01 Broken Access Control | Profile rejects unknown fields (no mass assignment) | PASS | HTTP 422 |
| A01 Broken Access Control | User A cannot log a study session against user B's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User A cannot change the priority of user B's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B's planner state never contains user A's task titles | PASS |  |
| A03 Injection | Planner text with instructions and a script tag gives clean JSON and no leaked prompt | PASS | HTTP 200 |
| A04 Insecure Design | Planner rejects oversize text | PASS | HTTP 422 |
| A04 Insecure Design | Assistant rejects an oversize question | PASS | HTTP 422 |
| A04 Insecure Design | A study session of 100000 minutes is rejected | PASS | HTTP 422 |
| A04 Insecure Design | Guest state with 61 tasks is rejected (bounded input; the limit is 60) | PASS | HTTP 422 |
| A04 Insecure Design | A forged guest clock 400 days ahead cannot give a wildly different 'today' | PASS | HTTP 200 |
| A04 Insecure Design | Guests never reach the language model by default | PASS | HTTP 200 |
| A01 Broken Access Control | The form endpoint needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Reading the saved form needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | The study guidance needs a login | PASS | HTTP 401 |
| A04 Insecure Design | The form rejects an unknown field (no mass assignment) | PASS | HTTP 422 |
| A04 Insecure Design | The form rejects 41 topics (limit 40) | PASS | HTTP 422 |
| A04 Insecure Design | The form rejects an invented task type | PASS | HTTP 422 |
| A04 Insecure Design | The form rejects 100000 minutes a day | PASS | HTTP 422 |
| A01 Broken Access Control | A form topic naming another student's task id changes nothing of theirs (IDOR) | PASS | HTTP 200 |
| A01 Broken Access Control | Deleting by id through the form cannot delete another student's task (IDOR) | PASS | HTTP 200 |
| A03 Injection | Hostile text in the form is kept as inert data: JSON only, nosniff, and shown by the page as plain text (see the browser test) | PASS | HTTP 200 |
| A04 Insecure Design | The guest form twin rejects 41 topics too | PASS | HTTP 422 |
| A09 Logging | AI usage (calls, tokens, cost) is recorded and visible to the student | PASS | HTTP 200 ['available', 'provider', 'model', 'student_allows', 'daily_cap'] |
| A02 Cryptographic Failures | No API key is ever returned by the usage endpoint | PASS |  |
| A01 Broken Access Control | GET /roadmap needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /roadmap/history needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /roadmap/replan/preview needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /reminders needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /reminders/read-all needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /studio/status needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /studio/packs needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /studio/sample needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /studio/summary needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /account/email needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | User B cannot POST another student's roadmap block (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot POST another student's roadmap block (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot POST another student's roadmap block (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot PATCH another student's roadmap block (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot DELETE another student's roadmap block (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | A's roadmap block is unchanged after B's attempts | PASS |  |
| A03 Injection | Roadmap confirm rejects bad input ['done', -5] | PASS | HTTP 422 |
| A03 Injection | Roadmap confirm rejects bad input ['done', 99999] | PASS | HTTP 422 |
| A03 Injection | Roadmap confirm rejects bad input ['hacked'] | PASS | HTTP 422 |
| A03 Injection | Roadmap confirm rejects bad input ['done', 'x'] | PASS | HTTP 422 |
| A03 Injection | Markup in a block title is kept as inert JSON text with nosniff | PASS | HTTP 200 |
| A04 Insecure Design | Removing a block needs explicit confirmation (?confirm=true) | PASS | HTTP 422 |
| A04 Insecure Design | Replan cannot be applied without explicit confirmation | PASS | HTTP 422 |
| A04 Insecure Design | A study block cannot be added in the past | PASS | HTTP 422 |
| A04 Insecure Design | The guest roadmap twin rejects 1600 blocks | PASS | HTTP 422 |
| A02 Cryptographic Failures | Reminders carry no password, token or e-mail address | PASS | HTTP 200 |
| A01 Broken Access Control | Marking an unknown reminder read is a clean 404 | PASS | HTTP 404 |
| A05 Misconfiguration | Studio status says AI is off and never shows a key | PASS | HTTP 200 |
| A04 Insecure Design | Creating a pack while AI is off is refused honestly (no fake pack, no cost) | PASS | HTTP 409 |
| A04 Insecure Design | The hand-written sample pack can be opened without AI | PASS | HTTP 200 |
| A01 Broken Access Control | User B cannot GET A's learning pack (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot GET A's learning pack (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot GET A's learning pack (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot DELETE A's learning pack (IDOR) | PASS | HTTP 404 |
| A02 Cryptographic Failures | A quiz sent to the browser never contains the right answers | PASS | HTTP 200 |
| A01 Broken Access Control | User B cannot submit answers to A's pack | PASS | HTTP 404 |
| A03 Injection | Quiz request with bad input [7] is rejected | PASS | HTTP 422 |
| A03 Injection | Quiz request with bad input [5, 'impossible'] is rejected | PASS | HTTP 422 |
| A03 Injection | Quiz request with bad input [5, 1] is rejected | PASS | HTTP 422 |
| A04 Insecure Design | Deleting a pack needs explicit confirmation | PASS | HTTP 422 |
| A08 Integrity | Upload of a .exe renamed .pdf is refused (no 200, no 500) | PASS | HTTP 422 |
| A08 Integrity | Upload of a script is refused (no 200, no 500) | PASS | HTTP 422 |
| A08 Integrity | Upload of an empty file is refused (no 200, no 500) | PASS | HTTP 422 |
| A08 Integrity | Upload of a fake docx that is not a zip is refused (no 200, no 500) | PASS | HTTP 422 |
| A01 Broken Access Control | A path-traversal file name is reduced to its last part (no ../ is kept or echoed) | PASS | HTTP 200 passwd.txt |
| A04 Insecure Design | A file over the size limit is refused before it is read | PASS | HTTP 422 |
| A04 Insecure Design | A normal text file is read as plain text only | PASS | HTTP 200 |
| A03 Injection | Profile rejects a markup avatar and a letters-only phone number | PASS | HTTP 422 |
| A03 Injection | Profile text is stored as plain JSON text | PASS | HTTP 200 |
| A07 Auth Failures | E-mail change with a wrong password is refused | PASS | HTTP 403 |
| A07 Auth Failures | E-mail change to an address that is taken is refused with a neutral message | PASS | HTTP 409 |
| A03 Injection | E-mail change rejects an invalid address | PASS | HTTP 422 |
| A02 Cryptographic Failures | The data export includes the new roadmap and Studio data but no password hash or API key | PASS | HTTP 200 |

### Live security test, 2026-10-29 18:00 (http://127.0.0.1:8000)

**159 / 159 checks passed**

| OWASP category | Check | Result | Detail |
|---|---|---|---|
| A03 Injection | SQL injection in login e-mail rejected (no 200/500) | PASS | HTTP 422 |
| A03 Injection | SQL injection in login password does not log in | PASS | HTTP 401 |
| A03 Injection | SQL in task title stored as plain text, tables intact (parameterised queries) | PASS | HTTP 201/200 |
| A03 Injection | XSS payload returned as inert JSON text (not HTML) with nosniff | PASS | application/json |
| A01 Broken Access Control | User B cannot read user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot edit user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot delete user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User A's task unchanged after B's attempts | PASS |  |
| A01 Broken Access Control | /tasks refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /recommend refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /energy-checkins refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /auth/me refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | Mass assignment: client cannot set owner_id/id | PASS | HTTP 201 |
| A02 Cryptographic Failures | API never returns password or password_hash | PASS |  |
| A07 Auth Failures | Tampered JWT signature rejected | PASS | HTTP 401 |
| A07 Auth Failures | JWT with alg=none rejected | PASS | HTTP 401 |
| A07 Auth Failures | Duplicate registration gets a clear 409 message (rate-limited) | PASS | {"detail":"An account with this email already exists. Please log in in |
| A07 Auth Failures | Password without a number is rejected with a readable reason | PASS | HTTP 422 |
| A07 Auth Failures | Weak/short password rejected (min 8) | PASS | HTTP 422 |
| A01 Broken Access Control | Email-alert settings need a login | PASS | HTTP 401 |
| A01 Broken Access Control | Deadline check-now needs a login | PASS | HTTP 401 |
| A03 Injection | Alert settings reject a non-boolean value | PASS | HTTP 422 |
| A01 Broken Access Control | Wellbeing assessment needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Wellbeing history needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Study planner (account route) needs a login | PASS | HTTP 401 |
| A03 Injection | Guest study planner rejects oversize / out-of-range input | PASS | HTTP 422 |
| A03 Injection | Planner returns data only (no HTML executed), topic text is just data | PASS | HTTP 200 |
| A07 Auth Failures | Brute-force login locked out with HTTP 429 after repeated failures | PASS | codes [401, 401, 401, 401, 401, 429, 429] |
| A07 Auth Failures | Even the correct password is refused during lock-out | PASS | HTTP 429 |
| A07 Auth Failures | Forgot-password gives the same answer for a registered and an unknown address (no account enumeration) | PASS | HTTP 200/200 |
| A02 Cryptographic Failures | The reset secret is never returned by the API (only e-mailed) | PASS |  |
| A03 Injection | SQL injection in the forgot-password e-mail field is rejected | PASS | HTTP 422 |
| A07 Auth Failures | A made-up reset token is refused | PASS | HTTP 400 |
| A07 Auth Failures | A too-short reset token is rejected by validation | PASS | HTTP 422 |
| A07 Auth Failures | A weak new password is rejected on reset | PASS | HTTP 422 |
| A04 Insecure Design | Repeated forgot-password requests for one address are rate limited (HTTP 429) | PASS | codes [200, 200, 200, 200, 200, 429, 429] |
| A01 Broken Access Control | Changing the password needs a login | PASS | HTTP 401 |
| A07 Auth Failures | Changing the password with a wrong current password is refused | PASS | HTTP 403 |
| A04 Insecure Design | Validation rejects title 201 chars | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 99 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 0 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects empty title | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects bad deadline | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects description 2001 chars | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 0 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 6 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level -1 rejected | PASS | HTTP 422 |
| A04 Insecure Design | PATCH with null title rejected (no server error) | PASS | HTTP 422 |
| A04 Insecure Design | Malformed JSON gives 4xx, not a crash | PASS | HTTP 422 |
| A05 Misconfiguration | CORS refuses unknown origin | PASS |  |
| A05 Misconfiguration | Security headers present | PASS | {'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'no-referrer', 'cache-control': 'no-store'} |
| A05 Misconfiguration | Bad ID gives clean 422 without stack trace | PASS | HTTP 422 |
| A03 Injection | Hostile task title does not break /recommend (explanation is built locally) | PASS | HTTP 200 |
| A04 Insecure Design | Models status states honestly whether an external language model is configured | PASS | HTTP 200 |
| A05 Misconfiguration | Removed cloud-AI routes no longer exist (404) | PASS | HTTP 404 |
| A04 Insecure Design | Valid wellbeing answers give a label and probabilities | PASS | HTTP 200 |
| A03 Injection | Wellbeing rejects unknown answer keys | PASS | HTTP 422 |
| A04 Insecure Design | Wellbeing rejects out-of-range numbers | PASS | HTTP 422 |
| A03 Injection | Wellbeing rejects text where a number is required | PASS | HTTP 422 |
| A01 Broken Access Control | User B does not see user A's wellbeing history | PASS | HTTP 200 |
| A01 Broken Access Control | GET /assist/state needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/understand needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/evaluate needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/accept needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/replan/apply needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/session needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/explain needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/ask needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/dashboard needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/review needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/usage needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/reminders needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /settings needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | PUT /settings needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /profile needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | PUT /profile needs a login | PASS | HTTP 401 |
| A04 Insecure Design | Settings reject an unknown field | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a 3-day study-time value out of range | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a made-up time zone | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a non-boolean AI switch | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a reminder lead time that is not offered | PASS | HTTP 422 |
| A04 Insecure Design | Profile rejects an oversize free-text field | PASS | HTTP 422 |
| A01 Broken Access Control | Profile rejects unknown fields (no mass assignment) | PASS | HTTP 422 |
| A01 Broken Access Control | User A cannot log a study session against user B's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User A cannot change the priority of user B's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B's planner state never contains user A's task titles | PASS |  |
| A03 Injection | Planner text with instructions and a script tag gives clean JSON and no leaked prompt | PASS | HTTP 200 |
| A04 Insecure Design | Planner rejects oversize text | PASS | HTTP 422 |
| A04 Insecure Design | Assistant rejects an oversize question | PASS | HTTP 422 |
| A04 Insecure Design | A study session of 100000 minutes is rejected | PASS | HTTP 422 |
| A04 Insecure Design | Guest state with 61 tasks is rejected (bounded input; the limit is 60) | PASS | HTTP 422 |
| A04 Insecure Design | A forged guest clock 400 days ahead cannot give a wildly different 'today' | PASS | HTTP 200 |
| A04 Insecure Design | Guests never reach the language model by default | PASS | HTTP 200 |
| A01 Broken Access Control | The form endpoint needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Reading the saved form needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | The study guidance needs a login | PASS | HTTP 401 |
| A04 Insecure Design | The form rejects an unknown field (no mass assignment) | PASS | HTTP 422 |
| A04 Insecure Design | The form rejects 41 topics (limit 40) | PASS | HTTP 422 |
| A04 Insecure Design | The form rejects an invented task type | PASS | HTTP 422 |
| A04 Insecure Design | The form rejects 100000 minutes a day | PASS | HTTP 422 |
| A01 Broken Access Control | A form topic naming another student's task id changes nothing of theirs (IDOR) | PASS | HTTP 200 |
| A01 Broken Access Control | Deleting by id through the form cannot delete another student's task (IDOR) | PASS | HTTP 200 |
| A03 Injection | Hostile text in the form is kept as inert data: JSON only, nosniff, and shown by the page as plain text (see the browser test) | PASS | HTTP 200 |
| A04 Insecure Design | The guest form twin rejects 41 topics too | PASS | HTTP 422 |
| A09 Logging | AI usage (calls, tokens, cost) is recorded and visible to the student | PASS | HTTP 200 ['available', 'provider', 'model', 'student_allows', 'daily_cap'] |
| A02 Cryptographic Failures | No API key is ever returned by the usage endpoint | PASS |  |
| A01 Broken Access Control | GET /roadmap needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /roadmap/history needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /roadmap/replan/preview needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /reminders needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /reminders/read-all needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /studio/status needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /studio/packs needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /studio/sample needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /studio/summary needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /account/email needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | User B cannot POST another student's roadmap block (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot POST another student's roadmap block (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot POST another student's roadmap block (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot PATCH another student's roadmap block (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot DELETE another student's roadmap block (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | A's roadmap block is unchanged after B's attempts | PASS |  |
| A03 Injection | Roadmap confirm rejects bad input ['done', -5] | PASS | HTTP 422 |
| A03 Injection | Roadmap confirm rejects bad input ['done', 99999] | PASS | HTTP 422 |
| A03 Injection | Roadmap confirm rejects bad input ['hacked'] | PASS | HTTP 422 |
| A03 Injection | Roadmap confirm rejects bad input ['done', 'x'] | PASS | HTTP 422 |
| A03 Injection | Markup in a block title is kept as inert JSON text with nosniff | PASS | HTTP 200 |
| A04 Insecure Design | Removing a block needs explicit confirmation (?confirm=true) | PASS | HTTP 422 |
| A04 Insecure Design | Replan cannot be applied without explicit confirmation | PASS | HTTP 422 |
| A04 Insecure Design | A study block cannot be added in the past | PASS | HTTP 422 |
| A04 Insecure Design | The guest roadmap twin rejects 1600 blocks | PASS | HTTP 422 |
| A02 Cryptographic Failures | Reminders carry no password, token or e-mail address | PASS | HTTP 200 |
| A01 Broken Access Control | Marking an unknown reminder read is a clean 404 | PASS | HTTP 404 |
| A05 Misconfiguration | Studio status says AI is off and never shows a key | PASS | HTTP 200 |
| A04 Insecure Design | Creating a pack while AI is off is refused honestly (no fake pack, no cost) | PASS | HTTP 409 |
| A04 Insecure Design | The hand-written sample pack can be opened without AI | PASS | HTTP 200 |
| A01 Broken Access Control | User B cannot GET A's learning pack (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot GET A's learning pack (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot GET A's learning pack (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot DELETE A's learning pack (IDOR) | PASS | HTTP 404 |
| A02 Cryptographic Failures | A quiz sent to the browser never contains the right answers | PASS | HTTP 200 |
| A01 Broken Access Control | User B cannot submit answers to A's pack | PASS | HTTP 404 |
| A03 Injection | Quiz request with bad input [7] is rejected | PASS | HTTP 422 |
| A03 Injection | Quiz request with bad input [5, 'impossible'] is rejected | PASS | HTTP 422 |
| A03 Injection | Quiz request with bad input [5, 1] is rejected | PASS | HTTP 422 |
| A04 Insecure Design | Deleting a pack needs explicit confirmation | PASS | HTTP 422 |
| A08 Integrity | Upload of a .exe renamed .pdf is refused (no 200, no 500) | PASS | HTTP 422 |
| A08 Integrity | Upload of a script is refused (no 200, no 500) | PASS | HTTP 422 |
| A08 Integrity | Upload of an empty file is refused (no 200, no 500) | PASS | HTTP 422 |
| A08 Integrity | Upload of a fake docx that is not a zip is refused (no 200, no 500) | PASS | HTTP 422 |
| A01 Broken Access Control | A path-traversal file name is reduced to its last part (no ../ is kept or echoed) | PASS | HTTP 200 passwd.txt |
| A04 Insecure Design | A file over the size limit is refused before it is read | PASS | HTTP 422 |
| A04 Insecure Design | A normal text file is read as plain text only | PASS | HTTP 200 |
| A03 Injection | Profile rejects a markup avatar and a letters-only phone number | PASS | HTTP 422 |
| A03 Injection | Profile text is stored as plain JSON text | PASS | HTTP 200 |
| A07 Auth Failures | E-mail change with a wrong password is refused | PASS | HTTP 403 |
| A07 Auth Failures | E-mail change to an address that is taken is refused with a neutral message | PASS | HTTP 409 |
| A03 Injection | E-mail change rejects an invalid address | PASS | HTTP 422 |
| A02 Cryptographic Failures | The data export includes the new roadmap and Studio data but no password hash or API key | PASS | HTTP 200 |

### Live security test, 2026-10-29 19:09 (http://127.0.0.1:8000)

**159 / 159 checks passed**

| OWASP category | Check | Result | Detail |
|---|---|---|---|
| A03 Injection | SQL injection in login e-mail rejected (no 200/500) | PASS | HTTP 422 |
| A03 Injection | SQL injection in login password does not log in | PASS | HTTP 401 |
| A03 Injection | SQL in task title stored as plain text, tables intact (parameterised queries) | PASS | HTTP 201/200 |
| A03 Injection | XSS payload returned as inert JSON text (not HTML) with nosniff | PASS | application/json |
| A01 Broken Access Control | User B cannot read user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot edit user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot delete user A's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User A's task unchanged after B's attempts | PASS |  |
| A01 Broken Access Control | /tasks refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /recommend refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /energy-checkins refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | /auth/me refuses requests with no token | PASS | HTTP 401 |
| A01 Broken Access Control | Mass assignment: client cannot set owner_id/id | PASS | HTTP 201 |
| A02 Cryptographic Failures | API never returns password or password_hash | PASS |  |
| A07 Auth Failures | Tampered JWT signature rejected | PASS | HTTP 401 |
| A07 Auth Failures | JWT with alg=none rejected | PASS | HTTP 401 |
| A07 Auth Failures | Duplicate registration gets a clear 409 message (rate-limited) | PASS | {"detail":"An account with this email already exists. Please log in in |
| A07 Auth Failures | Password without a number is rejected with a readable reason | PASS | HTTP 422 |
| A07 Auth Failures | Weak/short password rejected (min 8) | PASS | HTTP 422 |
| A01 Broken Access Control | Email-alert settings need a login | PASS | HTTP 401 |
| A01 Broken Access Control | Deadline check-now needs a login | PASS | HTTP 401 |
| A03 Injection | Alert settings reject a non-boolean value | PASS | HTTP 422 |
| A01 Broken Access Control | Wellbeing assessment needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Wellbeing history needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Study planner (account route) needs a login | PASS | HTTP 401 |
| A03 Injection | Guest study planner rejects oversize / out-of-range input | PASS | HTTP 422 |
| A03 Injection | Planner returns data only (no HTML executed), topic text is just data | PASS | HTTP 200 |
| A07 Auth Failures | Brute-force login locked out with HTTP 429 after repeated failures | PASS | codes [401, 401, 401, 401, 401, 429, 429] |
| A07 Auth Failures | Even the correct password is refused during lock-out | PASS | HTTP 429 |
| A07 Auth Failures | Forgot-password gives the same answer for a registered and an unknown address (no account enumeration) | PASS | HTTP 200/200 |
| A02 Cryptographic Failures | The reset secret is never returned by the API (only e-mailed) | PASS |  |
| A03 Injection | SQL injection in the forgot-password e-mail field is rejected | PASS | HTTP 422 |
| A07 Auth Failures | A made-up reset token is refused | PASS | HTTP 400 |
| A07 Auth Failures | A too-short reset token is rejected by validation | PASS | HTTP 422 |
| A07 Auth Failures | A weak new password is rejected on reset | PASS | HTTP 422 |
| A04 Insecure Design | Repeated forgot-password requests for one address are rate limited (HTTP 429) | PASS | codes [200, 200, 200, 200, 200, 429, 429] |
| A01 Broken Access Control | Changing the password needs a login | PASS | HTTP 401 |
| A07 Auth Failures | Changing the password with a wrong current password is refused | PASS | HTTP 403 |
| A04 Insecure Design | Validation rejects title 201 chars | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 99 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects difficulty 0 | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects empty title | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects bad deadline | PASS | HTTP 422 |
| A04 Insecure Design | Validation rejects description 2001 chars | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 0 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level 6 rejected | PASS | HTTP 422 |
| A04 Insecure Design | Energy level -1 rejected | PASS | HTTP 422 |
| A04 Insecure Design | PATCH with null title rejected (no server error) | PASS | HTTP 422 |
| A04 Insecure Design | Malformed JSON gives 4xx, not a crash | PASS | HTTP 422 |
| A05 Misconfiguration | CORS refuses unknown origin | PASS |  |
| A05 Misconfiguration | Security headers present | PASS | {'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'no-referrer', 'cache-control': 'no-store'} |
| A05 Misconfiguration | Bad ID gives clean 422 without stack trace | PASS | HTTP 422 |
| A03 Injection | Hostile task title does not break /recommend (explanation is built locally) | PASS | HTTP 200 |
| A04 Insecure Design | Models status states honestly whether an external language model is configured | PASS | HTTP 200 |
| A05 Misconfiguration | Removed cloud-AI routes no longer exist (404) | PASS | HTTP 404 |
| A04 Insecure Design | Valid wellbeing answers give a label and probabilities | PASS | HTTP 200 |
| A03 Injection | Wellbeing rejects unknown answer keys | PASS | HTTP 422 |
| A04 Insecure Design | Wellbeing rejects out-of-range numbers | PASS | HTTP 422 |
| A03 Injection | Wellbeing rejects text where a number is required | PASS | HTTP 422 |
| A01 Broken Access Control | User B does not see user A's wellbeing history | PASS | HTTP 200 |
| A01 Broken Access Control | GET /assist/state needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/understand needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/evaluate needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/accept needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/replan/apply needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/session needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/explain needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/ask needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/dashboard needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /assist/review needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/usage needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /assist/reminders needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /settings needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | PUT /settings needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /profile needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | PUT /profile needs a login | PASS | HTTP 401 |
| A04 Insecure Design | Settings reject an unknown field | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a 3-day study-time value out of range | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a made-up time zone | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a non-boolean AI switch | PASS | HTTP 422 |
| A04 Insecure Design | Settings reject a reminder lead time that is not offered | PASS | HTTP 422 |
| A04 Insecure Design | Profile rejects an oversize free-text field | PASS | HTTP 422 |
| A01 Broken Access Control | Profile rejects unknown fields (no mass assignment) | PASS | HTTP 422 |
| A01 Broken Access Control | User A cannot log a study session against user B's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User A cannot change the priority of user B's task (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B's planner state never contains user A's task titles | PASS |  |
| A03 Injection | Planner text with instructions and a script tag gives clean JSON and no leaked prompt | PASS | HTTP 200 |
| A04 Insecure Design | Planner rejects oversize text | PASS | HTTP 422 |
| A04 Insecure Design | Assistant rejects an oversize question | PASS | HTTP 422 |
| A04 Insecure Design | A study session of 100000 minutes is rejected | PASS | HTTP 422 |
| A04 Insecure Design | Guest state with 61 tasks is rejected (bounded input; the limit is 60) | PASS | HTTP 422 |
| A04 Insecure Design | A forged guest clock 400 days ahead cannot give a wildly different 'today' | PASS | HTTP 200 |
| A04 Insecure Design | Guests never reach the language model by default | PASS | HTTP 200 |
| A01 Broken Access Control | The form endpoint needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | Reading the saved form needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | The study guidance needs a login | PASS | HTTP 401 |
| A04 Insecure Design | The form rejects an unknown field (no mass assignment) | PASS | HTTP 422 |
| A04 Insecure Design | The form rejects 41 topics (limit 40) | PASS | HTTP 422 |
| A04 Insecure Design | The form rejects an invented task type | PASS | HTTP 422 |
| A04 Insecure Design | The form rejects 100000 minutes a day | PASS | HTTP 422 |
| A01 Broken Access Control | A form topic naming another student's task id changes nothing of theirs (IDOR) | PASS | HTTP 200 |
| A01 Broken Access Control | Deleting by id through the form cannot delete another student's task (IDOR) | PASS | HTTP 200 |
| A03 Injection | Hostile text in the form is kept as inert data: JSON only, nosniff, and shown by the page as plain text (see the browser test) | PASS | HTTP 200 |
| A04 Insecure Design | The guest form twin rejects 41 topics too | PASS | HTTP 422 |
| A09 Logging | AI usage (calls, tokens, cost) is recorded and visible to the student | PASS | HTTP 200 ['available', 'provider', 'model', 'student_allows', 'daily_cap'] |
| A02 Cryptographic Failures | No API key is ever returned by the usage endpoint | PASS |  |
| A01 Broken Access Control | GET /roadmap needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /roadmap/history needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /roadmap/replan/preview needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /reminders needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /reminders/read-all needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /studio/status needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /studio/packs needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /studio/sample needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | GET /studio/summary needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | POST /account/email needs a login | PASS | HTTP 401 |
| A01 Broken Access Control | User B cannot POST another student's roadmap block (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot POST another student's roadmap block (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot POST another student's roadmap block (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot PATCH another student's roadmap block (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot DELETE another student's roadmap block (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | A's roadmap block is unchanged after B's attempts | PASS |  |
| A03 Injection | Roadmap confirm rejects bad input ['done', -5] | PASS | HTTP 422 |
| A03 Injection | Roadmap confirm rejects bad input ['done', 99999] | PASS | HTTP 422 |
| A03 Injection | Roadmap confirm rejects bad input ['hacked'] | PASS | HTTP 422 |
| A03 Injection | Roadmap confirm rejects bad input ['done', 'x'] | PASS | HTTP 422 |
| A03 Injection | Markup in a block title is kept as inert JSON text with nosniff | PASS | HTTP 200 |
| A04 Insecure Design | Removing a block needs explicit confirmation (?confirm=true) | PASS | HTTP 422 |
| A04 Insecure Design | Replan cannot be applied without explicit confirmation | PASS | HTTP 422 |
| A04 Insecure Design | A study block cannot be added in the past | PASS | HTTP 422 |
| A04 Insecure Design | The guest roadmap twin rejects 1600 blocks | PASS | HTTP 422 |
| A02 Cryptographic Failures | Reminders carry no password, token or e-mail address | PASS | HTTP 200 |
| A01 Broken Access Control | Marking an unknown reminder read is a clean 404 | PASS | HTTP 404 |
| A05 Misconfiguration | Studio status says AI is off and never shows a key | PASS | HTTP 200 |
| A04 Insecure Design | Creating a pack while AI is off is refused honestly (no fake pack, no cost) | PASS | HTTP 409 |
| A04 Insecure Design | The hand-written sample pack can be opened without AI | PASS | HTTP 200 |
| A01 Broken Access Control | User B cannot GET A's learning pack (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot GET A's learning pack (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot GET A's learning pack (IDOR) | PASS | HTTP 404 |
| A01 Broken Access Control | User B cannot DELETE A's learning pack (IDOR) | PASS | HTTP 404 |
| A02 Cryptographic Failures | A quiz sent to the browser never contains the right answers | PASS | HTTP 200 |
| A01 Broken Access Control | User B cannot submit answers to A's pack | PASS | HTTP 404 |
| A03 Injection | Quiz request with bad input [7] is rejected | PASS | HTTP 422 |
| A03 Injection | Quiz request with bad input [5, 'impossible'] is rejected | PASS | HTTP 422 |
| A03 Injection | Quiz request with bad input [5, 1] is rejected | PASS | HTTP 422 |
| A04 Insecure Design | Deleting a pack needs explicit confirmation | PASS | HTTP 422 |
| A08 Integrity | Upload of a .exe renamed .pdf is refused (no 200, no 500) | PASS | HTTP 422 |
| A08 Integrity | Upload of a script is refused (no 200, no 500) | PASS | HTTP 422 |
| A08 Integrity | Upload of an empty file is refused (no 200, no 500) | PASS | HTTP 422 |
| A08 Integrity | Upload of a fake docx that is not a zip is refused (no 200, no 500) | PASS | HTTP 422 |
| A01 Broken Access Control | A path-traversal file name is reduced to its last part (no ../ is kept or echoed) | PASS | HTTP 200 passwd.txt |
| A04 Insecure Design | A file over the size limit is refused before it is read | PASS | HTTP 422 |
| A04 Insecure Design | A normal text file is read as plain text only | PASS | HTTP 200 |
| A03 Injection | Profile rejects a markup avatar and a letters-only phone number | PASS | HTTP 422 |
| A03 Injection | Profile text is stored as plain JSON text | PASS | HTTP 200 |
| A07 Auth Failures | E-mail change with a wrong password is refused | PASS | HTTP 403 |
| A07 Auth Failures | E-mail change to an address that is taken is refused with a neutral message | PASS | HTTP 409 |
| A03 Injection | E-mail change rejects an invalid address | PASS | HTTP 422 |
| A02 Cryptographic Failures | The data export includes the new roadmap and Studio data but no password hash or API key | PASS | HTTP 200 |

