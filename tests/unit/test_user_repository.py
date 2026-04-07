import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlalchemy.orm import Session
from src.repositories.user import UserRepository
from shared.database.models.user import User
from shared.database.models.user_token import UserToken
from shared.database.models.password_reset_token import PasswordResetToken


@pytest.mark.unit
class TestUserRepository:
    def test_get_by_id(self, db_session: Session, sample_user: User):
        repo = UserRepository(db_session)
        
        user = repo.get_by_id(sample_user.id)
        
        assert user is not None
        assert user.id == sample_user.id
        assert user.email == sample_user.email
        
    def test_get_by_id_not_found(self, db_session: Session):
        repo = UserRepository(db_session)
        
        user = repo.get_by_id(uuid4())
        
        assert user is None
        
    def test_get_by_email(self, db_session: Session, sample_user: User):
        repo = UserRepository(db_session)
        
        user = repo.get_by_email(sample_user.email)
        
        assert user is not None
        assert user.email == sample_user.email
        
    def test_get_by_email_not_found(self, db_session: Session):
        repo = UserRepository(db_session)
        
        user = repo.get_by_email("nonexistent@example.com")
        
        assert user is None
        
    def test_get_by_username(self, db_session: Session, sample_user: User):
        repo = UserRepository(db_session)
        
        user = repo.get_by_username(sample_user.username)
        
        assert user is not None
        assert user.username == sample_user.username
        
    def test_get_by_username_not_found(self, db_session: Session):
        repo = UserRepository(db_session)
        
        user = repo.get_by_username("nonexistent")
        
        assert user is None
        
    def test_create_user(self, db_session: Session):
        repo = UserRepository(db_session)
        
        new_user = User(
            id=uuid4(),
            username="newuser",
            email="newuser@example.com",
            password_hash="hashed_password",
            is_active=True
        )
        
        created_user = repo.create(new_user)
        
        assert created_user.id is not None
        assert created_user.username == "newuser"
        assert created_user.email == "newuser@example.com"
        
    def test_update_user(self, db_session: Session, sample_user: User):
        repo = UserRepository(db_session)
        
        sample_user.username = "updated_username"
        updated_user = repo.update(sample_user)
        
        assert updated_user.username == "updated_username"
        
    def test_create_token(self, db_session: Session, sample_user: User):
        repo = UserRepository(db_session)
        
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        token = repo.create_token(
            user_id=sample_user.id,
            token="test_token_123",
            token_type="access",
            expires_at=expires_at
        )
        
        assert token.id is not None
        assert token.user_id == sample_user.id
        assert token.token == "test_token_123"
        assert token.token_type == "access"
        assert token.is_active is True
        
    def test_get_token(self, db_session: Session, sample_user_token: UserToken):
        repo = UserRepository(db_session)
        
        token = repo.get_token(sample_user_token.token)
        
        assert token is not None
        assert token.id == sample_user_token.id
        assert token.is_active is True
        
    def test_get_token_not_found(self, db_session: Session):
        repo = UserRepository(db_session)
        
        token = repo.get_token("nonexistent_token")
        
        assert token is None
        
    def test_get_token_inactive(self, db_session: Session, sample_user_token: UserToken):
        repo = UserRepository(db_session)
        
        sample_user_token.is_active = False
        db_session.commit()
        
        token = repo.get_token(sample_user_token.token)
        
        assert token is None
        
    def test_invalidate_token(self, db_session: Session, sample_user_token: UserToken):
        repo = UserRepository(db_session)
        
        repo.invalidate_token(sample_user_token.token)
        
        db_session.refresh(sample_user_token)
        assert sample_user_token.is_active is False
        
    def test_invalidate_all_user_tokens(self, db_session: Session, sample_user: User):
        repo = UserRepository(db_session)
        
        token1 = repo.create_token(
            user_id=sample_user.id,
            token="token1",
            token_type="access",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        token2 = repo.create_token(
            user_id=sample_user.id,
            token="token2",
            token_type="refresh",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        repo.invalidate_all_user_tokens(sample_user.id)
        
        db_session.refresh(token1)
        db_session.refresh(token2)
        assert token1.is_active is False
        assert token2.is_active is False
        
    def test_create_password_reset_token(self, db_session: Session, sample_user: User):
        repo = UserRepository(db_session)
        
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        reset_token = repo.create_password_reset_token(
            user_id=sample_user.id,
            token="reset_token_123",
            expires_at=expires_at
        )
        
        assert reset_token.id is not None
        assert reset_token.user_id == sample_user.id
        assert reset_token.token == "reset_token_123"
        assert reset_token.is_active is True
        
    def test_create_password_reset_token_invalidates_old(self, db_session: Session, sample_user: User):
        repo = UserRepository(db_session)
        
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        old_token = repo.create_password_reset_token(
            user_id=sample_user.id,
            token="old_token",
            expires_at=expires_at
        )
        
        new_token = repo.create_password_reset_token(
            user_id=sample_user.id,
            token="new_token",
            expires_at=expires_at
        )
        
        db_session.refresh(old_token)
        assert old_token.is_active is False
        assert new_token.is_active is True
        
    def test_get_password_reset_token(self, db_session: Session, sample_password_reset_token: PasswordResetToken):
        repo = UserRepository(db_session)
        
        token = repo.get_password_reset_token(sample_password_reset_token.token)
        
        assert token is not None
        assert token.id == sample_password_reset_token.id
        
    def test_get_password_reset_token_expired(self, db_session: Session, sample_user: User):
        repo = UserRepository(db_session)
        
        expired_token = PasswordResetToken(
            id=uuid4(),
            user_id=sample_user.id,
            token="expired_token",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            is_active=True
        )
        db_session.add(expired_token)
        db_session.commit()
        
        token = repo.get_password_reset_token("expired_token")
        
        assert token is None
        
    def test_invalidate_password_reset_token(self, db_session: Session, sample_password_reset_token: PasswordResetToken):
        repo = UserRepository(db_session)
        
        repo.invalidate_password_reset_token(sample_password_reset_token.token)
        
        db_session.refresh(sample_password_reset_token)
        assert sample_password_reset_token.is_active is False
        assert sample_password_reset_token.used_at is not None
