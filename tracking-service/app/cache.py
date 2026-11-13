import json

import redis.asyncio as redis

from .config import settings

_client: redis.Redis | None = None


async def init_cache() -> None:
    global _client
    _client = redis.from_url(settings.redis_url, decode_responses=True)
    await _client.ping()


async def close_cache() -> None:
    if _client is not None:
        await _client.aclose()


def get_cache() -> redis.Redis:
    if _client is None:
        raise RuntimeError("Redis client is not initialized")
    return _client


def status_key(tracking_no: str) -> str:
    return f"shipment:{tracking_no}:status"


async def get_status(tracking_no: str) -> dict | None:
    raw = await get_cache().get(status_key(tracking_no))
    return json.loads(raw) if raw else None


async def set_status(tracking_no: str, payload: dict) -> None:
    await get_cache().set(
        status_key(tracking_no),
        json.dumps(payload, default=str),
        ex=settings.status_ttl_sec,
    )