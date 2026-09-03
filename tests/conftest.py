from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from sqlalchemy import DateTime, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Load test environment variables before importing any modules that depend on settings
test_env_path = Path(__file__).parent / ".env.test"
if test_env_path.exists():
    load_dotenv(test_env_path, override=True)

from shared.database.models.chat import Chat
from shared.database.models.chat_type import ChatType
from shared.database.models.message import Message, MessageRole
from shared.database.models.password_reset_token import PasswordResetToken
from shared.database.models.user import User
from shared.database.models.user_token import UserToken
from shared.database.session import Base


def _ensure_aware_datetimes(target):
    """
    SQLite returns naive datetimes even for DateTime(timezone=True) columns.
    This simulates PostgreSQL behavior by converting naive datetimes to UTC-aware
    on all DateTime(timezone=True) columns of the loaded object.
    """
    mapper = target.__class__.__mapper__
    for column in mapper.columns:
        if isinstance(column.type, DateTime) and column.type.timezone:
            value = getattr(target, column.key, None)
            if value is not None and value.tzinfo is None:
                setattr(target, column.key, value.replace(tzinfo=UTC))


@event.listens_for(Base, "load", propagate=True)
def _tz_aware_on_load(target, context):
    _ensure_aware_datetimes(target)


@event.listens_for(Base, "refresh", propagate=True)
def _tz_aware_on_refresh(target, context, attrs):
    _ensure_aware_datetimes(target)


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
        session.close()


@pytest.fixture
def sample_user(db_session: Session):
    """Create a sample user for testing with password hash matching AuthService."""
    from src.services.auth import AuthService

    auth_service = AuthService()
    password_hash = auth_service.get_password_hash("password123")

    user = User(
        id=uuid4(),
        username="testuser",
        email="test@example.com",
        password_hash=password_hash,
        is_active=True,
        email_verified=True,
        created_at=datetime.now(UTC),
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
        created_at=datetime.now(UTC),
    )
    db_session.add(chat_type)
    db_session.commit()
    db_session.refresh(chat_type)
    return chat_type


@pytest.fixture
def sample_chat(db_session: Session, sample_user: User, sample_chat_type: ChatType):
    """Create a sample chat for testing. Each test gets a fresh chat."""
    # Create a completely new chat for this test
    chat = Chat(
        id=uuid4(),
        title="Test Chat",
        user_id=sample_user.id,
        chat_type_id=sample_chat_type.id,
        created_at=datetime.now(UTC),
    )
    db_session.add(chat)
    db_session.commit()
    db_session.refresh(chat)

    yield chat

    # Clean up: delete all messages for this chat after test
    try:
        db_session.query(Message).filter(Message.chat_id == chat.id).delete()
        db_session.commit()
    except Exception:
        db_session.rollback()


@pytest.fixture
def sample_message(db_session: Session, sample_chat: Chat):
    """Create a sample message for testing."""
    message = Message(
        id=uuid4(),
        chat_id=sample_chat.id,
        role=MessageRole.USER,
        content="Test message",
        created_at=datetime.now(UTC),
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
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        is_active=True,
        created_at=datetime.now(UTC),
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
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db_session.add(token)
    db_session.commit()
    db_session.refresh(token)
    return token


@pytest.fixture
def sample_jwt_token(db_session: Session, sample_user: User):
    """Create a valid JWT access token registered in the database for integration tests."""
    from src.repositories.user import UserRepository
    from src.services.auth import AuthService

    auth_service = AuthService()
    jwt_string = auth_service.create_access_token(
        {"sub": str(sample_user.id)}, expires_delta=timedelta(hours=1)
    )

    user_repo = UserRepository(db_session)
    user_repo.create_token(
        user_id=sample_user.id,
        token=jwt_string,
        token_type="access",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    db_session.commit()

    return jwt_string


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


@pytest.fixture(autouse=True)
def mock_pagarme_for_integration_tests(request):
    """Prevent integration tests from calling the real payment gateway."""
    if request.node.get_closest_marker("integration") is None:
        yield
        return

    mock_pagarme = MagicMock()
    mock_pagarme.create_customer = AsyncMock(return_value="test_customer")
    mock_pagarme.create_subscription_checkout = AsyncMock(
        return_value="https://checkout.pagar.me/test"
    )
    mock_pagarme.create_refill_checkout = AsyncMock(
        return_value="https://checkout.pagar.me/test"
    )
    mock_pagarme.cancel_subscription = AsyncMock(return_value=True)

    with patch("src.api.routes.payments.pagarme_service", mock_pagarme):
        yield


@pytest.fixture
def client(db_session):
    """Create a test client for FastAPI app."""
    from fastapi.testclient import TestClient

    from shared.database.session import get_db
    from src.api.dependencies import (
        get_current_active_user,
        get_current_active_user_no_terms_check,
    )
    from src.api.main import app

    # Override the database dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = (
        get_current_active_user_no_terms_check
    )

    # Patch lifespan hooks (run_migrations) while starting the client
    with patch("src.api.main.run_migrations") as mock_migrations:
        # Prevent actually running migrations during tests_client:
        with TestClient(app) as test_client:
            yield test_client

    # Clean up overrides
    app.dependency_overrides.clear()
