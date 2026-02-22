import asyncio
import os
from pathlib import Path

_backend_root = Path(__file__).resolve().parent.parent
_env_file = _backend_root / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = value

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_database_url_and_connect_args, settings
from app.db.base import Base
from app.db.models import User, TestResult

config = context.config
_db_url, _connect_args = get_database_url_and_connect_args()
config.set_main_option("sqlalchemy.url", _db_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    _url, _connect_args = get_database_url_and_connect_args()
    if "neon.tech" in _url:
        print("Alembic: running migrations against Neon database (neon.tech)")
    connectable = create_async_engine(_url, poolclass=NullPool, connect_args=_connect_args)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
