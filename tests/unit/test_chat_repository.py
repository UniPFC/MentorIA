import pytest
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from src.repositories.chat import ChatRepository
from shared.database.models.chat import Chat
from shared.database.models.chat_type import ChatType
from shared.database.models.user import User


class TestChatRepository:
    """Test suite for ChatRepository"""

    @pytest.fixture
    def chat_repo(self, db_session: Session):
        return ChatRepository(db_session)

    def test_get_by_id_found(self, chat_repo: ChatRepository, sample_chat: Chat):
        result = chat_repo.get_by_id(sample_chat.id)
        
        assert result is not None
        assert result.id == sample_chat.id
        assert result.title == sample_chat.title

    def test_get_by_id_not_found(self, chat_repo: ChatRepository):
        non_existent_id = uuid4()
        result = chat_repo.get_by_id(non_existent_id)
        
        assert result is None

    def test_get_by_user(self, chat_repo: ChatRepository, db_session: Session, sample_user: User, sample_chat_type: ChatType):
        chat1 = Chat(
            id=uuid4(),
            title="Chat 1",
            user_id=sample_user.id,
            chat_type_id=sample_chat_type.id,
            created_at=datetime.now(timezone.utc)
        )
        chat2 = Chat(
            id=uuid4(),
            title="Chat 2",
            user_id=sample_user.id,
            chat_type_id=sample_chat_type.id,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add_all([chat1, chat2])
        db_session.commit()
        
        result = chat_repo.get_by_user(sample_user.id)
        
        assert len(result) == 2
        assert result[0].user_id == sample_user.id
        assert result[1].user_id == sample_user.id

    def test_get_by_user_with_chat_type_filter(self, chat_repo: ChatRepository, db_session: Session, sample_user: User):
        chat_type1 = ChatType(
            id=uuid4(),
            name="Type 1",
            description="Description 1",
            owner_id=sample_user.id,
            collection_name="type_1",
            created_at=datetime.now(timezone.utc)
        )
        chat_type2 = ChatType(
            id=uuid4(),
            name="Type 2",
            description="Description 2",
            owner_id=sample_user.id,
            collection_name="type_2",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add_all([chat_type1, chat_type2])
        db_session.commit()
        
        chat1 = Chat(
            id=uuid4(),
            title="Chat 1",
            user_id=sample_user.id,
            chat_type_id=chat_type1.id,
            created_at=datetime.now(timezone.utc)
        )
        chat2 = Chat(
            id=uuid4(),
            title="Chat 2",
            user_id=sample_user.id,
            chat_type_id=chat_type2.id,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add_all([chat1, chat2])
        db_session.commit()
        
        result = chat_repo.get_by_user(sample_user.id, chat_type_id=chat_type1.id)
        
        assert len(result) == 1
        assert result[0].chat_type_id == chat_type1.id

    def test_get_by_user_with_pagination(self, chat_repo: ChatRepository, db_session: Session, sample_user: User, sample_chat_type: ChatType):
        for i in range(5):
            chat = Chat(
                id=uuid4(),
                title=f"Chat {i}",
                user_id=sample_user.id,
                chat_type_id=sample_chat_type.id,
                created_at=datetime.now(timezone.utc)
            )
            db_session.add(chat)
        db_session.commit()
        
        result = chat_repo.get_by_user(sample_user.id, skip=2, limit=2)
        
        assert len(result) == 2

    def test_count_by_user(self, chat_repo: ChatRepository, db_session: Session, sample_user: User, sample_chat_type: ChatType):
        for i in range(3):
            chat = Chat(
                id=uuid4(),
                title=f"Chat {i}",
                user_id=sample_user.id,
                chat_type_id=sample_chat_type.id,
                created_at=datetime.now(timezone.utc)
            )
            db_session.add(chat)
        db_session.commit()
        
        count = chat_repo.count_by_user(sample_user.id)
        
        assert count == 3

    def test_count_by_user_empty(self, chat_repo: ChatRepository):
        non_existent_user_id = uuid4()
        count = chat_repo.count_by_user(non_existent_user_id)
        
        assert count == 0

    def test_create(self, chat_repo: ChatRepository, sample_user: User, sample_chat_type: ChatType):
        chat = Chat(
            id=uuid4(),
            title="New Chat",
            user_id=sample_user.id,
            chat_type_id=sample_chat_type.id,
            created_at=datetime.now(timezone.utc)
        )
        
        result = chat_repo.create(chat)
        
        assert result.id == chat.id
        assert result.title == "New Chat"

    def test_update(self, chat_repo: ChatRepository, sample_chat: Chat):
        sample_chat.title = "Updated Title"
        sample_chat.llm_model = "gpt-4"
        
        result = chat_repo.update(sample_chat)
        
        assert result.title == "Updated Title"
        assert result.llm_model == "gpt-4"

    def test_delete(self, chat_repo: ChatRepository, db_session: Session, sample_chat: Chat):
        chat_id = sample_chat.id
        
        chat_repo.delete(sample_chat)
        
        deleted_chat = db_session.query(Chat).filter(Chat.id == chat_id).first()
        assert deleted_chat is None
