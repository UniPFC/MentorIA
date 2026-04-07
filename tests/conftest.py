import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import Mock, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from shared.database.session import Base
from shared.database.models.user import User
from shared.database.models.chat_type import ChatType
from shared.database.models.chat import Chat
from shared.database.models.message import Message, MessageRole
from shared.database.models.user_token import UserToken
from shared.database.models.password_reset_token import PasswordResetToken


@pytest.fixture(scope="function")
def db_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a new database session for a test."""
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=db_engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def sample_user(db_session: Session):
    """Create a sample user for testing."""
    user = User(
        id=uuid4(),
        username="testuser",
        email="test@example.com",
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqYj5rHQZe",  # "password123"
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_chat_type(db_session: Session, sample_user: User):
    """Create a sample chat type for testing."""
    chat_type_id = uuid4()
    chat_type = ChatType(
        id=chat_type_id,
        name="Test Chat Type",
        description="A test chat type",
        owner_id=sample_user.id,
        collection_name=f"chat_type_{chat_type_id}",
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(chat_type)
    db_session.commit()
    db_session.refresh(chat_type)
    return chat_type


@pytest.fixture
def sample_chat(db_session: Session, sample_user: User, sample_chat_type: ChatType):
    """Create a sample chat for testing."""
    chat = Chat(
        id=uuid4(),
        title="Test Chat",
        user_id=sample_user.id,
        chat_type_id=sample_chat_type.id,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(chat)
    db_session.commit()
    db_session.refresh(chat)
    return chat


@pytest.fixture
def sample_message(db_session: Session, sample_chat: Chat):
    """Create a sample message for testing."""
    message = Message(
        id=uuid4(),
        chat_id=sample_chat.id,
        role=MessageRole.USER,
        content="Test message",
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(message)
    db_session.commit()
    db_session.refresh(message)
    return message


@pytest.fixture
def sample_user_token(db_session: Session, sample_user: User):
    """Create a sample user token for testing."""
    token = UserToken(
        id=uuid4(),
        user_id=sample_user.id,
        token="test_access_token",
        token_type="access",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(token)
    db_session.commit()
    db_session.refresh(token)
    return token


@pytest.fixture
def sample_password_reset_token(db_session: Session, sample_user: User):
    """Create a sample password reset token for testing."""
    token = PasswordResetToken(
        id=uuid4(),
        user_id=sample_user.id,
        token="test_reset_token",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(token)
    db_session.commit()
    db_session.refresh(token)
    return token


@pytest.fixture
def mock_qdrant_client():
    """Create a mock Qdrant client."""
    mock_client = MagicMock()
    mock_client.get_collections.return_value.collections = []
    mock_client.create_collection.return_value = True
    mock_client.delete_collection.return_value = True
    mock_client.upsert.return_value = True
    return mock_client


@pytest.fixture
def mock_embedding_provider():
    """Create a mock embedding provider."""
    mock_provider = MagicMock()
    mock_provider.embed.return_value = [[0.1] * 384]  # Mock 384-dim embedding
    return mock_provider


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    mock_provider = MagicMock()
    mock_provider.generate.return_value = "Mock LLM response"
    mock_provider.stream.return_value = iter(["Mock ", "LLM ", "response"])
    return mock_provider
