"""SQLite returns naive datetimes; every stored time is UTC. The weekly numbers must not depend on the computer's own time zone."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.assist.summary import _d


def test_naive_stored_time_is_read_as_utc_whatever_the_machine_time_zone(monkeypatch):
    naive = datetime(2026, 10, 29, 22, 23)  # as SQLite returns it; meant as 22:23 UTC
    assert _d(naive, ZoneInfo("UTC")).isoformat() == "2026-10-29"
    assert _d(naive, ZoneInfo("Asia/Tokyo")).isoformat() == "2026-10-30"  # 07:23 next morning in Tokyo
    assert _d(naive.replace(tzinfo=timezone.utc), ZoneInfo("Asia/Tokyo")).isoformat() == "2026-10-30"
