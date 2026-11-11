"""Forgot password, reset by e-mailed link, and change password while logged in."""
import re

import pytest

from app import notifier, passwordreset, ratelimit
from app.config import settings


@pytest.fixture()
def mails(monkeypatch, api):
    """Captures every e-mail the app tries to send (instead of writing files) and starts with fresh limiters."""
    sent = []

    async def fake_deliver(msg):
        sent.append(msg)
        return "outbox"

    monkeypatch.setattr(notifier, "deliver", fake_deliver)
    monkeypatch.setattr(passwordreset, "forgot_limiter", ratelimit.LoginRateLimiter(5, 900))
    monkeypatch.setattr(passwordreset, "forgot_ip_limiter", ratelimit.LoginRateLimiter(100, 3600))
    monkeypatch.setattr(passwordreset, "reset_limiter", ratelimit.LoginRateLimiter(10, 900))
    return sent


def _token(msg) -> str:
    body = msg.get_body(("plain",)).get_content()
    m = re.search(r"reset-password\?token=([A-Za-z0-9_\-]+)", body)
    assert m, body
    return m.group(1)


def _forgot(api, email):
    return api.client.post("/auth/forgot-password", json={"email": email})


def _reset(api, token, password="Brand-new-pass-9"):
    return api.client.post("/auth/reset-password", json={"token": token, "new_password": password})


def _login(api, email, password):
    return api.client.post("/auth/login", json={"email": email, "password": password})


def test_unknown_and_known_address_get_the_same_answer_and_unknown_gets_no_email(api, mails):
    user = api.register()
    known = _forgot(api, user["email"])
    unknown = _forgot(api, "nobody-here@example.com")
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()            # nothing in the answer reveals whether the account exists
    assert len(mails) == 1 and mails[0]["To"] == user["email"]


def test_email_contains_a_link_to_the_site_and_the_expiry(api, mails):
    user = api.register(name="Abi <b>")
    _forgot(api, user["email"])
    msg = mails[0]
    assert "reset your password" in msg["Subject"].lower()
    plain = msg.get_body(("plain",)).get_content()
    assert settings.app_url.rstrip("/") + "/reset-password?token=" in plain
    assert "30 minutes" in plain
    html_part = msg.get_body(("html",)).get_content()
    assert "Abi &lt;b&gt;" in html_part and "Abi <b>" not in html_part


def test_full_reset_flow_changes_the_password_once(api, mails):
    user = api.register()
    _forgot(api, user["email"])
    token = _token(mails[0])
    r = _reset(api, token)
    assert r.status_code == 200
    assert _login(api, user["email"], "Brand-new-pass-9").status_code == 200
    assert _login(api, user["email"], user["password"]).status_code == 401      # old password is gone
    assert _reset(api, token, "Another-pass-77").status_code == 400             # the link works only once
    assert "changed" in mails[-1]["Subject"].lower()                            # the owner is told by e-mail


def test_garbage_and_short_tokens_are_refused(api, mails):
    assert _reset(api, "x" * 43).status_code == 400
    assert _reset(api, "short").status_code == 422


def test_expired_link_is_refused(api, mails, monkeypatch):
    monkeypatch.setattr(passwordreset, "RESET_MINUTES", -1)     # a link that is already expired when it is made
    user = api.register()
    _forgot(api, user["email"])
    assert _reset(api, _token(mails[0])).status_code == 400
    assert _login(api, user["email"], user["password"]).status_code == 200      # password unchanged


def test_a_new_request_replaces_the_old_link(api, mails):
    user = api.register()
    _forgot(api, user["email"])
    _forgot(api, user["email"])
    first, second = _token(mails[0]), _token(mails[1])
    assert first != second
    assert _reset(api, first).status_code == 400
    assert _reset(api, second).status_code == 200


def test_weak_new_password_is_refused_and_the_link_still_works(api, mails):
    user = api.register()
    _forgot(api, user["email"])
    token = _token(mails[0])
    assert _reset(api, token, "onlyletters").status_code == 422
    assert _reset(api, token, "short1").status_code == 422
    assert _reset(api, token, "Good-pass-123").status_code == 200


def test_forgot_password_is_rate_limited(api, mails):
    user = api.register()
    codes = [_forgot(api, user["email"]).status_code for _ in range(6)]
    assert codes[:5] == [200] * 5 and codes[5] == 429
    assert len(mails) == 5


def test_bad_email_format_is_a_validation_error(api, mails):
    assert api.client.post("/auth/forgot-password", json={"email": "not-an-email"}).status_code == 422


def test_a_failing_mail_server_does_not_break_the_answer(api, monkeypatch, mails):
    async def broken(msg):
        raise OSError("mail server down")
    monkeypatch.setattr(notifier, "deliver", broken)
    user = api.register()
    assert _forgot(api, user["email"]).status_code == 200


def test_reset_unlocks_an_account_locked_by_wrong_passwords(api, mails):
    user = api.register()
    for _ in range(5):
        _login(api, user["email"], "wrong-password-1")
    assert _login(api, user["email"], user["password"]).status_code == 429
    _forgot(api, user["email"])
    assert _reset(api, _token(mails[0])).status_code == 200
    assert _login(api, user["email"], "Brand-new-pass-9").status_code == 200


def test_deleting_an_account_with_a_pending_reset_link_works(api, mails):
    user = api.register()
    _forgot(api, user["email"])
    r = api.client.request("DELETE", "/account", json={"password": user["password"]}, headers=user["headers"])
    assert r.status_code == 204


# ---------- change password while logged in ----------
def _change(api, user, current, new):
    return api.client.post("/account/password", json={"current_password": current, "new_password": new},
                           headers=user["headers"])


def test_change_password_needs_login(api, mails):
    r = api.client.post("/account/password", json={"current_password": "a", "new_password": "Whatever-123"})
    assert r.status_code == 401


def test_change_password_success_and_notification(api, mails):
    user = api.register()
    assert _change(api, user, user["password"], "Changed-pass-42").status_code == 204
    assert _login(api, user["email"], "Changed-pass-42").status_code == 200
    assert _login(api, user["email"], user["password"]).status_code == 401
    assert "changed" in mails[-1]["Subject"].lower()


def test_change_password_rejects_wrong_current_same_and_weak(api, mails):
    user = api.register()
    assert _change(api, user, "not-my-password-1", "Changed-pass-42").status_code == 403
    assert _change(api, user, user["password"], user["password"]).status_code == 400
    assert _change(api, user, user["password"], "lettersonly").status_code == 422
    assert _login(api, user["email"], user["password"]).status_code == 200      # nothing changed


def test_wrong_current_password_counts_towards_the_lockout(api, mails):
    user = api.register()
    for _ in range(5):
        _change(api, user, "wrong-password-1", "Changed-pass-42")
    assert _change(api, user, user["password"], "Changed-pass-42").status_code == 429


def test_change_password_also_cancels_open_reset_links(api, mails):
    user = api.register()
    _forgot(api, user["email"])
    token = _token(mails[0])
    assert _change(api, user, user["password"], "Changed-pass-42").status_code == 204
    assert _reset(api, token).status_code == 400


def test_token_hash_is_not_the_token():
    t = "abc" * 15
    assert passwordreset.hash_token(t) != t and len(passwordreset.hash_token(t)) == 64
