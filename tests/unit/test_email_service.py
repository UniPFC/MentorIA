from unittest.mock import MagicMock, patch

import pytest

from src.services.email_service import EmailService


@pytest.mark.unit
class TestEmailService:
    @pytest.fixture
    def email_service(self):
        with patch("src.services.email_service.settings") as mock_settings:
            mock_settings.SMTP_SERVER = "smtp.test.com"
            mock_settings.SMTP_PORT = 587
            mock_settings.SMTP_USERNAME = "test@test.com"
            mock_settings.SMTP_PASSWORD = "password"
            mock_settings.FROM_EMAIL = "noreply@test.com"
            mock_settings.FRONTEND_URL = "http://localhost:3000"
            return EmailService()

    def test_init(self, email_service):
        assert email_service.smtp_server == "smtp.test.com"
        assert email_service.smtp_port == 587
        assert email_service.smtp_username == "test@test.com"
        assert email_service.smtp_password == "password"
        assert email_service.from_email == "noreply@test.com"
        assert email_service.frontend_url == "http://localhost:3000"

    def test_init_with_defaults(self):
        with patch("src.services.email_service.settings") as mock_settings:
            del mock_settings.SMTP_SERVER
            del mock_settings.SMTP_PORT
            del mock_settings.SMTP_USERNAME
            del mock_settings.SMTP_PASSWORD
            del mock_settings.FROM_EMAIL
            del mock_settings.FRONTEND_URL

            service = EmailService()

            assert service.smtp_server == "smtp.gmail.com"
            assert service.smtp_port == 587

    def test_generate_reset_token(self, email_service):
        token = email_service.generate_reset_token()

        assert isinstance(token, str)
        assert len(token) > 0

    @patch("src.services.email_service.smtplib.SMTP")
    def test_send_email_success(self, mock_smtp, email_service):
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = email_service._send_email(
            to_email="user@test.com",
            subject="Test Subject",
            html_body="<p>Test Body</p>",
        )

        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@test.com", "password")
        mock_server.send_message.assert_called_once()

    @patch("src.services.email_service.smtplib.SMTP")
    def test_send_email_failure(self, mock_smtp, email_service):
        mock_smtp.side_effect = Exception("SMTP error")

        result = email_service._send_email(
            to_email="user@test.com",
            subject="Test Subject",
            html_body="<p>Test Body</p>",
        )

        assert result is False

    @patch("src.services.email_service.smtplib.SMTP")
    def test_send_password_reset_email_success(self, mock_smtp, email_service):
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = email_service.send_password_reset_email(
            to_email="user@test.com", username="testuser", reset_token="test_token_123"
        )

        assert result is True
        mock_server.send_message.assert_called_once()

        call_args = mock_server.send_message.call_args[0][0]
        email_string = call_args.as_string()
        assert "Recuperação de Senha - MentorIA" in call_args["Subject"]
        assert "user@test.com" in call_args["To"]

    @patch("src.services.email_service.smtplib.SMTP")
    def test_send_password_reset_email_failure(self, mock_smtp, email_service):
        mock_smtp.side_effect = Exception("SMTP error")

        result = email_service.send_password_reset_email(
            to_email="user@test.com", username="testuser", reset_token="test_token_123"
        )

        assert result is False

    @patch("src.services.email_service.smtplib.SMTP")
    def test_send_password_changed_email_success(self, mock_smtp, email_service):
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = email_service.send_password_changed_email(
            to_email="user@test.com", username="testuser"
        )

        assert result is True
        mock_server.send_message.assert_called_once()

        call_args = mock_server.send_message.call_args[0][0]
        assert "Senha Alterada" in call_args["Subject"]
        assert "user@test.com" in call_args["To"]

    @patch("src.services.email_service.smtplib.SMTP")
    def test_send_password_changed_email_failure(self, mock_smtp, email_service):
        mock_smtp.side_effect = Exception("SMTP error")

        result = email_service.send_password_changed_email(
            to_email="user@test.com", username="testuser"
        )

        assert result is False

    def test_get_base_template_fallback(self, email_service):
        with patch("builtins.open", side_effect=Exception("File read error")):
            template = email_service._get_base_template()
            assert "<html>" in template

    @patch("src.services.email_service.smtplib.SMTP")
    def test_send_password_reset_notification_success(self, mock_smtp, email_service):
        mock_server = mock_smtp.return_value.__enter__.return_value
        result = email_service.send_password_reset_notification(
            to_email="user@test.com", username="testuser"
        )
        assert result is True
        mock_server.send_message.assert_called_once()

    @patch("src.services.email_service.smtplib.SMTP")
    def test_send_password_reset_notification_failure(self, mock_smtp, email_service):
        mock_smtp.side_effect = Exception("SMTP error")
        result = email_service.send_password_reset_notification(
            to_email="user@test.com", username="testuser"
        )
        assert result is False

    @patch("src.services.email_service.smtplib.SMTP")
    def test_send_verification_email_success(self, mock_smtp, email_service):
        mock_server = mock_smtp.return_value.__enter__.return_value
        result = email_service.send_verification_email(
            to_email="user@test.com", username="testuser", token="test_token"
        )
        assert result is True
        mock_server.send_message.assert_called_once()

    @patch("src.services.email_service.smtplib.SMTP")
    def test_send_verification_email_custom_frontend_url(
        self, mock_smtp, email_service
    ):
        mock_server = mock_smtp.return_value.__enter__.return_value
        result = email_service.send_verification_email(
            to_email="user@test.com",
            username="testuser",
            token="test_token",
            frontend_url="https://custom-tunnel.trycloudflare.com",
        )
        assert result is True
        mock_server.send_message.assert_called_once()
        call_args = mock_server.send_message.call_args[0][0]
        html_body = call_args.get_payload(0).get_payload(decode=True).decode("utf-8")
        assert (
            "https://custom-tunnel.trycloudflare.com/verify-email?token=test_token"
            in html_body
        )

    @patch("src.services.email_service.smtplib.SMTP")
    def test_send_password_reset_email_custom_frontend_url(
        self, mock_smtp, email_service
    ):
        mock_server = mock_smtp.return_value.__enter__.return_value
        result = email_service.send_password_reset_email(
            to_email="user@test.com",
            username="testuser",
            reset_token="test_token",
            frontend_url="https://custom-tunnel.trycloudflare.com/",
        )
        assert result is True
        mock_server.send_message.assert_called_once()
        call_args = mock_server.send_message.call_args[0][0]
        html_body = call_args.get_payload(0).get_payload(decode=True).decode("utf-8")
        assert (
            "https://custom-tunnel.trycloudflare.com/reset-password?token=test_token"
            in html_body
        )

    @patch("src.services.email_service.smtplib.SMTP")
    def test_send_account_deletion_email_custom_frontend_url(
        self, mock_smtp, email_service
    ):
        mock_server = mock_smtp.return_value.__enter__.return_value
        result = email_service.send_account_deletion_email(
            to_email="user@test.com",
            username="testuser",
            token="test_token",
            frontend_url="https://custom-tunnel.trycloudflare.com",
        )
        assert result is True
        mock_server.send_message.assert_called_once()
        call_args = mock_server.send_message.call_args[0][0]
        html_body = call_args.get_payload(0).get_payload(decode=True).decode("utf-8")
        assert (
            "https://custom-tunnel.trycloudflare.com/delete-account?token=test_token"
            in html_body
        )


def test_get_frontend_url():
    from unittest.mock import MagicMock

    from src.api.routes.auth import get_frontend_url

    # 1. None
    assert get_frontend_url(None) == "http://localhost:3000"

    # 2. Origin header
    req_origin = MagicMock()
    req_origin.headers.get.side_effect = lambda k, d=None: (
        "https://foo.trycloudflare.com" if k == "origin" else d
    )
    assert get_frontend_url(req_origin) == "https://foo.trycloudflare.com"

    # 3. Referer header
    def mock_referer(k, d=None):
        if k == "referer":
            return "https://bar.trycloudflare.com/auth/login?redirect=1"
        return d

    req_ref = MagicMock()
    req_ref.headers.get.side_effect = mock_referer
    assert get_frontend_url(req_ref) == "https://bar.trycloudflare.com"

    # 4. X-Forwarded-Host header
    def mock_forwarded(k, d=None):
        if k == "x-forwarded-host":
            return "my-app.com, proxy.internal"
        if k == "x-forwarded-proto":
            return "https, http"
        return d

    req_fwd = MagicMock()
    req_fwd.headers.get.side_effect = mock_forwarded
    assert get_frontend_url(req_fwd) == "https://my-app.com"
