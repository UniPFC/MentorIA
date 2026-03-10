from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from shared.database.models.user import User
from shared.database.models.user_token import UserToken

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
        user_token = self.db.query(UserToken).filter(UserToken.token == token).first()
        if user_token:
            user_token.is_active = False
            self.db.commit()

    def invalidate_all_user_tokens(self, user_id: UUID):
        self.db.query(UserToken).filter(
            UserToken.user_id == user_id
        ).update({"is_active": False})
        self.db.commit()
