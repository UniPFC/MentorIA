from sqlalchemy import Column, String, DateTime, Boolean, Uuid
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from shared.database.session import Base
from src.services.encryption import encrypt_sensitive_data, decrypt_sensitive_data, is_encrypted_data


class User(Base):
    __tablename__ = "users"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    _email = Column("email", String(500), unique=True, nullable=False, index=True)  # Aumentado para dados criptografados
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
    def email(self) -> str:
        """Retorna email decriptado"""
        if hasattr(self, '_email') and self._email:
            try:
                return decrypt_sensitive_data(self._email)
            except:
                # Se falhar na decriptação, assume que já está em plain text
                return self._email
        return self._email
    
    @email.setter
    def email(self, value: str):
        """Define email criptografado"""
        if value:
            if is_encrypted_data(value):
                self._email = value
            else:
                self._email = encrypt_sensitive_data(value)
        else:
            self._email = value
    
    @property
    def email_plain(self) -> str:
        """Retorna email decriptado (alias para compatibilidade)"""
        return self.email
    
    @email_plain.setter
    def email_plain(self, value: str):
        """Define email criptografado (alias para compatibilidade)"""
        self.email = value
    
    def __repr__(self):
        # Mostrar email real no repr para testes
        email_display = self.email if self.email else "None"
        return f"<User(id={self.id}, username='{self.username}', email='{email_display}', active={self.is_active})>"
