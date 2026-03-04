"""Subscription: create Stripe Checkout Session for premium. Payment handled securely by Stripe."""

import logging

from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.dependencies import get_current_active_user
from app.core.exceptions import bad_request
from app.db.models.user import User as UserModel
from app.schemas.subscription import CheckoutSessionResponse

router = APIRouter(tags=["subscription"])
logger = logging.getLogger(__name__)


@router.post("/subscription/create-checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    user: UserModel = Depends(get_current_active_user),
):
    """
    Create a Stripe Checkout Session for the monthly subscription.
    Client redirects to the returned URL; Stripe hosts the payment form (no card data touches our server).
    """
    if not settings.stripe_secret_key or not settings.stripe_price_id_monthly:
        raise bad_request("Subscription is not configured.")
    if not settings.frontend_url:
        raise bad_request("Frontend URL is not configured for redirects.")

    try:
        import stripe
        stripe.api_key = settings.stripe_secret_key
    except ImportError:
        raise bad_request("Payment provider is not available.")

    base = settings.frontend_url.rstrip("/")
    success_url = f"{base}/home?subscription=success"
    cancel_url = f"{base}/home?subscription=canceled"

    try:
        # Get or create Stripe customer so we can attach subscription to them
        customer_id = user.stripe_customer_id
        if not customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.name or user.email,
                metadata={"user_id": str(user.id)},
            )
            customer_id = customer.id
            # Persist for next time (webhook will also set it when session completes)
            from app.db.session import AsyncSessionLocal
            from sqlalchemy import update
            from app.db.models.user import User
            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(User).where(User.id == user.id).values(stripe_customer_id=customer_id)
                )
                await session.commit()

        session = stripe.checkout.Session.create(
            mode="subscription",
            customer=customer_id,
            client_reference_id=str(user.id),
            line_items=[
                {
                    "price": settings.stripe_price_id_monthly,
                    "quantity": 1,
                }
            ],
            success_url=success_url,
            cancel_url=cancel_url,
            subscription_data={
                "metadata": {"user_id": str(user.id)},
            },
            allow_promotion_codes=True,
        )
        return CheckoutSessionResponse(url=session.url or "")
    except Exception as e:
        logger.exception("Stripe checkout session creation failed: %s", e)
        raise bad_request("Could not start checkout. Please try again.")
