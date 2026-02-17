import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.v1.routers import router as api_router
from app.core.config import settings
from app.core.redis import init_redis, close_redis
from app.core.queue import get_arq_pool, close_arq_pool

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: Redis + Arq pool. Shutdown: close both."""
    try:
        await init_redis()
    except Exception as e:
        logger.warning("Redis init failed (caching disabled): %s", e)
    await get_arq_pool()  # no-op if Redis down
    yield
    await close_arq_pool()
    await close_redis()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


app.include_router(api_router, prefix=settings.api_v1_prefix)
