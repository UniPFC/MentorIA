from sqlalchemy import Column, String, DateTime, Boolean, Uuid
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from shared.database.session import Base
from src.services.encryption import encrypt_sensitive_data, decrypt_sensitive_data


class User(Base):
    __tablename__ = "users"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(500), unique=True, nullable=False, index=True)  # Aumentado para dados criptografados
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    chat_types = relationship("ChatType", back_populates="owner", cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    tokens = relationship("UserToken", back_populates="user", cascade="all, delete-orphan")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    favorite_chat_types = relationship("ChatTypeFavorite", back_populates="user", cascade="all, delete-orphan")
    
    # Property para email criptografado
    @property
    def email_plain(self) -> str:
        """Retorna email decriptado"""
        if self.email:
            return decrypt_sensitive_data(self.email)
        return self.email
    
    @email_plain.setter
    def email_plain(self, value: str):
        """Define email criptografado"""
        if value:
            self.email = encrypt_sensitive_data(value)
        else:
            self.email = value
    
    def __repr__(self):
        # Mostrar email mascarado no repr
        email_masked = "***@***.com" if self.email else "None"
        return f"<User(id={self.id}, username='{self.username}', email='{email_masked}', active={self.is_active})>"
