from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from shared.database.models.user import User
from shared.database.models.user_token import UserToken
from shared.database.models.password_reset_token import PasswordResetToken

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user: User) -> User:
        self.db.commit()
        self.db.refresh(user)
        return user

    def create_token(self, user_id: UUID, token: str, token_type: str, expires_at: datetime) -> UserToken:
        user_token = UserToken(
            user_id=user_id,
            token=token,
            token_type=token_type,
            expires_at=expires_at,
            is_active=True
        )
        self.db.add(user_token)
        self.db.commit()
        self.db.refresh(user_token)
        return user_token

    def get_token(self, token: str) -> Optional[UserToken]:
        return self.db.query(UserToken).filter(
            UserToken.token == token,
            UserToken.is_active == True
        ).first()

    def invalidate_token(self, token: str):
        self.db.query(UserToken).filter(UserToken.token == token).delete()
        self.db.commit()

    def invalidate_all_user_tokens(self, user_id: UUID):
        self.db.query(UserToken).filter(
            UserToken.user_id == user_id
        ).delete()
        self.db.commit()

    def invalidate_refresh_tokens(self, user_id: UUID):
        """Deleta todos os refresh tokens do usuário"""
        self.db.query(UserToken).filter(
            UserToken.user_id == user_id,
            UserToken.token_type == 'refresh'
        ).delete()
        self.db.commit()

    def create_password_reset_token(self, user_id: UUID, token: str, expires_at: datetime) -> PasswordResetToken:
        # Invalidar tokens anteriores
        self.db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.is_active == True
        ).update({"is_active": False})
        
        reset_token = PasswordResetToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
            is_active=True
        )
        self.db.add(reset_token)
        self.db.commit()
        self.db.refresh(reset_token)
        return reset_token

    def get_password_reset_token(self, token: str) -> Optional[PasswordResetToken]:
        return self.db.query(PasswordResetToken).filter(
            PasswordResetToken.token == token,
            PasswordResetToken.is_active == True,
            PasswordResetToken.expires_at > datetime.now(timezone.utc)
        ).first()

    def invalidate_password_reset_token(self, token: str):
        reset_token = self.db.query(PasswordResetToken).filter(PasswordResetToken.token == token).first()
        if reset_token:
            reset_token.is_active = False
            reset_token.used_at = datetime.now(timezone.utc)
            self.db.commit()

    def cleanup_expired_tokens(self):
        """Delete expired or inactive user tokens to prevent database bloat"""
        now = datetime.now(timezone.utc)
        self.db.query(UserToken).filter(
            (UserToken.expires_at <= now) | (UserToken.is_active == False)
        ).delete()
        self.db.commit()

    def cleanup_expired_password_reset_tokens(self):
        """Delete expired or inactive password reset tokens to prevent database bloat"""
        now = datetime.now(timezone.utc)
        self.db.query(PasswordResetToken).filter(
            (PasswordResetToken.expires_at <= now) | (PasswordResetToken.is_active == False)
        ).delete()
        self.db.commit()
