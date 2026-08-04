import json

import redis.asyncio as redis

from app.core.config import settings

_redis: redis.Redis | None = None

DREAM_CACHE_PREFIX = "dreams:recent:"
DREAM_CACHE_TTL = 3600
DREAM_CACHE_LIMIT = 10


async def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.close()
        _redis = None


async def cache_recent_dream(user_id: int, dream_data: dict) -> None:
    r = await get_redis()
    key = f"{DREAM_CACHE_PREFIX}{user_id}"
    await r.lpush(key, json.dumps(dream_data, ensure_ascii=False))
    await r.ltrim(key, 0, DREAM_CACHE_LIMIT - 1)
    await r.expire(key, DREAM_CACHE_TTL)


async def get_cached_dreams(user_id: int) -> list[dict]:
    r = await get_redis()
    key = f"{DREAM_CACHE_PREFIX}{user_id}"
    items = await r.lrange(key, 0, DREAM_CACHE_LIMIT - 1)
    return [json.loads(item) for item in items]


async def invalidate_dream_cache(user_id: int) -> None:
    r = await get_redis()
    await r.delete(f"{DREAM_CACHE_PREFIX}{user_id}")
