"""Create backend/.env on first run (no Notepad needed). Run by start-backend.bat when the file is missing.
Asks for the PostgreSQL password locally; nothing is sent anywhere. Never commit the resulting .env."""
import pathlib
import secrets
import sys
from urllib.parse import quote

target = pathlib.Path(__file__).resolve().parents[1] / ".env"
if target.exists() and "--force" not in sys.argv:
    print(".env already exists:", target)
    sys.exit(0)

print()
print("MindSync needs your PostgreSQL password (the one you chose when you installed PostgreSQL).")
pw = ""
while not pw:
    pw = input("PostgreSQL password: ").strip()   # no default password is stored in the code
db = input("Database name [mindsync]: ").strip() or "mindsync"

lines = [
    f"DATABASE_URL=postgresql+asyncpg://postgres:{quote(pw, safe='')}@127.0.0.1:5432/{db}",
    f"JWT_SECRET={secrets.token_urlsafe(48)}",
    "JWT_ALGORITHM=HS256",
    "ACCESS_TOKEN_EXPIRE_MINUTES=60",
    "FRONTEND_ORIGIN=http://localhost:5173",
    "REMINDERS_ENABLED=true",
    "APP_URL=http://localhost:5173",
    "OPENAI_API_KEY=",
]
target.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("Created", target)
