"""
Database seed: run on first open or anytime via CLI.

- Creates an admin user if SEED_ADMIN_EMAIL and SEED_ADMIN_PASSWORD are set
  and no user with role=admin exists.
- Idempotent: safe to run on every startup or manually.
"""

import asyncio
import logging
from sqlalchemy import func, select

from app.core.config import settings
from app.core.security import hash_password
from app.db.models.user import User
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def run_seed() -> None:
    """Create seed data (e.g. admin user) when configured and missing."""
    async with AsyncSessionLocal() as session:
        if settings.seed_admin_email.strip() and settings.seed_admin_password:
            r = await session.execute(
                select(func.count(User.id)).where(User.role == "admin")
            )
            admin_count = r.scalar() or 0
            if admin_count == 0:
                email = settings.seed_admin_email.strip().lower()
                admin = User(
                    email=email,
                    hashed_password=hash_password(settings.seed_admin_password),
                    role="admin",
                    is_active=True,
                    name="Admin",
                )
                session.add(admin)
                try:
                    await session.commit()
                    logger.info("Seed: created admin user for %s", email)
                except Exception as e:
                    await session.rollback()
                    logger.warning(
                        "Seed: could not create admin (e.g. email already in use): %s",
                        e,
                    )
            else:
                logger.debug("Seed: admin user(s) already exist, skipping")
        else:
            logger.debug("Seed: SEED_ADMIN_EMAIL/SEED_ADMIN_PASSWORD not set, skipping admin seed")


def main() -> None:
    """CLI entry point: run seed once."""
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_seed())


if __name__ == "__main__":
    main()
