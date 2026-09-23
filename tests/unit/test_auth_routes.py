from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException, status

from src.api.routes.auth import _get_client_ip


@pytest.mark.unit
class TestAuthRoutes:
    """Testes unitários para rotas de autenticação"""

    def test_get_client_ip_with_x_forwarded_for(self):
        """Testa obtenção de IP via X-Forwarded-For header"""
        request = Mock()
        request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1"}

        ip = _get_client_ip(request)
        assert ip == "192.168.1.1"

    def test_get_client_ip_with_x_real_ip(self):
        """Testa obtenção de IP via X-Real-IP header"""
        request = Mock()
        request.headers = {"X-Real-IP": "192.168.1.2"}

        ip = _get_client_ip(request)
        assert ip == "192.168.1.2"

    def test_get_client_ip_with_client_host(self):
        """Testa obtenção de IP via client.host"""
        request = Mock()
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.3"

        ip = _get_client_ip(request)
        assert ip == "192.168.1.3"

    def test_get_client_ip_unknown(self):
        """Testa obtenção de IP quando não é possível determinar"""
        request = Mock()
        request.headers = {}
        request.client = None

        ip = _get_client_ip(request)
        assert ip == "unknown"

    def test_get_client_ip_x_forwarded_for_priority(self):
        """Testa que X-Forwarded-For tem prioridade sobre X-Real-IP"""
        request = Mock()
        request.headers = {"X-Forwarded-For": "192.168.1.1", "X-Real-IP": "192.168.1.2"}

        ip = _get_client_ip(request)
        assert ip == "192.168.1.1"

    def test_get_client_ip_x_forwarded_for_multiple_ips(self):
        """Testa que pega o primeiro IP quando há múltiplos em X-Forwarded-For"""
        request = Mock()
        request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1, 172.16.0.1"}

        ip = _get_client_ip(request)
        assert ip == "192.168.1.1"

    def test_get_client_ip_x_real_ip_priority_over_client_host(self):
        """Testa que X-Real-IP tem prioridade sobre client.host"""
        request = Mock()
        request.headers = {"X-Real-IP": "192.168.1.2"}
        request.client = Mock()
        request.client.host = "192.168.1.3"

        ip = _get_client_ip(request)
        assert ip == "192.168.1.2"

    @pytest.mark.asyncio
    async def test_refresh_token_from_cookie(self):
        """Testa refresh token pegando o token do cookie (linha 227)"""
        from src.api.routes.auth import refresh_token

        request = Mock()
        request.cookies = {"refreshToken": "cookie_refresh_token"}
        response = Mock()
        user_repo = Mock()

        with (
            patch("src.api.routes.auth.auth_service") as mock_auth,
            patch("src.api.routes.auth.settings") as mock_settings,
        ):
            mock_settings.SECURE_COOKIES = False
            mock_auth.refresh_access_token.return_value = {
                "access_token": "new_access",
                "refresh_token": "new_refresh",
                "token_type": "bearer",
                "expires_in": 3600,
            }
            result = await refresh_token(request, response, None, user_repo)
            assert result["access_token"] == "new_access"
            mock_auth.refresh_access_token.assert_called_once_with(
                "cookie_refresh_token", user_repo
            )

    @pytest.mark.asyncio
    async def test_refresh_token_missing(self):
        """Testa refresh token sem enviar token nenhum (linha 230)"""
        from src.api.routes.auth import refresh_token

        request = Mock()
        request.cookies = {}
        response = Mock()
        user_repo = Mock()

        with pytest.raises(HTTPException) as exc:
            await refresh_token(request, response, None, user_repo)

        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_logout_from_cookie(self):
        """Testa logout pegando o token do cookie (linha 290)"""
        from src.api.routes.auth import logout

        request = Mock()
        request.cookies = {"authToken": "cookie_auth_token"}
        response = Mock()
        current_user = Mock()
        current_user.id = "user_123"
        user_repo = Mock()

        # Simular que 'credentials' é None, forçando a busca no cookie
        result = await logout(request, response, None, current_user, user_repo)

        assert result["success"] is True
        user_repo.invalidate_token.assert_called_once_with("cookie_auth_token")

    @pytest.mark.asyncio
    async def test_delete_current_user_invalid_token(self):
        """Testa exclusão com token inválido ou tipo incorreto (400)"""
        from src.api.routes.auth import delete_current_user
        from src.api.schemas.auth import AccountDeletionRequest

        request_data = AccountDeletionRequest(token="invalid_token")
        request = Mock()
        response = Mock()
        user_repo = Mock()
        user_repo.get_token.return_value = None

        with pytest.raises(HTTPException) as exc:
            await delete_current_user(request_data, request, response, user_repo)

        assert exc.value.status_code == 400
        assert "Token inválido ou expirado" in exc.value.detail

    @pytest.mark.asyncio
    async def test_delete_current_user_expired_token(self):
        """Testa exclusão com token expirado (400)"""
        from datetime import UTC, datetime, timedelta

        from src.api.routes.auth import delete_current_user
        from src.api.schemas.auth import AccountDeletionRequest

        request_data = AccountDeletionRequest(token="expired_token")
        request = Mock()
        response = Mock()
        user_repo = Mock()

        token_obj = Mock()
        token_obj.token_type = "account_deletion"
        token_obj.expires_at = datetime.now(UTC) - timedelta(hours=1)
        user_repo.get_token.return_value = token_obj

        with pytest.raises(HTTPException) as exc:
            await delete_current_user(request_data, request, response, user_repo)

        assert exc.value.status_code == 400
        assert "Token expirado" in exc.value.detail

    @pytest.mark.asyncio
    async def test_delete_current_user_user_not_found(self):
        """Testa exclusão onde o usuário não é encontrado (404)"""
        from datetime import UTC, datetime, timedelta

        from src.api.routes.auth import delete_current_user
        from src.api.schemas.auth import AccountDeletionRequest

        request_data = AccountDeletionRequest(token="valid_token")
        request = Mock()
        response = Mock()
        user_repo = Mock()

        token_obj = Mock()
        token_obj.token_type = "account_deletion"
        token_obj.expires_at = datetime.now(UTC) + timedelta(hours=1)
        token_obj.user_id = "user_123"
        user_repo.get_token.return_value = token_obj
        user_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            await delete_current_user(request_data, request, response, user_repo)

        assert exc.value.status_code == 404
        assert "User not found" in exc.value.detail
        user_repo.invalidate_token.assert_called_once_with("valid_token")

    @pytest.mark.asyncio
    @patch("shared.database.session.SessionLocal")
    @patch("src.api.routes.auth.QdrantManager")
    async def test_delete_current_user_success(
        self, mock_qdrant_cls, mock_session_local
    ):
        """Testa exclusão da conta com sucesso e limpeza do Qdrant"""
        from datetime import UTC, datetime, timedelta

        from src.api.routes.auth import delete_current_user
        from src.api.schemas.auth import AccountDeletionRequest

        request_data = AccountDeletionRequest(token="valid_token")
        request = Mock()
        response = Mock()
        user_repo = Mock()

        token_obj = Mock()
        token_obj.token_type = "account_deletion"
        token_obj.expires_at = datetime.now(UTC) + timedelta(hours=1)
        token_obj.user_id = "user_123"
        user_repo.get_token.return_value = token_obj

        current_user = Mock()
        current_user.id = "user_123"
        current_user.username = "testuser"
        user_repo.get_by_id.return_value = current_user

        mock_db_session = Mock()
        mock_session_local.return_value = mock_db_session

        mock_chat_type = Mock()
        mock_chat_type.id = "ct_123"
        mock_db_session.query.return_value.filter.return_value.all.return_value = [
            mock_chat_type
        ]

        mock_qdrant_instance = Mock()
        mock_qdrant_cls.return_value = mock_qdrant_instance

        with patch("src.api.routes.auth.settings") as mock_settings:
            mock_settings.SECURE_COOKIES = True
            result = await delete_current_user(
                request_data, request, response, user_repo
            )

            assert result["success"] is True

            user_repo.invalidate_token.assert_called_once_with("valid_token")
            user_repo.delete.assert_called_once_with(current_user)
            response.delete_cookie.assert_any_call(
                key="authToken", httponly=True, samesite="lax", secure=True
            )
            response.delete_cookie.assert_any_call(
                key="refreshToken", httponly=True, samesite="lax", secure=True
            )

            mock_qdrant_instance.delete_collection.assert_called_once_with("ct_123")
            mock_db_session.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("shared.database.session.SessionLocal")
    @patch("src.api.routes.auth.QdrantManager")
    async def test_delete_current_user_qdrant_error(
        self, mock_qdrant_cls, mock_session_local
    ):
        """Testa exclusão da conta lidando com erro do Qdrant"""
        from datetime import UTC, datetime, timedelta

        from src.api.routes.auth import delete_current_user
        from src.api.schemas.auth import AccountDeletionRequest

        request_data = AccountDeletionRequest(token="valid_token")
        request = Mock()
        response = Mock()
        user_repo = Mock()

        token_obj = Mock()
        token_obj.token_type = "account_deletion"
        token_obj.expires_at = datetime.now(UTC) + timedelta(hours=1)
        token_obj.user_id = "user_123"
        user_repo.get_token.return_value = token_obj

        current_user = Mock()
        current_user.id = "user_123"
        user_repo.get_by_id.return_value = current_user

        mock_db_session = Mock()
        mock_session_local.return_value = mock_db_session

        mock_chat_type = Mock()
        mock_chat_type.id = "ct_123"
        mock_db_session.query.return_value.filter.return_value.all.return_value = [
            mock_chat_type
        ]

        mock_qdrant_instance = Mock()
        mock_qdrant_cls.return_value = mock_qdrant_instance
        mock_qdrant_instance.delete_collection.side_effect = Exception("Qdrant failure")

        result = await delete_current_user(request_data, request, response, user_repo)

        assert result["success"] is True
        user_repo.delete.assert_called_once_with(current_user)
        mock_qdrant_instance.delete_collection.assert_called_once_with("ct_123")
