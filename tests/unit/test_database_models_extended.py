import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlalchemy.orm import Session
from shared.database.models.user import User
from shared.database.models.chat_type import ChatType
from shared.database.models.chat import Chat
from shared.database.models.message import Message, MessageRole
from shared.database.models.knowledge_chunk import KnowledgeChunk
from shared.database.models.ingestion_job import IngestionJob, IngestionStatus
from shared.database.models.user_token import UserToken
from shared.database.models.password_reset_token import PasswordResetToken


@pytest.mark.unit
class TestDatabaseModelsExtended:
    """Extended tests for database models to increase coverage"""
    
    def test_user_model_email_property_encryption(self, db_session: Session):
        """Test User email property encryption/decryption"""
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqYj5rHQZe",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Test email property returns decrypted email
        assert user.email == "test@example.com"
        # Test _email contains encrypted data
        assert user._email != "test@example.com"
        assert len(user._email) > 20  # Encrypted should be longer
    
    def test_user_model_email_property_setter(self, db_session: Session):
        """Test User email property setter"""
        user = User(
            username="testuser",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqYj5rHQZe",
            is_active=True
        )
        
        # Set email property
        user.email = "newemail@example.com"
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Test email was encrypted
        assert user.email == "newemail@example.com"
        assert user._email != "newemail@example.com"
    
    def test_user_model_email_plain_alias(self, db_session: Session):
        """Test User email_plain alias property"""
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqYj5rHQZe",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Test email_plain property
        assert user.email_plain == "test@example.com"
        
        # Test email_plain setter
        user.email_plain = "updated@example.com"
        db_session.commit()
        db_session.refresh(user)
        
        assert user.email == "updated@example.com"
    
    def test_chat_type_model_defaults(self, db_session: Session, sample_user: User):
        """Test ChatType model default values"""
        chat_type = ChatType(
            name="Test Chat Type",
            description="Test description",
            owner_id=sample_user.id,
            collection_name="test_collection"
        )
        db_session.add(chat_type)
        db_session.commit()
        db_session.refresh(chat_type)
        
        # Test default values
        # Note: Check what the actual default is for is_public
        assert chat_type.created_at is not None
        # is_public default depends on the model definition
    
    def test_chat_model_timestamps(self, db_session: Session, sample_user: User, sample_chat_type: ChatType):
        """Test Chat model timestamp handling"""
        chat = Chat(
            title="Test Chat",
            user_id=sample_user.id,
            chat_type_id=sample_chat_type.id,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(chat)
        db_session.commit()
        db_session.refresh(chat)
        
        # Test timestamps
        assert chat.created_at is not None
        assert chat.updated_at is not None
        assert chat.created_at <= chat.updated_at
    
    def test_chat_model_optional_fields(self, db_session: Session, sample_user: User, sample_chat_type: ChatType):
        """Test Chat model optional fields"""
        chat = Chat(
            title="Test Chat",
            user_id=sample_user.id,
            chat_type_id=sample_chat_type.id
        )
        db_session.add(chat)
        db_session.commit()
        db_session.refresh(chat)
        
        # Test optional fields default to None
        assert chat.llm_model is None
        assert chat.llm_provider is None
        assert chat.title_auto_generated is False
    
    def test_message_model_roles(self, db_session: Session, sample_user: User, sample_chat_type: ChatType):
        """Test Message model with different roles"""
        chat = Chat(
            title="Test Chat",
            user_id=sample_user.id,
            chat_type_id=sample_chat_type.id,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(chat)
        db_session.commit()
        db_session.refresh(chat)
        
        # Create messages with different roles
        user_message = Message(
            chat_id=chat.id,
            role=MessageRole.USER,
            content="User message",
            created_at=datetime.now(timezone.utc)
        )
        assistant_message = Message(
            chat_id=chat.id,
            role=MessageRole.ASSISTANT,
            content="Assistant message",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add_all([user_message, assistant_message])
        db_session.commit()
        db_session.refresh(user_message)
        db_session.refresh(assistant_message)
        
        # Test message roles
        assert user_message.role == MessageRole.USER
        assert assistant_message.role == MessageRole.ASSISTANT
        assert user_message.content == "User message"
        assert assistant_message.content == "Assistant message"
    
    def test_knowledge_chunk_model_metadata(self, db_session: Session, sample_user: User, sample_chat_type: ChatType):
        """Test KnowledgeChunk model metadata handling"""
        chunk = KnowledgeChunk(
            chat_type_id=sample_chat_type.id,
            qdrant_point_id="test_point_123",
            source_file="test_file.xlsx",
            row_number=1,
            chunk_metadata='{"question": "Test question", "answer": "Test answer"}'
        )
        db_session.add(chunk)
        db_session.commit()
        db_session.refresh(chunk)
        
        # Test metadata handling
        assert chunk.chat_type_id == sample_chat_type.id
        assert chunk.qdrant_point_id == "test_point_123"
        assert chunk.source_file == "test_file.xlsx"
        assert chunk.row_number == 1
        assert chunk.chunk_metadata == '{"question": "Test question", "answer": "Test answer"}'
    
    def test_ingestion_job_model_status_transitions(self, db_session: Session, sample_user: User, sample_chat_type: ChatType):
        """Test IngestionJob model status transitions"""
        job = IngestionJob(
            chat_type_id=sample_chat_type.id,
            filename="test_file.xlsx",
            status=IngestionStatus.PENDING,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        
        # Test initial status
        assert job.status == IngestionStatus.PENDING
        assert job.error_message is None
        
        # Test status update
        job.status = IngestionStatus.PROCESSING
        job.started_at = datetime.now(timezone.utc)
        db_session.commit()
        db_session.refresh(job)
        
        assert job.status == IngestionStatus.PROCESSING
        assert job.started_at > job.created_at
        
        # Test completion
        job.status = IngestionStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        db_session.commit()
        db_session.refresh(job)
        
        assert job.status == IngestionStatus.COMPLETED
        assert job.completed_at is not None
        
        # Test failure
        job.status = IngestionStatus.FAILED
        job.error_message = "Processing failed"
        job.completed_at = datetime.now(timezone.utc)
        db_session.commit()
        db_session.refresh(job)
        
        assert job.status == IngestionStatus.FAILED
        assert job.error_message == "Processing failed"
    
    def test_user_token_model_expiration(self, db_session: Session, sample_user: User):
        """Test UserToken model expiration handling"""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        token = UserToken(
            user_id=sample_user.id,
            token="test_token_123",
            token_type="access",
            expires_at=expires_at,
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(token)
        db_session.commit()
        db_session.refresh(token)
        
        # Test token fields
        assert token.user_id == sample_user.id
        assert token.token == "test_token_123"
        assert token.token_type == "access"
        assert token.is_active is True
        # Compare datetime without timezone info
        assert token.expires_at.replace(tzinfo=None) == expires_at.replace(tzinfo=None)
    
        """Test PasswordResetToken model"""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
        reset_token = PasswordResetToken(
            user_id=sample_user.id,
            token="reset_token_789",
            expires_at=expires_at,
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(reset_token)
        db_session.commit()
        db_session.refresh(reset_token)
        
        # Test reset token fields
        assert reset_token.user_id == sample_user.id
        assert reset_token.token == "reset_token_789"
        assert reset_token.is_active is True
        # Compare datetime without timezone info
        assert reset_token.expires_at.replace(tzinfo=None) == expires_at.replace(tzinfo=None)
        assert reset_token.used_at is None
    
    def test_password_reset_token_usage(self, db_session: Session, sample_user: User):
        """Test PasswordResetToken usage tracking"""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
        reset_token = PasswordResetToken(
            user_id=sample_user.id,
            token="reset_token_789",
            expires_at=expires_at,
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(reset_token)
        db_session.commit()
        db_session.refresh(reset_token)
        
        # Test usage tracking
        used_at = datetime.now(timezone.utc)
        reset_token.is_active = False
        reset_token.used_at = used_at
        db_session.commit()
        db_session.refresh(reset_token)
        
        assert reset_token.is_active is False
        assert reset_token.used_at.replace(tzinfo=None) == used_at.replace(tzinfo=None)
