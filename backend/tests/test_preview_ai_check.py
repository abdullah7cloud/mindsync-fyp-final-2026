"""The safety checks used by the separate AI preview script (PREVIEW-MINDSYNC-27-AI.bat). No network, no real key."""
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.preview_ai_check import check_env_file, key_problem

SECRET = "x" * 48
FAKE_KEY = "AIza" + "B" * 35


def good(key=""):
    return ["# MindSync AI preview settings", "DATABASE_URL=sqlite+aiosqlite:///./preview.db", f"JWT_SECRET={SECRET}",
            "FRONTEND_ORIGIN=http://localhost:5181", "APP_URL=http://localhost:5181", "REMINDERS_ENABLED=false",
            "AI_PROVIDER=gemini", "GEMINI_MODEL=gemini-3.5-flash-lite", f"GEMINI_API_KEY={key}"]


def run(tmp_path, lines, bom=False):
    p = tmp_path / ".env"
    p.write_bytes((("﻿" if bom else "") + "\r\n".join(lines) + "\r\n").encode("utf-8"))
    return check_env_file(str(p))


def test_blank_key_is_allowed_and_means_ai_off(tmp_path):
    code, msgs = run(tmp_path, good(""))
    assert code == 2 and "AI OFF" in msgs[0]


def test_good_key_is_accepted_and_never_printed(tmp_path):
    code, msgs = run(tmp_path, good(FAKE_KEY))
    assert code == 0
    assert all(FAKE_KEY not in m and FAKE_KEY[:8] not in m for m in msgs)


def test_notepad_byte_order_mark_is_tolerated(tmp_path):
    assert run(tmp_path, good(FAKE_KEY), bom=True)[0] == 0


@pytest.mark.parametrize("bad", [" " + FAKE_KEY, FAKE_KEY + " ", f'"{FAKE_KEY}"', f"'{FAKE_KEY}'", "your-key-here-please-paste-it", "short", FAKE_KEY[:10] + " " + FAKE_KEY[10:], "AIza<" + "B" * 30])
def test_wrong_looking_keys_stop_the_preview_without_repeating_them(tmp_path, bad):
    code, msgs = run(tmp_path, good(bad))
    assert code == 1
    assert all(bad.strip(" \"'") not in m for m in msgs if len(bad.strip()) > 8)


@pytest.mark.parametrize("edit", [
    lambda L: [x.replace("sqlite+aiosqlite:///./preview.db", "postgresql+asyncpg://u:p@localhost/db") for x in L],
    lambda L: [x for x in L if not x.startswith("AI_PROVIDER")] + ["AI_PROVIDER=off"],
    lambda L: [x for x in L if not x.startswith("AI_PROVIDER")] + ["AI_PROVIDER=openai"],
    lambda L: L + ["OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz"],
    lambda L: L + ["GEMINI_BASE_URL=https://evil.example.com/v1beta"],
    lambda L: L + ["AI_MONTHLY_BUDGET_USD=500"],
    lambda L: L + ["GEMINI_API_KEY=" + FAKE_KEY],                        # same name twice
    lambda L: [x.replace("5181", "5173") for x in L],
    lambda L: [x for x in L if not x.startswith("GEMINI_MODEL")] + ["GEMINI_MODEL=gemini-2.5-pro"],
    lambda L: [x for x in L if not x.startswith("JWT_SECRET")] + ["JWT_SECRET=short"],
    lambda L: [x for x in L if not x.startswith("GEMINI_API_KEY")],       # the key line was deleted
    lambda L: [x.replace("false", "true") for x in L],
    lambda L: L + ["this line has no equals sign"],
])
def test_any_wrong_setting_stops_the_preview(tmp_path, edit):
    assert run(tmp_path, edit(good()))[0] == 1


def test_missing_file_stops_the_preview(tmp_path):
    assert check_env_file(str(tmp_path / "nope.env"))[0] == 1


def test_key_problem_helper():
    assert key_problem("") is None and key_problem(FAKE_KEY) is None and key_problem("bad key") is not None


def _settings_run(env_extra, tmp_path, key=""):
    """Runs the real settings check in a scratch folder that holds its own .env (the way the preview folder does)."""
    root = str(Path(__file__).resolve().parents[1])
    base = {"PATH": "/usr/bin:/bin", "PYTHONPATH": root, "DATABASE_URL": "sqlite+aiosqlite:///./preview.db", "AI_PROVIDER": "gemini",
            "REMINDERS_ENABLED": "false", "FRONTEND_ORIGIN": "http://localhost:5181", "APP_URL": "http://localhost:5181", "GEMINI_MODEL": "gemini-3.5-flash-lite"}
    base.update(env_extra)
    (tmp_path / ".env").write_text("\n".join(good(key)) + "\n")
    return subprocess.run([sys.executable, "-m", "scripts.preview_ai_check", "settings"], cwd=str(tmp_path), env=base, capture_output=True, text=True)


def test_settings_check_no_key_means_ai_off(tmp_path):
    r = _settings_run({}, tmp_path)
    assert r.returncode == 2 and "SAFETY CHECK: OK" in r.stdout and "AI is OFF" in r.stdout


def test_settings_check_with_key_is_ok_and_never_prints_it(tmp_path):
    r = _settings_run({}, tmp_path, key=FAKE_KEY)
    assert r.returncode == 0 and "AI is ON" in r.stdout
    assert FAKE_KEY not in r.stdout + r.stderr and FAKE_KEY[:8] not in r.stdout + r.stderr


@pytest.mark.parametrize("extra", [{"GEMINI_BASE_URL": "https://evil.example.com/v1beta"}, {"OPENAI_API_KEY": "sk-abcdefghijklmnopqrstuvwxyz0123"},
                                   {"AI_MONTHLY_BUDGET_USD": "500"}, {"AI_PROVIDER": "openai"}, {"GEMINI_MODEL": "gemini-2.5-pro"},
                                   {"DATABASE_URL": "postgresql+asyncpg://u:p@localhost/db"}, {"AI_ALLOW_GUESTS": "true"}, {"SMTP_HOST": "smtp.example.com"}])
def test_settings_check_stops_on_any_wrong_or_leftover_setting(tmp_path, extra):
    r = _settings_run(extra, tmp_path)
    assert r.returncode == 1 and "FAILED" in r.stdout
    assert "evil.example.com" not in r.stdout and "sk-abc" not in r.stdout
