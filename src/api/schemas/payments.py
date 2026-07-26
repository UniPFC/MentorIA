"""Schemas for Pagar.me payment integration.

All payment processing is handled by Pagar.me's checkout interface.
We only generate checkout URLs and receive webhook confirmations.
No card data is handled or stored on our side.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from shared.database.models.user import UserLevel


class CreateSubscriptionRequest(BaseModel):
    """Request to create a subscription checkout for level upgrade."""

    target_level: UserLevel = Field(..., description="Target level to subscribe to")
    skip_payment: bool = Field(
        False,
        description="Skip payment and apply immediately (requires SKIP_PAYMENT=True in env)",
    )


class CreateSubscriptionResponse(BaseModel):
    """Response with Pagar.me checkout URL for subscription."""

    success: bool
    message: str
    checkout_url: str | None = None
    current_level: UserLevel
    target_level: UserLevel
    new_budget: int | None = None


class CreateRefillRequest(BaseModel):
    """Request to create a refill checkout or apply refill directly."""

    skip_payment: bool = Field(
        False,
        description="Skip payment and apply immediately (requires SKIP_PAYMENT=True in env)",
    )


class CreateRefillResponse(BaseModel):
    """Response for token refill."""

    success: bool
    message: str
    checkout_url: str | None = None
    amount_refilled: int
    previous_budget: int | None = None
    new_budget: int | None = None


class CancelSubscriptionResponse(BaseModel):
    """Response after canceling a subscription."""

    success: bool
    message: str
    effective_until: datetime | None = None


class SubscriptionStatusResponse(BaseModel):
    """Response with current subscription status."""

    has_subscription: bool
    status: str | None = None
    current_level: UserLevel
    period_start: datetime | None = None
    period_end: datetime | None = None
