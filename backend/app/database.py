"""
Async SQLAlchemy engine/session setup.

Using the async engine end-to-end (asyncpg driver) is what lets the API
stay responsive under the sub-3-second latency target agreed in the
project contract, rather than blocking a worker thread per DB call.
"""
import asyncio
import time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

def _engine_options(url: str) -> dict:
    """
    Connection-pool settings (PostgreSQL only; SQLite used in tests manages its own connections).

    Why this matters: PostgreSQL starts a separate operating-system process for every connection, and on a Windows
    laptop that took about 380 ms per new connection (measured with scripts/diagnose_db.py; 7 ms on Linux). If the pool
    opens connections only when a request needs one, students who arrive together each wait for a slow connection and
    the API falls behind. So the pool is sized for the expected number of simultaneous students and is opened in
    advance at start-up (warm_pool below).
      pool_size / max_overflow  steady connections / extra connections allowed in a burst
      pool_pre_ping             test a connection before using it, so a restarted database never causes an error page
      pool_recycle              replace connections after 30 minutes (some servers drop idle ones)
      pool_timeout              wait at most 10 s for a free connection, then fail clearly instead of hanging
      connect timeout           give up on a database that is not answering after 10 s
    """
    if not url.startswith("postgresql"):
        return {}
    return {"pool_size": settings.db_pool_size, "max_overflow": settings.db_max_overflow, "pool_pre_ping": True,
            "pool_recycle": 1800, "pool_timeout": 10, "connect_args": {"timeout": 10}}


engine = create_async_engine(settings.database_url, future=True, **_engine_options(settings.database_url))

AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency: yields a request-scoped DB session and always closes it."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_models() -> None:
    """
    Dev/first-run convenience: creates tables from the ORM models if they
    don't exist yet. database/schema.sql holds the equivalent raw SQL. A bigger project would
    use a migration tool (e.g. Alembic); here the small _MIGRATIONS list below is enough.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Columns added after the first release. create_all() never alters an existing
# table, so these idempotent statements bring an older database up to date
# (safe to run on every start-up).
_MIGRATIONS = [
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_alerts BOOLEAN NOT NULL DEFAULT TRUE",
    "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS reminder_sent_at TIMESTAMPTZ NULL",
    "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ NULL",
    # Tasks finished before this column existed: use their last-change time as the best estimate.
    # My Tasks (update 24): per-block progress and edits
    "ALTER TABLE plan_sessions ADD COLUMN IF NOT EXISTS actual_minutes INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE plan_sessions ADD COLUMN IF NOT EXISTS title VARCHAR(200) NULL",
    "ALTER TABLE plan_sessions ADD COLUMN IF NOT EXISTS subject VARCHAR(100) NULL",
    "ALTER TABLE plan_sessions ADD COLUMN IF NOT EXISTS manual BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE plan_sessions ADD COLUMN IF NOT EXISTS original_day DATE NULL",
    "ALTER TABLE plan_sessions ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ NULL",
    "ALTER TABLE plan_sessions ADD COLUMN IF NOT EXISTS felt VARCHAR(10) NULL",
    # blocks that were already marked done before actual minutes existed: use the planned minutes as the best estimate
    "UPDATE plan_sessions SET actual_minutes = minutes WHERE status = 'done' AND actual_minutes = 0",
    "UPDATE tasks SET completed_at = updated_at WHERE status = 'completed' AND completed_at IS NULL",
]


async def warm_pool() -> float:
    """
    Open the pool's steady connections at the same time, then hand them back (they stay open and ready).
    Returns the seconds it took. Does nothing for SQLite. Called once at start-up.
    """
    if engine.dialect.name != "postgresql":
        return 0.0
    t0 = time.perf_counter()
    conns = await asyncio.gather(*[engine.connect() for _ in range(settings.db_pool_size)])
    for c in conns:
        await c.close()
    return time.perf_counter() - t0


async def ensure_schema() -> None:
    """Create missing tables and add any newer columns. Called once at start-up."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if engine.dialect.name == "postgresql":
            for stmt in _MIGRATIONS:
                await conn.execute(text(stmt))
