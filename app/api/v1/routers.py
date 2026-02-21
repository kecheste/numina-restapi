from fastapi import APIRouter

from app.api.v1 import auth, health, users, tests, utils

router = APIRouter()
router.include_router(health.router)
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(tests.router, tags=["tests"])
router.include_router(utils.router, prefix="/utils", tags=["utils"])
