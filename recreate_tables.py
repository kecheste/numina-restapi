import asyncio
from app.db.base import Base
import app.db.models  # This imports User, TestResult, etc. and registers them
from app.db.session import engine

async def force_create():
    async with engine.begin() as conn:
        print("Imported models. Base.metadata now contains tables:")
        print(list(Base.metadata.tables.keys()))
        print("Forcing table creation...")
        await conn.run_sync(Base.metadata.create_all)
        print("Done.")

if __name__ == "__main__":
    asyncio.run(force_create())
