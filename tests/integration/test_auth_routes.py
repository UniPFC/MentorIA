import pytest
from unittest.mock import Mock, patch
from fastapi import status


@pytest.fixture(autouse=True)
def mock_security_cache():
    """Mock security cache for all auth integration tests to prevent 429 errors."""
    with patch('src.api.routes.auth.security_cache') as mock_cache:
        mock_cache.should_block_ip.return_value = (False, None)
        mock_cache.detect_anomalies.return_value = {
            'risk_score': 'LOW',
            'anomalies': []
        }
        mock_cache.record_login_attempt.return_value = None
        yield


@pytest.mark.integration
class TestAuthRoutes:
    """Testes de integração para rotas de autenticação"""

    def test_register_user_success(self, client):
        """Testa registro de usuário com sucesso"""
        response = client.post("/api/v1/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "StrongPassword123!"
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"

    def test_register_user_reserved_username(self, client):
        """Testa registro com username reservado - Pydantic valida primeiro como 'MentorIA' reservado"""
        response = client.post("/api/v1/auth/register", json={
            "username": "mentoria",
            "email": "mentoria@example.com",
            "password": "StrongPassword123!"
        })
        
        # Pydantic validation returns 422, or route returns 400 if past validation
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_CONTENT]

    def test_register_user_duplicate_username(self, client, sample_user):
        """Testa registro com username duplicado"""
        response = client.post("/api/v1/auth/register", json={
            "username": sample_user.username,
            "email": "different@example.com",
            "password": "StrongPassword123!"
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Nome de usuário já existe" in response.json()["detail"]

    def test_register_user_duplicate_email(self, client, sample_user):
        """Testa registro com email duplicado"""
        response = client.post("/api/v1/auth/register", json={
            "username": "differentuser",
            "email": sample_user.email,
            "password": "StrongPassword123!"
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Email já cadastrado" in response.json()["detail"]

    def test_login_success(self, client, sample_user):
        """Testa login com sucesso"""
        response = client.post("/api/v1/auth/login", json={
            "email": sample_user.email,
            "password": "password123"
        })
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self, client, sample_user):
        """Testa login com credenciais inválidas"""
        response = client.post("/api/v1/auth/login", json={
            "email": sample_user.email,
            "password": "wrongpassword"
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, client):
        """Testa login com usuário inexistente"""
        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "anypassword"
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_authenticated(self, client, sample_user, sample_jwt_token):
        """Testa obter informações do usuário autenticado"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {sample_jwt_token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(sample_user.id)
        assert data["username"] == sample_user.username

    def test_me_unauthenticated(self, client):
        """Testa obter informações sem autenticação"""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_verify_token_valid(self, client, sample_jwt_token):
        """Testa verificação de token válido"""
        response = client.post(
            "/api/v1/auth/verify-token",
            headers={"Authorization": f"Bearer {sample_jwt_token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["valid"] is True

    def test_verify_token_invalid(self, client):
        """Testa verificação de token inválido"""
        response = client.post(
            "/api/v1/auth/verify-token",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_forgot_password_nonexistent_email(self, client):
        """Testa forgot password com email inexistente"""
        response = client.post("/api/v1/auth/forgot-password", json={
            "email": "nonexistent@example.com"
        })
        
        # Should return success even for non-existent emails (security)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["success"] is True

    def test_logout(self, client, sample_user, sample_jwt_token):
        """Testa logout de usuário"""
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {sample_jwt_token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

    def test_refresh_token_invalid(self, client):
        """Testa refresh com token inválido"""
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "invalid_refresh_token"
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_ip_blocked(self, client, sample_user):
        """Testa login com IP bloqueado"""
        with patch('src.api.routes.auth.security_cache') as mock_cache:
            mock_cache.should_block_ip.return_value = (True, "Test block reason")
            
            response = client.post("/api/v1/auth/login", json={
                "email": sample_user.email,
                "password": "password123"
            })
            
            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            assert "bloqueado" in response.json()["detail"]

    def test_login_anomaly_critical(self, client, sample_user):
        """Testa login com anomalia CRITICAL"""
        with patch('src.api.routes.auth.security_cache') as mock_cache:
            mock_cache.should_block_ip.return_value = (False, None)
            mock_cache.detect_anomalies.return_value = {
                'risk_score': 'CRITICAL',
                'anomalies': ['test_anomaly']
            }
            
            response = client.post("/api/v1/auth/login", json={
                "email": sample_user.email,
                "password": "password123"
            })
            
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert "Acesso bloqueado" in response.json()["detail"]

    def test_login_anomaly_high(self, client, sample_user):
        """Testa login com anomalia HIGH (rate limit)"""
        with patch('src.api.routes.auth.security_cache') as mock_cache:
            mock_cache.should_block_ip.return_value = (False, None)
            mock_cache.detect_anomalies.return_value = {
                'risk_score': 'HIGH',
                'anomalies': ['test_anomaly']
            }
            
            response = client.post("/api/v1/auth/login", json={
                "email": sample_user.email,
                "password": "password123"
            })
            
            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            assert "Muitas tentativas" in response.json()["detail"]

    def test_login_password_reset_required(self, client, sample_user, db_session):
        """Testa login quando senha precisa ser resetada"""
        from src.services.auth import AuthService
        
        # Set password hash to require reset
        sample_user.password_hash = "RESET_REQUIRED_test"
        db_session.commit()
        
        with patch('src.api.routes.auth.security_cache') as mock_cache, \
             patch('src.api.routes.auth.auth_service.authenticate_user', return_value=sample_user):
            mock_cache.should_block_ip.return_value = (False, None)
            mock_cache.detect_anomalies.return_value = {
                'risk_score': 'LOW',
                'anomalies': []
            }
            
            response = client.post("/api/v1/auth/login", json={
                "email": sample_user.email,
                "password": "password123"
            })
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert "senha precisa ser redefinida" in response.json()["detail"]

    def test_forgot_password_existing_email(self, client, sample_user):
        """Testa forgot password com email existente"""
        with patch('src.services.email.email_service.send_password_reset_email', return_value=True):
            response = client.post("/api/v1/auth/forgot-password", json={
                "email": sample_user.email
            })
            
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["success"] is True

    def test_forgot_password_email_send_failure(self, client, sample_user):
        """Testa forgot password quando envio de email falha"""
        with patch('src.services.email.email_service.send_password_reset_email', return_value=False):
            response = client.post("/api/v1/auth/forgot-password", json={
                "email": sample_user.email
            })
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_confirm_reset_password_success(self, client, sample_user, sample_password_reset_token):
        """Testa confirmação de reset de senha com sucesso"""
        with patch('src.services.email.email_service.send_password_changed_email', return_value=True):
            response = client.post("/api/v1/auth/confirm-reset-password", json={
                "token": sample_password_reset_token.token,
                "new_password": "NewStrongPassword123!"
            })
            
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["success"] is True

    def test_refresh_token_success(self, client, sample_user, db_session):
        """Testa refresh de token com sucesso"""
        from src.services.auth import AuthService
        from src.repositories.user import UserRepository
        
        auth_service = AuthService()
        user_repo = UserRepository(db_session)
        
        # Create refresh token
        tokens = auth_service.create_user_tokens(sample_user, user_repo)
        db_session.commit()
        
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": tokens["refresh_token"]
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.json()

    def test_confirm_reset_password_invalid_token(self, client):
        """Testa reset de senha com token inválido"""
        response = client.post("/api/v1/auth/confirm-reset-password", json={
            "token": "invalid_token",
            "new_password": "NewPassword123!"
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Token inválido" in response.json()["detail"]
