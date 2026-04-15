import pytest
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from src.repositories.chat_type import ChatTypeRepository
from shared.database.models.chat_type import ChatType
from shared.database.models.user import User


class TestChatTypeRepository:
    """Test suite for ChatTypeRepository"""

    @pytest.fixture
    def chat_type_repo(self, db_session: Session):
        return ChatTypeRepository(db_session)

    def test_get_by_id_found(self, chat_type_repo: ChatTypeRepository, sample_chat_type: ChatType):
        result = chat_type_repo.get_by_id(sample_chat_type.id)
        
        assert result is not None
        assert result.id == sample_chat_type.id
        assert result.name == sample_chat_type.name

    def test_get_by_id_with_owner(self, chat_type_repo: ChatTypeRepository, sample_chat_type: ChatType):
        result = chat_type_repo.get_by_id(sample_chat_type.id, load_owner=True)
        
        assert result is not None
        assert result.owner is not None
        assert result.owner.id == sample_chat_type.owner_id

    def test_get_by_id_not_found(self, chat_type_repo: ChatTypeRepository):
        non_existent_id = uuid4()
        result = chat_type_repo.get_by_id(non_existent_id)
        
        assert result is None

    def test_get_by_name_found(self, chat_type_repo: ChatTypeRepository, sample_chat_type: ChatType):
        result = chat_type_repo.get_by_name(sample_chat_type.name)
        
        assert result is not None
        assert result.name == sample_chat_type.name

    def test_get_by_name_not_found(self, chat_type_repo: ChatTypeRepository):
        result = chat_type_repo.get_by_name("NonExistentName")
        
        assert result is None

    def test_create(self, chat_type_repo: ChatTypeRepository, sample_user: User):
        chat_type = ChatType(
            id=uuid4(),
            name="New Chat Type",
            description="New Description",
            owner_id=sample_user.id,
            collection_name="new_chat_type",
            created_at=datetime.now(timezone.utc)
        )
        
        result = chat_type_repo.create(chat_type)
        
        assert result.id == chat_type.id
        assert result.name == "New Chat Type"

    def test_delete(self, chat_type_repo: ChatTypeRepository, db_session: Session, sample_chat_type: ChatType):
        chat_type_id = sample_chat_type.id
        
        chat_type_repo.delete(sample_chat_type)
        
        deleted = db_session.query(ChatType).filter(ChatType.id == chat_type_id).first()
        assert deleted is None

    def test_search_without_filters(self, chat_type_repo: ChatTypeRepository, db_session: Session, sample_user: User):
        ct1 = ChatType(
            id=uuid4(),
            name="Public Type 1",
            description="Public description",
            is_public=True,
            owner_id=sample_user.id,
            collection_name="public_1",
            created_at=datetime.now(timezone.utc)
        )
        ct2 = ChatType(
            id=uuid4(),
            name="Private Type 1",
            description="Private description",
            is_public=False,
            owner_id=sample_user.id,
            collection_name="private_1",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add_all([ct1, ct2])
        db_session.commit()
        
        chat_types, total = chat_type_repo.search(user_id=sample_user.id)
        
        assert total == 2
        assert len(chat_types) == 2

    def test_search_with_query(self, chat_type_repo: ChatTypeRepository, db_session: Session, sample_user: User):
        ct1 = ChatType(
            id=uuid4(),
            name="Math Helper",
            description="Helps with math",
            is_public=True,
            owner_id=sample_user.id,
            collection_name="math_helper",
            created_at=datetime.now(timezone.utc)
        )
        ct2 = ChatType(
            id=uuid4(),
            name="Science Helper",
            description="Helps with science",
            is_public=True,
            owner_id=sample_user.id,
            collection_name="science_helper",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add_all([ct1, ct2])
        db_session.commit()
        
        chat_types, total = chat_type_repo.search(query="Math", user_id=sample_user.id)
        
        assert total == 1
        assert chat_types[0].name == "Math Helper"

    def test_search_with_is_public_filter(self, chat_type_repo: ChatTypeRepository, db_session: Session, sample_user: User):
        ct1 = ChatType(
            id=uuid4(),
            name="Public Type",
            description="Public",
            is_public=True,
            owner_id=sample_user.id,
            collection_name="public",
            created_at=datetime.now(timezone.utc)
        )
        ct2 = ChatType(
            id=uuid4(),
            name="Private Type",
            description="Private",
            is_public=False,
            owner_id=sample_user.id,
            collection_name="private",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add_all([ct1, ct2])
        db_session.commit()
        
        chat_types, total = chat_type_repo.search(is_public=True, user_id=sample_user.id)
        
        assert total == 1
        assert chat_types[0].is_public is True

    def test_search_with_owner_filter(self, chat_type_repo: ChatTypeRepository, db_session: Session, sample_user: User):
        other_user = User(
            id=uuid4(),
            username="otheruser",
            email="other@example.com",
            password_hash="hash",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(other_user)
        db_session.commit()
        
        ct1 = ChatType(
            id=uuid4(),
            name="User Type",
            description="Owned by user",
            is_public=True,
            owner_id=sample_user.id,
            collection_name="user_type",
            created_at=datetime.now(timezone.utc)
        )
        ct2 = ChatType(
            id=uuid4(),
            name="Other Type",
            description="Owned by other",
            is_public=True,
            owner_id=other_user.id,
            collection_name="other_type",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add_all([ct1, ct2])
        db_session.commit()
        
        chat_types, total = chat_type_repo.search(owner_id=sample_user.id, user_id=sample_user.id)
        
        assert total == 1
        assert chat_types[0].owner_id == sample_user.id

    def test_search_with_pagination(self, chat_type_repo: ChatTypeRepository, db_session: Session, sample_user: User):
        for i in range(5):
            ct = ChatType(
                id=uuid4(),
                name=f"Type {i}",
                description=f"Description {i}",
                is_public=True,
                owner_id=sample_user.id,
                collection_name=f"type_{i}",
                created_at=datetime.now(timezone.utc)
            )
            db_session.add(ct)
        db_session.commit()
        
        chat_types, total = chat_type_repo.search(user_id=sample_user.id, skip=2, limit=2)
        
        assert total == 5
        assert len(chat_types) == 2

    def test_search_security_filter(self, chat_type_repo: ChatTypeRepository, db_session: Session, sample_user: User):
        other_user = User(
            id=uuid4(),
            username="otheruser",
            email="other@example.com",
            password_hash="hash",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(other_user)
        db_session.commit()
        
        ct1 = ChatType(
            id=uuid4(),
            name="My Private",
            description="My private type",
            is_public=False,
            owner_id=sample_user.id,
            collection_name="my_private",
            created_at=datetime.now(timezone.utc)
        )
        ct2 = ChatType(
            id=uuid4(),
            name="Other Private",
            description="Other's private type",
            is_public=False,
            owner_id=other_user.id,
            collection_name="other_private",
            created_at=datetime.now(timezone.utc)
        )
        ct3 = ChatType(
            id=uuid4(),
            name="Public Type",
            description="Public type",
            is_public=True,
            owner_id=other_user.id,
            collection_name="public",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add_all([ct1, ct2, ct3])
        db_session.commit()
        
        chat_types, total = chat_type_repo.search(user_id=sample_user.id)
        
        assert total == 2
        chat_type_names = [ct.name for ct in chat_types]
        assert "My Private" in chat_type_names
        assert "Public Type" in chat_type_names
        assert "Other Private" not in chat_type_names

    def test_list_user_available(self, chat_type_repo: ChatTypeRepository, db_session: Session, sample_user: User):
        other_user = User(
            id=uuid4(),
            username="otheruser",
            email="other@example.com",
            password_hash="hash",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(other_user)
        db_session.commit()
        
        ct1 = ChatType(
            id=uuid4(),
            name="My Type",
            description="Owned by me",
            is_public=False,
            owner_id=sample_user.id,
            collection_name="my_type",
            created_at=datetime.now(timezone.utc)
        )
        ct2 = ChatType(
            id=uuid4(),
            name="Favorited Type",
            description="Favorited by me",
            is_public=True,
            owner_id=other_user.id,
            collection_name="favorited",
            created_at=datetime.now(timezone.utc)
        )
        ct3 = ChatType(
            id=uuid4(),
            name="Not Available",
            description="Not available to me",
            is_public=True,
            owner_id=other_user.id,
            collection_name="not_available",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add_all([ct1, ct2, ct3])
        db_session.commit()
        
        favorited_ids = [ct2.id]
        chat_types, total = chat_type_repo.list_user_available(sample_user.id, favorited_ids)
        
        assert total == 2
        chat_type_names = [ct.name for ct in chat_types]
        assert "My Type" in chat_type_names
        assert "Favorited Type" in chat_type_names
        assert "Not Available" not in chat_type_names

    def test_list_user_available_empty_favorites(self, chat_type_repo: ChatTypeRepository, db_session: Session, sample_user: User):
        ct = ChatType(
            id=uuid4(),
            name="My Type",
            description="Owned by me",
            is_public=False,
            owner_id=sample_user.id,
            collection_name="my_type",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(ct)
        db_session.commit()
        
        chat_types, total = chat_type_repo.list_user_available(sample_user.id, [])
        
        assert total == 1
        assert chat_types[0].name == "My Type"

    def test_list_by_ids(self, chat_type_repo: ChatTypeRepository, db_session: Session, sample_user: User):
        ct1 = ChatType(
            id=uuid4(),
            name="Type 1",
            description="Description 1",
            is_public=True,
            owner_id=sample_user.id,
            collection_name="type_1",
            created_at=datetime.now(timezone.utc)
        )
        ct2 = ChatType(
            id=uuid4(),
            name="Type 2",
            description="Description 2",
            is_public=True,
            owner_id=sample_user.id,
            collection_name="type_2",
            created_at=datetime.now(timezone.utc)
        )
        ct3 = ChatType(
            id=uuid4(),
            name="Type 3",
            description="Description 3",
            is_public=True,
            owner_id=sample_user.id,
            collection_name="type_3",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add_all([ct1, ct2, ct3])
        db_session.commit()
        
        chat_types, total = chat_type_repo.list_by_ids([ct1.id, ct2.id])
        
        assert total == 2
        assert len(chat_types) == 2

    def test_list_by_ids_empty(self, chat_type_repo: ChatTypeRepository):
        chat_types, total = chat_type_repo.list_by_ids([])
        
        assert total == 0
        assert len(chat_types) == 0

    def test_list_by_ids_with_pagination(self, chat_type_repo: ChatTypeRepository, db_session: Session, sample_user: User):
        ids = []
        for i in range(5):
            ct = ChatType(
                id=uuid4(),
                name=f"Type {i}",
                description=f"Description {i}",
                is_public=True,
                owner_id=sample_user.id,
                collection_name=f"type_{i}",
                created_at=datetime.now(timezone.utc)
            )
            db_session.add(ct)
            ids.append(ct.id)
        db_session.commit()
        
        chat_types, total = chat_type_repo.list_by_ids(ids, skip=2, limit=2)
        
        assert total == 5
        assert len(chat_types) == 2

    def test_list_user_available_with_filters(self, chat_type_repo: ChatTypeRepository, db_session: Session, sample_user: User):
        ct1 = ChatType(
            id=uuid4(),
            name="Public Mine",
            is_public=True,
            owner_id=sample_user.id,
            collection_name="pub_mine",
            created_at=datetime.now(timezone.utc)
        )
        ct2 = ChatType(
            id=uuid4(),
            name="Private Mine",
            is_public=False,
            owner_id=sample_user.id,
            collection_name="priv_mine",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add_all([ct1, ct2])
        db_session.commit()
        
        # Test is_public filter
        chat_types, total = chat_type_repo.list_user_available(sample_user.id, [], is_public=True)
        assert total == 1
        assert chat_types[0].name == "Public Mine"
        
        # Test owner_id filter
        chat_types, total = chat_type_repo.list_user_available(sample_user.id, [], owner_id=sample_user.id)
        assert total == 2

    def test_tags_operations(self, chat_type_repo: ChatTypeRepository, sample_chat_type: ChatType):
        tags = ["python", "ai", "coding"]
        
        # Add tags
        chat_type_repo.add_tags(sample_chat_type.id, tags)
        
        # Get tags
        retrieved_tags = chat_type_repo.get_tags(sample_chat_type.id)
        assert len(retrieved_tags) == 3
        assert set(retrieved_tags) == set(tags)
        
        # Replace tags
        new_tags = ["backend", "fastapi"]
        chat_type_repo.add_tags(sample_chat_type.id, new_tags)
        
        retrieved_tags = chat_type_repo.get_tags(sample_chat_type.id)
        assert len(retrieved_tags) == 2
        assert set(retrieved_tags) == set(new_tags)
        assert "python" not in retrieved_tags
