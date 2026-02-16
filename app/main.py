from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.routers import router as api_router

app = FastAPI(title=settings.app_name)

app.include_router(api_router, prefix=settings.api_v1_prefix)
