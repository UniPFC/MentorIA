import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Uuid
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from config.settings import settings
from shared.database.session import Base


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
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    level = Column(SQLEnum(UserLevel), nullable=False, default=UserLevel.LEVEL_01)
    token_budget = Column(Integer, nullable=True)

    # 2FA
    two_factor_secret = Column(String(32), nullable=True)
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    last_2fa_reminder_at = Column(DateTime(timezone=True), nullable=True)

    # Subscription fields (Pagar.me integration)
    pagarme_customer_id = Column(String(255), nullable=True, index=True)
    subscription_id = Column(String(255), nullable=True, index=True)
    subscription_status = Column(
        String(50), nullable=True
    )  # active, canceled, past_due, unpaid, ended
    subscription_period_start = Column(DateTime(timezone=True), nullable=True)
    subscription_period_end = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    chat_types = relationship(
        "ChatType", back_populates="owner", cascade="all, delete-orphan"
    )
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    tokens = relationship(
        "UserToken", back_populates="user", cascade="all, delete-orphan"
    )
    password_reset_tokens = relationship(
        "PasswordResetToken", back_populates="user", cascade="all, delete-orphan"
    )
    email_verification_tokens = relationship(
        "EmailVerificationToken", back_populates="user", cascade="all, delete-orphan"
    )
    favorite_chat_types = relationship(
        "ChatTypeFavorite", back_populates="user", cascade="all, delete-orphan"
    )

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
    def max_token_budget(self) -> int | None:
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
    def remaining_tokens(self) -> int | None:
        """Get the remaining tokens (same as token_budget for non-unlimited users)."""
        if self.has_unlimited_budget:
            return None
        return self.token_budget
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}', active={self.is_active})>"
