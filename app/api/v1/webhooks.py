"""Stripe webhook: update user subscription status from Stripe events. Uses raw body for signature verification."""

import logging
from typing import Any

from fastapi import APIRouter, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import cache_delete, cache_key_user_profile
from app.db.models.user import User as UserModel
from app.db.session import AsyncSessionLocal

router = APIRouter(tags=["webhooks"])
logger = logging.getLogger(__name__)


async def _get_user_by_id(session: AsyncSession, user_id: int) -> UserModel | None:
    result = await session.execute(select(UserModel).where(UserModel.id == user_id))
    return result.scalar_one_or_none()


async def _set_subscription_active(
    session: AsyncSession,
    user_id: int,
    subscription_id: str,
    stripe_customer_id: str | None = None,
) -> None:
    user = await _get_user_by_id(session, user_id)
    if not user:
        logger.warning("Webhook: user_id=%s not found", user_id)
        return
    user.is_premium = True
    user.subscription_status = "active"
    user.subscription_id = subscription_id
    if stripe_customer_id:
        user.stripe_customer_id = stripe_customer_id
    await session.commit()
    await cache_delete(cache_key_user_profile(user_id))
    logger.info("Webhook: user_id=%s set active, subscription_id=%s", user_id, subscription_id)


async def _set_subscription_inactive(session: AsyncSession, user_id: int) -> None:
    user = await _get_user_by_id(session, user_id)
    if not user:
        return
    user.is_premium = False
    user.subscription_status = "canceled"
    user.subscription_id = None
    await session.commit()
    await cache_delete(cache_key_user_profile(user_id))
    logger.info("Webhook: user_id=%s set canceled", user_id)


async def _set_subscription_status(
    session: AsyncSession, user_id: int, status: str, subscription_id: str | None
) -> None:
    user = await _get_user_by_id(session, user_id)
    if not user:
        return
    user.subscription_status = status
    if subscription_id:
        user.subscription_id = subscription_id
    # active, trialing -> premium; past_due we could keep premium with a flag; canceled, unpaid, etc -> not premium
    user.is_premium = status in ("active", "trialing")
    await session.commit()
    await cache_delete(cache_key_user_profile(user_id))
    logger.info("Webhook: user_id=%s status=%s", user_id, status)


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request) -> Response:
    """
    Stripe webhook: verify signature and process subscription events.
    No auth - Stripe signs the payload; we verify using STRIPE_WEBHOOK_SECRET.
    """
    if not settings.stripe_webhook_secret or not settings.stripe_secret_key:
        logger.warning("Stripe webhook secret not configured")
        return Response(status_code=503, content="Webhook not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        import stripe
        stripe.api_key = settings.stripe_secret_key
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError as e:
        logger.warning("Stripe webhook invalid payload: %s", e)
        return Response(status_code=400, content="Invalid payload")
    except Exception as e:
        logger.warning("Stripe webhook signature verification failed: %s", e)
        return Response(status_code=400, content="Invalid signature")

    async with AsyncSessionLocal() as session:
        try:
            if event["type"] == "checkout.session.completed":
                data = event["data"]["object"]
                subscription_id = data.get("subscription")
                customer_id = data.get("customer")
                client_ref = data.get("client_reference_id")
                if not client_ref or not subscription_id:
                    logger.warning("checkout.session.completed missing client_reference_id or subscription")
                    return Response(status_code=200)
                user_id = int(client_ref)
                await _set_subscription_active(
                    session, user_id, subscription_id, stripe_customer_id=customer_id
                )

            elif event["type"] == "customer.subscription.updated":
                sub = event["data"]["object"]
                user_id_str = (sub.get("metadata") or {}).get("user_id")
                if not user_id_str:
                    # Fallback: find user by subscription_id
                    sub_id = sub.get("id")
                    result = await session.execute(
                        select(UserModel).where(UserModel.subscription_id == sub_id)
                    )
                    user = result.scalar_one_or_none()
                    if user:
                        user_id_str = str(user.id)
                if user_id_str:
                    user_id = int(user_id_str)
                    status = sub.get("status", "active")
                    await _set_subscription_status(
                        session, user_id, status, sub.get("id")
                    )

            elif event["type"] == "customer.subscription.deleted":
                sub = event["data"]["object"]
                user_id_str = (sub.get("metadata") or {}).get("user_id")
                if not user_id_str:
                    sub_id = sub.get("id")
                    result = await session.execute(
                        select(UserModel).where(UserModel.subscription_id == sub_id)
                    )
                    user = result.scalar_one_or_none()
                    if user:
                        user_id_str = str(user.id)
                if user_id_str:
                    await _set_subscription_inactive(session, int(user_id_str))
        except Exception as e:
            logger.exception("Webhook handler error: %s", e)
            return Response(status_code=500, content="Handler error")

    return Response(status_code=200, content="ok")
