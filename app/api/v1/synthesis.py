"""Synthesis: GET current user's preview or full synthesis (JSON for synthesis screen)."""

from fastapi import APIRouter, Depends

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.synthesis import SYNTHESIS_FULL_MIN_TESTS, SYNTHESIS_PREVIEW_MIN_TESTS
from app.core.dependencies import get_current_active_user, get_db
from app.core.exceptions import not_found
from app.db.models.test_result import TestResult
from app.db.models.user import User as UserModel
from app.db.models.user_synthesis import UserSynthesis
from app.schemas.synthesis import SynthesisResultResponse

router = APIRouter(tags=["synthesis"])


@router.get("/synthesis", response_model=SynthesisResultResponse)
async def get_synthesis(
    user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    count_result = await db.execute(
        select(func.count(TestResult.id)).where(
            TestResult.user_id == user.id,
            TestResult.status == "completed",
        )
    )
    completed_count = count_result.scalar() or 0

    if completed_count >= SYNTHESIS_FULL_MIN_TESTS and user.is_premium:
        row = await db.execute(
            select(UserSynthesis).where(
                UserSynthesis.user_id == user.id,
                UserSynthesis.synthesis_type == "full",
            )
        )
        syn = row.scalar_one_or_none()
        if syn:
            return SynthesisResultResponse(
                type="full",
                completed_count=completed_count,
                result=syn.result_json,
            )

    if completed_count >= SYNTHESIS_PREVIEW_MIN_TESTS:
        row = await db.execute(
            select(UserSynthesis).where(
                UserSynthesis.user_id == user.id,
                UserSynthesis.synthesis_type == "preview",
            )
        )
        syn = row.scalar_one_or_none()
        if syn:
            return SynthesisResultResponse(
                type="preview",
                completed_count=completed_count,
                result=syn.result_json,
            )
    raise not_found("Complete at least 3 tests to unlock your synthesis.")
