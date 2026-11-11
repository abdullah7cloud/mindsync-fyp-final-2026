"""Small helper for studio tests: change a pack's status directly in the test database."""
import uuid

from app.database import get_db
from app.main import app
from app.studio.models import LearningPack


def set_status(api, pack_id: str, status: str) -> None:
    import asyncio

    async def go():
        gen = app.dependency_overrides[get_db]()
        db = await gen.__anext__()
        p = await db.get(LearningPack, uuid.UUID(pack_id))
        p.status = status
        await db.commit()
        await gen.aclose()
    # the test client runs the app on its own loop; run the update on a loop of our own (SQLite file/memory shared via the override's engine)
    loop = api.client.portal if hasattr(api.client, "portal") else None
    if loop is not None:
        loop.call(go)
    else:
        asyncio.new_event_loop().run_until_complete(go())
