"""Redis client and cache helpers. Used by cache layer and arq worker."""

import json
from typing import Any

import redis.asyncio as redis

from app.core.config import settings

_redis: redis.Redis | None = None

CACHE_TTL_SECONDS = 300
AI_RESULT_CACHE_TTL = 86400 * 7
USER_PROFILE_CACHE_TTL = 300
TEST_LIST_CACHE_TTL = 600

def get_redis() -> redis.Redis | None:
    return _redis

def normalize_redis_url(url: str) -> str:
    url = url.strip()
    if "redislabs.com" not in url:
        return url
    if url.startswith("rediss://") and "ssl_cert_reqs" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}ssl_cert_reqs=none"
    return url


async def init_redis() -> redis.Redis:
    global _redis
    url = normalize_redis_url(settings.redis_url)
    _redis = redis.from_url(
        url,
        encoding="utf-8",
        decode_responses=True,
    )
    await _redis.ping()
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


async def cache_get(key: str) -> Any | None:
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
    if _redis is None:
        return
    try:
        await _redis.set(key, json.dumps(value), ex=ttl_seconds)
    except Exception:
        pass


async def cache_delete(key: str) -> None:
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
    return f"ai:result:{test_id}:{user_id}:{answer_hash}"
