import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import ProgrammingError, OperationalError

import os
import subprocess
import sys
from pathlib import Path

from app.api.v1.routers import router as api_router
from app.core.config import settings
from app.core.redis import init_redis, close_redis
from app.core.queue import get_arq_pool, close_arq_pool
from app.db.seed import run_seed

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parent.parent

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: run DB migrations (so users table exists), Redis + Arq pool. Shutdown: close both."""
    import asyncio

    def _run_migrations() -> None:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=str(_BACKEND_ROOT),
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Migrations failed: {result.stderr or result.stdout or 'unknown'}"
            )

    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _run_migrations)
    except Exception as e:
        logger.exception("Database migrations failed: %s", e)
        raise
    try:
        await init_redis()
    except Exception as e:
        logger.warning("Redis init failed (caching disabled): %s", e)
    await get_arq_pool()
    try:
        await run_seed()
    except Exception as e:
        logger.warning("Seed failed (non-fatal): %s", e)
    yield
    await close_arq_pool()
    await close_redis()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


@app.exception_handler(ProgrammingError)
@app.exception_handler(OperationalError)
async def db_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Return database errors so clients see e.g. 'relation users does not exist'."""
    logger.exception("Database error: %s", exc)
    orig = getattr(exc, "orig", None)
    msg = str(orig) if orig is not None else str(exc)
    return JSONResponse(
        status_code=503,
        content={"detail": f"Database error: {msg}"},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


app.include_router(api_router, prefix=settings.api_v1_prefix)
