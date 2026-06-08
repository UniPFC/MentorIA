import pytest
from unittest.mock import Mock
from src.middleware.csrf_protection import CSRFProtectionMiddleware


@pytest.mark.unit
class TestCSRFProtectionMiddleware:
    """Testes unitários para CSRFProtectionMiddleware"""

    def test_needs_csrf_protection_safe_methods(self):
        """Testa que métodos seguros não precisam de CSRF"""
        middleware = CSRFProtectionMiddleware(Mock(), Mock())
        
        for method in ["GET", "HEAD", "OPTIONS", "TRACE"]:
            request = Mock()
            request.method = method
            request.url.path = "/api/v1/test"
            request.headers = {}
            
            assert middleware._needs_csrf_protection(request) is False

    def test_needs_csrf_protection_auth_paths(self):
        """Testa que rotas de autenticação não precisam de CSRF"""
        middleware = CSRFProtectionMiddleware(Mock(), Mock())
        
        auth_paths = ["/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/auth/refresh"]
        
        for path in auth_paths:
            request = Mock()
            request.method = "POST"
            request.url.path = path
            request.headers = {}
            
            assert middleware._needs_csrf_protection(request) is False

    def test_needs_csrf_protection_auth_path_prefix(self):
        """Testa que rotas com prefixo de auth não precisam de CSRF"""
        middleware = CSRFProtectionMiddleware(Mock(), Mock())
        
        request = Mock()
        request.method = "POST"
        request.url.path = "/api/v1/auth/login/extra"
        request.headers = {}
        
        assert middleware._needs_csrf_protection(request) is False

    def test_needs_csrf_protection_public_paths(self):
        """Testa que rotas públicas não precisam de CSRF"""
        middleware = CSRFProtectionMiddleware(Mock(), Mock())
        
        public_paths = ["/", "/health", "/docs", "/openapi.json"]
        
        for path in public_paths:
            request = Mock()
            request.method = "POST"
            request.url.path = path
            request.headers = {}
            
            assert middleware._needs_csrf_protection(request) is False

    def test_needs_csrf_protection_with_api_key_header(self):
        """Testa que requests com x-api-key não precisam de CSRF"""
        middleware = CSRFProtectionMiddleware(Mock(), Mock())
        
        request = Mock()
        request.method = "POST"
        request.url.path = "/api/v1/test"
        request.headers = {"x-api-key": "test_key"}
        
        assert middleware._needs_csrf_protection(request) is False

    def test_needs_csrf_protection_with_authorization_header(self):
        """Testa que requests com authorization não precisam de CSRF"""
        middleware = CSRFProtectionMiddleware(Mock(), Mock())
        
        request = Mock()
        request.method = "POST"
        request.url.path = "/api/v1/test"
        request.headers = {"authorization": "Bearer token"}
        
        assert middleware._needs_csrf_protection(request) is False

    def test_needs_csrf_protection_with_json_content_type(self):
        """Testa que requests com application/json não precisam de CSRF"""
        middleware = CSRFProtectionMiddleware(Mock(), Mock())
        
        request = Mock()
        request.method = "POST"
        request.url.path = "/api/v1/test"
        request.headers = {"content-type": "application/json"}
        
        assert middleware._needs_csrf_protection(request) is False

    def test_needs_csrf_protection_with_multipart_form_data(self):
        """Testa que requests com multipart/form-data precisam de CSRF"""
        middleware = CSRFProtectionMiddleware(Mock(), Mock())
        
        request = Mock()
        request.method = "POST"
        request.url.path = "/api/v1/test"
        request.headers = {"content-type": "multipart/form-data"}
        
        assert middleware._needs_csrf_protection(request) is True

    def test_needs_csrf_protection_with_form_urlencoded(self):
        """Testa que requests com application/x-www-form-urlencoded precisam de CSRF"""
        middleware = CSRFProtectionMiddleware(Mock(), Mock())
        
        request = Mock()
        request.method = "POST"
        request.url.path = "/api/v1/test"
        request.headers = {"content-type": "application/x-www-form-urlencoded"}
        
        assert middleware._needs_csrf_protection(request) is True

    def test_needs_csrf_protection_no_content_type(self):
        """Testa que requests sem content-type precisam de CSRF"""
        middleware = CSRFProtectionMiddleware(Mock(), Mock())
        
        request = Mock()
        request.method = "POST"
        request.url.path = "/api/v1/test"
        request.headers = {}
        
        assert middleware._needs_csrf_protection(request) is True
