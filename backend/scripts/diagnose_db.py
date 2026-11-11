"""
Database-only timing (no web server, no HTTP). Tells us whether slowness under parallel use comes from PostgreSQL / the
driver / the connection pool, or from the web layer.

    python -m scripts.diagnose_db

It reads DATABASE_URL from backend/.env like the app does, never prints the password, and only runs SELECTs.
Measures, in milliseconds:
  1. opening a brand-new connection (raw driver)         - expensive on some Windows setups (password hashing)
  2. one trivial query on an already-open connection     - the round trip to PostgreSQL
  3. the app's own engine and pool: sequential queries, then parallel ones (1, 5, 10, 20 at once)
  4. the same parallel test with a larger pool and without 'pre-ping'
"""
import asyncio
import platform
import statistics
import sys
import time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings


def ms(x):
    return round(x * 1000, 1)


async def raw_connect_times(url: str, n: int = 5):
    import asyncpg
    dsn = url.replace("postgresql+asyncpg://", "postgresql://")
    out = []
    for _ in range(n):
        t0 = time.perf_counter()
        conn = await asyncpg.connect(dsn)
        out.append(time.perf_counter() - t0)
        await conn.close()
    return out


async def query_once(maker):
    async with maker() as s:
        await s.execute(text("SELECT count(*) FROM tasks"))


async def parallel(maker, n_clients: int, per_client: int = 10):
    times, errors = [], []

    async def client():
        for _ in range(per_client):
            t0 = time.perf_counter()
            try:
                await query_once(maker)
                times.append(time.perf_counter() - t0)
            except BaseException as exc:          # MemoryError etc. are reported, not allowed to stop the test
                errors.append(type(exc).__name__)
    t0 = time.perf_counter()
    await asyncio.gather(*[client() for _ in range(n_clients)])
    wall = time.perf_counter() - t0
    if not times:
        return {"clients": n_clients, "all_failed": sorted(set(errors))}
    return {"clients": n_clients, "median_ms": ms(statistics.median(times)),
            "p95_ms": ms(sorted(times)[int(0.95 * (len(times) - 1))]), "max_ms": ms(max(times)),
            "queries_per_s": round(len(times) / wall, 1), "errors": len(errors),
            **({"error_types": sorted(set(errors))} if errors else {})}


def memory_report() -> str:
    """Free physical memory and this process's peak memory (Windows only; plain ctypes, no extra packages)."""
    if platform.system() != "Windows":
        return "(memory report only on Windows)"
    import ctypes

    class MEMSTAT(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
    m = MEMSTAT()
    m.dwLength = ctypes.sizeof(MEMSTAT)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    gb = lambda b: round(b / 1024 ** 3, 2)
    return (f"memory in use {m.dwMemoryLoad}%  | physical free {gb(m.ullAvailPhys)} of {gb(m.ullTotalPhys)} GB  | "
            f"commit (page file) free {gb(m.ullAvailPageFile)} of {gb(m.ullTotalPageFile)} GB  | "
            f"this process is {'64' if sys.maxsize > 2**32 else '32'}-bit")


async def warm_up(eng, n: int) -> float:
    """Open n connections at the same time, then hand them back to the pool (what the app now does at start-up)."""
    t0 = time.perf_counter()
    conns = await asyncio.gather(*[eng.connect() for _ in range(n)])
    for c in conns:
        await c.close()
    return time.perf_counter() - t0


async def main():
    print(f"Python {platform.python_version()} on {platform.system()}, event loop: {type(asyncio.get_running_loop()).__name__}")
    url = settings.database_url
    print("driver/dialect:", url.split("://")[0])
    print("system:", memory_report(), flush=True)
    c = await raw_connect_times(url)
    print(f"1. new raw connection x5: median {ms(statistics.median(c))} ms, max {ms(max(c))} ms")

    for label, kwargs, warm in (("A. old settings: default pool, pre-ping, NOT warmed", dict(pool_pre_ping=True), 0),
                                ("B. new settings: pool of 10 opened in advance", dict(pool_pre_ping=True, pool_size=10, max_overflow=10, pool_recycle=1800), 10)):
        eng = create_async_engine(url, **kwargs)
        maker = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
        async with eng.connect() as conn:
            r = await conn.execute(text("SHOW max_connections"))
            if label.startswith("A"):
                print("   PostgreSQL max_connections:", r.scalar())
        if warm:
            print(f"     opening {warm} connections in advance took {ms(await warm_up(eng, warm))} ms", flush=True)
        else:
            await query_once(maker)
        seq = []
        for _ in range(50):
            t0 = time.perf_counter()
            await query_once(maker)
            seq.append(time.perf_counter() - t0)
        print(f"2/3. {label}: sequential median {ms(statistics.median(seq))} ms, p95 {ms(sorted(seq)[47])} ms")
        for n in (1, 5, 10, 20):
            print("     parallel", await parallel(maker, n), flush=True)
        print("     system:", memory_report(), flush=True)
        await eng.dispose()


if __name__ == "__main__":
    asyncio.run(main())
