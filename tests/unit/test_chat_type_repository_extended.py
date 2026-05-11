import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlalchemy.orm import Session
from src.repositories.chat_type import ChatTypeRepository
from shared.database.models.chat_type import ChatType
from shared.database.models.user import User


@pytest.mark.unit
class TestChatTypeRepositoryExtended:
    """Extended tests for ChatTypeRepository to increase coverage"""
    
    @pytest.fixture
    def chat_type_repo(self, db_session: Session):
        return ChatTypeRepository(db_session)
    
    @pytest.fixture
    def sample_user(self, db_session: Session):
        user = User(
            id=uuid4(),
            username="testuser",
            email="test@example.com",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqYj5rHQZe",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    
    def test_get_by_id_with_relations(self, chat_type_repo: ChatTypeRepository, db_session: Session, sample_user: User):
        """Test get_by_id with loaded relations"""
        # Create chat type
        chat_type = ChatType(
            id=uuid4(),
            name="Test Chat Type",
            description="Test description",
            owner_id=sample_user.id,
            collection_name="test_collection",
            is_public=True,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(chat_type)
        db_session.commit()
        db_session.refresh(chat_type)
        
        # Test get_by_id
        found_chat_type = chat_type_repo.get_by_id(chat_type.id)
        assert found_chat_type is not None
        assert found_chat_type.id == chat_type.id
        assert found_chat_type.name == chat_type.name
        assert found_chat_type.owner_id == sample_user.id
    
    def test_get_by_id_not_found(self, chat_type_repo: ChatTypeRepository):
        """Test get_by_id with non-existent ID"""
        non_existent_id = uuid4()
        found_chat_type = chat_type_repo.get_by_id(non_existent_id)
        assert found_chat_type is None
    
    def test_get_public_chat_types(self, chat_type_repo: ChatTypeRepository, db_session: Session, sample_user: User):
        """Test get_public_chat_types using search method"""
        # Create public and private chat types
        public_chat_type = ChatType(
            id=uuid4(),
            name="Public Chat Type",
            description="Public description",
            owner_id=sample_user.id,
            collection_name="public_collection",
            is_public=True,
            created_at=datetime.now(timezone.utc)
        )
        private_chat_type = ChatType(
            id=uuid4(),
            name="Private Chat Type",
            description="Private description",
            owner_id=sample_user.id,
            collection_name="private_collection",
            is_public=False,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add_all([public_chat_type, private_chat_type])
        db_session.commit()
        
        # Test search method with is_public=True
        public_chat_types, total = chat_type_repo.search(is_public=True)
        assert len(public_chat_types) == 1
        assert public_chat_types[0].name == "Public Chat Type"
        assert public_chat_types[0].is_public is True
    
    def test_search_method(self, chat_type_repo: ChatTypeRepository, db_session: Session, sample_user: User):
        """Test search method with various filters"""
        # Create chat types for testing
        public_chat_type = ChatType(
            id=uuid4(),
            name="Public Chat Type",
            description="Public description",
            owner_id=sample_user.id,
            collection_name="public_collection",
            is_public=True,
            created_at=datetime.now(timezone.utc)
        )
        private_chat_type = ChatType(
            id=uuid4(),
            name="Private Chat Type",
            description="Private description",
            owner_id=sample_user.id,
            collection_name="private_collection",
            is_public=False,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add_all([public_chat_type, private_chat_type])
        db_session.commit()
        
        # Test search for public chat types
        public_results, total = chat_type_repo.search(is_public=True)
        assert len(public_results) == 1
        assert public_results[0].name == "Public Chat Type"
        assert total == 1
        
        # Test search by owner
        owner_results, total = chat_type_repo.search(owner_id=sample_user.id)
        assert len(owner_results) == 2
        assert total == 2
        
        # Test search with query
        query_results, total = chat_type_repo.search(query="Public")
        assert len(query_results) == 1
        assert query_results[0].name == "Public Chat Type"
    
    def test_list_user_available(self, chat_type_repo: ChatTypeRepository, db_session: Session, sample_user: User):
        """Test list_user_available method"""
        # Create chat types for user
        chat_type1 = ChatType(
            id=uuid4(),
            name="User Chat Type 1",
            description="User description 1",
            owner_id=sample_user.id,
            collection_name="user_collection_1",
            is_public=False,
            created_at=datetime.now(timezone.utc)
        )
        chat_type2 = ChatType(
            id=uuid4(),
            name="User Chat Type 2",
            description="User description 2",
            owner_id=sample_user.id,
            collection_name="user_collection_2",
            is_public=True,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add_all([chat_type1, chat_type2])
        db_session.commit()
        
        # Test list_user_available
        user_chat_types, total = chat_type_repo.list_user_available(user_id=sample_user.id, favorited_ids=[])
        assert len(user_chat_types) == 2
        assert total == 2
    
    def test_list_by_ids(self, chat_type_repo: ChatTypeRepository, db_session: Session, sample_user: User):
        """Test list_by_ids method"""
        # Create chat types
        chat_type1 = ChatType(
            id=uuid4(),
            name="Chat Type 1",
            description="Description 1",
            owner_id=sample_user.id,
            collection_name="collection_1",
            created_at=datetime.now(timezone.utc)
        )
        chat_type2 = ChatType(
            id=uuid4(),
            name="Chat Type 2",
            description="Description 2",
            owner_id=sample_user.id,
            collection_name="collection_2",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add_all([chat_type1, chat_type2])
        db_session.commit()
        db_session.refresh(chat_type1)
        db_session.refresh(chat_type2)
        
        # Test list_by_ids
        chat_types, total = chat_type_repo.list_by_ids([chat_type1.id, chat_type2.id])
        assert len(chat_types) == 2
        assert total == 2
        assert chat_types[0].id in [chat_type1.id, chat_type2.id]
        assert chat_types[1].id in [chat_type1.id, chat_type2.id]
    
    def test_list_by_ids_empty(self, chat_type_repo: ChatTypeRepository):
        """Test list_by_ids with empty list"""
        chat_types, total = chat_type_repo.list_by_ids([])
        assert len(chat_types) == 0
        assert total == 0
    
    def test_add_tags(self, chat_type_repo: ChatTypeRepository, db_session: Session, sample_user: User):
        """Test add_tags method"""
        # Create chat type
        chat_type = ChatType(
            id=uuid4(),
            name="Chat Type with Tags",
            description="Description",
            owner_id=sample_user.id,
            collection_name="tagged_collection",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(chat_type)
        db_session.commit()
        
        # Add tags
        chat_type_repo.add_tags(chat_type.id, ["tag1", "tag2", "tag3"])
        
        # Verify tags were added
        tags = chat_type_repo.get_tags(chat_type.id)
        assert len(tags) == 3
        assert "tag1" in tags
        assert "tag2" in tags
        assert "tag3" in tags
    
    def test_get_tags(self, chat_type_repo: ChatTypeRepository, db_session: Session, sample_user: User):
        """Test get_tags method"""
        # Create chat type with tags
        chat_type = ChatType(
            id=uuid4(),
            name="Chat Type with Tags",
            description="Description",
            owner_id=sample_user.id,
            collection_name="tagged_collection",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(chat_type)
        db_session.commit()
        
        # Add tags
        chat_type_repo.add_tags(chat_type.id, ["tag1", "tag2"])
        
        # Test get_tags
        tags = chat_type_repo.get_tags(chat_type.id)
        assert len(tags) == 2
        assert "tag1" in tags
        assert "tag2" in tags
    
    def test_get_tags_empty(self, chat_type_repo: ChatTypeRepository):
        """Test get_tags with no tags"""
        chat_type_id = uuid4()
        tags = chat_type_repo.get_tags(chat_type_id)
        assert len(tags) == 0
