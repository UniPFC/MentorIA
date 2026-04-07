import pytest
from unittest.mock import patch, MagicMock
from src.services.email import EmailService


@pytest.mark.unit
class TestEmailService:
    @pytest.fixture
    def email_service(self):
        with patch('src.services.email.settings') as mock_settings:
            mock_settings.SMTP_SERVER = 'smtp.test.com'
            mock_settings.SMTP_PORT = 587
            mock_settings.SMTP_USERNAME = 'test@test.com'
            mock_settings.SMTP_PASSWORD = 'password'
            mock_settings.FROM_EMAIL = 'noreply@test.com'
            mock_settings.FRONTEND_URL = 'http://localhost:3000'
            return EmailService()
    
    def test_init(self, email_service):
        assert email_service.smtp_server == 'smtp.test.com'
        assert email_service.smtp_port == 587
        assert email_service.smtp_username == 'test@test.com'
        assert email_service.smtp_password == 'password'
        assert email_service.from_email == 'noreply@test.com'
        assert email_service.frontend_url == 'http://localhost:3000'
    
    def test_init_with_defaults(self):
        with patch('src.services.email.settings') as mock_settings:
            del mock_settings.SMTP_SERVER
            del mock_settings.SMTP_PORT
            del mock_settings.SMTP_USERNAME
            del mock_settings.SMTP_PASSWORD
            del mock_settings.FROM_EMAIL
            del mock_settings.FRONTEND_URL
            
            service = EmailService()
            
            assert service.smtp_server == 'smtp.gmail.com'
            assert service.smtp_port == 587
    
    def test_generate_reset_token(self, email_service):
        token = email_service.generate_reset_token()
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    @patch('src.services.email.smtplib.SMTP')
    def test_send_email_success(self, mock_smtp, email_service):
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        result = email_service._send_email(
            to_email='user@test.com',
            subject='Test Subject',
            html_body='<p>Test Body</p>'
        )
        
        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with('test@test.com', 'password')
        mock_server.send_message.assert_called_once()
    
    @patch('src.services.email.smtplib.SMTP')
    def test_send_email_failure(self, mock_smtp, email_service):
        mock_smtp.side_effect = Exception("SMTP error")
        
        result = email_service._send_email(
            to_email='user@test.com',
            subject='Test Subject',
            html_body='<p>Test Body</p>'
        )
        
        assert result is False
    
    @patch('src.services.email.smtplib.SMTP')
    def test_send_password_reset_email_success(self, mock_smtp, email_service):
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        result = email_service.send_password_reset_email(
            to_email='user@test.com',
            username='testuser',
            reset_token='test_token_123'
        )
        
        assert result is True
        mock_server.send_message.assert_called_once()
        
        call_args = mock_server.send_message.call_args[0][0]
        email_string = call_args.as_string()
        assert 'Reset de Senha' in call_args['Subject']
        assert 'user@test.com' in call_args['To']
    
    @patch('src.services.email.smtplib.SMTP')
    def test_send_password_reset_email_failure(self, mock_smtp, email_service):
        mock_smtp.side_effect = Exception("SMTP error")
        
        result = email_service.send_password_reset_email(
            to_email='user@test.com',
            username='testuser',
            reset_token='test_token_123'
        )
        
        assert result is False
    
    @patch('src.services.email.smtplib.SMTP')
    def test_send_password_changed_email_success(self, mock_smtp, email_service):
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        result = email_service.send_password_changed_email(
            to_email='user@test.com',
            username='testuser'
        )
        
        assert result is True
        mock_server.send_message.assert_called_once()
        
        call_args = mock_server.send_message.call_args[0][0]
        assert 'Senha Alterada' in call_args['Subject']
        assert 'user@test.com' in call_args['To']
    
    @patch('src.services.email.smtplib.SMTP')
    def test_send_password_changed_email_failure(self, mock_smtp, email_service):
        mock_smtp.side_effect = Exception("SMTP error")
        
        result = email_service.send_password_changed_email(
            to_email='user@test.com',
            username='testuser'
        )
        
        assert result is False
