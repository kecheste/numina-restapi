from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import get_database_url_and_connect_args

_db_url, _connect_args = get_database_url_and_connect_args()

engine = create_async_engine(
    _db_url,
    future=True,
    echo=False,
    connect_args=_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)
