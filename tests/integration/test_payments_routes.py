from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import status

from shared.database.models.user import User


@pytest.mark.integration
class TestPaymentsRoutes:
    """Testes de integração para rotas de pagamento"""

    def test_subscribe_level_05_reserved(self, client, sample_user, sample_jwt_token):
        """Testa que LEVEL_05 não pode ser assinado"""
        response = client.post(
            "/api/v1/payments/subscribe",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
            json={"target_level": "LEVEL_05", "skip_payment": True},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "LEVEL_05 is reserved" in response.json()["detail"]

    def test_subscribe_level_01_free_tier(self, client, sample_user, sample_jwt_token):
        """Testa que LEVEL_01 não precisa de assinatura"""
        response = client.post(
            "/api/v1/payments/subscribe",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
            json={"target_level": "LEVEL_01", "skip_payment": True},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "LEVEL_01 is the free tier" in response.json()["detail"]

    def test_subscribe_cannot_downgrade(
        self, client, sample_user, sample_jwt_token, db_session
    ):
        """Testa que não é possível fazer downgrade"""
        from shared.database.models.user import UserLevel

        db_session.query(User).filter(User.id == sample_user.id).update(
            {"level": UserLevel.LEVEL_03}
        )
        db_session.commit()

        response = client.post(
            "/api/v1/payments/subscribe",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
            json={"target_level": "LEVEL_02", "skip_payment": True},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot downgrade" in response.json()["detail"]

    def test_subscribe_skip_payment_success(
        self, client, sample_user, sample_jwt_token
    ):
        """Testa upgrade com skip_payment=True"""
        with patch("src.api.routes.payments.settings") as mock_settings:
            mock_settings.SKIP_PAYMENT = True
            mock_settings.TOKEN_BUDGET_LEVEL_02 = 50000

            response = client.post(
                "/api/v1/payments/subscribe",
                headers={"Authorization": f"Bearer {sample_jwt_token}"},
                json={"target_level": "LEVEL_02", "skip_payment": True},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["target_level"] == "LEVEL_02"
            assert data["new_budget"] == 50000
            assert "SKIP_PAYMENT" in data["message"]

    def test_subscribe_checkout_creation_success(
        self, client, sample_user, sample_jwt_token
    ):
        """Testa criação de checkout URL com sucesso"""
        mock_pagarme = AsyncMock()
        mock_pagarme.cancel_subscription = AsyncMock(return_value=True)
        mock_pagarme.create_customer = AsyncMock(return_value="cust_123")
        mock_pagarme.create_subscription_checkout = AsyncMock(
            return_value="https://checkout.pagar.me/xyz"
        )

        with patch("src.api.routes.payments.pagarme_service", mock_pagarme):
            response = client.post(
                "/api/v1/payments/subscribe",
                headers={"Authorization": f"Bearer {sample_jwt_token}"},
                json={"target_level": "LEVEL_02", "skip_payment": False},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["checkout_url"] == "https://checkout.pagar.me/xyz"

    def test_subscribe_cancel_existing_subscription(
        self, client, sample_user, sample_jwt_token, db_session
    ):
        """Testa cancelamento de assinatura existente antes de criar nova"""
        from shared.database.models.user import User

        db_session.query(User).filter(User.id == sample_user.id).update(
            {"subscription_id": "sub_old", "subscription_status": "active"}
        )
        db_session.commit()

        mock_pagarme = AsyncMock()
        mock_pagarme.cancel_subscription = AsyncMock(return_value=True)
        mock_pagarme.create_customer = AsyncMock(return_value="cust_123")
        mock_pagarme.create_subscription_checkout = AsyncMock(
            return_value="https://checkout.pagar.me/new"
        )

        with patch("src.api.routes.payments.pagarme_service", mock_pagarme):
            response = client.post(
                "/api/v1/payments/subscribe",
                headers={"Authorization": f"Bearer {sample_jwt_token}"},
                json={"target_level": "LEVEL_03", "skip_payment": False},
            )

            assert response.status_code == status.HTTP_200_OK
            mock_pagarme.cancel_subscription.assert_called_once_with("sub_old")

    def test_subscribe_generic_exception(self, client, sample_user, sample_jwt_token):
        """Testa exceção genérica em create_subscription"""
        mock_pagarme = AsyncMock()
        mock_pagarme.cancel_subscription = AsyncMock(return_value=True)
        mock_pagarme.create_customer = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with patch("src.api.routes.payments.pagarme_service", mock_pagarme):
            response = client.post(
                "/api/v1/payments/subscribe",
                headers={"Authorization": f"Bearer {sample_jwt_token}"},
                json={"target_level": "LEVEL_02", "skip_payment": False},
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to create checkout" in response.json()["detail"]

    def test_subscribe_customer_creation_failure(
        self, client, sample_user, sample_jwt_token
    ):
        """Testa falha ao criar customer"""
        mock_pagarme = AsyncMock()
        mock_pagarme.cancel_subscription = AsyncMock(return_value=True)
        mock_pagarme.create_customer = AsyncMock(return_value=None)

        with patch("src.api.routes.payments.pagarme_service", mock_pagarme):
            response = client.post(
                "/api/v1/payments/subscribe",
                headers={"Authorization": f"Bearer {sample_jwt_token}"},
                json={"target_level": "LEVEL_02", "skip_payment": False},
            )

            assert response.status_code == status.HTTP_502_BAD_GATEWAY
            assert "Failed to create payment customer" in response.json()["detail"]

    def test_subscribe_checkout_creation_failure(
        self, client, sample_user, sample_jwt_token
    ):
        """Testa falha ao criar checkout"""
        mock_pagarme = AsyncMock()
        mock_pagarme.cancel_subscription = AsyncMock(return_value=True)
        mock_pagarme.create_customer = AsyncMock(return_value="cust_123")
        mock_pagarme.create_subscription_checkout = AsyncMock(return_value=None)

        with patch("src.api.routes.payments.pagarme_service", mock_pagarme):
            response = client.post(
                "/api/v1/payments/subscribe",
                headers={"Authorization": f"Bearer {sample_jwt_token}"},
                json={"target_level": "LEVEL_02", "skip_payment": False},
            )

            assert response.status_code == status.HTTP_502_BAD_GATEWAY
            assert "Failed to create checkout" in response.json()["detail"]

    def test_refill_level_05_unlimited(
        self, client, sample_user, sample_jwt_token, db_session
    ):
        """Testa que LEVEL_05 não precisa de refill"""
        from shared.database.models.user import UserLevel

        db_session.query(User).filter(User.id == sample_user.id).update(
            {"level": UserLevel.LEVEL_05}
        )
        db_session.commit()

        response = client.post(
            "/api/v1/payments/refill",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
            json={"skip_payment": True},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "unlimited budget" in response.json()["detail"]

    def test_refill_already_at_max(
        self, client, sample_user, sample_jwt_token, db_session
    ):
        """Testa refill quando já está no máximo"""
        from shared.database.models.user import UserLevel

        db_session.query(User).filter(User.id == sample_user.id).update(
            {"level": UserLevel.LEVEL_02, "token_budget": 50000}
        )
        db_session.commit()

        response = client.post(
            "/api/v1/payments/refill",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
            json={"skip_payment": True},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already at maximum" in response.json()["detail"]

    def test_refill_skip_payment_success(
        self, client, sample_user, sample_jwt_token, db_session
    ):
        """Testa refill com skip_payment=True"""
        from shared.database.models.user import UserLevel

        db_session.query(User).filter(User.id == sample_user.id).update(
            {"level": UserLevel.LEVEL_02, "token_budget": 1000}
        )
        db_session.commit()

        with patch("src.api.routes.payments.settings") as mock_settings:
            mock_settings.SKIP_PAYMENT = True
            mock_settings.TOKEN_BUDGET_LEVEL_02 = 50000

            response = client.post(
                "/api/v1/payments/refill",
                headers={"Authorization": f"Bearer {sample_jwt_token}"},
                json={"skip_payment": True},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["new_budget"] == 50000
            assert data["amount_refilled"] == 49000

    def test_refill_checkout_creation_success(
        self, client, sample_user, sample_jwt_token, db_session
    ):
        """Testa criação de checkout URL para refill"""
        from shared.database.models.user import UserLevel

        db_session.query(User).filter(User.id == sample_user.id).update(
            {"level": UserLevel.LEVEL_02, "token_budget": 1000}
        )
        db_session.commit()

        mock_pagarme = AsyncMock()
        mock_pagarme.create_customer = AsyncMock(return_value="cust_123")
        mock_pagarme.create_refill_checkout = AsyncMock(
            return_value="https://checkout.pagar.me/refill"
        )

        with patch("src.api.routes.payments.pagarme_service", mock_pagarme):
            response = client.post(
                "/api/v1/payments/refill",
                headers={"Authorization": f"Bearer {sample_jwt_token}"},
                json={"skip_payment": False},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["checkout_url"] == "https://checkout.pagar.me/refill"

    def test_refill_customer_id_already_exists(
        self, client, sample_user, sample_jwt_token, db_session
    ):
        """Testa refill quando customer_id já existe"""
        from shared.database.models.user import UserLevel

        db_session.query(User).filter(User.id == sample_user.id).update(
            {
                "level": UserLevel.LEVEL_02,
                "token_budget": 1000,
                "pagarme_customer_id": "cust_existing",
            }
        )
        db_session.commit()

        mock_pagarme = AsyncMock()
        mock_pagarme.create_customer = AsyncMock(return_value="cust_existing")
        mock_pagarme.create_refill_checkout = AsyncMock(
            return_value="https://checkout.pagar.me/refill"
        )

        with patch("src.api.routes.payments.pagarme_service", mock_pagarme):
            response = client.post(
                "/api/v1/payments/refill",
                headers={"Authorization": f"Bearer {sample_jwt_token}"},
                json={"skip_payment": False},
            )

            assert response.status_code == status.HTTP_200_OK

    def test_refill_checkout_creation_failure(
        self, client, sample_user, sample_jwt_token, db_session
    ):
        """Testa falha ao criar checkout de refill"""
        from shared.database.models.user import UserLevel

        db_session.query(User).filter(User.id == sample_user.id).update(
            {"level": UserLevel.LEVEL_02, "token_budget": 1000}
        )
        db_session.commit()

        mock_pagarme = AsyncMock()
        mock_pagarme.create_customer = AsyncMock(return_value="cust_123")
        mock_pagarme.create_refill_checkout = AsyncMock(return_value=None)

        with patch("src.api.routes.payments.pagarme_service", mock_pagarme):
            response = client.post(
                "/api/v1/payments/refill",
                headers={"Authorization": f"Bearer {sample_jwt_token}"},
                json={"skip_payment": False},
            )

            assert response.status_code == status.HTTP_502_BAD_GATEWAY
            assert "Failed to create refill checkout" in response.json()["detail"]

    def test_refill_generic_exception(
        self, client, sample_user, sample_jwt_token, db_session
    ):
        """Testa exceção genérica em create_refill"""
        from shared.database.models.user import UserLevel

        db_session.query(User).filter(User.id == sample_user.id).update(
            {"level": UserLevel.LEVEL_02, "token_budget": 1000}
        )
        db_session.commit()

        mock_pagarme = AsyncMock()
        mock_pagarme.create_customer = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with patch("src.api.routes.payments.pagarme_service", mock_pagarme):
            response = client.post(
                "/api/v1/payments/refill",
                headers={"Authorization": f"Bearer {sample_jwt_token}"},
                json={"skip_payment": False},
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to create refill" in response.json()["detail"]

    def test_cancel_no_subscription(self, client, sample_user, sample_jwt_token):
        """Testa cancelamento sem assinatura ativa"""
        response = client.delete(
            "/api/v1/payments/subscribe",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "No active subscription" in response.json()["detail"]

    def test_cancel_not_active(self, client, sample_user, sample_jwt_token, db_session):
        """Testa cancelamento de assinatura não ativa"""
        from shared.database.models.user import User

        db_session.query(User).filter(User.id == sample_user.id).update(
            {"subscription_id": "sub_123", "subscription_status": "canceled"}
        )
        db_session.commit()

        response = client.delete(
            "/api/v1/payments/subscribe",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "not active" in response.json()["detail"]

    def test_cancel_success(self, client, sample_user, sample_jwt_token, db_session):
        """Testa cancelamento com sucesso"""
        from shared.database.models.user import User

        period_end = datetime.now(UTC) + timedelta(days=30)
        db_session.query(User).filter(User.id == sample_user.id).update(
            {
                "subscription_id": "sub_123",
                "subscription_status": "active",
                "subscription_period_end": period_end,
            }
        )
        db_session.commit()

        mock_pagarme = AsyncMock()
        mock_pagarme.cancel_subscription = AsyncMock(return_value=True)

        with patch("src.api.routes.payments.pagarme_service", mock_pagarme):
            response = client.delete(
                "/api/v1/payments/subscribe",
                headers={"Authorization": f"Bearer {sample_jwt_token}"},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert "canceled" in data["message"]

    def test_cancel_pagarme_failure(
        self, client, sample_user, sample_jwt_token, db_session
    ):
        """Testa falha ao cancelar no Pagar.me"""
        from shared.database.models.user import User

        db_session.query(User).filter(User.id == sample_user.id).update(
            {"subscription_id": "sub_123", "subscription_status": "active"}
        )
        db_session.commit()

        mock_pagarme = AsyncMock()
        mock_pagarme.cancel_subscription = AsyncMock(return_value=False)

        with patch("src.api.routes.payments.pagarme_service", mock_pagarme):
            response = client.delete(
                "/api/v1/payments/subscribe",
                headers={"Authorization": f"Bearer {sample_jwt_token}"},
            )

            assert response.status_code == status.HTTP_502_BAD_GATEWAY
            assert "Failed to cancel subscription" in response.json()["detail"]

    def test_cancel_generic_exception(
        self, client, sample_user, sample_jwt_token, db_session
    ):
        """Testa exceção genérica em cancel_subscription"""
        from shared.database.models.user import User

        db_session.query(User).filter(User.id == sample_user.id).update(
            {"subscription_id": "sub_123", "subscription_status": "active"}
        )
        db_session.commit()

        mock_pagarme = AsyncMock()
        mock_pagarme.cancel_subscription = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with patch("src.api.routes.payments.pagarme_service", mock_pagarme):
            response = client.delete(
                "/api/v1/payments/subscribe",
                headers={"Authorization": f"Bearer {sample_jwt_token}"},
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to cancel subscription" in response.json()["detail"]

    def test_get_subscription_status_no_subscription(
        self, client, sample_user, sample_jwt_token
    ):
        """Testa status sem assinatura"""
        response = client.get(
            "/api/v1/payments/subscription",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["has_subscription"] is False
        assert data["status"] is None

    def test_get_subscription_status_with_subscription(
        self, client, sample_user, sample_jwt_token, db_session
    ):
        """Testa status com assinatura ativa"""
        from shared.database.models.user import User

        period_start = datetime.now(UTC)
        period_end = period_start + timedelta(days=30)
        db_session.query(User).filter(User.id == sample_user.id).update(
            {
                "subscription_id": "sub_123",
                "subscription_status": "active",
                "subscription_period_start": period_start,
                "subscription_period_end": period_end,
            }
        )
        db_session.commit()

        response = client.get(
            "/api/v1/payments/subscription",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["has_subscription"] is True
        assert data["status"] == "active"

    def test_webhook_invalid_signature(self, client):
        """Testa webhook com assinatura inválida"""
        mock_pagarme = AsyncMock()
        mock_pagarme.verify_webhook_signature = Mock(return_value=False)

        with patch("src.api.routes.payments.pagarme_service", mock_pagarme):
            response = client.post(
                "/api/v1/payments/webhook",
                json={"type": "subscription.created", "data": {"id": "sub_123"}},
            )

            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Invalid webhook signature" in response.json()["detail"]

    def test_webhook_generic_exception(self, client):
        """Testa exceção genérica em webhook"""
        mock_pagarme = AsyncMock()
        mock_pagarme.verify_webhook_signature = Mock(
            side_effect=Exception("Unexpected error")
        )

        with patch("src.api.routes.payments.pagarme_service", mock_pagarme):
            response = client.post(
                "/api/v1/payments/webhook",
                json={"type": "subscription.created", "data": {"id": "sub_123"}},
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Error processing webhook" in response.json()["detail"]

    def test_webhook_subscription_created(self, client, sample_user, db_session):
        """Testa webhook subscription.created"""
        from shared.database.models.user import User

        db_session.query(User).filter(User.id == sample_user.id).update(
            {"subscription_id": "sub_123"}
        )
        db_session.commit()

        mock_pagarme = AsyncMock()
        mock_pagarme.verify_webhook_signature = Mock(return_value=True)

        with patch("src.api.routes.payments.pagarme_service", mock_pagarme):
            response = client.post(
                "/api/v1/payments/webhook",
                json={
                    "type": "subscription.created",
                    "data": {
                        "id": "sub_123",
                        "metadata": {"target_level": "LEVEL_02"},
                        "current_period": {"end_at": "2024-12-31T23:59:59Z"},
                    },
                },
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.json()["status"] == "ok"

    def test_webhook_subscription_created_no_target_level(
        self, client, sample_user, db_session
    ):
        """Testa webhook subscription.created sem target_level"""
        from shared.database.models.user import User

        db_session.query(User).filter(User.id == sample_user.id).update(
            {"subscription_id": "sub_123"}
        )
        db_session.commit()

        mock_pagarme = AsyncMock()
        mock_pagarme.verify_webhook_signature = Mock(return_value=True)

        with patch("src.api.routes.payments.pagarme_service", mock_pagarme):
            response = client.post(
                "/api/v1/payments/webhook",
                json={
                    "type": "subscription.created",
                    "data": {
                        "id": "sub_123",
                        "metadata": {},
                        "current_period": {"end_at": "2024-12-31T23:59:59Z"},
                    },
                },
            )

            assert response.status_code == status.HTTP_200_OK

    def test_webhook_subscription_created_invalid_period_end(
        self, client, sample_user, db_session
    ):
        """Testa webhook subscription.created com period_end inválido"""
        from shared.database.models.user import User

        db_session.query(User).filter(User.id == sample_user.id).update(
            {"subscription_id": "sub_123"}
        )
        db_session.commit()

        mock_pagarme = AsyncMock()
        mock_pagarme.verify_webhook_signature = Mock(return_value=True)

        with patch("src.api.routes.payments.pagarme_service", mock_pagarme):
            response = client.post(
                "/api/v1/payments/webhook",
                json={
                    "type": "subscription.created",
                    "data": {
                        "id": "sub_123",
                        "metadata": {"target_level": "LEVEL_02"},
                        "current_period": {"end_at": "invalid-date"},
                    },
                },
            )

            assert response.status_code == status.HTTP_200_OK

    def test_webhook_subscription_canceled(self, client, sample_user, db_session):
        """Testa webhook subscription.canceled"""
        from shared.database.models.user import User

        db_session.query(User).filter(User.id == sample_user.id).update(
            {"subscription_id": "sub_123", "level": "LEVEL_03"}
        )
        db_session.commit()

        mock_pagarme = AsyncMock()
        mock_pagarme.verify_webhook_signature = Mock(return_value=True)

        with patch("src.api.routes.payments.pagarme_service", mock_pagarme):
            response = client.post(
                "/api/v1/payments/webhook",
                json={"type": "subscription.canceled", "data": {"id": "sub_123"}},
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.json()["status"] == "ok"

    def test_webhook_subscription_payment_failed(self, client, sample_user, db_session):
        """Testa webhook subscription.payment_failed"""
        from shared.database.models.user import User

        db_session.query(User).filter(User.id == sample_user.id).update(
            {"subscription_id": "sub_123", "level": "LEVEL_03"}
        )
        db_session.commit()

        mock_pagarme = AsyncMock()
        mock_pagarme.verify_webhook_signature = Mock(return_value=True)

        with patch("src.api.routes.payments.pagarme_service", mock_pagarme):
            response = client.post(
                "/api/v1/payments/webhook",
                json={"type": "subscription.payment_failed", "data": {"id": "sub_123"}},
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.json()["status"] == "ok"

    def test_webhook_order_paid_refill(self, client, sample_user, db_session):
        """Testa webhook order.paid para refill"""
        from shared.database.models.user import User

        db_session.query(User).filter(User.id == sample_user.id).update(
            {"level": "LEVEL_02", "token_budget": 1000}
        )
        db_session.commit()

        mock_pagarme = AsyncMock()
        mock_pagarme.verify_webhook_signature = Mock(return_value=True)

        with patch("src.api.routes.payments.pagarme_service", mock_pagarme):
            response = client.post(
                "/api/v1/payments/webhook",
                json={
                    "type": "order.paid",
                    "data": {
                        "metadata": {"type": "refill", "user_id": str(sample_user.id)}
                    },
                },
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.json()["status"] == "ok"

    def test_webhook_order_not_refill(self, client):
        """Testa webhook order.paid que não é refill"""
        mock_pagarme = AsyncMock()
        mock_pagarme.verify_webhook_signature = Mock(return_value=True)

        with patch("src.api.routes.payments.pagarme_service", mock_pagarme):
            response = client.post(
                "/api/v1/payments/webhook",
                json={"type": "order.paid", "data": {"metadata": {"type": "other"}}},
            )

            assert response.status_code == status.HTTP_200_OK

    def test_webhook_order_not_paid(self, client):
        """Testa webhook order que não é paid"""
        mock_pagarme = AsyncMock()
        mock_pagarme.verify_webhook_signature = Mock(return_value=True)

        with patch("src.api.routes.payments.pagarme_service", mock_pagarme):
            response = client.post(
                "/api/v1/payments/webhook",
                json={
                    "type": "order.created",
                    "data": {"metadata": {"type": "refill"}},
                },
            )

            assert response.status_code == status.HTTP_200_OK

    def test_webhook_subscription_event_no_subscription_id(self, client):
        """Testa webhook subscription event sem subscription_id"""
        mock_pagarme = AsyncMock()
        mock_pagarme.verify_webhook_signature = Mock(return_value=True)

        with patch("src.api.routes.payments.pagarme_service", mock_pagarme):
            response = client.post(
                "/api/v1/payments/webhook",
                json={"type": "subscription.created", "data": {}},
            )

            assert response.status_code == status.HTTP_200_OK

    def test_webhook_subscription_event_user_not_found(self, client):
        """Testa webhook subscription event com usuário não encontrado"""
        mock_pagarme = AsyncMock()
        mock_pagarme.verify_webhook_signature = Mock(return_value=True)

        with patch("src.api.routes.payments.pagarme_service", mock_pagarme):
            response = client.post(
                "/api/v1/payments/webhook",
                json={
                    "type": "subscription.created",
                    "data": {"id": "sub_999", "metadata": {"user_id": str(uuid4())}},
                },
            )

            assert response.status_code == status.HTTP_200_OK

    def test_webhook_order_event_no_user_id(self, client):
        """Testa webhook order event sem user_id"""
        mock_pagarme = AsyncMock()
        mock_pagarme.verify_webhook_signature = Mock(return_value=True)

        with patch("src.api.routes.payments.pagarme_service", mock_pagarme):
            response = client.post(
                "/api/v1/payments/webhook",
                json={"type": "order.paid", "data": {"metadata": {"type": "refill"}}},
            )

            assert response.status_code == status.HTTP_200_OK

    def test_webhook_order_event_user_not_found(self, client):
        """Testa webhook order event com usuário não encontrado"""
        mock_pagarme = AsyncMock()
        mock_pagarme.verify_webhook_signature = Mock(return_value=True)

        with patch("src.api.routes.payments.pagarme_service", mock_pagarme):
            response = client.post(
                "/api/v1/payments/webhook",
                json={
                    "type": "order.paid",
                    "data": {"metadata": {"type": "refill", "user_id": str(uuid4())}},
                },
            )

            assert response.status_code == status.HTTP_200_OK

    def test_webhook_order_event_unlimited_budget_user(
        self, client, sample_user, db_session
    ):
        """Testa webhook order event para usuário com budget ilimitado"""
        from shared.database.models.user import UserLevel

        db_session.query(User).filter(User.id == sample_user.id).update(
            {"level": UserLevel.LEVEL_05}
        )
        db_session.commit()

        mock_pagarme = AsyncMock()
        mock_pagarme.verify_webhook_signature = Mock(return_value=True)

        with patch("src.api.routes.payments.pagarme_service", mock_pagarme):
            response = client.post(
                "/api/v1/payments/webhook",
                json={
                    "type": "order.paid",
                    "data": {
                        "metadata": {"type": "refill", "user_id": str(sample_user.id)}
                    },
                },
            )

            assert response.status_code == status.HTTP_200_OK
