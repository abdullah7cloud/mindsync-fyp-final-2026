"""
Safety checks used ONLY by PREVIEW-MINDSYNC-27-AI.bat (the separate AI preview). Nothing here contacts the internet.

    python scripts/preview_ai_check.py file  <path-to-backend-.env>     (standard library only, can run before packages are installed)
    python -m scripts.preview_ai_check settings                         (asks the real app code what it will use; run inside backend/)

Exit codes:  0 = all good and a key is set   2 = all good but no key yet (AI stays off)   1 = something is wrong (the preview must not start)

These checks NEVER print the key, not even part of it.
"""
import os
import re
import sys

DB_URL = "sqlite+aiosqlite:///./preview.db"
WEB_URL = "http://localhost:5181"
MODEL = "gemini-3.5-flash-lite"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta"
ALLOWED = ("DATABASE_URL", "JWT_SECRET", "FRONTEND_ORIGIN", "APP_URL", "REMINDERS_ENABLED", "AI_PROVIDER", "GEMINI_MODEL", "GEMINI_API_KEY")
EXACT = {"DATABASE_URL": DB_URL, "FRONTEND_ORIGIN": WEB_URL, "APP_URL": WEB_URL, "REMINDERS_ENABLED": "false", "AI_PROVIDER": "gemini", "GEMINI_MODEL": MODEL}
KEY_SHAPE = re.compile(r"^[A-Za-z0-9_.\-]{20,200}$")      # letters, numbers, _ - . only; no spaces, no quotes


def key_problem(value: str):
    """None if the key line is fine (or empty). Otherwise a plain-English reason that does not repeat the key."""
    if value == "":
        return None
    if value != value.strip() or " " in value or "\t" in value:
        return "The key has a space in it. Remove every space around it."
    if value[0] in "\"'" or value[-1] in "\"'":
        return "The key has quote marks around it. Remove the quote marks."
    if value.lower().startswith(("your", "paste", "put", "xxx")) or "<" in value or ">" in value:
        return "That still looks like the example text, not a real key."
    if not KEY_SHAPE.match(value):
        return "The key looks wrong (a Google key is one long line of letters and numbers)."
    return None


def check_env_file(path: str):
    """Returns (code, messages)."""
    msgs = []
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return 1, ["The preview settings file could not be read."]
    except UnicodeDecodeError:
        return 1, ["The preview settings file has strange characters. Save it as plain UTF-8 text in Notepad."]
    seen = {}
    for raw in lines:
        line = raw.strip("\r\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "=" not in line:
            return 1, ["A line in the settings file is not in the form NAME=value."]
        name, value = line.split("=", 1)
        if name != name.strip() or name not in ALLOWED:
            return 1, [f"The settings file contains a setting that is not allowed in this preview: {name.strip()[:40]}"]
        if name in seen:
            return 1, [f"The setting {name} appears twice. Keep only one line for it."]
        seen[name] = value
    if any("postgres" in v.lower() for v in seen.values()):
        return 1, ["The preview settings mention PostgreSQL."]
    for name, want in EXACT.items():
        if seen.get(name) != want:
            return 1, [f"The preview setting {name} is not the expected value."]
    if len(seen.get("JWT_SECRET", "")) < 40:
        return 1, ["The preview secret code is missing or too short."]
    if "GEMINI_API_KEY" not in seen:
        return 1, ["The line GEMINI_API_KEY= is missing from the settings file."]
    why = key_problem(seen["GEMINI_API_KEY"])
    if why:
        return 1, [why, "Fix the line GEMINI_API_KEY=... in the settings file, save it, and run this again."]
    if seen["GEMINI_API_KEY"] == "":
        return 2, ["No key has been added yet. The preview will run with AI OFF (built-in planner only)."]
    return 0, ["A key line is present (its value is hidden)."]


def check_settings():
    """Ask the real app code what it will use. Imported lazily so the file check works without packages."""
    from app.config import Settings, settings as s
    from app.database import engine as e

    keep = {"DATABASE_URL", "AI_PROVIDER", "REMINDERS_ENABLED", "FRONTEND_ORIGIN", "APP_URL", "GEMINI_MODEL"}
    names = {x.upper() for x in os.environ}
    bad = [k for k in Settings.model_fields if k.upper() in names and k.upper() not in keep]
    problems = []
    if bad:
        problems.append("Leftover Windows settings: " + ", ".join(sorted(bad)))
    if s.database_url != DB_URL or e.url.get_backend_name() != "sqlite" or e.url.database != "./preview.db":
        problems.append("The database is not the preview's own SQLite file.")
    if s.ai_provider != "gemini":
        problems.append("AI_PROVIDER is not gemini.")
    if s.gemini_model != MODEL:
        problems.append("The Gemini model name is not the expected one.")
    if s.gemini_base_url != GEMINI_URL:
        problems.append("The Gemini web address is not Google's official one.")
    if s.openai_api_key.strip():
        problems.append("An OpenAI key is set. It must not be in this preview.")
    if s.smtp_host or s.reminders_enabled:
        problems.append("E-mail or reminders are switched on.")
    if s.ai_allow_guests:
        problems.append("AI for guests is switched on.")
    if len(s.jwt_secret) < 40:
        problems.append("The secret code is too short.")
    if s.frontend_origin != WEB_URL or s.app_url != WEB_URL:
        problems.append("The website address setting is wrong.")
    why = key_problem(s.gemini_api_key)
    if why:
        problems.append(why)
    print("SAFETY CHECK:", "FAILED" if problems else "OK")
    for p in problems:
        print("  -", p)
    if problems:
        return 1
    if not s.gemini_api_key.strip():
        print("AI KEY: not set yet -> AI is OFF, the built-in planner is used.")
        return 2
    print("AI KEY: found (hidden) -> AI is ON using", s.gemini_model)
    return 0


def main(argv):
    mode = argv[1] if len(argv) > 1 else ""
    if mode == "file" and len(argv) == 3:
        code, msgs = check_env_file(argv[2])
        for m in msgs:
            print(m)
        return code
    if mode == "settings":
        return check_settings()
    print("usage: preview_ai_check.py file <path> | settings")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
