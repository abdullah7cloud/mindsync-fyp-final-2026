"""
FastAPI application assembly: CORS, router registration, and a health
check. This is the ASGI entrypoint run by uvicorn (see README.md):

    uvicorn app.main:app --reload
"""
import asyncio
import logging
import traceback
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.account import router as account_router
from app.auth import router as auth_router
from app.config import settings
from app.passwordreset import router as passwordreset_router
from app.database import AsyncSessionLocal, ensure_schema, warm_pool
from app.modelcards import router as modelcards_router
from app.notifications import router as notifications_router
from app.notifier import config_problems, delivery_mode, reminder_loop
from app.demo import router as demo_router
from app.taskaware.routes import demo_router as smart_demo_router, router as smart_router
from app.assist import models as _assist_models  # noqa: F401  (registers the new tables so create_all builds them)
from app.assist.prefs import router as prefs_router
from app.assist.reminders import router as reminders_router
from app.studio import models as _studio_models  # noqa: F401  (registers the Learning Studio tables)
from app.studio.routes import demo_router as studio_demo_router, router as studio_router
from app.assist.roadmap import demo_router as roadmap_demo_router, router as roadmap_router
from app.assist.routes import demo_router as assist_demo_router, router as assist_router
from app.simple import models as _simple_models  # noqa: F401  (registers the study-plan, notes and documents tables)
from app.simple.study import router as study_router
from app.simple.notebook import router as notebook_router
from app.profile28 import models as _profile28_models  # noqa: F401  (registers the Update 28 tables)
from app.profile28.routes import router as profile28_router
from app.profile28 import reminders as profile28_reminders
from app.feedback import router as feedback_router
from app.energy import router as energy_router
from app.planner import router as planner_router
from app.recommend import router as recommend_router
from app.tasks import router as tasks_router
from app.wellbeing import router as wellbeing_router

log = logging.getLogger("mindsync")

# A small, private error log: backend/logs/backend_errors.log (kept out of Git). When a request fails with an unexpected
# server error (HTTP 500) the user only sees "Internal Server Error", and the details used to appear only in the
# console window. This file keeps WHERE it failed (exception type and code lines) so a problem can be diagnosed
# afterwards. It deliberately does NOT store the exception message, request body, e-mail or password, because database
# error messages can contain the values that were being saved.
_LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
try:
    _LOG_DIR.mkdir(exist_ok=True)
    _handler = RotatingFileHandler(_LOG_DIR / "backend_errors.log", maxBytes=200_000, backupCount=2, encoding="utf-8")
    _handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    log.addHandler(_handler)
    log.setLevel(logging.INFO)
except OSError:   # read-only folder: the API still works, it just has no file log
    pass


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Start-up: bring the database schema up to date, then start the e-mail alert job."""
    try:
        await ensure_schema()
    except Exception as exc:  # the API should still start; routes will report DB errors themselves
        log.warning("Database schema check failed: %s", type(exc).__name__)
    try:
        seconds = await warm_pool()
        if seconds:
            log.info("Database connection pool opened in advance (%.2f s)", seconds)
    except Exception as exc:  # not fatal: connections are then opened on demand
        log.warning("Could not open the connection pool in advance: %s", type(exc).__name__)
    task = None
    # One clear line about email mode at start-up (never contains a password).
    log.info("Email alerts: %s", "real email via SMTP" if delivery_mode() == "smtp" else "demo mode (saved to backend/outbox)")
    for problem in config_problems():
        log.warning("Email settings: %s", problem)
    if settings.reminders_enabled:
        task = asyncio.create_task(reminder_loop(AsyncSessionLocal))
    task28 = None
    if settings.task_reminders_enabled:      # Update 28: e-mail reminders chosen in Settings. Only students who switched them on get anything.
        task28 = asyncio.create_task(profile28_reminders.loop(AsyncSessionLocal, settings.task_reminder_check_minutes))
    try:
        yield
    finally:
        if task:
            task.cancel()
        if task28:
            task28.cancel()


app = FastAPI(
    lifespan=lifespan,
    title="MindSync API",
    description=(
        "Study task management API: a local heuristic plus locally trained models "
        "(task fit, wellbeing / stress risk). No external AI service is used. "
        "See the project report for the full system design."
    ),
    version="0.7.0",
)

# Only the configured frontend origin is allowed — a deliberately narrow
# CORS policy rather than a wildcard, per the contract's OWASP Top 10
# adherence target (broad CORS is a common misconfiguration flagged under
# A05:2021).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def log_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Record where an unexpected error happened (no message, no user data), then answer with a plain 500."""
    frames = traceback.extract_tb(exc.__traceback__)[-6:]
    where = " <- ".join(f"{Path(f.filename).name}:{f.lineno} {f.name}" for f in reversed(frames))
    log.error("500 %s %s: %s | %s", request.method, request.url.path, type(exc).__name__, where)
    return JSONResponse({"detail": "Internal Server Error"}, status_code=500)


@app.middleware("http")
async def security_headers(request, call_next):
    """Standard defensive HTTP headers on every API response (OWASP A05:2021)."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    return response


app.include_router(auth_router)
app.include_router(passwordreset_router)
app.include_router(account_router)
app.include_router(feedback_router)
app.include_router(tasks_router)
app.include_router(energy_router)
app.include_router(recommend_router)
app.include_router(planner_router)
app.include_router(wellbeing_router)
app.include_router(modelcards_router)
app.include_router(notifications_router)
app.include_router(demo_router)
app.include_router(smart_router)
app.include_router(smart_demo_router)
app.include_router(assist_router)
app.include_router(roadmap_router)
app.include_router(roadmap_demo_router)
app.include_router(reminders_router)
app.include_router(studio_router)
app.include_router(studio_demo_router)
app.include_router(assist_demo_router)
app.include_router(prefs_router)
app.include_router(study_router)
app.include_router(notebook_router)
app.include_router(profile28_router)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}
