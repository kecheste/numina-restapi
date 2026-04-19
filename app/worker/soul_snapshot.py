import json
import logging
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.prompts import SOUL_SNAPSHOT_SYSTEM, SOUL_SNAPSHOT_USER_TEMPLATE
from app.db.models.user import User as UserModel
from app.db.models.test_result import TestResult
from app.worker.helpers import zodiac_from_date

logger = logging.getLogger(__name__)

# Tests that have a major impact on the Soul Snapshot
CORE_IDENTITY_TEST_IDS = {1, 2, 7, 8, 9, 10, 13, 14, 15, 19, 20, 24}

async def generate_soul_snapshot(session: AsyncSession, user_id: int, refresh_pulse_only: bool = False) -> None:
    """
    Generates or refreshes the user's Soul Snapshot.
    If refresh_pulse_only=True, we keep the existing summary/sure_things and only refresh message/quote.
    """
    user_result = await session.execute(select(UserModel).where(UserModel.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return

    today_str = date.today().isoformat()
    
    # If we are only refreshing the daily pulse (message/quote) and it's already today, skip
    if refresh_pulse_only and user.soul_snapshot and user.soul_snapshot.get("daily_date") == today_str:
        return

    # 1. Gather Data Signals
    signals = []
    
    # A) Birth Data & Basic Profile
    if user.birth_month and user.birth_day:
        zodiac = zodiac_from_date(user.birth_month, user.birth_day)
        signals.append(f"Zodiac: {zodiac}")
    
    if user.mbti_type:
        signals.append(f"MBTI: {user.mbti_type} ({user.mbti_descriptor or ''})")
        
    if user.life_path_number:
        signals.append(f"Life Path: {user.life_path_number}")

    # B) Latest Core Test Results
    results_query = await session.execute(
        select(TestResult)
        .where(
            TestResult.user_id == user_id,
            TestResult.test_id.in_(CORE_IDENTITY_TEST_IDS),
            TestResult.status == "completed"
        )
        .order_by(TestResult.completed_at.desc())
    )
    results = results_query.scalars().all()
    
    # Deduplicate by test_id to get only the latest of each
    latest_results = {}
    for r in results:
        if r.test_id not in latest_results:
            latest_results[r.test_id] = r
            
    for test_id, r in latest_results.items():
        title = r.personality_type or r.test_title
        insights = ", ".join(r.insights[:3]) if r.insights else ""
        signals.append(f"{title}: {insights}")

    # C) Existing Snapshot (to maintain consistency if refresh_pulse_only)
    existing_snapshot = user.soul_snapshot or {}
    
    # 2. Call LLM
    if not settings.openai_api_key:
        # Fallback
        user.soul_snapshot = {
            "summary": "A deep seeker navigating an evolving path of self-discovery.",
            "sure_things": ["Intuitive", "Reflective", "Grounded"],
            "daily_message": "Today is a day for gentle observation. Watch the patterns without judging them.",
            "daily_quote": "The quietest water runs the deepest.",
            "daily_date": today_str,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    else:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            
            input_data = "\n".join(signals)
            if refresh_pulse_only:
                input_data += f"\n\nExisting Identity Context: {existing_snapshot.get('summary', '')}"

            user_prompt = SOUL_SNAPSHOT_USER_TEMPLATE.format(input_data=input_data)
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SOUL_SNAPSHOT_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=500,
                temperature=0.7,
            )
            raw = (response.choices[0].message.content or "").strip()
            raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            data = json.loads(raw)
            
            new_snapshot = {
                "summary": existing_snapshot.get("summary") if refresh_pulse_only and existing_snapshot.get("summary") else data.get("summary"),
                "sure_things": existing_snapshot.get("sure_things") if refresh_pulse_only and existing_snapshot.get("sure_things") else data.get("sure_things"),
                "daily_message": data.get("daily_message"),
                "daily_quote": data.get("daily_quote"),
                "daily_date": today_str,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            user.soul_snapshot = new_snapshot
            
        except Exception as e:
            logger.error(f"Failed to generate soul snapshot for user {user_id}: {e}")
            # Don't overwrite if it failed, just let it be

    await session.commit()
