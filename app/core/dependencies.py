from app.db.session import AsyncSessionLocal
from collections.abc import AsyncGenerator

async def get_db() -> AsyncGenerator:
    async with AsyncSessionLocal() as session:
        yield session
