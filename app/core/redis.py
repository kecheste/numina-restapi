"""Redis client and cache helpers. Used by cache layer and arq worker."""

import json
from typing import Any

import redis.asyncio as redis

from app.core.config import settings

# Global client; set in lifespan if needed
_redis: redis.Redis | None = None

CACHE_TTL_SECONDS = 300  # 5 min default
AI_RESULT_CACHE_TTL = 86400 * 7  # 7 days for AI results
USER_PROFILE_CACHE_TTL = 300  # 5 min
TEST_LIST_CACHE_TTL = 600  # 10 min


def get_redis() -> redis.Redis | None:
    """Return Redis client if initialized; None otherwise."""
    return _redis


async def init_redis() -> redis.Redis:
    """Create and store async Redis client from settings."""
    global _redis
    _redis = redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    return _redis


async def close_redis() -> None:
    """Close Redis connection (lifespan shutdown)."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


async def cache_get(key: str) -> Any | None:
    """Get JSON value from cache. Returns None if missing, invalid, or Redis down."""
    if _redis is None:
        return None
    try:
        raw = await _redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except (json.JSONDecodeError, Exception):
        return None


async def cache_set(
    key: str,
    value: Any,
    ttl_seconds: int = CACHE_TTL_SECONDS,
) -> None:
    """Set JSON value in cache with TTL. No-op if Redis not initialized."""
    if _redis is None:
        return
    try:
        await _redis.set(key, json.dumps(value), ex=ttl_seconds)
    except Exception:
        pass


async def cache_delete(key: str) -> None:
    """Delete a cache key (e.g. on profile update)."""
    if _redis is None:
        return
    try:
        await _redis.delete(key)
    except Exception:
        pass


def cache_key_user_profile(user_id: int) -> str:
    return f"user:profile:{user_id}"


def cache_key_test_list() -> str:
    return "tests:list"


def cache_key_ai_result(test_id: int, user_id: int, answer_hash: str) -> str:
    """Cache key for AI refinement result to avoid duplicate OpenAI calls."""
    return f"ai:result:{test_id}:{user_id}:{answer_hash}"
