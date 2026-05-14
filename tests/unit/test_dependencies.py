import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials


@pytest.mark.unit
class TestDependencies:
    """Testes unitários para dependências da API"""

    def test_get_user_repo(self):
        """Testa obtenção de UserRepository"""
        from src.api.dependencies import get_user_repo
        
        mock_db = Mock()
        repo = get_user_repo(mock_db)
        
        assert repo is not None

    def test_get_chat_type_repo(self):
        """Testa obtenção de ChatTypeRepository"""
        from src.api.dependencies import get_chat_type_repo
        
        mock_db = Mock()
        repo = get_chat_type_repo(mock_db)
        
        assert repo is not None

    def test_get_chat_repo(self):
        """Testa obtenção de ChatRepository"""
        from src.api.dependencies import get_chat_repo
        
        mock_db = Mock()
        repo = get_chat_repo(mock_db)
        
        assert repo is not None

    def test_get_ingestion_job_repo(self):
        """Testa obtenção de IngestionJobRepository"""
        from src.api.dependencies import get_ingestion_job_repo
        
        mock_db = Mock()
        repo = get_ingestion_job_repo(mock_db)
        
        assert repo is not None

    def test_get_current_user_success(self):
        """Testa obtenção de usuário atual com sucesso"""
        from src.api.dependencies import get_current_user
        
        mock_user = Mock()
        mock_user.id = "test-user-id"
        
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "valid_token"
        
        with patch('src.api.dependencies.UserRepository') as mock_repo, \
             patch('src.api.dependencies.auth_service') as mock_auth:
            
            mock_auth.get_current_user_from_token.return_value = mock_user
            
            result = get_current_user(mock_credentials, Mock())
            
            assert result == mock_user
            mock_auth.get_current_user_from_token.assert_called_once()

    def test_get_current_user_invalid_token(self):
        """Testa obtenção de usuário com token inválido"""
        from src.api.dependencies import get_current_user
        
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "invalid_token"
        
        with patch('src.api.dependencies.UserRepository'), \
             patch('src.api.dependencies.auth_service') as mock_auth:
            
            mock_auth.get_current_user_from_token.return_value = None
            
            with pytest.raises(HTTPException) as exc_info:
                get_current_user(mock_credentials, Mock())
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_exception(self):
        """Testa obtenção de usuário quando ocorre exceção"""
        from src.api.dependencies import get_current_user
        
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "token"
        
        with patch('src.api.dependencies.UserRepository'), \
             patch('src.api.dependencies.auth_service') as mock_auth:
            
            mock_auth.get_current_user_from_token.side_effect = Exception("Auth error")
            
            with pytest.raises(HTTPException) as exc_info:
                get_current_user(mock_credentials, Mock())
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_active_user(self):
        """Testa obtenção de usuário ativo"""
        from src.api.dependencies import get_current_active_user
        
        mock_user = Mock()
        mock_user.is_active = True
        
        result = get_current_active_user(mock_user)
        
        assert result == mock_user

    def test_get_optional_current_user_no_credentials(self):
        """Testa usuário opcional sem credenciais"""
        from src.api.dependencies import get_optional_current_user
        
        result = get_optional_current_user(None, Mock())
        
        assert result is None

    def test_get_optional_current_user_valid(self):
        """Testa usuário opcional com token válido"""
        from src.api.dependencies import get_optional_current_user
        
        mock_user = Mock()
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "valid_token"
        
        with patch('src.api.dependencies.UserRepository'), \
             patch('src.api.dependencies.auth_service') as mock_auth:
            
            mock_auth.get_current_user_from_token.return_value = mock_user
            
            result = get_optional_current_user(mock_credentials, Mock())
            
            assert result == mock_user

    def test_get_optional_current_user_invalid(self):
        """Testa usuário opcional com token inválido"""
        from src.api.dependencies import get_optional_current_user
        
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "invalid_token"
        
        with patch('src.api.dependencies.UserRepository'), \
             patch('src.api.dependencies.auth_service') as mock_auth:
            
            mock_auth.get_current_user_from_token.side_effect = Exception("Auth error")
            
            result = get_optional_current_user(mock_credentials, Mock())
            
            assert result is None
