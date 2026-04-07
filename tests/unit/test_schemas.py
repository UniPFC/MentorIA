import pytest
from pydantic import ValidationError
from src.api.schemas.auth import (
    UserRegister, UserLogin, PasswordResetRequest, PasswordResetConfirm,
    Token, UserResponse, LogoutResponse, TokenVerifyResponse
)
from src.api.schemas.chat import ChatCreate, ChatResponse, SendMessageRequest
from src.api.schemas.chat_type import ChatTypeCreate, ChatTypeResponse
from uuid import uuid4
from datetime import datetime, timezone


@pytest.mark.unit
class TestAuthSchemas:
    def test_user_register_valid(self):
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "SecurePassword123!"
        }
        user = UserRegister(**data)
        
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.password == "SecurePassword123!"
        
    def test_user_register_weak_password(self):
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "123"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(**data)
        
        errors = exc_info.value.errors()
        assert any("password" in str(error) for error in errors)
        
    def test_user_register_reserved_username(self):
        data = {
            "username": "mentoria",
            "email": "test@example.com",
            "password": "SecurePassword123!"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(**data)
        
        errors = exc_info.value.errors()
    
    def test_user_register_password_too_long(self):
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "a" * 1001
        }
        
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(**data)
        
        errors = exc_info.value.errors()
        error_msg = str(errors)
        assert "Senha muito longa" in error_msg or "String should have at most" in error_msg
    
    def test_user_register_weak_password_with_warning(self):
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "password"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(**data)
        
        errors = exc_info.value.errors()
        error_msg = str(errors)
        assert "Senha fraca" in error_msg
    
    def test_user_register_weak_password_no_suggestions(self):
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "12345678"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(**data)
        
        errors = exc_info.value.errors()
        error_msg = str(errors)
        assert "Senha fraca" in error_msg
    
    def test_translate_zxcvbn_suggestion(self):
        from src.api.schemas.auth import translate_zxcvbn_suggestion
        
        result = translate_zxcvbn_suggestion("Add another word or two")
        assert isinstance(result, str)
        
        result_unknown = translate_zxcvbn_suggestion("Unknown suggestion")
        assert result_unknown == "Unknown suggestion"
        
    def test_user_register_short_username(self):
        data = {
            "username": "ab",
            "email": "test@example.com",
            "password": "SecurePassword123!"
        }
        
        with pytest.raises(ValidationError):
            UserRegister(**data)
            
    def test_user_register_invalid_email(self):
        data = {
            "username": "testuser",
            "email": "invalid-email",
            "password": "SecurePassword123!"
        }
        
        with pytest.raises(ValidationError):
            UserRegister(**data)
            
    def test_user_login_valid(self):
        data = {
            "email": "test@example.com",
            "password": "password123"
        }
        login = UserLogin(**data)
        
        assert login.email == "test@example.com"
        assert login.password == "password123"
        
    def test_user_login_invalid_email(self):
        data = {
            "email": "not-an-email",
            "password": "password123"
        }
        
        with pytest.raises(ValidationError):
            UserLogin(**data)
            
    def test_password_reset_request_valid(self):
        data = {"email": "test@example.com"}
        request = PasswordResetRequest(**data)
        
        assert request.email == "test@example.com"
        
    def test_password_reset_confirm_valid(self):
        data = {
            "token": "reset_token_123",
            "new_password": "NewSecurePassword123!"
        }
        confirm = PasswordResetConfirm(**data)
        
        assert confirm.token == "reset_token_123"
        assert confirm.new_password == "NewSecurePassword123!"
        
    def test_password_reset_confirm_password_too_long(self):
        data = {
            "token": "reset_token_123",
            "new_password": "a" * 1001
        }
        
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetConfirm(**data)
        
        errors = exc_info.value.errors()
        error_msg = str(errors)
        assert "Senha muito longa" in error_msg or "String should have at most" in error_msg
    
    def test_password_reset_confirm_weak_password_with_warning(self):
        data = {
            "token": "reset_token_123",
            "new_password": "password"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetConfirm(**data)
        
        errors = exc_info.value.errors()
        error_msg = str(errors)
        assert "Senha fraca" in error_msg
    
    def test_password_reset_confirm_weak_password_no_suggestions(self):
        data = {
            "token": "reset_token_123",
            "new_password": "12345678"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetConfirm(**data)
        
        errors = exc_info.value.errors()
        error_msg = str(errors)
        assert "Senha fraca" in error_msg
    
    def test_password_reset_confirm_weak_password(self):
        data = {
            "token": "reset_token_123",
            "new_password": "weak"
        }
        
        with pytest.raises(ValidationError):
            PasswordResetConfirm(**data)
            
    def test_token_schema(self):
        data = {
            "access_token": "access_token_123",
            "refresh_token": "refresh_token_123",
            "token_type": "bearer",
            "expires_in": 1800
        }
        token = Token(**data)
        
        assert token.access_token == "access_token_123"
        assert token.refresh_token == "refresh_token_123"
        assert token.token_type == "bearer"
        assert token.expires_in == 1800


@pytest.mark.unit
class TestChatSchemas:
    def test_chat_create_valid(self):
        chat_type_id = uuid4()
        data = {
            "title": "Test Chat",
            "chat_type_id": str(chat_type_id)
        }
        chat = ChatCreate(**data)
        
        assert chat.title == "Test Chat"
        assert chat.chat_type_id == chat_type_id
        
    def test_send_message_request_valid(self):
        data = {
            "content": "Hello, world!"
        }
        message = SendMessageRequest(**data)
        
        assert message.content == "Hello, world!"
        
    def test_send_message_request_empty(self):
        data = {
            "content": ""
        }
        
        with pytest.raises(ValidationError):
            SendMessageRequest(**data)


@pytest.mark.unit
class TestChatTypeSchemas:
    def test_chat_type_create_valid(self):
        data = {
            "name": "Test Chat Type",
            "description": "A test chat type"
        }
        chat_type = ChatTypeCreate(**data)
        
        assert chat_type.name == "Test Chat Type"
        assert chat_type.description == "A test chat type"
        
    def test_chat_type_create_no_description(self):
        data = {
            "name": "Test Chat Type"
        }
        chat_type = ChatTypeCreate(**data)
        
        assert chat_type.name == "Test Chat Type"
        assert chat_type.description is None
