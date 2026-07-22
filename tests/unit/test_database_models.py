import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlalchemy.orm import Session
from shared.database.models.user import User
from shared.database.models.chat_type import ChatType
from shared.database.models.chat import Chat
from shared.database.models.message import Message, MessageRole
from shared.database.models.user_token import UserToken
from shared.database.models.password_reset_token import PasswordResetToken
from shared.database.models.knowledge_chunk import KnowledgeChunk
from shared.database.models.ingestion_job import IngestionJob, IngestionStatus


@pytest.mark.unit
class TestUserModel:
    def test_create_user(self, db_session: Session):
        user = User(
            id=uuid4(),
            username="newuser",
            email="newuser@example.com",
            password_hash="hashed_password",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert user.username == "newuser"
        assert user.email == "newuser@example.com"
        assert user.is_active is True
        
    def test_user_unique_email(self, db_session: Session, sample_user: User):
        duplicate_user = User(
            id=uuid4(),
            username="anotheruser",
            email=sample_user.email,
            password_hash="hashed_password",
            is_active=True
        )
        db_session.add(duplicate_user)
        
        with pytest.raises(Exception):
            db_session.commit()
            
    def test_user_unique_username(self, db_session: Session, sample_user: User):
        duplicate_user = User(
            id=uuid4(),
            username=sample_user.username,
            email="different@example.com",
            password_hash="hashed_password",
            is_active=True
        )
        db_session.add(duplicate_user)
        
        with pytest.raises(Exception):
            db_session.commit()
            
    def test_user_repr(self, sample_user: User):
        repr_str = repr(sample_user)
        assert "User" in repr_str
        assert sample_user.username in repr_str
        assert sample_user.email in repr_str


@pytest.mark.unit
class TestChatTypeModel:
    def test_create_chat_type(self, db_session: Session, sample_user: User):
        chat_type_id = uuid4()
        chat_type = ChatType(
            id=chat_type_id,
            name="New Chat Type",
            description="Description",
            owner_id=sample_user.id,
            collection_name=f"chat_type_{chat_type_id}",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(chat_type)
        db_session.commit()
        
        assert chat_type.id is not None
        assert chat_type.name == "New Chat Type"
        assert chat_type.owner_id == sample_user.id
        assert chat_type.collection_name == f"chat_type_{chat_type_id}"
        
    def test_chat_type_cascade_delete(self, db_session: Session, sample_user: User, sample_chat_type: ChatType):
        chat = Chat(
            id=uuid4(),
            title="Test Chat",
            user_id=sample_user.id,
            chat_type_id=sample_chat_type.id
        )
        db_session.add(chat)
        db_session.commit()
        
        db_session.delete(sample_chat_type)
        db_session.commit()
        
        deleted_chat = db_session.query(Chat).filter(Chat.id == chat.id).first()
        assert deleted_chat is None


@pytest.mark.unit
class TestChatModel:
    def test_create_chat(self, db_session: Session, sample_user: User, sample_chat_type: ChatType):
        chat = Chat(
            id=uuid4(),
            title="New Chat",
            user_id=sample_user.id,
            chat_type_id=sample_chat_type.id
        )
        db_session.add(chat)
        db_session.commit()
        
        assert chat.id is not None
        assert chat.title == "New Chat"
        assert chat.user_id == sample_user.id
        assert chat.chat_type_id == sample_chat_type.id


@pytest.mark.unit
class TestMessageModel:
    def test_create_message(self, db_session: Session, sample_chat: Chat):
        message = Message(
            id=uuid4(),
            chat_id=sample_chat.id,
            role=MessageRole.USER,
            content="Hello, world!"
        )
        db_session.add(message)
        db_session.commit()
        
        assert message.id is not None
        assert message.chat_id == sample_chat.id
        assert message.role == MessageRole.USER
        assert message.content == "Hello, world!"
        
    def test_message_role_enum(self, db_session: Session, sample_chat: Chat):
        user_msg = Message(
            id=uuid4(),
            chat_id=sample_chat.id,
            role=MessageRole.USER,
            content="User message"
        )
        assistant_msg = Message(
            id=uuid4(),
            chat_id=sample_chat.id,
            role=MessageRole.ASSISTANT,
            content="Assistant message"
        )
        
        db_session.add_all([user_msg, assistant_msg])
        db_session.commit()
        
        assert user_msg.role == MessageRole.USER
        assert assistant_msg.role == MessageRole.ASSISTANT


@pytest.mark.unit
class TestUserTokenModel:
    def test_create_token(self, db_session: Session, sample_user: User):
        token = UserToken(
            id=uuid4(),
            user_id=sample_user.id,
            token="test_token_123",
            token_type="access",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            is_active=True
        )
        db_session.add(token)
        db_session.commit()
        
        assert token.id is not None
        assert token.user_id == sample_user.id
        assert token.token == "test_token_123"
        assert token.is_active is True
        
    def test_token_expiration(self, db_session: Session, sample_user: User):
        now = datetime.now(timezone.utc)
        expired_time = now - timedelta(hours=1)
        
        expired_token = UserToken(
            id=uuid4(),
            user_id=sample_user.id,
            token="expired_token",
            token_type="access",
            expires_at=expired_time,
            is_active=True
        )
        db_session.add(expired_token)
        db_session.commit()
        db_session.refresh(expired_token)
        
        current_time = datetime.now(timezone.utc)
        
        assert expired_token.expires_at < current_time


@pytest.mark.unit
class TestPasswordResetTokenModel:
    def test_create_reset_token(self, db_session: Session, sample_user: User):
        reset_token = PasswordResetToken(
            id=uuid4(),
            user_id=sample_user.id,
            token="reset_token_123",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            is_active=True
        )
        db_session.add(reset_token)
        db_session.commit()
        
        assert reset_token.id is not None
        assert reset_token.user_id == sample_user.id
        assert reset_token.is_active is True
        assert reset_token.used_at is None
        
    def test_mark_token_used(self, db_session: Session, sample_password_reset_token: PasswordResetToken):
        sample_password_reset_token.is_active = False
        sample_password_reset_token.used_at = datetime.now(timezone.utc)
        db_session.commit()
        
        assert sample_password_reset_token.is_active is False
        assert sample_password_reset_token.used_at is not None


@pytest.mark.unit
class TestKnowledgeChunkModel:
    def test_create_knowledge_chunk(self, db_session: Session, sample_chat_type: ChatType):
        chunk = KnowledgeChunk(
            id=uuid4(),
            chat_type_id=sample_chat_type.id,
            qdrant_point_id="point_123",
            source_file="test.txt",
            row_number=1,
            chunk_metadata='{"question": "What is AI?", "answer": "Artificial Intelligence is..."}'
        )
        db_session.add(chunk)
        db_session.commit()
        
        assert chunk.id is not None
        assert chunk.chat_type_id == sample_chat_type.id
        assert chunk.qdrant_point_id == "point_123"
        assert chunk.source_file == "test.txt"
        assert chunk.row_number == 1


@pytest.mark.unit
class TestIngestionJobModel:
    def test_create_ingestion_job(self, db_session: Session, sample_chat_type: ChatType):
        job = IngestionJob(
            id=uuid4(),
            chat_type_id=sample_chat_type.id,
            filename="test.xlsx",
            status=IngestionStatus.PENDING,
            total_chunks=0
        )
        db_session.add(job)
        db_session.commit()
        
        assert job.id is not None
        assert job.chat_type_id == sample_chat_type.id
        assert job.status == IngestionStatus.PENDING
        assert job.total_chunks == 0
        
    def test_job_status_transitions(self, db_session: Session, sample_chat_type: ChatType):
        job = IngestionJob(
            id=uuid4(),
            chat_type_id=sample_chat_type.id,
            filename="test.xlsx",
            status=IngestionStatus.PENDING
        )
        db_session.add(job)
        db_session.commit()
        
        job.status = IngestionStatus.PROCESSING
        db_session.commit()
        assert job.status == IngestionStatus.PROCESSING
        
        job.status = IngestionStatus.COMPLETED
        job.processed_chunks = 100
        job.total_chunks = 100
        db_session.commit()
        assert job.status == IngestionStatus.COMPLETED
        assert job.processed_chunks == 100
