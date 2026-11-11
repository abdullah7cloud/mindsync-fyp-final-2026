"""
Unit tests for the security layer: Argon2id password hashing and JWT
issuing/verification. No database or HTTP involved.
"""
import uuid

from app.security import create_access_token, decode_access_token, hash_password, verify_password


def test_hash_password_does_not_store_plaintext():
    hashed = hash_password("correct-horse-battery-staple")
    assert hashed != "correct-horse-battery-staple"
    assert hashed.startswith("$argon2id$")


def test_verify_password_accepts_correct_password():
    hashed = hash_password("correct-horse-battery-staple")
    assert verify_password("correct-horse-battery-staple", hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("correct-horse-battery-staple")
    assert verify_password("wrong-password", hashed) is False


def test_verify_password_rejects_malformed_hash_without_raising():
    assert verify_password("anything", "not-a-real-hash") is False


def test_access_token_roundtrip():
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    assert decode_access_token(token) == user_id


def test_decode_access_token_rejects_garbage_token():
    assert decode_access_token("not.a.jwt") is None


def test_decode_access_token_rejects_tampered_token():
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    # Flip a character in the MIDDLE of the signature. (The very last base64
    # character only carries 4 meaningful bits, so changing it can leave the
    # decoded signature identical - that made this test randomly fail.)
    i = len(token) - 10
    tampered = token[:i] + ("A" if token[i] != "A" else "B") + token[i + 1:]
    assert decode_access_token(tampered) is None


# ---- Argon2 must not freeze the web server (found when 10 students used the app at once on the laptop) ----
def test_async_hashing_gives_same_result_as_sync():
    import asyncio
    from app.security import hash_password_async, verify_password_async

    async def run():
        hashed = await hash_password_async("correct-horse-battery-staple")
        return hashed, await verify_password_async("correct-horse-battery-staple", hashed), \
            await verify_password_async("wrong", hashed)
    hashed, ok, bad = asyncio.run(run())
    assert hashed.startswith("$argon2id$") and ok is True and bad is False


def test_hashing_does_not_block_the_event_loop():
    """While passwords are being hashed, other work on the event loop must keep running.
    A 'ticker' asks to wake every 5 ms; if hashing froze the loop, the largest gap between ticks would be about
    as long as a whole hash. With hashing moved to worker threads the gaps stay far shorter."""
    import asyncio
    import time
    from app.security import hash_password, hash_password_async

    t0 = time.perf_counter()
    hash_password("measure-one-hash")
    one_hash = time.perf_counter() - t0

    async def run():
        gaps, stop = [], False

        async def ticker():
            last = time.perf_counter()
            while not stop:
                await asyncio.sleep(0.005)
                now = time.perf_counter()
                gaps.append(now - last)
                last = now
        task = asyncio.create_task(ticker())
        await asyncio.gather(*[hash_password_async(f"password-{i}-abc") for i in range(4)])
        stop = True
        await task
        return max(gaps)
    worst_gap = asyncio.run(run())
    assert worst_gap < max(0.5 * one_hash, 0.05), f"event loop stalled {worst_gap:.3f}s while hashing ({one_hash:.3f}s per hash)"
