"""Arq worker settings: Redis and task list."""

from dataclasses import replace

from arq.connections import RedisSettings

from app.core.config import settings
from app.core.redis import normalize_redis_url
from app.worker.tasks import refine_test_result, startup


def get_redis_settings() -> RedisSettings:
    url = normalize_redis_url(settings.redis_url)
    rs = RedisSettings.from_dsn(url)
    if "redislabs.com" in settings.redis_url and rs.ssl:
        rs = replace(rs, ssl_cert_reqs="none")
    return rs


class WorkerSettings:
    """Arq worker config. max_jobs=1 to avoid bursting OpenAI (429) with parallel LLM calls."""

    functions = [refine_test_result]
    redis_settings = get_redis_settings()
    on_startup = startup
    max_jobs = 1
    job_timeout = 120
