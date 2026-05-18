"""Pagar.me payment gateway integration service.

All payment processing is handled by Pagar.me's hosted checkout.
We only create checkout URLs and receive webhook confirmations.
No card or sensitive payment data is handled on our side.
"""

import httpx
import hashlib
import hmac
import base64
from typing import Optional, Dict, Any
from shared.database.models.user import User, UserLevel
from config.settings import settings
from config.logger import logger


class PagarmeService:
    """Service for interacting with Pagar.me API v5 using hosted checkout."""
    
    def __init__(self):
        self.api_url = settings.PAGARME_API_URL
        self.api_key = settings.PAGARME_API_KEY
        self.webhook_secret = settings.PAGARME_WEBHOOK_SECRET
    
    def _get_headers(self) -> dict:
        """Get authentication headers for Pagar.me API."""
        auth = base64.b64encode(f"{self.api_key}:".encode()).decode()
        return {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def _get_plan_id(self, level: UserLevel) -> Optional[str]:
        """Get Pagar.me plan ID for the given level."""
        plan_map = {
            UserLevel.LEVEL_02: settings.PAGARME_PLAN_LEVEL_02,
            UserLevel.LEVEL_03: settings.PAGARME_PLAN_LEVEL_03,
            UserLevel.LEVEL_04: settings.PAGARME_PLAN_LEVEL_04,
        }
        return plan_map.get(level)
    
    async def create_customer(self, user: User) -> Optional[str]:
        """Create or retrieve a customer in Pagar.me. Returns customer_id."""
        if user.pagarme_customer_id:
            return user.pagarme_customer_id
        
        payload = {
            "name": user.username,
            "email": user.email,
            "type": "individual",
            "metadata": {
                "user_id": str(user.id)
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/customers",
                    headers=self._get_headers(),
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code in (200, 201):
                    data = response.json()
                    customer_id = data.get("id")
                    logger.info(f"Pagar.me customer created: {customer_id} for user {user.username}")
                    return customer_id
                else:
                    logger.error(f"Failed to create Pagar.me customer: {response.status_code} - {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error creating Pagar.me customer: {e}")
            return None
    
    async def create_subscription_checkout(
        self,
        customer_id: str,
        user: User,
        target_level: UserLevel
    ) -> Optional[str]:
        """
        Create a Pagar.me checkout for subscription.
        Returns the checkout URL where the user completes payment.
        Pagar.me handles all card/payment data collection.
        """
        plan_id = self._get_plan_id(target_level)
        if not plan_id:
            logger.error(f"No plan configured for level {target_level}")
            return None
        
        payload = {
            "customer_id": customer_id,
            "plan_id": plan_id,
            "success_url": f"{settings.FRONTEND_URL}/payment/success",
            "metadata": {
                "user_id": str(user.id),
                "target_level": target_level.value,
                "type": "subscription"
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/checkouts",
                    headers=self._get_headers(),
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code in (200, 201):
                    data = response.json()
                    checkout_url = data.get("url")
                    logger.info(
                        f"Pagar.me subscription checkout created for user {user.username}, "
                        f"target={target_level}, url={checkout_url}"
                    )
                    return checkout_url
                else:
                    logger.error(f"Failed to create checkout: {response.status_code} - {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error creating Pagar.me checkout: {e}")
            return None
    
    async def create_refill_checkout(
        self,
        customer_id: str,
        user: User,
        amount_to_refill: int,
        max_budget: int
    ) -> Optional[str]:
        """
        Create a Pagar.me checkout for one-time token refill.
        Returns the checkout URL where the user completes payment.
        """
        refill_item_id = settings.PAGARME_REFILL_ITEM_ID
        
        payload = {
            "customer_id": customer_id,
            "success_url": f"{settings.FRONTEND_URL}/payment/success",
            "items": [
                {
                    "amount": 990,  # R$ 9,90 - TODO: adjust per level/business rules
                    "description": f"Token refill - {amount_to_refill} tokens",
                    "quantity": 1
                }
            ],
            "metadata": {
                "user_id": str(user.id),
                "type": "refill",
                "amount_to_refill": str(amount_to_refill),
                "max_budget": str(max_budget)
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/checkouts",
                    headers=self._get_headers(),
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code in (200, 201):
                    data = response.json()
                    checkout_url = data.get("url")
                    logger.info(
                        f"Pagar.me refill checkout created for user {user.username}, "
                        f"amount={amount_to_refill}, url={checkout_url}"
                    )
                    return checkout_url
                else:
                    logger.error(f"Failed to create refill checkout: {response.status_code} - {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error creating Pagar.me refill checkout: {e}")
            return None
    
    async def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancel a subscription in Pagar.me."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.api_url}/subscriptions/{subscription_id}",
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code in (200, 204):
                    logger.info(f"Pagar.me subscription canceled: {subscription_id}")
                    return True
                else:
                    logger.error(f"Failed to cancel subscription: {response.status_code} - {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Error canceling Pagar.me subscription: {e}")
            return False
    
    def verify_webhook_signature(self, payload_body: bytes, signature: str) -> bool:
        """Verify Pagar.me webhook signature (HMAC SHA256)."""
        if not self.webhook_secret:
            logger.warning("PAGARME_WEBHOOK_SECRET not configured, skipping signature verification")
            return True
        
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            payload_body,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)


pagarme_service = PagarmeService()
