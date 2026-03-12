"""Enqueue background jobs (e.g. AI refinement). Uses same Redis as arq worker."""

import logging

from arq import create_pool
from arq.connections import ArqRedis

from app.worker.worker_settings import get_redis_settings

logger = logging.getLogger(__name__)

_pool: ArqRedis | None = None
_init_failed = False


async def get_arq_pool() -> ArqRedis | None:
    """Create or return shared Arq Redis pool. Returns None if Redis unavailable."""
    global _pool, _init_failed
    if _pool is not None:
        return _pool
    if _init_failed:
        return None
    try:
        rs = get_redis_settings()
        _pool = await create_pool(rs)
        return _pool
    except Exception as e:
        logger.warning("Arq pool init failed: %s", e)
        _init_failed = True
        return None


async def close_arq_pool() -> None:
    global _pool, _init_failed
    if _pool is not None:
        await _pool.close()
        _pool = None
    _init_failed = False


async def enqueue_refine_test_result(result_id: int) -> bool:
    """Enqueue AI refinement job for the given test result. Returns True if enqueued."""
    pool = await get_arq_pool()
    if pool is None:
        return False
    try:
        await pool.enqueue_job("refine_test_result", result_id, _job_id=f"refine_test_{result_id}")
        return True
    except Exception as e:
        logger.exception("Failed to enqueue refine_test_result: %s", e)
        return False


async def enqueue_astrology_blueprint(user_id: int) -> bool:
    """Astrology blueprint (sun/moon/rising teaser). Updates User table."""
    pool = await get_arq_pool()
    if pool:
        await pool.enqueue_job("refine_astrology_blueprint", user_id, _job_id=f"astrology_blueprint_{user_id}")
        return True
    return False


async def enqueue_numerology_blueprint(user_id: int) -> bool:
    """Numerology blueprint (teaser items). Updates User table."""
    pool = await get_arq_pool()
    if pool:
        await pool.enqueue_job("refine_numerology_blueprint", user_id, _job_id=f"numerology_blueprint_{user_id}")
        return True
    return False
