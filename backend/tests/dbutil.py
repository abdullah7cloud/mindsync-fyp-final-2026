"""
One place that decides which database the tests use.

Default: a throw-away in-memory SQLite database (fast, no server).
Set MINDSYNC_TEST_DATABASE_URL (e.g. postgresql+asyncpg://user:pass@localhost/mindsync_test) to run the SAME tests against
PostgreSQL: every test then starts from freshly created tables. Use a database that holds nothing you want to keep:
all MindSync tables in it are dropped and re-created.
"""
import os

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool, StaticPool

PG_URL = os.environ.get("MINDSYNC_TEST_DATABASE_URL", "")


async def make_engine(foreign_keys: bool = False):
    from app.database import Base
    import app.models  # noqa: F401  (registers every table)
    if PG_URL:
        engine = create_async_engine(PG_URL, poolclass=NullPool)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        return engine
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if foreign_keys:
            await conn.exec_driver_sql("PRAGMA foreign_keys=ON")     # SQLite ignores foreign keys unless asked
    return engine


async def seed(db, objs):
    """Insert test rows parents first (users, then tasks, then the rest). SQLite ignores foreign keys, PostgreSQL enforces them."""
    from app.models import Task, User
    for group in ([o for o in objs if isinstance(o, User)], [o for o in objs if isinstance(o, Task)],
                  [o for o in objs if not isinstance(o, (User, Task))]):
        if group:
            db.add_all(group)
            await db.flush()
    await db.commit()
