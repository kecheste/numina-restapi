"""Arq worker settings: Redis and task list."""

from arq.connections import RedisSettings

from app.core.config import settings
from app.worker.tasks import refine_test_result, startup


def get_redis_settings() -> RedisSettings:
    """Parse REDIS_URL into Arq RedisSettings."""
    # redis://localhost:6379/0 -> host, port, database
    url = settings.redis_url
    if url.startswith("redis://"):
        url = url[8:]
    elif url.startswith("rediss://"):
        url = url[9:]
    parts = url.split("/")
    host_port = parts[0]
    database = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    if ":" in host_port:
        host, port = host_port.rsplit(":", 1)
        port = int(port)
    else:
        host = host_port
        port = 6379
    return RedisSettings(host=host, port=port, database=database)


class WorkerSettings:
    """Arq worker config."""

    functions = [refine_test_result]
    redis_settings = get_redis_settings()
    on_startup = startup
    max_jobs = 5
    job_timeout = 120  # 2 min per AI job
