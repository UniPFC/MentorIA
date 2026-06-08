import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.middleware.https_security import (
    HTTPSRedirectMiddleware,
    SecurityHeadersMiddleware,
    SecureCookieMiddleware
)


@pytest.mark.unit
class TestHTTPSRedirectMiddleware:
    """Testes unitários para HTTPSRedirectMiddleware"""

    @pytest.mark.asyncio
    @patch('src.middleware.https_security.settings')
    async def test_dispatch_force_https_disabled(self, mock_settings):
        """Testa que quando FORCE_HTTPS=False, não redireciona"""
        mock_settings.FORCE_HTTPS = False
        
        middleware = HTTPSRedirectMiddleware(Mock())
        request = Mock()
        request.url.scheme = "http"
        call_next = AsyncMock(return_value=Mock())
        
        response = await middleware.dispatch(request, call_next)
        
        assert response == call_next.return_value
        call_next.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.middleware.https_security.settings')
    async def test_dispatch_already_https(self, mock_settings):
        """Testa que quando já é HTTPS, não redireciona"""
        mock_settings.FORCE_HTTPS = True
        
        middleware = HTTPSRedirectMiddleware(Mock())
        request = Mock()
        request.url.scheme = "https"
        request.url.replace = Mock(return_value=request.url)
        call_next = AsyncMock(return_value=Mock())
        
        response = await middleware.dispatch(request, call_next)
        
        assert response == call_next.return_value
        call_next.assert_called_once()
        request.url.replace.assert_not_called()

    @pytest.mark.asyncio
    @patch('src.middleware.https_security.settings')
    async def test_redirects_http_to_https(self, mock_settings):
        """Testa redirecionamento de HTTP para HTTPS"""
        mock_settings.FORCE_HTTPS = True
        
        middleware = HTTPSRedirectMiddleware(Mock())
        request = Mock()
        request.url.scheme = "http"
        request.url = Mock()
        https_url = Mock()
        https_url.__str__ = Mock(return_value="https://example.com")
        request.url.replace = Mock(return_value=https_url)
        call_next = AsyncMock(return_value=Mock())
        
        response = await middleware.dispatch(request, call_next)
        
        assert response.status_code == 301
        assert response.headers["Location"] == "https://example.com"
        call_next.assert_not_called()


@pytest.mark.unit
class TestSecurityHeadersMiddleware:
    """Testes unitários para SecurityHeadersMiddleware"""

    @pytest.mark.asyncio
    @patch('src.middleware.https_security.settings')
    async def test_dispatch_dev_mode(self, mock_settings):
        """Testa que em DEV_MODE, não adiciona headers"""
        mock_settings.DEV_MODE = True
        
        middleware = SecurityHeadersMiddleware(Mock())
        request = Mock()
        response = Mock()
        response.headers = {}
        call_next = AsyncMock(return_value=response)
        
        result = await middleware.dispatch(request, call_next)
        
        assert result == response
        assert len(result.headers) == 0

    @pytest.mark.asyncio
    @patch('src.middleware.https_security.settings')
    async def test_dispatch_adds_security_headers(self, mock_settings):
        """Testa que adiciona headers de segurança em produção"""
        mock_settings.DEV_MODE = False
        
        middleware = SecurityHeadersMiddleware(Mock())
        request = Mock()
        response = Mock()
        response.headers = {}
        call_next = AsyncMock(return_value=response)
        
        result = await middleware.dispatch(request, call_next)
        
        expected_headers = [
            "Strict-Transport-Security",
            "X-Frame-Options",
            "X-Content-Type-Options",
            "Referrer-Policy",
            "X-XSS-Protection",
            "Content-Security-Policy",
            "Permissions-Policy"
        ]
        
        for header in expected_headers:
            assert header in result.headers


@pytest.mark.unit
class TestSecureCookieMiddleware:
    """Testes unitários para SecureCookieMiddleware"""

    @pytest.mark.asyncio
    @patch('src.middleware.https_security.settings')
    async def test_dispatch_dev_mode(self, mock_settings):
        """Testa que em DEV_MODE, não modifica cookies"""
        mock_settings.DEV_MODE = True
        
        middleware = SecureCookieMiddleware(Mock())
        request = Mock()
        response = Mock()
        response.headers = {"Set-Cookie": "session=abc123"}
        call_next = AsyncMock(return_value=response)
        
        result = await middleware.dispatch(request, call_next)
        
        assert result.headers["Set-Cookie"] == "session=abc123"

    @pytest.mark.asyncio
    @patch('src.middleware.https_security.settings')
    async def test_dispatch_adds_secure_flag(self, mock_settings):
        """Testa que adiciona flag Secure a cookies"""
        mock_settings.DEV_MODE = False
        
        middleware = SecureCookieMiddleware(Mock())
        request = Mock()
        response = Mock()
        response.headers = {"Set-Cookie": "session=abc123"}
        call_next = AsyncMock(return_value=response)
        
        result = await middleware.dispatch(request, call_next)
        
        assert "Secure" in result.headers["Set-Cookie"]

    @pytest.mark.asyncio
    @patch('src.middleware.https_security.settings')
    async def test_dispatch_adds_httponly_flag(self, mock_settings):
        """Testa que adiciona flag HttpOnly a cookies"""
        mock_settings.DEV_MODE = False
        
        middleware = SecureCookieMiddleware(Mock())
        request = Mock()
        response = Mock()
        response.headers = {"Set-Cookie": "session=abc123"}
        call_next = AsyncMock(return_value=response)
        
        result = await middleware.dispatch(request, call_next)
        
        assert "HttpOnly" in result.headers["Set-Cookie"]

    @pytest.mark.asyncio
    @patch('src.middleware.https_security.settings')
    async def test_dispatch_adds_samesite_flag(self, mock_settings):
        """Testa que adiciona flag SameSite a cookies"""
        mock_settings.DEV_MODE = False
        
        middleware = SecureCookieMiddleware(Mock())
        request = Mock()
        response = Mock()
        response.headers = {"Set-Cookie": "session=abc123"}
        call_next = AsyncMock(return_value=response)
        
        result = await middleware.dispatch(request, call_next)
        
        assert "SameSite=Strict" in result.headers["Set-Cookie"]

    @pytest.mark.asyncio
    @patch('src.middleware.https_security.settings')
    async def test_dispatch_preserves_existing_flags(self, mock_settings):
        """Testa que preserva flags existentes nos cookies"""
        mock_settings.DEV_MODE = False
        
        middleware = SecureCookieMiddleware(Mock())
        request = Mock()
        response = Mock()
        response.headers = {"Set-Cookie": "session=abc123; Secure"}
        call_next = AsyncMock(return_value=response)
        
        result = await middleware.dispatch(request, call_next)
        
        # Should not add Secure again (it already exists)
        # The middleware checks if 'secure=' is already present
        assert "Secure" in result.headers["Set-Cookie"]
        assert "HttpOnly" in result.headers["Set-Cookie"]
        assert "SameSite=Strict" in result.headers["Set-Cookie"]

    @pytest.mark.asyncio
    @patch('src.middleware.https_security.settings')
    async def test_dispatch_case_insensitive_cookie_name(self, mock_settings):
        """Testa que detecta cookies case-insensitive"""
        mock_settings.DEV_MODE = False
        
        middleware = SecureCookieMiddleware(Mock())
        request = Mock()
        response = Mock()
        response.headers = {"set-cookie": "session=abc123"}
        call_next = AsyncMock(return_value=response)
        
        result = await middleware.dispatch(request, call_next)
        
        assert "Secure" in result.headers["set-cookie"]
