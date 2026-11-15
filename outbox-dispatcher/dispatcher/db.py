import asyncpg
import json

from .config import settings

_pool: asyncpg.Pool | None = None


async def init_pool() -> None:
    global _pool
    _pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=1,
        max_size=5,
        command_timeout=5,
        init=lambda conn: conn.set_type_codec(
            "jsonb",
            encoder=json.dumps,
            decoder=json.loads,
            schema="pg_catalog",
        ),
    )


async def close_pool() -> None:
    if _pool is not None:
        await _pool.close()


async def fetch_unpublished(limit: int) -> list[dict]:
    rows = await _pool.fetch(
        """
        SELECT id, event_type, payload
        FROM outbox
        WHERE published = false
        ORDER BY id
        LIMIT $1
        """,
        limit,
    )
    return [dict(r) for r in rows]


async def mark_published(ids: list[int]) -> None:
    if not ids:
        return
    await _pool.execute(
        "UPDATE outbox SET published = true, published_at = now() WHERE id = ANY($1::bigint[])",
        ids,
    )