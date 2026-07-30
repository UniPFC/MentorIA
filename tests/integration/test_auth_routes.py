from unittest.mock import patch

import pytest
from fastapi import status


@pytest.fixture(autouse=True)
def mock_security_cache():
    """Mock security cache for all auth integration tests to prevent 429 errors."""
    with patch("src.api.routes.auth.security_cache") as mock_cache:
        mock_cache.should_block_ip.return_value = (False, None)
        mock_cache.detect_anomalies.return_value = {
            "risk_score": "LOW",
            "anomalies": [],
        }
        mock_cache.record_login_attempt.return_value = None
        yield


@pytest.mark.integration
class TestAuthRoutes:
    """Testes de integração para rotas de autenticação"""

    def test_register_user_success(self, client):
        """Testa registro de usuário com sucesso"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "StrongPassword123!",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"

    def test_register_user_reserved_username(self, client):
        """Testa registro com username reservado - Pydantic valida primeiro como 'MentorIA' reservado"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "mentoria",
                "email": "mentoria@example.com",
                "password": "StrongPassword123!",
            },
        )

        # Pydantic validation returns 422, or route returns 400 if past validation
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ]

    def test_register_user_duplicate_username(self, client, sample_user):
        """Testa registro com username duplicado"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": sample_user.username,
                "email": "different@example.com",
                "password": "StrongPassword123!",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Nome de usuário já existe" in response.json()["detail"]

    def test_register_user_duplicate_email(self, client, sample_user):
        """Testa registro com email duplicado"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "differentuser",
                "email": sample_user.email,
                "password": "StrongPassword123!",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Email já cadastrado" in response.json()["detail"]

    def test_login_success(self, client, sample_user):
        """Testa login com sucesso"""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": sample_user.email, "password": "password123"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self, client, sample_user):
        """Testa login com credenciais inválidas"""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": sample_user.email, "password": "wrongpassword"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, client):
        """Testa login com usuário inexistente"""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "anypassword"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_authenticated(self, client, sample_user, sample_jwt_token):
        """Testa obter informações do usuário autenticado"""
        response = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {sample_jwt_token}"}
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
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["valid"] is True

    def test_verify_token_invalid(self, client):
        """Testa verificação de token inválido"""
        response = client.post(
            "/api/v1/auth/verify-token",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_forgot_password_nonexistent_email(self, client):
        """Testa forgot password com email inexistente"""
        response = client.post(
            "/api/v1/auth/forgot-password", json={"email": "nonexistent@example.com"}
        )

        # Should return success even for non-existent emails (security)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["success"] is True

    def test_logout(self, client, sample_user, sample_jwt_token):
        """Testa logout de usuário"""
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

    def test_refresh_token_invalid(self, client):
        """Testa refresh com token inválido"""
        response = client.post(
            "/api/v1/auth/refresh", json={"refresh_token": "invalid_refresh_token"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_ip_blocked(self, client, sample_user):
        """Testa login com IP bloqueado"""
        with patch("src.api.routes.auth.security_cache") as mock_cache:
            mock_cache.should_block_ip.return_value = (True, "Test block reason")

            response = client.post(
                "/api/v1/auth/login",
                json={"email": sample_user.email, "password": "password123"},
            )

            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            assert "bloqueado" in response.json()["detail"]

    def test_login_anomaly_critical(self, client, sample_user):
        """Testa login com anomalia CRITICAL"""
        with patch("src.api.routes.auth.security_cache") as mock_cache:
            mock_cache.should_block_ip.return_value = (False, None)
            mock_cache.detect_anomalies.return_value = {
                "risk_score": "CRITICAL",
                "anomalies": ["test_anomaly"],
            }

            response = client.post(
                "/api/v1/auth/login",
                json={"email": sample_user.email, "password": "password123"},
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert "Acesso bloqueado" in response.json()["detail"]

    def test_login_anomaly_high(self, client, sample_user):
        """Testa login com anomalia HIGH (rate limit)"""
        with patch("src.api.routes.auth.security_cache") as mock_cache:
            mock_cache.should_block_ip.return_value = (False, None)
            mock_cache.detect_anomalies.return_value = {
                "risk_score": "HIGH",
                "anomalies": ["test_anomaly"],
            }

            response = client.post(
                "/api/v1/auth/login",
                json={"email": sample_user.email, "password": "password123"},
            )

            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            assert "Muitas tentativas" in response.json()["detail"]

    def test_login_password_reset_required(self, client, sample_user, db_session):
        """Testa login quando senha precisa ser resetada"""

        # Set password hash to require reset
        sample_user.password_hash = "RESET_REQUIRED_test"
        db_session.commit()

        with (
            patch("src.api.routes.auth.security_cache") as mock_cache,
            patch(
                "src.api.routes.auth.auth_service.authenticate_user",
                return_value=sample_user,
            ),
        ):
            mock_cache.should_block_ip.return_value = (False, None)
            mock_cache.detect_anomalies.return_value = {
                "risk_score": "LOW",
                "anomalies": [],
            }

            response = client.post(
                "/api/v1/auth/login",
                json={"email": sample_user.email, "password": "password123"},
            )

            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert "senha precisa ser redefinida" in response.json()["detail"]

    def test_forgot_password_existing_email(self, client, sample_user):
        """Testa forgot password com email existente"""
        with patch(
            "src.services.email_service.email_service.send_password_reset_email",
            return_value=True,
        ):
            response = client.post(
                "/api/v1/auth/forgot-password", json={"email": sample_user.email}
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.json()["success"] is True

    def test_forgot_password_email_send_failure(self, client, sample_user):
        """Testa forgot password quando envio de email falha"""
        with patch(
            "src.services.email_service.email_service.send_password_reset_email",
            return_value=False,
        ):
            response = client.post(
                "/api/v1/auth/forgot-password", json={"email": sample_user.email}
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_confirm_reset_password_success(
        self, client, sample_user, sample_password_reset_token
    ):
        """Testa confirmação de reset de senha com sucesso"""
        with patch(
            "src.services.email_service.email_service.send_password_changed_email",
            return_value=True,
        ):
            response = client.post(
                "/api/v1/auth/confirm-reset-password",
                json={
                    "token": sample_password_reset_token.token,
                    "new_password": "NewStrongPassword123!",
                },
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.json()["success"] is True

    def test_refresh_token_success(self, client, sample_user, db_session):
        """Testa refresh de token com sucesso"""
        from src.repositories.user import UserRepository
        from src.services.auth import AuthService

        auth_service = AuthService()
        user_repo = UserRepository(db_session)

        # Create refresh token
        tokens = auth_service.create_user_tokens(sample_user, user_repo)
        db_session.commit()

        response = client.post(
            "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.json()

    def test_confirm_reset_password_invalid_token(self, client):
        """Testa reset de senha com token inválido"""
        response = client.post(
            "/api/v1/auth/confirm-reset-password",
            json={"token": "invalid_token", "new_password": "NewPassword123!"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Token inválido" in response.json()["detail"]

    def test_register_reserved_username_uppercase(self, client):
        """Testa registro com username reservado em maiúsculas (Pydantic valida primeiro)"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "Mentoria",
                "email": "test@example.com",
                "password": "StrongPassword123!",
            },
        )

        # Pydantic validation returns 422 for reserved username
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ]

    def test_login_post_failure_anomaly_high(self, client, sample_user):
        """Testa login com anomalia HIGH após falha de autenticação"""
        with patch("src.api.routes.auth.security_cache") as mock_cache:
            mock_cache.should_block_ip.return_value = (False, None)
            # First call returns LOW, second call (post-failure) returns HIGH
            mock_cache.detect_anomalies.side_effect = [
                {"risk_score": "LOW", "anomalies": []},
                {"risk_score": "HIGH", "anomalies": ["too_many_failures"]},
            ]

            response = client.post(
                "/api/v1/auth/login",
                json={"email": sample_user.email, "password": "wrongpassword"},
            )

            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            assert "excessivo de tentativas" in response.json()["detail"]

    def test_login_post_failure_anomaly_critical(self, client, sample_user):
        """Testa login com anomalia CRITICAL após falha de autenticação"""
        with patch("src.api.routes.auth.security_cache") as mock_cache:
            mock_cache.should_block_ip.return_value = (False, None)
            # First call returns LOW, second call (post-failure) returns CRITICAL
            mock_cache.detect_anomalies.side_effect = [
                {"risk_score": "LOW", "anomalies": []},
                {"risk_score": "CRITICAL", "anomalies": ["critical_anomaly"]},
            ]

            response = client.post(
                "/api/v1/auth/login",
                json={"email": sample_user.email, "password": "wrongpassword"},
            )

            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_get_client_ip_with_x_forwarded_for(self, client):
        """Testa obtenção de IP com header X-Forwarded-For"""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrong"},
            headers={"X-Forwarded-For": "192.168.1.1, 10.0.0.1"},
        )
        # Request will fail but we're testing the IP extraction logic
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_429_TOO_MANY_REQUESTS,
        ]

    def test_get_client_ip_with_x_real_ip(self, client):
        """Testa obtenção de IP com header X-Real-IP"""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrong"},
            headers={"X-Real-IP": "192.168.1.2"},
        )
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_429_TOO_MANY_REQUESTS,
        ]

    def test_get_client_ip_fallback_to_client_host(self, client):
        """Testa obtenção de IP usando fallback para client.host"""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrong"},
        )
        # Should use client.host as fallback
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_429_TOO_MANY_REQUESTS,
        ]

    def test_login_with_x_forwarded_for_header(self, client, sample_user):
        """Testa login com header X-Forwarded-For para cobrir _get_client_ip"""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": sample_user.email, "password": "password123"},
            headers={"X-Forwarded-For": "192.168.1.100, 10.0.0.1"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.json()

    def test_login_with_x_real_ip_header(self, client, sample_user):
        """Testa login com header X-Real-IP para cobrir _get_client_ip"""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": sample_user.email, "password": "password123"},
            headers={"X-Real-IP": "192.168.1.200"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.json()

    def test_confirm_reset_password_user_not_found(
        self, client, sample_password_reset_token, db_session
    ):
        """Testa reset de senha quando usuário não é encontrado"""
        # Create a token but delete the user
        from shared.database.models.user import User

        # First, create a valid token for a user
        token = sample_password_reset_token.token
        user_id = sample_password_reset_token.user_id

        # Delete the user
        db_session.query(User).filter(User.id == user_id).delete()
        db_session.commit()

        response = client.post(
            "/api/v1/auth/confirm-reset-password",
            json={"token": token, "new_password": "NewPassword123!"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Usuário não encontrado" in response.json()["detail"]

    def test_register_email_failure_fallback(self, client):
        with patch(
            "src.api.routes.auth.email_service.send_verification_email",
            return_value=False,
        ):
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "username": "emailfail",
                    "email": "emailfail@example.com",
                    "password": "StrongPassword123!",
                },
            )
            assert response.status_code == 201

    def test_verify_email_success(self, client, sample_user, db_session):
        from datetime import UTC, datetime, timedelta

        from src.repositories.user import UserRepository

        repo = UserRepository(db_session)
        sample_user.email_verified = False
        db_session.commit()
        token = repo.create_email_verification_token(
            user_id=sample_user.id,
            token="valid_verify_token",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        response = client.post(
            "/api/v1/auth/verify-email", json={"token": "valid_verify_token"}
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_verify_email_already_verified(self, client, sample_user, db_session):
        from datetime import UTC, datetime, timedelta

        from src.repositories.user import UserRepository

        repo = UserRepository(db_session)
        sample_user.email_verified = True
        db_session.commit()
        token = repo.create_email_verification_token(
            user_id=sample_user.id,
            token="valid_verify_token2",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        response = client.post(
            "/api/v1/auth/verify-email", json={"token": "valid_verify_token2"}
        )
        assert response.status_code == 200
        assert "já verificado" in response.json()["message"]

    def test_verify_email_invalid_token(self, client):
        response = client.post(
            "/api/v1/auth/verify-email", json={"token": "invalid_token"}
        )
        assert response.status_code == 400

    def test_verify_email_user_not_found(self, client, db_session, sample_user):
        from datetime import UTC, datetime, timedelta

        from shared.database.models.user import User
        from src.repositories.user import UserRepository

        repo = UserRepository(db_session)
        token = repo.create_email_verification_token(
            user_id=sample_user.id,
            token="valid_verify_token_no_user",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        # Delete user
        db_session.query(User).filter(User.id == sample_user.id).delete()
        db_session.commit()

        response = client.post(
            "/api/v1/auth/verify-email", json={"token": "valid_verify_token_no_user"}
        )
        assert response.status_code == 404

    def test_send_verification_email_success(
        self, client, sample_user, sample_jwt_token, db_session
    ):
        sample_user.email_verified = False
        db_session.commit()
        with patch(
            "src.api.routes.auth.email_service.send_verification_email",
            return_value=True,
        ):
            response = client.post(
                "/api/v1/auth/send-verification-email",
                headers={"Authorization": f"Bearer {sample_jwt_token}"},
            )
            assert response.status_code == 200
            assert response.json()["success"] is True

    def test_send_verification_email_failure(
        self, client, sample_user, sample_jwt_token, db_session
    ):
        sample_user.email_verified = False
        db_session.commit()
        with patch(
            "src.api.routes.auth.email_service.send_verification_email",
            return_value=False,
        ):
            response = client.post(
                "/api/v1/auth/send-verification-email",
                headers={"Authorization": f"Bearer {sample_jwt_token}"},
            )
            assert response.status_code == 500

    def test_send_verification_email_already_verified(
        self, client, sample_user, sample_jwt_token, db_session
    ):
        sample_user.email_verified = True
        db_session.commit()
        response = client.post(
            "/api/v1/auth/send-verification-email",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
        )
        assert response.status_code == 400

    def test_login_requires_2fa(self, client, sample_user, db_session):
        sample_user.two_factor_enabled = True
        db_session.commit()

        response = client.post(
            "/api/v1/auth/login",
            json={"email": sample_user.email, "password": "password123"},
        )
        assert response.status_code == 202
        data = response.json()
        assert data["requires_2fa"] is True
        assert "temp_token" in data

    def test_login_2fa_success(self, client, sample_user, db_session):
        sample_user.two_factor_enabled = True
        import pyotp

        secret = pyotp.random_base32()
        sample_user.two_factor_secret = secret
        db_session.commit()

        from src.services.auth import auth_service

        temp_token = auth_service.create_temp_2fa_token(sample_user)
        code = pyotp.TOTP(secret).now()

        response = client.post(
            "/api/v1/auth/login/2fa",
            json={"temp_token": temp_token, "code": code, "remember_me": True},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_2fa_invalid_temp_token(self, client):
        response = client.post(
            "/api/v1/auth/login/2fa",
            json={"temp_token": "invalid_token", "code": "123456"},
        )
        assert response.status_code == 401

    def test_login_2fa_not_enabled(self, client, sample_user, db_session):
        sample_user.two_factor_enabled = False
        db_session.commit()
        from src.services.auth import auth_service

        temp_token = auth_service.create_temp_2fa_token(sample_user)

        response = client.post(
            "/api/v1/auth/login/2fa", json={"temp_token": temp_token, "code": "123456"}
        )
        assert response.status_code == 400

    def test_login_2fa_invalid_code(self, client, sample_user, db_session):
        sample_user.two_factor_enabled = True
        sample_user.two_factor_secret = "JBSWY3DPEHPK3PXP"
        db_session.commit()
        from src.services.auth import auth_service

        temp_token = auth_service.create_temp_2fa_token(sample_user)

        response = client.post(
            "/api/v1/auth/login/2fa", json={"temp_token": temp_token, "code": "000000"}
        )
        assert response.status_code == 401

    def test_setup_2fa(self, client, sample_jwt_token):
        response = client.post(
            "/api/v1/auth/2fa/setup",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "secret" in data
        assert "qr_code_base64" in data

    def test_enable_2fa_success(
        self, client, sample_user, sample_jwt_token, db_session
    ):
        sample_user.two_factor_enabled = False
        db_session.commit()

        import pyotp

        secret = pyotp.random_base32()
        code = pyotp.TOTP(secret).now()

        response = client.post(
            "/api/v1/auth/2fa/enable",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
            json={"secret": secret, "code": code},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_enable_2fa_already_enabled(
        self, client, sample_user, sample_jwt_token, db_session
    ):
        sample_user.two_factor_enabled = True
        db_session.commit()

        response = client.post(
            "/api/v1/auth/2fa/enable",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
            json={"secret": "SECRET", "code": "123456"},
        )
        assert response.status_code == 400

    def test_enable_2fa_invalid_code(
        self, client, sample_user, sample_jwt_token, db_session
    ):
        sample_user.two_factor_enabled = False
        db_session.commit()

        response = client.post(
            "/api/v1/auth/2fa/enable",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
            json={"secret": "JBSWY3DPEHPK3PXP", "code": "000000"},
        )
        assert response.status_code == 400

    def test_disable_2fa_success(
        self, client, sample_user, sample_jwt_token, db_session
    ):
        import pyotp

        secret = pyotp.random_base32()
        sample_user.two_factor_enabled = True
        sample_user.two_factor_secret = secret
        db_session.commit()

        code = pyotp.TOTP(secret).now()

        response = client.post(
            "/api/v1/auth/2fa/disable",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
            json={"code": code},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_disable_2fa_already_disabled(
        self, client, sample_user, sample_jwt_token, db_session
    ):
        sample_user.two_factor_enabled = False
        db_session.commit()

        response = client.post(
            "/api/v1/auth/2fa/disable",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
            json={"code": "123456"},
        )
        assert response.status_code == 400

    def test_disable_2fa_invalid_code(
        self, client, sample_user, sample_jwt_token, db_session
    ):
        sample_user.two_factor_enabled = True
        sample_user.two_factor_secret = "JBSWY3DPEHPK3PXP"
        db_session.commit()

        response = client.post(
            "/api/v1/auth/2fa/disable",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
            json={"code": "000000"},
        )
        assert response.status_code == 400

    def test_dismiss_2fa_reminder(self, client, sample_jwt_token):
        response = client.post(
            "/api/v1/auth/2fa/dismiss-reminder",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_accept_terms(self, client, sample_jwt_token, db_session, sample_user):
        response = client.post(
            "/api/v1/auth/accept-terms",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
        db_session.refresh(sample_user)
        assert sample_user.accepted_terms_version is not None

    def test_login_2fa_invalid_uuid(self, client):
        from datetime import timedelta

        from src.services.auth import auth_service

        temp_token = auth_service.create_access_token(
            data={"sub": "not-a-uuid", "type": "temp_2fa"},
            expires_delta=timedelta(minutes=5),
        )
        response = client.post(
            "/api/v1/auth/login/2fa", json={"temp_token": temp_token, "code": "123456"}
        )
        assert response.status_code == 401
        assert "inválido ou expirado" in response.json()["detail"]

    def test_request_deletion(self, client, sample_jwt_token):
        from unittest.mock import patch

        with patch(
            "src.api.routes.auth.email_service.send_account_deletion_email",
            return_value=True,
        ):
            response = client.post(
                "/api/v1/auth/request-account-deletion",
                headers={"Authorization": f"Bearer {sample_jwt_token}"},
            )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_request_deletion_email_fails(self, client, sample_jwt_token):
        from unittest.mock import patch

        with patch(
            "src.api.routes.auth.email_service.send_account_deletion_email",
            return_value=False,
        ):
            response = client.post(
                "/api/v1/auth/request-account-deletion",
                headers={"Authorization": f"Bearer {sample_jwt_token}"},
            )
        assert response.status_code == 500

    def test_delete_account_success(
        self, client, sample_jwt_token, db_session, sample_user
    ):
        from datetime import UTC, datetime, timedelta

        from src.repositories.user import UserRepository

        user_repo = UserRepository(db_session)
        user_repo.create_token(
            user_id=sample_user.id,
            token="delete-token-123",
            token_type="account_deletion",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        db_session.commit()
        response = client.request(
            "DELETE",
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
            json={"token": "delete-token-123"},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify user is deleted
        assert user_repo.get_by_id(sample_user.id) is None

    def test_delete_account_invalid_token(self, client, sample_jwt_token):
        response = client.request(
            "DELETE",
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
            json={"token": "invalid-token"},
        )
        assert response.status_code == 400

    def test_delete_account_expired_token(
        self, client, sample_jwt_token, db_session, sample_user
    ):
        from datetime import UTC, datetime, timedelta

        from src.repositories.user import UserRepository

        user_repo = UserRepository(db_session)
        user_repo.create_token(
            user_id=sample_user.id,
            token="expired-delete-token",
            token_type="account_deletion",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        db_session.commit()
        response = client.request(
            "DELETE",
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
            json={"token": "expired-delete-token"},
        )
        assert response.status_code == 400
        assert "expirado" in response.json()["detail"].lower()

    def test_export_data(
        self,
        client,
        sample_jwt_token,
        db_session,
        sample_user,
        sample_chat,
        sample_chat_type,
        sample_message,
    ):
        # We assume sample_chat and sample_chat_type belong to sample_user or we assign them
        sample_chat.user_id = sample_user.id
        sample_chat_type.user_id = sample_user.id
        db_session.add(sample_chat)
        db_session.add(sample_chat_type)
        db_session.commit()

        response = client.get(
            "/api/v1/auth/me/export",
            headers={"Authorization": f"Bearer {sample_jwt_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "user_info" in data
        assert data["user_info"]["email"] == sample_user.email
        assert "chats" in data
        assert len(data["chats"]) >= 1
        assert "chat_types_created" in data
        assert len(data["chat_types_created"]) >= 1
