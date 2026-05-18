"""Schemas for Pagar.me payment integration.

All payment processing is handled by Pagar.me's checkout interface.
We only generate checkout URLs and receive webhook confirmations.
No card data is handled or stored on our side.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from shared.database.models.user import UserLevel


class CreateSubscriptionRequest(BaseModel):
    """Request to create a subscription checkout for level upgrade."""
    target_level: UserLevel = Field(..., description="Target level to subscribe to")
    skip_payment: bool = Field(False, description="Skip payment and apply immediately (DEV_MODE only)")


class CreateSubscriptionResponse(BaseModel):
    """Response with Pagar.me checkout URL for subscription."""
    success: bool
    message: str
    checkout_url: Optional[str] = None
    current_level: UserLevel
    target_level: UserLevel
    new_budget: Optional[int] = None


class CreateRefillRequest(BaseModel):
    """Request to create a refill checkout or apply refill directly."""
    skip_payment: bool = Field(False, description="Skip payment and apply immediately (DEV_MODE only)")


class CreateRefillResponse(BaseModel):
    """Response for token refill."""
    success: bool
    message: str
    checkout_url: Optional[str] = None
    amount_refilled: int
    previous_budget: Optional[int] = None
    new_budget: Optional[int] = None


class CancelSubscriptionResponse(BaseModel):
    """Response after canceling a subscription."""
    success: bool
    message: str
    effective_until: Optional[datetime] = None


class SubscriptionStatusResponse(BaseModel):
    """Response with current subscription status."""
    has_subscription: bool
    status: Optional[str] = None
    current_level: UserLevel
    period_end: Optional[datetime] = None
