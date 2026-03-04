"""Subscription API schemas."""

from pydantic import BaseModel


class CheckoutSessionResponse(BaseModel):
    """URL to redirect the user to Stripe Checkout."""

    url: str
