import asyncpg

from .config import settings

_pool: asyncpg.Pool | None = None


async def init_pool() -> None:
    global _pool
    _pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=2,
        max_size=10,
        command_timeout=5,
    )


async def close_pool() -> None:
    if _pool is not None:
        await _pool.close()


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("DB pool is not initialized")
    return _pool


async def create_user(username: str, hashed_password: str, role: str, is_active: bool = True) -> dict | None:
    row = await get_pool().fetchrow(
        """
        INSERT INTO users (username, hashed_password, role, is_active)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (username) DO NOTHING
        RETURNING id, username, role, is_active
        """,
        username, hashed_password, role, is_active,
    )
    return dict(row) if row else None


async def get_user_by_username(username: str) -> dict | None:
    row = await get_pool().fetchrow(
        "SELECT id, username, hashed_password, role, is_active FROM users WHERE username = $1",
        username,
    )
    return dict(row) if row else None


async def approve_user(username: str) -> dict | None:
    row = await get_pool().fetchrow(
        "UPDATE users SET is_active = true WHERE username = $1 RETURNING id, username, role, is_active",
        username,
    )
    return dict(row) if row else None


async def upsert_shipment(tracking_no: str, status: str, client_id: str | None = None) -> dict:
    row = await get_pool().fetchrow(
        """
        INSERT INTO shipments (tracking_no, status, client_id, updated_at)
        VALUES ($1, $2, $3, now())
        ON CONFLICT (tracking_no)
        DO UPDATE SET status = EXCLUDED.status, updated_at = now()
        RETURNING tracking_no, status, client_id, updated_at
        """,
        tracking_no, status, client_id,
    )
    return dict(row)


async def fetch_shipment(tracking_no: str) -> dict | None:
    row = await get_pool().fetchrow(
        "SELECT tracking_no, status, client_id, updated_at FROM shipments WHERE tracking_no = $1",
        tracking_no,
    )
    return dict(row) if row else None


async def delete_shipment(tracking_no: str) -> bool:
    result = await get_pool().execute(
        "DELETE FROM shipments WHERE tracking_no = $1",
        tracking_no,
    )
    return result.endswith(" 1")