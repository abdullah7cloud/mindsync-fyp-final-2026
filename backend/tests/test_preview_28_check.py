"""Safety checks of the separate Update 28 preview (PREVIEW-MINDSYNC-28.bat). No network, no real key, no real mail password."""
import pytest

from scripts.preview_28_check import check_env_file, mail_file_problem

SECRET = "x" * 48
PW = "abcd efgh ijkl mnop".replace(" ", "")
FAKE_KEY = "AIza" + "B" * 35


def good(key="", mail=None):
    lines = ["# MindSync Update 28 preview", "DATABASE_URL=sqlite+aiosqlite:///./preview28.db", f"JWT_SECRET={SECRET}",
             "FRONTEND_ORIGIN=http://localhost:5182", "APP_URL=http://localhost:5182", "REMINDERS_ENABLED=false",
             "TASK_REMINDERS_ENABLED=true", "TASK_REMINDER_CHECK_MINUTES=5",
             "AI_PROVIDER=gemini", "GEMINI_MODEL=gemini-3.5-flash-lite", f"GEMINI_API_KEY={key}"]
    return lines + (mail or [])


def run(tmp_path, lines):
    p = tmp_path / ".env"
    p.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    return check_env_file(str(p))


MAIL = ["SMTP_HOST=smtp.gmail.com", "SMTP_PORT=587", "SMTP_USER=me@gmail.com", f"SMTP_PASSWORD={PW}", "SMTP_FROM=me@gmail.com"]


def test_default_file_is_fine_without_key_or_mail(tmp_path):
    assert run(tmp_path, good())[0] == 2


def test_with_key_and_mail_and_nothing_is_printed(tmp_path):
    code, msgs = run(tmp_path, good(FAKE_KEY, MAIL))
    assert code == 0 and all(PW not in m and FAKE_KEY not in m for m in msgs)


def test_commented_mail_lines_are_fine(tmp_path):
    assert run(tmp_path, good("", ["# " + k for k in MAIL]))[0] == 2


def test_empty_mail_lines_are_refused_because_they_would_crash_the_backend(tmp_path):
    assert run(tmp_path, good("", [k.split("=")[0] + "=" for k in MAIL]))[0] == 1


@pytest.mark.parametrize("edit", [
    lambda m: [x for x in m if not x.startswith("SMTP_PASSWORD")] + ["SMTP_PASSWORD="],
    lambda m: [x.replace("smtp.gmail.com", "smtp gmail.com") for x in m],
    lambda m: [x.replace("587", "abc") for x in m],
    lambda m: [x.replace("SMTP_FROM=me@gmail.com", "SMTP_FROM=nobody") for x in m],
    lambda m: [x.replace(PW, f'"{PW}"') for x in m],
])
def test_half_filled_or_odd_mail_lines_stop_the_preview(tmp_path, edit):
    code, msgs = run(tmp_path, good("", edit(MAIL)))
    assert code == 1 and all(PW not in m for m in msgs)


@pytest.mark.parametrize("edit", [
    lambda L: [x.replace("5182", "5173") for x in L],
    lambda L: [x.replace("preview28.db", "preview.db") for x in L],
    lambda L: [x.replace("TASK_REMINDERS_ENABLED=true", "TASK_REMINDERS_ENABLED=false") for x in L],
    lambda L: [x.replace("REMINDERS_ENABLED=false", "REMINDERS_ENABLED=true") if x.startswith("REMINDERS") else x for x in L],
    lambda L: L + ["OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz"],
    lambda L: L + ["GEMINI_BASE_URL=https://evil.example.com/v1beta"],
    lambda L: L + ["DATABASE_URL=postgresql+asyncpg://u:p@localhost/db"],
])
def test_other_unsafe_changes_stop_the_preview(tmp_path, edit):
    assert run(tmp_path, edit(good()))[0] == 1


def test_mail_problem_helper_accepts_empty():
    assert mail_file_problem({}) is None
