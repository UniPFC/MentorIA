import pytest
from unittest.mock import Mock, patch
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
