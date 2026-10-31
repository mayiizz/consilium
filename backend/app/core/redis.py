from typing import Optional

import redis.asyncio as aioredis

from app.core.config import get_settings

_redis: Optional[aioredis.Redis] = None


async def connect_redis() -> aioredis.Redis:
    global _redis
    settings = get_settings()
    _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    await _redis.ping()
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.close()
    _redis = None


def get_redis() -> aioredis.Redis:
    if _redis is None:
        raise RuntimeError("Redis not initialized")
    return _redis
