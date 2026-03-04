from fastapi import APIRouter

from app.api.v1 import admin, auth, daily_message, health, users, tests, utils, subscription, webhooks, synthesis

router = APIRouter()
router.include_router(health.router)
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(tests.router, tags=["tests"])
router.include_router(utils.router, prefix="/utils", tags=["utils"])
router.include_router(subscription.router)
router.include_router(webhooks.router)
router.include_router(synthesis.router)
router.include_router(daily_message.router)
router.include_router(admin.router)
