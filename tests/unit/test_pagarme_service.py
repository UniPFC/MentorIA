import hashlib
import hmac
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from shared.database.models.user import User, UserLevel
from src.services.pagarme import PagarmeService, pagarme_service


@pytest.mark.unit
class TestPagarmeService:
    """Testes unitários para o serviço Pagar.me"""

    def test_get_headers(self):
        """Testa geração de headers para autenticação no Pagar.me"""
        service = PagarmeService()
        with patch.object(service, "api_key", "test_key"):
            headers = service._get_headers()
            assert "Authorization" in headers
            assert headers["Authorization"].startswith("Basic ")
            assert headers["Content-Type"] == "application/json"

    def test_get_plan_id(self):
        """Testa mapeamento de níveis para IDs de planos"""
        service = PagarmeService()
        with patch("src.services.pagarme.settings") as mock_settings:
            mock_settings.PAGARME_PLAN_LEVEL_02 = "plan_02"
            mock_settings.PAGARME_PLAN_LEVEL_03 = "plan_03"
            mock_settings.PAGARME_PLAN_LEVEL_04 = "plan_04"

            assert service._get_plan_id(UserLevel.LEVEL_02) == "plan_02"
            assert service._get_plan_id(UserLevel.LEVEL_03) == "plan_03"
            assert service._get_plan_id(UserLevel.LEVEL_04) == "plan_04"
            assert service._get_plan_id(UserLevel.LEVEL_01) is None

    @pytest.mark.asyncio
    async def test_create_customer_already_exists(self):
        """Testa criação de cliente quando ID já existe no usuário"""
        service = PagarmeService()
        user = Mock(spec=User)
        user.pagarme_customer_id = "cus_existing"

        customer_id = await service.create_customer(user)
        assert customer_id == "cus_existing"

    @pytest.mark.asyncio
    async def test_create_customer_success(self):
        """Testa criação de cliente com sucesso na API"""
        service = PagarmeService()
        user = Mock(spec=User)
        user.pagarme_customer_id = None
        user.username = "testuser"
        user.email = "test@example.com"
        user.id = "user_uuid_123"

        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "cus_new_123"}

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post.return_value = mock_response

        with patch("httpx.AsyncClient", return_value=mock_client):
            customer_id = await service.create_customer(user)
            assert customer_id == "cus_new_123"

    @pytest.mark.asyncio
    async def test_create_customer_failed_status(self):
        """Testa falha na criação de cliente por status inválido"""
        service = PagarmeService()
        user = Mock(spec=User)
        user.pagarme_customer_id = None
        user.username = "testuser"
        user.email = "test@example.com"

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post.return_value = mock_response

        with patch("httpx.AsyncClient", return_value=mock_client):
            customer_id = await service.create_customer(user)
            assert customer_id is None

    @pytest.mark.asyncio
    async def test_create_customer_exception(self):
        """Testa exceção/timeout na chamada de criação de cliente"""
        service = PagarmeService()
        user = Mock(spec=User)
        user.pagarme_customer_id = None

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post.side_effect = httpx.ConnectTimeout(
            "Timeout"
        )

        with patch("httpx.AsyncClient", return_value=mock_client):
            customer_id = await service.create_customer(user)
            assert customer_id is None

    @pytest.mark.asyncio
    async def test_create_subscription_checkout_no_plan(self):
        """Testa criação de checkout de assinatura sem plano configurado"""
        service = PagarmeService()
        user = Mock(spec=User)

        with patch.object(service, "_get_plan_id", return_value=None):
            url = await service.create_subscription_checkout(
                "cus_123", user, UserLevel.LEVEL_02
            )
            assert url is None

    @pytest.mark.asyncio
    async def test_create_subscription_checkout_success(self):
        """Testa criação de checkout de assinatura com sucesso"""
        service = PagarmeService()
        user = Mock(spec=User)
        user.id = "user_uuid"
        user.username = "testuser"

        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"url": "https://checkout.pagar.me/abc"}

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post.return_value = mock_response

        with patch.object(service, "_get_plan_id", return_value="plan_02"):
            with patch("httpx.AsyncClient", return_value=mock_client):
                url = await service.create_subscription_checkout(
                    "cus_123", user, UserLevel.LEVEL_02
                )
                assert url == "https://checkout.pagar.me/abc"

    @pytest.mark.asyncio
    async def test_create_subscription_checkout_failed_status(self):
        """Testa falha de status na criação de checkout de assinatura"""
        service = PagarmeService()
        user = Mock(spec=User)

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid Payload"

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post.return_value = mock_response

        with patch.object(service, "_get_plan_id", return_value="plan_02"):
            with patch("httpx.AsyncClient", return_value=mock_client):
                url = await service.create_subscription_checkout(
                    "cus_123", user, UserLevel.LEVEL_02
                )
                assert url is None

    @pytest.mark.asyncio
    async def test_create_subscription_checkout_exception(self):
        """Testa exceção na criação de checkout de assinatura"""
        service = PagarmeService()
        user = Mock(spec=User)

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post.side_effect = Exception("API Error")

        with patch.object(service, "_get_plan_id", return_value="plan_02"):
            with patch("httpx.AsyncClient", return_value=mock_client):
                url = await service.create_subscription_checkout(
                    "cus_123", user, UserLevel.LEVEL_02
                )
                assert url is None

    @pytest.mark.asyncio
    async def test_create_refill_checkout_success(self):
        """Testa criação de checkout de recarga com sucesso"""
        service = PagarmeService()
        user = Mock(spec=User)
        user.id = "user_uuid"
        user.username = "testuser"

        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"url": "https://checkout.pagar.me/refill"}

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post.return_value = mock_response

        with patch("httpx.AsyncClient", return_value=mock_client):
            url = await service.create_refill_checkout("cus_123", user, 1000, 5000)
            assert url == "https://checkout.pagar.me/refill"

    @pytest.mark.asyncio
    async def test_create_refill_checkout_failed_status(self):
        """Testa falha de status na criação de checkout de recarga"""
        service = PagarmeService()
        user = Mock(spec=User)

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post.return_value = mock_response

        with patch("httpx.AsyncClient", return_value=mock_client):
            url = await service.create_refill_checkout("cus_123", user, 1000, 5000)
            assert url is None

    @pytest.mark.asyncio
    async def test_create_refill_checkout_exception(self):
        """Testa exceção na criação de checkout de recarga"""
        service = PagarmeService()
        user = Mock(spec=User)

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post.side_effect = Exception("API Error")

        with patch("httpx.AsyncClient", return_value=mock_client):
            url = await service.create_refill_checkout("cus_123", user, 1000, 5000)
            assert url is None

    @pytest.mark.asyncio
    async def test_cancel_subscription_success(self):
        """Testa cancelamento de assinatura com sucesso"""
        service = PagarmeService()

        mock_response = Mock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.delete.return_value = mock_response

        with patch("httpx.AsyncClient", return_value=mock_client):
            success = await service.cancel_subscription("sub_123")
            assert success is True

    @pytest.mark.asyncio
    async def test_cancel_subscription_failed_status(self):
        """Testa falha de status no cancelamento de assinatura"""
        service = PagarmeService()

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.delete.return_value = mock_response

        with patch("httpx.AsyncClient", return_value=mock_client):
            success = await service.cancel_subscription("sub_123")
            assert success is False

    @pytest.mark.asyncio
    async def test_cancel_subscription_exception(self):
        """Testa exceção no cancelamento de assinatura"""
        service = PagarmeService()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.delete.side_effect = Exception("API Error")

        with patch("httpx.AsyncClient", return_value=mock_client):
            success = await service.cancel_subscription("sub_123")
            assert success is False

    def test_verify_webhook_signature_no_secret(self):
        """Testa assinatura de webhook sem secret configurado (pula verificação)"""
        service = PagarmeService()
        with patch.object(service, "webhook_secret", None):
            assert service.verify_webhook_signature(b"payload", "sig") is True

    def test_verify_webhook_signature_valid(self):
        """Testa assinatura de webhook válida"""
        service = PagarmeService()
        with patch.object(service, "webhook_secret", "secret"):
            payload = b"test_payload"
            signature = hmac.new(b"secret", payload, hashlib.sha256).hexdigest()
            assert service.verify_webhook_signature(payload, signature) is True

    def test_verify_webhook_signature_invalid(self):
        """Testa assinatura de webhook inválida"""
        service = PagarmeService()
        with patch.object(service, "webhook_secret", "secret"):
            payload = b"test_payload"
            assert service.verify_webhook_signature(payload, "wrong_signature") is False

    def test_global_service_instance(self):
        """Testa instância global padrão exportada"""
        assert pagarme_service is not None
        assert isinstance(pagarme_service, PagarmeService)
