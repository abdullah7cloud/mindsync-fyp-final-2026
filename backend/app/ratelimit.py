"""
Brute-force protection for login (OWASP A07:2021 - Identification and
Authentication Failures).

A small in-memory sliding-window limiter: after MAX_FAILURES wrong-password
attempts for the same email+IP inside WINDOW_SECONDS, further attempts get
HTTP 429 until the window passes. A successful login clears the counter.

Trade-off (mention in the report): counters live in this server process's
memory, so they reset when the server restarts and are not shared between
multiple server copies. For a single-instance student deployment that is
acceptable; a production system would keep the counters in Redis.
"""
import time
from collections import defaultdict, deque
from typing import Deque

MAX_FAILURES = 5
WINDOW_SECONDS = 15 * 60


class LoginRateLimiter:
    """
    Sliding-window counter. For each key (e.g. "email|ip") we keep a queue of timestamps of recent
    failures. Old timestamps (older than the window) are dropped on every call, so the queue length
    is always "failures in the last N seconds". If that length reaches the limit, the key is blocked
    until the oldest failure falls out of the window.
    The same class is reused for sign-up spam, guest-route limits and the wellbeing-check limit.
    """

    def __init__(self, max_failures: int = MAX_FAILURES, window_seconds: int = WINDOW_SECONDS):
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._failures: dict[str, Deque[float]] = defaultdict(deque)

    def _prune(self, key: str, now: float) -> Deque[float]:
        q = self._failures[key]
        while q and now - q[0] > self.window_seconds:
            q.popleft()
        if not q:
            self._failures.pop(key, None)
            return deque()
        return q

    def retry_after(self, key: str, now: float | None = None) -> int:
        """Seconds the caller must wait, or 0 if the attempt is allowed."""
        # monotonic clock: not affected by the computer's clock being changed.
        now = time.monotonic() if now is None else now
        q = self._prune(key, now)
        if len(q) < self.max_failures:
            return 0
        if not q:                      # max_failures == 0: always blocked
            return self.window_seconds
        return max(1, int(self.window_seconds - (now - q[0])) + 1)

    def record_failure(self, key: str, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        self._prune(key, now)
        self._failures[key].append(now)

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)


login_limiter = LoginRateLimiter()


def limiter_key(email: str, client_ip: str | None) -> str:
    return f"{(email or '').strip().lower()}|{client_ip or 'unknown'}"


# Sign-up spam protection: at most 20 new accounts per IP per hour.
register_limiter = LoginRateLimiter(max_failures=20, window_seconds=60 * 60)
