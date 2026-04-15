import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4
from sqlalchemy.orm import Session
from src.services.auth import AuthService
from shared.database.models.user import User


@pytest.mark.unit
class TestAuthService:
    @pytest.fixture
    def auth_service(self):
        with patch('src.services.auth.settings') as mock_settings:
            mock_settings.SECRET_KEY = "test_secret_key"
            mock_settings.ALGORITHM = "HS256"
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
            mock_settings.REFRESH_TOKEN_EXPIRE_DAYS = 7
            return AuthService()
    
    def test_prepare_password_for_bcrypt(self, auth_service):
        password = "test_password_123"
        prepared = auth_service._prepare_password_for_bcrypt(password)
        
        assert isinstance(prepared, str)
        assert len(prepared) < 72
        
    def test_get_password_hash(self, auth_service):
        password = "secure_password_123"
        hashed = auth_service.get_password_hash(password)
        
        assert isinstance(hashed, str)
        assert hashed.startswith("$2b$")
        assert hashed != password
        
    def test_verify_password_correct(self, auth_service):
        password = "test_password_123"
        hashed = auth_service.get_password_hash(password)
        
        assert auth_service.verify_password(password, hashed) is True
        
    def test_verify_password_incorrect(self, auth_service):
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = auth_service.get_password_hash(password)
        
        assert auth_service.verify_password(wrong_password, hashed) is False
        
    def test_verify_password_error_handling(self, auth_service):
        with patch('src.services.auth.bcrypt.checkpw', side_effect=Exception("Bcrypt error")):
            result = auth_service.verify_password("password", "hash")
            assert result is False
    
    def test_get_password_hash_error_handling(self, auth_service):
        with patch('src.services.auth.bcrypt.hashpw', side_effect=Exception("Hash error")):
            with pytest.raises(Exception, match="Hash error"):
                auth_service.get_password_hash("password")
    
    def test_verify_password_reset_required(self, auth_service):
        password = "test_password"
        hashed = "RESET_REQUIRED_old_hash"
        
        assert auth_service.verify_password(password, hashed) is False
        
    def test_needs_password_reset(self, auth_service):
        assert auth_service.needs_password_reset("RESET_REQUIRED_hash") is True
        assert auth_service.needs_password_reset("$2b$12$normal_hash") is False
        
    def test_create_access_token(self, auth_service):
        data = {"sub": str(uuid4()), "username": "testuser"}
        token = auth_service.create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
    def test_create_access_token_with_expiry(self, auth_service):
        data = {"sub": str(uuid4()), "username": "testuser"}
        expires_delta = timedelta(minutes=15)
        token = auth_service.create_access_token(data, expires_delta)
        
        assert isinstance(token, str)
        
    def test_create_refresh_token(self, auth_service):
        data = {"sub": str(uuid4()), "username": "testuser"}
        token = auth_service.create_refresh_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
    def test_verify_token_valid(self, auth_service):
        data = {"sub": str(uuid4()), "username": "testuser"}
        token = auth_service.create_access_token(data)
        
        payload = auth_service.verify_token(token, "access")
        
        assert payload is not None
        assert payload["sub"] == data["sub"]
        assert payload["username"] == data["username"]
        assert payload["type"] == "access"
        
    def test_verify_token_wrong_type(self, auth_service):
        data = {"sub": str(uuid4()), "username": "testuser"}
        token = auth_service.create_access_token(data)
        
        payload = auth_service.verify_token(token, "refresh")
        
        assert payload is None
        
    def test_verify_token_expired(self, auth_service):
        data = {"sub": str(uuid4()), "username": "testuser"}
        expires_delta = timedelta(seconds=-1)
        token = auth_service.create_access_token(data, expires_delta)
        
        payload = auth_service.verify_token(token, "access")
        
        assert payload is None
        
    def test_verify_token_invalid(self, auth_service):
        invalid_token = "invalid.token.here"
        
        payload = auth_service.verify_token(invalid_token, "access")
        
        assert payload is None
    
    def test_verify_token_no_exp(self, auth_service):
        with patch('src.services.auth.jwt.decode') as mock_decode:
            mock_decode.return_value = {"sub": "user_id", "type": "access"}
            
            payload = auth_service.verify_token("token", "access")
            
            assert payload is None
        
    def test_authenticate_user_success(self, auth_service, db_session: Session, sample_user: User):
        mock_repo = MagicMock()
        mock_repo.get_by_email.return_value = sample_user
        
        password = "password123"
        sample_user.password_hash = auth_service.get_password_hash(password)
        
        user = auth_service.authenticate_user(mock_repo, sample_user.email, password)
        
        assert user is not None
        assert user.id == sample_user.id
        
    def test_authenticate_user_wrong_password(self, auth_service, sample_user: User):
        mock_repo = MagicMock()
        mock_repo.get_by_email.return_value = sample_user
        
        user = auth_service.authenticate_user(mock_repo, sample_user.email, "wrong_password")
        
        assert user is None
        
    def test_authenticate_user_not_found(self, auth_service):
        mock_repo = MagicMock()
        mock_repo.get_by_email.return_value = None
        
        user = auth_service.authenticate_user(mock_repo, "nonexistent@example.com", "password")
        
        assert user is None
        
    def test_create_user_tokens(self, auth_service, sample_user: User):
        mock_repo = MagicMock()
        
        tokens = auth_service.create_user_tokens(sample_user, mock_repo)
        
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
        assert tokens["expires_in"] > 0
        assert mock_repo.create_token.call_count == 2
        
    def test_refresh_access_token_success(self, auth_service, sample_user: User):
        refresh_token = auth_service.create_refresh_token({
            "sub": str(sample_user.id),
            "username": sample_user.username
        })
        
        mock_stored_token = MagicMock()
        mock_stored_token.token_type = "refresh"
        mock_stored_token.user_id = sample_user.id
        
        mock_repo = MagicMock()
        mock_repo.get_token.return_value = mock_stored_token
        
        result = auth_service.refresh_access_token(refresh_token, mock_repo)
        
        assert result is not None
        assert "access_token" in result
        assert result["token_type"] == "bearer"
        
    def test_refresh_access_token_invalid(self, auth_service):
        mock_repo = MagicMock()
        mock_repo.get_token.return_value = None
        
        result = auth_service.refresh_access_token("invalid_token", mock_repo)
        
        assert result is None
    
    def test_refresh_access_token_invalid_payload(self, auth_service):
        mock_repo = MagicMock()
        mock_stored_token = MagicMock()
        mock_stored_token.token_type = "refresh"
        mock_repo.get_token.return_value = mock_stored_token
        
        result = auth_service.refresh_access_token("invalid.jwt.token", mock_repo)
        
        assert result is None
        
    def test_get_current_user_from_token_invalid_payload(self, auth_service):
        mock_repo = MagicMock()
        mock_stored_token = MagicMock()
        mock_stored_token.is_active = True
        mock_repo.get_token.return_value = mock_stored_token
        
        result = auth_service.get_current_user_from_token("invalid.jwt.token", mock_repo)
        
        assert result is None
    
    def test_get_current_user_from_token_no_sub(self, auth_service):
        access_token = auth_service.create_access_token({
            "username": "testuser",
            "email": "test@example.com"
        })
        
        mock_stored_token = MagicMock()
        mock_stored_token.is_active = True
        mock_repo = MagicMock()
        mock_repo.get_token.return_value = mock_stored_token
        
        result = auth_service.get_current_user_from_token(access_token, mock_repo)
        
        assert result is None
    
    def test_get_current_user_from_token_invalid_uuid(self, auth_service):
        access_token = auth_service.create_access_token({
            "sub": "not-a-valid-uuid",
            "username": "testuser",
            "email": "test@example.com"
        })
        
        mock_stored_token = MagicMock()
        mock_stored_token.is_active = True
        mock_repo = MagicMock()
        mock_repo.get_token.return_value = mock_stored_token
        
        result = auth_service.get_current_user_from_token(access_token, mock_repo)
        
        assert result is None
    
    def test_get_current_user_from_token_success(self, auth_service, sample_user: User):
        access_token = auth_service.create_access_token({
            "sub": str(sample_user.id),
            "username": sample_user.username,
            "email": sample_user.email
        })
        
        mock_stored_token = MagicMock()
        mock_stored_token.is_active = True
        mock_stored_token.user_id = sample_user.id
        
        mock_repo = MagicMock()
        mock_repo.get_token.return_value = mock_stored_token
        mock_repo.get_by_id.return_value = sample_user
        
        user = auth_service.get_current_user_from_token(access_token, mock_repo)
        
        assert user is not None
        assert user.id == sample_user.id
        
    def test_get_current_user_from_token_inactive(self, auth_service):
        mock_stored_token = MagicMock()
        mock_stored_token.is_active = False
        
        mock_repo = MagicMock()
        mock_repo.get_token.return_value = mock_stored_token
        
        user = auth_service.get_current_user_from_token("some_token", mock_repo)
        
        assert user is None
        
    def test_get_current_user_from_token_not_found(self, auth_service):
        mock_repo = MagicMock()
        mock_repo.get_token.return_value = None
        
        user = auth_service.get_current_user_from_token("some_token", mock_repo)
        
        assert user is None
