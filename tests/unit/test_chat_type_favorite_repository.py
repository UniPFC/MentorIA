import pytest
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from src.repositories.chat_type_favorite import ChatTypeFavoriteRepository
from shared.database.models.chat_type_favorite import ChatTypeFavorite
from shared.database.models.chat_type import ChatType
from shared.database.models.user import User


class TestChatTypeFavoriteRepository:
    """Test suite for ChatTypeFavoriteRepository"""

    @pytest.fixture
    def favorite_repo(self, db_session: Session):
        return ChatTypeFavoriteRepository(db_session)

    def test_get_by_user_and_chat_type_found(self, favorite_repo: ChatTypeFavoriteRepository, db_session: Session, sample_user: User, sample_chat_type: ChatType):
        favorite = ChatTypeFavorite(
            user_id=sample_user.id,
            chat_type_id=sample_chat_type.id
        )
        db_session.add(favorite)
        db_session.commit()
        
        result = favorite_repo.get_by_user_and_chat_type(sample_user.id, sample_chat_type.id)
        
        assert result is not None
        assert result.user_id == sample_user.id
        assert result.chat_type_id == sample_chat_type.id

    def test_get_by_user_and_chat_type_not_found(self, favorite_repo: ChatTypeFavoriteRepository, sample_user: User):
        non_existent_chat_type_id = uuid4()
        result = favorite_repo.get_by_user_and_chat_type(sample_user.id, non_existent_chat_type_id)
        
        assert result is None

    def test_get_user_favorites(self, favorite_repo: ChatTypeFavoriteRepository, db_session: Session, sample_user: User):
        ct1 = ChatType(
            id=uuid4(),
            name="Type 1",
            description="Description 1",
            owner_id=sample_user.id,
            collection_name="type_1",
            created_at=datetime.now(timezone.utc)
        )
        ct2 = ChatType(
            id=uuid4(),
            name="Type 2",
            description="Description 2",
            owner_id=sample_user.id,
            collection_name="type_2",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add_all([ct1, ct2])
        db_session.commit()
        
        fav1 = ChatTypeFavorite(user_id=sample_user.id, chat_type_id=ct1.id)
        fav2 = ChatTypeFavorite(user_id=sample_user.id, chat_type_id=ct2.id)
        db_session.add_all([fav1, fav2])
        db_session.commit()
        
        result = favorite_repo.get_user_favorites(sample_user.id)
        
        assert len(result) == 2
        assert all(f.user_id == sample_user.id for f in result)

    def test_get_user_favorites_empty(self, favorite_repo: ChatTypeFavoriteRepository):
        non_existent_user_id = uuid4()
        result = favorite_repo.get_user_favorites(non_existent_user_id)
        
        assert len(result) == 0

    def test_get_user_favorite_ids(self, favorite_repo: ChatTypeFavoriteRepository, db_session: Session, sample_user: User):
        ct1 = ChatType(
            id=uuid4(),
            name="Type 1",
            description="Description 1",
            owner_id=sample_user.id,
            collection_name="type_1",
            created_at=datetime.now(timezone.utc)
        )
        ct2 = ChatType(
            id=uuid4(),
            name="Type 2",
            description="Description 2",
            owner_id=sample_user.id,
            collection_name="type_2",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add_all([ct1, ct2])
        db_session.commit()
        
        fav1 = ChatTypeFavorite(user_id=sample_user.id, chat_type_id=ct1.id)
        fav2 = ChatTypeFavorite(user_id=sample_user.id, chat_type_id=ct2.id)
        db_session.add_all([fav1, fav2])
        db_session.commit()
        
        result = favorite_repo.get_user_favorite_ids(sample_user.id)
        
        assert len(result) == 2
        assert ct1.id in result
        assert ct2.id in result

    def test_get_user_favorite_ids_empty(self, favorite_repo: ChatTypeFavoriteRepository):
        non_existent_user_id = uuid4()
        result = favorite_repo.get_user_favorite_ids(non_existent_user_id)
        
        assert len(result) == 0

    def test_create(self, favorite_repo: ChatTypeFavoriteRepository, sample_user: User, sample_chat_type: ChatType):
        result = favorite_repo.create(sample_user.id, sample_chat_type.id)
        
        assert result.user_id == sample_user.id
        assert result.chat_type_id == sample_chat_type.id
        assert result.id is not None

    def test_delete(self, favorite_repo: ChatTypeFavoriteRepository, db_session: Session, sample_user: User, sample_chat_type: ChatType):
        favorite = ChatTypeFavorite(
            user_id=sample_user.id,
            chat_type_id=sample_chat_type.id
        )
        db_session.add(favorite)
        db_session.commit()
        favorite_id = favorite.id
        
        favorite_repo.delete(favorite)
        
        deleted = db_session.query(ChatTypeFavorite).filter(ChatTypeFavorite.id == favorite_id).first()
        assert deleted is None

    def test_delete_by_user_and_chat_type_success(self, favorite_repo: ChatTypeFavoriteRepository, db_session: Session, sample_user: User, sample_chat_type: ChatType):
        favorite = ChatTypeFavorite(
            user_id=sample_user.id,
            chat_type_id=sample_chat_type.id
        )
        db_session.add(favorite)
        db_session.commit()
        
        result = favorite_repo.delete_by_user_and_chat_type(sample_user.id, sample_chat_type.id)
        
        assert result is True
        deleted = db_session.query(ChatTypeFavorite).filter(
            ChatTypeFavorite.user_id == sample_user.id,
            ChatTypeFavorite.chat_type_id == sample_chat_type.id
        ).first()
        assert deleted is None

    def test_delete_by_user_and_chat_type_not_found(self, favorite_repo: ChatTypeFavoriteRepository, sample_user: User):
        non_existent_chat_type_id = uuid4()
        result = favorite_repo.delete_by_user_and_chat_type(sample_user.id, non_existent_chat_type_id)
        
        assert result is False

    def test_is_favorited_true(self, favorite_repo: ChatTypeFavoriteRepository, db_session: Session, sample_user: User, sample_chat_type: ChatType):
        favorite = ChatTypeFavorite(
            user_id=sample_user.id,
            chat_type_id=sample_chat_type.id
        )
        db_session.add(favorite)
        db_session.commit()
        
        result = favorite_repo.is_favorited(sample_user.id, sample_chat_type.id)
        
        assert result is True

    def test_is_favorited_false(self, favorite_repo: ChatTypeFavoriteRepository, sample_user: User):
        non_existent_chat_type_id = uuid4()
        result = favorite_repo.is_favorited(sample_user.id, non_existent_chat_type_id)
        
        assert result is False
