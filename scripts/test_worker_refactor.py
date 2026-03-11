import asyncio
import json
import logging
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models.user import User as UserModel
from app.db.models.test_result import TestResult
from app.worker.tasks import refine_astrology_blueprint, refine_numerology_blueprint, refine_test_result

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_worker_refactor():
    async with AsyncSessionLocal() as session:
        # 1. Get or create a test user
        result = await session.execute(select(UserModel).where(UserModel.email == "admin@numina.ai"))
        user = result.scalar_one_or_none()
        if not user:
            logger.info("Test user not found, please create one or run seed.")
            return

        # Ensure user has birth data for calculations
        if user.birth_year is None:
            user.birth_year = 1990
            user.birth_month = 1
            user.birth_day = 1
            user.birth_time = "12:00"
            user.birth_place_lat = 40.7128
            user.birth_place_lng = -74.0060
            user.birth_place_timezone = "America/New_York"
            user.name = "Admin"
            user.full_name = "Admin User"
            session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info("Updated test user with birth data")

        logger.info(f"Using test user: {user.email} (ID: {user.id})")

        # 2. Verify Astrology Blueprint Task
        logger.info("--- Testing refine_astrology_blueprint ---")
        row = TestResult(
            user_id=user.id,
            test_id=25,
            test_title="Astrology Blueprint",
            category="Cosmic Identity",
            answers={},
            status="pending_ai",
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        
        logger.info(f"Created Astrology Blueprint result (ID: {row.id}) with status {row.status}")
        
        # Simulate worker call
        await refine_astrology_blueprint({}, row.id)
        
        await session.refresh(row)
        logger.info(f"Processed Astrology Blueprint status: {row.status}")
        if row.status == "completed" and row.llm_result_json:
            logger.info("✅ Astrology Blueprint success")
        else:
            logger.error("❌ Astrology Blueprint failed")

        # 3. Verify Numerology Blueprint Task
        logger.info("--- Testing refine_numerology_blueprint ---")
        row_num = TestResult(
            user_id=user.id,
            test_id=26,
            test_title="Numerology Blueprint",
            category="Cosmic Identity",
            answers={},
            status="pending_ai",
        )
        session.add(row_num)
        await session.commit()
        await session.refresh(row_num)
        
        logger.info(f"Created Numerology Blueprint result (ID: {row_num.id}) with status {row_num.status}")
        
        # Simulate worker call
        await refine_numerology_blueprint({}, row_num.id)
        
        await session.refresh(row_num)
        logger.info(f"Processed Numerology Blueprint status: {row_num.status}")
        if row_num.status == "completed" and row_num.llm_result_json:
            logger.info("✅ Numerology Blueprint success")
        else:
            logger.error("❌ Numerology Blueprint failed")

        # 4. Verify Astrology Chart Narrative Task
        logger.info("--- Testing Astrology Chart Narrative via refine_test_result ---")
        row_narrative = TestResult(
            user_id=user.id,
            test_id=1,
            test_title="Astrology Chart Narrative",
            category="Cosmic Identity",
            answers={"mock": "data"},
            status="pending_ai",
        )
        session.add(row_narrative)
        await session.commit()
        await session.refresh(row_narrative)
        
        logger.info(f"Created Astrology Chart Narrative result (ID: {row_narrative.id}) with status {row_narrative.status}")
        
        # Simulate worker call
        await refine_test_result({}, row_narrative.id)
        
        await session.refresh(row_narrative)
        logger.info(f"Processed Astrology Chart Narrative status: {row_narrative.status}")
        if row_narrative.status == "completed" and row_narrative.llm_result_json:
            logger.info("✅ Astrology Chart Narrative success")
        else:
            logger.error("❌ Astrology Chart Narrative failed")
        # 4. Verify Numerology Actual Task via refine_test_result
        logger.info("--- Testing Numerology Actual via refine_test_result ---")
        row_num_actual = TestResult(
            user_id=user.id,
            test_id=2,
            test_title="Numerology",
            category="Cosmic Identity",
            answers=[], # simulated questionless submission
            status="pending_ai",
        )
        session.add(row_num_actual)
        await session.commit()
        await session.refresh(row_num_actual)
        
        logger.info(f"Created Numerology Actual result (ID: {row_num_actual.id}) with status {row_num_actual.status}")
        
        # Simulate worker call
        await refine_test_result({}, row_num_actual.id)
        
        await session.refresh(row_num_actual)
        logger.info(f"Processed Numerology Actual status: {row_num_actual.status}")
        if row_num_actual.status == "completed" and row_num_actual.llm_result_json:
            logger.info("✅ Numerology Actual success")
            logger.info(f"   Title: {row_num_actual.personality_type}")
        else:
            logger.error("❌ Numerology Actual failed")

if __name__ == "__main__":
    asyncio.run(test_worker_refactor())
