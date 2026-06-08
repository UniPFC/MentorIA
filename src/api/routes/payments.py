"""Payment routes for Pagar.me integration.

All payment processing is handled by Pagar.me's hosted checkout interface.
We generate checkout URLs and receive webhook confirmations.
No card or sensitive payment data is handled on our side.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import uuid
from shared.database.session import get_db
from shared.database.models.user import User, UserLevel
from src.repositories.user import UserRepository
from src.api.schemas.payments import (
    CreateSubscriptionRequest, CreateSubscriptionResponse,
    CreateRefillRequest, CreateRefillResponse,
    CancelSubscriptionResponse, SubscriptionStatusResponse
)
from src.api.dependencies import get_current_active_user
from src.services.pagarme import pagarme_service
from config.logger import logger
from config.settings import settings

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/subscribe", response_model=CreateSubscriptionResponse)
async def create_subscription(
    request: CreateSubscriptionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upgrade user level via Pagar.me subscription checkout.
    In DEV_MODE with skip_payment=True, applies upgrade immediately.
    Otherwise, generates a Pagar.me checkout URL.
    """
    try:
        target_level = request.target_level
        
        if target_level == UserLevel.LEVEL_05:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="LEVEL_05 is reserved for admins and cannot be subscribed to."
            )
        
        if target_level == UserLevel.LEVEL_01:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="LEVEL_01 is the free tier and does not require a subscription."
            )
        
        level_order = [UserLevel.LEVEL_01, UserLevel.LEVEL_02, UserLevel.LEVEL_03, UserLevel.LEVEL_04, UserLevel.LEVEL_05]
        if level_order.index(target_level) <= level_order.index(current_user.level):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot downgrade or stay at same level. Current: {current_user.level}, Target: {target_level}"
            )
        
        budget_map = {
            UserLevel.LEVEL_01: settings.TOKEN_BUDGET_LEVEL_01,
            UserLevel.LEVEL_02: settings.TOKEN_BUDGET_LEVEL_02,
            UserLevel.LEVEL_03: settings.TOKEN_BUDGET_LEVEL_03,
            UserLevel.LEVEL_04: settings.TOKEN_BUDGET_LEVEL_04,
            UserLevel.LEVEL_05: None,
        }
        new_budget = budget_map[target_level]
        
        # SKIP_PAYMENT: apply immediately without payment gateway
        if request.skip_payment and settings.SKIP_PAYMENT:
            user_repo = UserRepository(db)
            current_level = current_user.level
            now = datetime.now(timezone.utc)
            period_end = now + timedelta(days=30)
            current_user.level = target_level
            current_user.token_budget = new_budget
            current_user.subscription_id = f"skip_sub_{uuid.uuid4().hex[:12]}"
            current_user.subscription_status = "active"
            current_user.subscription_period_start = now
            current_user.subscription_period_end = period_end
            if not current_user.pagarme_customer_id:
                current_user.pagarme_customer_id = f"skip_cus_{uuid.uuid4().hex[:12]}"
            user_repo.update(current_user)
            
            logger.info(
                f"Level upgrade applied immediately (SKIP_PAYMENT): user={current_user.username} "
                f"from {current_level} to {target_level}, budget={new_budget}"
            )
            
            return CreateSubscriptionResponse(
                success=True,
                message=f"Upgrade to {target_level} applied immediately (SKIP_PAYMENT).",
                checkout_url=None,
                current_level=current_level,
                target_level=target_level,
                new_budget=new_budget if new_budget else 0
            )
        
        # Cancel existing subscription if any
        if current_user.subscription_id and current_user.subscription_status == "active":
            await pagarme_service.cancel_subscription(current_user.subscription_id)
        
        user_repo = UserRepository(db)
        
        # Create or get Pagar.me customer
        customer_id = await pagarme_service.create_customer(current_user)
        if not customer_id:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to create payment customer. Please try again."
            )
        
        if not current_user.pagarme_customer_id:
            current_user.pagarme_customer_id = customer_id
            user_repo.update(current_user)
        
        # Create checkout URL — Pagar.me handles all payment data
        checkout_url = await pagarme_service.create_subscription_checkout(
            customer_id=customer_id,
            user=current_user,
            target_level=target_level
        )
        
        if not checkout_url:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to create checkout. Please try again."
            )
        
        logger.info(
            f"Subscription checkout created: user={current_user.username} target={target_level}"
        )
        
        return CreateSubscriptionResponse(
            success=True,
            message=f"Checkout created. Redirect user to complete payment.",
            checkout_url=checkout_url,
            current_level=current_user.level,
            target_level=target_level
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create subscription checkout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout. Please try again later."
        )


@router.post("/refill", response_model=CreateRefillResponse)
async def create_refill(
    request: CreateRefillRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Refill user's token budget to the maximum of their current level.
    In DEV_MODE with skip_payment=True, applies refill immediately.
    Otherwise, generates a Pagar.me checkout URL.
    """
    try:
        if current_user.level == UserLevel.LEVEL_05:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Users with LEVEL_05 have unlimited budget and do not need token refills."
            )
        
        previous_budget = current_user.token_budget or 0
        max_budget = current_user.max_token_budget
        amount_to_refill = max_budget - previous_budget
        
        if amount_to_refill <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token budget is already at maximum for this level."
            )
        
        # SKIP_PAYMENT: apply immediately without payment gateway
        if request.skip_payment and settings.SKIP_PAYMENT:
            user_repo = UserRepository(db)
            current_user.token_budget = max_budget
            user_repo.update(current_user)
            
            logger.info(
                f"Token refill applied immediately (SKIP_PAYMENT): user={current_user.username} "
                f"amount={amount_to_refill}, previous_budget={previous_budget}, new_budget={max_budget}"
            )
            
            return CreateRefillResponse(
                success=True,
                message=f"Token budget refilled to maximum ({max_budget} tokens) immediately (SKIP_PAYMENT).",
                checkout_url=None,
                amount_refilled=amount_to_refill,
                previous_budget=previous_budget,
                new_budget=max_budget
            )
        
        user_repo = UserRepository(db)
        
        # Create or get Pagar.me customer
        customer_id = await pagarme_service.create_customer(current_user)
        if not customer_id:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to create payment customer. Please try again."
            )
        
        if not current_user.pagarme_customer_id:
            current_user.pagarme_customer_id = customer_id
            user_repo.update(current_user)
        
        # Create checkout URL — Pagar.me handles all payment data
        checkout_url = await pagarme_service.create_refill_checkout(
            customer_id=customer_id,
            user=current_user,
            amount_to_refill=amount_to_refill,
            max_budget=max_budget
        )
        
        if not checkout_url:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to create refill checkout. Please try again."
            )
        
        logger.info(
            f"Refill checkout created: user={current_user.username} amount={amount_to_refill}"
        )
        
        return CreateRefillResponse(
            success=True,
            message=f"Checkout created. Redirect user to complete payment.",
            checkout_url=checkout_url,
            amount_refilled=amount_to_refill,
            previous_budget=previous_budget,
            new_budget=max_budget
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create refill: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create refill. Please try again later."
        )


@router.delete("/subscribe", response_model=CancelSubscriptionResponse)
async def cancel_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Cancel the current user's subscription. Downgrades to LEVEL_01 when period ends."""
    try:
        if not current_user.subscription_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active subscription found."
            )
        
        if current_user.subscription_status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Subscription is not active (status: {current_user.subscription_status})."
            )
        
        success = await pagarme_service.cancel_subscription(current_user.subscription_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to cancel subscription. Please try again."
            )
        
        user_repo = UserRepository(db)
        current_user.subscription_status = "canceled"
        user_repo.update(current_user)
        
        logger.info(
            f"Subscription canceled: user={current_user.username} "
            f"sub_id={current_user.subscription_id}"
        )
        
        return CancelSubscriptionResponse(
            success=True,
            message="Subscription canceled. Your level will revert to LEVEL_01 at the end of the billing period.",
            effective_until=current_user.subscription_period_end
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription. Please try again later."
        )


@router.get("/subscription", response_model=SubscriptionStatusResponse)
async def get_subscription_status(
    current_user: User = Depends(get_current_active_user)
):
    """Get the current user's subscription status."""
    return SubscriptionStatusResponse(
        has_subscription=current_user.subscription_id is not None,
        status=current_user.subscription_status,
        current_level=current_user.level,
        period_start=current_user.subscription_period_start,
        period_end=current_user.subscription_period_end
    )


@router.post("/webhook")
async def pagarme_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Pagar.me webhook endpoint.
    Handles subscription and order events to apply upgrades, refills, and downgrades.
    
    Key events handled:
    - subscription.created / subscription.paid: Apply level upgrade
    - subscription.canceled / subscription.ended / subscription.unpaid: Downgrade to LEVEL_01
    - subscription.payment_failed: Mark subscription as past_due
    - order.paid: Apply token refill
    """
    try:
        body = await request.body()
        
        # Verify webhook signature
        signature = request.headers.get("x-hub-signature", "")
        if not pagarme_service.verify_webhook_signature(body, signature):
            logger.warning("Invalid webhook signature received")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
        
        payload = await request.json()
        event_type = payload.get("type", "")
        data = payload.get("data", {})
        
        logger.info(f"Pagar.me webhook received: type={event_type}")
        
        user_repo = UserRepository(db)
        
        if event_type.startswith("subscription."):
            await _handle_subscription_event(event_type, data, user_repo)
        elif event_type.startswith("order."):
            await _handle_order_event(event_type, data, user_repo)
        
        return {"status": "ok"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing webhook"
        )


async def _handle_subscription_event(
    event_type: str,
    data: dict,
    user_repo: UserRepository
):
    """Handle Pagar.me subscription webhook events."""
    subscription_id = data.get("id")
    if not subscription_id:
        logger.warning("Subscription event without subscription ID")
        return
    
    # Find user by subscription_id or metadata
    user = user_repo.db.query(User).filter(User.subscription_id == subscription_id).first()
    if not user:
        metadata = data.get("metadata", {})
        user_id = metadata.get("user_id")
        if user_id:
            user = user_repo.get_by_id(uuid.UUID(user_id))
    
    if not user:
        logger.warning(f"User not found for subscription {subscription_id}")
        return
    
    target_level_str = data.get("metadata", {}).get("target_level")
    
    if event_type in ("subscription.created", "subscription.paid"):
        # Apply the upgrade
        if target_level_str:
            target_level = UserLevel(target_level_str)
        else:
            target_level = user.level
        
        budget_map = {
            UserLevel.LEVEL_01: settings.TOKEN_BUDGET_LEVEL_01,
            UserLevel.LEVEL_02: settings.TOKEN_BUDGET_LEVEL_02,
            UserLevel.LEVEL_03: settings.TOKEN_BUDGET_LEVEL_03,
            UserLevel.LEVEL_04: settings.TOKEN_BUDGET_LEVEL_04,
            UserLevel.LEVEL_05: None,
        }
        
        new_budget = budget_map.get(target_level, settings.TOKEN_BUDGET_LEVEL_01)
        
        user.level = target_level
        user.token_budget = new_budget
        user.subscription_status = "active"
        user.subscription_id = subscription_id
        
        # Set period end from subscription data
        current_period = data.get("current_period", {})
        period_end = current_period.get("end_at")
        if period_end:
            from datetime import datetime
            try:
                user.subscription_period_end = datetime.fromisoformat(period_end.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass
        
        user_repo.update(user)
        
        logger.info(
            f"Subscription payment confirmed: user={user.username} "
            f"level={target_level} budget={new_budget} sub_id={subscription_id}"
        )
    
    elif event_type in ("subscription.canceled", "subscription.ended", "subscription.unpaid"):
        # Downgrade to LEVEL_01
        user.level = UserLevel.LEVEL_01
        user.token_budget = settings.TOKEN_BUDGET_LEVEL_01
        user.subscription_status = event_type.split(".")[1]
        user.subscription_id = None
        user.subscription_period_end = None
        user_repo.update(user)
        
        logger.info(
            f"Subscription {event_type}: user={user.username} downgraded to LEVEL_01 "
            f"budget={settings.TOKEN_BUDGET_LEVEL_01}"
        )
    
    elif event_type == "subscription.payment_failed":
        user.level = UserLevel.LEVEL_01
        user.token_budget = settings.TOKEN_BUDGET_LEVEL_01
        user.subscription_status = "past_due"
        user.subscription_id = None
        user.subscription_period_end = None
        user_repo.update(user)

        logger.warning(
            f"Subscription payment failed: user={user.username} downgraded to LEVEL_01 "
            f"budget={settings.TOKEN_BUDGET_LEVEL_01}"
        )


async def _handle_order_event(
    event_type: str,
    data: dict,
    user_repo: UserRepository
):
    """Handle Pagar.me order webhook events (refill)."""
    if event_type != "order.paid":
        return
    
    metadata = data.get("metadata", {})
    order_type = metadata.get("type")
    
    if order_type != "refill":
        return
    
    user_id = metadata.get("user_id")
    if not user_id:
        logger.warning("Refill order without user_id in metadata")
        return
    
    user = user_repo.get_by_id(uuid.UUID(user_id))
    if not user:
        logger.warning(f"User not found for refill order: user_id={user_id}")
        return
    
    # Refill to max budget of current level
    max_budget = user.max_token_budget
    if max_budget is None:
        logger.warning(f"Cannot refill unlimited budget user: {user.username}")
        return
    
    user.token_budget = max_budget
    user_repo.update(user)
    
    logger.info(
        f"Token refill applied via payment: user={user.username} "
        f"new_budget={max_budget}"
    )
