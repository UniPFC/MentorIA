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
        request.headers = {
            "X-Forwarded-For": "192.168.1.1",
            "X-Real-IP": "192.168.1.2"
        }

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

        with patch("src.api.routes.auth.auth_service") as mock_auth, patch("src.api.routes.auth.settings") as mock_settings:
            mock_settings.SECURE_COOKIES = False
            mock_auth.refresh_access_token.return_value = {
                "access_token": "new_access",
                "refresh_token": "new_refresh",
                "token_type": "bearer",
                "expires_in": 3600
            }
            result = await refresh_token(request, response, None, user_repo)
            assert result["access_token"] == "new_access"
            mock_auth.refresh_access_token.assert_called_once_with("cookie_refresh_token", user_repo)

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
