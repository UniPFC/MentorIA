from sqlalchemy import Column, String, DateTime, Boolean, Uuid, Integer, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
import enum
from shared.database.session import Base
from config.settings import settings
from src.services.encryption import encrypt_sensitive_data, decrypt_sensitive_data, is_encrypted_data

class UserLevel(str, enum.Enum):
    """User subscription levels with token budgets."""
    LEVEL_01 = "LEVEL_01"
    LEVEL_02 = "LEVEL_02"
    LEVEL_03 = "LEVEL_03"
    LEVEL_04 = "LEVEL_04"
    LEVEL_05 = "LEVEL_05"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    _email = Column("email", String(500), unique=True, nullable=False, index=True)  # Aumentado para dados criptografados
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    level = Column(SQLEnum(UserLevel), nullable=False, default=UserLevel.LEVEL_01)
    token_budget = Column(Integer, nullable=True)
    
    # Subscription fields (Pagar.me integration)
    pagarme_customer_id = Column(String(255), nullable=True, index=True)
    subscription_id = Column(String(255), nullable=True, index=True)
    subscription_status = Column(String(50), nullable=True)  # active, canceled, past_due, unpaid, ended
    subscription_period_start = Column(DateTime(timezone=True), nullable=True)
    subscription_period_end = Column(DateTime(timezone=True), nullable=True)
    
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
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}', active={self.is_active}, level={self.level})>"
    
    @property
    def has_unlimited_budget(self) -> bool:
        """Check if user has unlimited token budget (LEVEL_05)."""
        return self.level == UserLevel.LEVEL_05
    
    def can_afford_tokens(self, tokens_needed: int) -> bool:
        """Check if user has enough budget for the required tokens."""
        if self.has_unlimited_budget:
            return True
        if self.token_budget is None:
            return False
        return self.token_budget >= tokens_needed
    
    @property
    def max_token_budget(self) -> int:
        """Get the maximum token budget for the user's level."""
        if self.has_unlimited_budget:
            return None
        budget_map = {
            UserLevel.LEVEL_01: settings.TOKEN_BUDGET_LEVEL_01,
            UserLevel.LEVEL_02: settings.TOKEN_BUDGET_LEVEL_02,
            UserLevel.LEVEL_03: settings.TOKEN_BUDGET_LEVEL_03,
            UserLevel.LEVEL_04: settings.TOKEN_BUDGET_LEVEL_04,
            UserLevel.LEVEL_05: None,
        }
        return budget_map.get(self.level, 0)
    
    @property
    def remaining_tokens(self) -> int:
        """Get the remaining tokens (same as token_budget for non-unlimited users)."""
        if self.has_unlimited_budget:
            return None
        return self.token_budget
        # Mostrar email real no repr para testes
        email_display = self.email if self.email else "None"
        return f"<User(id={self.id}, username='{self.username}', email='{email_display}', active={self.is_active})>"
