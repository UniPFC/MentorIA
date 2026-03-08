from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Nome de usuário")
    email: EmailStr = Field(..., description="Email válido")
    password: str = Field(..., min_length=6, max_length=100, description="Senha (mínimo 6 caracteres)")
    
    @validator('password')
    def validate_password_length(cls, v):
        """Valida se a senha não excede limites seguros para processamento"""
        if len(v.encode('utf-8')) > 1000:  # Limite seguro para processamento
            raise ValueError('Senha muito longa. Máximo 1000 bytes.')
        return v


class UserLogin(BaseModel):
    username: str = Field(..., description="Nome de usuário ou email")
    password: str = Field(..., description="Senha")
    
    @validator('password')
    def validate_password_length(cls, v):
        """Valida se a senha não excede limites seguros para processamento"""
        if len(v.encode('utf-8')) > 1000:  # Limite seguro para processamento
            raise ValueError('Senha muito longa. Máximo 1000 bytes.')
        return v


class Token(BaseModel):
    access_token: str = Field(..., description="Token JWT de acesso")
    refresh_token: str = Field(..., description="Token JWT de atualização")
    token_type: str = Field(default="bearer", description="Tipo do token")
    expires_in: int = Field(..., description="Tempo de expiração em segundos")


class TokenRefresh(BaseModel):
    refresh_token: str = Field(..., description="Token de atualização")


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class LogoutResponse(BaseModel):
    message: str = Field(default="Logout realizado com sucesso")
    success: bool = Field(default=True)


class PasswordReset(BaseModel):
    current_password: str = Field(..., description="Senha atual")
    new_password: str = Field(..., min_length=6, max_length=100, description="Nova senha (mínimo 6 caracteres)")
    
    @validator('current_password', 'new_password')
    def validate_password_length(cls, v):
        """Valida se a senha não excede limites seguros para processamento"""
        if len(v.encode('utf-8')) > 1000:  # Limite seguro para processamento
            raise ValueError('Senha muito longa. Máximo 1000 bytes.')
        return v


class AdminPasswordReset(BaseModel):
    user_id: int = Field(..., description="ID do usuário")
    new_password: str = Field(..., min_length=6, max_length=100, description="Nova senha temporária")
    
    @validator('new_password')
    def validate_password_length(cls, v):
        """Valida se a senha não excede limites seguros para processamento"""
        if len(v.encode('utf-8')) > 1000:  # Limite seguro para processamento
            raise ValueError('Senha muito longa. Máximo 1000 bytes.')
        return v
