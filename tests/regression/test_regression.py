import pytest
import uuid
from sqlalchemy.orm import Session
from src.services.auth import AuthService
from src.repositories.user import UserRepository
from src.services.chat import ChatService
from shared.database.models.user import User
from shared.database.models.chat_type import ChatType
from shared.database.models.chat import Chat
from shared.database.models.message import MessageRole


def _unique_email(base: str) -> str:
    """Gera email único para evitar conflitos em testes"""
    return f"{base}_{uuid.uuid4().hex[:8]}@test.com"


@pytest.mark.regression
class TestRegressionAuthFlow:
    """Testes de regressão para fluxo de autenticação"""
    
    def test_user_registration_and_login(self, db_session: Session):
        """Valida que registro e login funcionam corretamente"""
        auth_service = AuthService()
        user_repo = UserRepository(db_session)
        
        email = _unique_email("regression")
        password = "Password123!"
        
        # Registrar usuário
        user = User(
            email=email,
            username=f"user_{uuid.uuid4().hex[:8]}",
            password_hash=auth_service.get_password_hash(password),
            is_active=True
        )
        user = user_repo.create(user)
        
        # Validar que usuário foi criado
        assert user.id is not None
        assert user.email == email
        assert user.is_active is True
        
        # Validar que consegue fazer login
        authenticated = auth_service.authenticate_user(user_repo, email, password)
        assert authenticated is not None
        assert authenticated.id == user.id
    
    def test_token_generation_and_verification(self, db_session: Session):
        """Valida que geração e verificação de tokens funcionam"""
        auth_service = AuthService()
        user_repo = UserRepository(db_session)
        
        user = User(
            email=_unique_email("token"),
            username=f"user_{uuid.uuid4().hex[:8]}",
            password_hash=auth_service.get_password_hash("Password123!"),
            is_active=True
        )
        user = user_repo.create(user)
        
        # Gerar tokens
        tokens = auth_service.create_user_tokens(user, user_repo)
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        
        # Verificar que token funciona
        current_user = auth_service.get_current_user_from_token(
            tokens["access_token"],
            user_repo
        )
        assert current_user is not None
        assert current_user.id == user.id


@pytest.mark.regression
class TestRegressionChatFlow:
    """Testes de regressão para fluxo de chat"""
    
    def test_chat_creation_and_messaging(self, db_session: Session):
        """Valida que criação de chat e envio de mensagens funcionam"""
        auth_service = AuthService()
        user_repo = UserRepository(db_session)
        chat_service = ChatService(db_session)
        
        # Criar usuário
        user = User(
            email=_unique_email("chat"),
            username=f"user_{uuid.uuid4().hex[:8]}",
            password_hash=auth_service.get_password_hash("Password123!"),
            is_active=True
        )
        user = user_repo.create(user)
        
        # Criar ChatType
        chat_type = ChatType(
            name=f"KB_{uuid.uuid4().hex[:8]}",
            description="Test KB",
            is_public=True,
            owner_id=user.id,
            collection_name=f"coll_{uuid.uuid4().hex[:8]}"
        )
        db_session.add(chat_type)
        db_session.commit()
        db_session.refresh(chat_type)
        
        # Criar Chat
        chat = Chat(
            user_id=user.id,
            chat_type_id=chat_type.id,
            title="Regression Chat"
        )
        db_session.add(chat)
        db_session.commit()
        db_session.refresh(chat)
        
        # Validar que chat foi criado
        assert chat.id is not None
        assert chat.user_id == user.id
        
        # Enviar mensagens
        chat_service.save_message(chat.id, MessageRole.USER, "Hello")
        chat_service.save_message(chat.id, MessageRole.ASSISTANT, "Hi there!")
        
        # Validar histórico
        history = chat_service.get_chat_history(chat.id)
        assert len(history) == 2
        assert history[0]["content"] == "Hello"
        assert history[1]["content"] == "Hi there!"
    
    def test_multiple_independent_chats(self, db_session: Session):
        """Valida que múltiplos chats são independentes"""
        auth_service = AuthService()
        user_repo = UserRepository(db_session)
        chat_service = ChatService(db_session)
        
        user = User(
            email=_unique_email("multichats"),
            username=f"user_{uuid.uuid4().hex[:8]}",
            password_hash=auth_service.get_password_hash("Password123!"),
            is_active=True
        )
        user = user_repo.create(user)
        
        chat_type = ChatType(
            name=f"KB_{uuid.uuid4().hex[:8]}",
            description="Test",
            is_public=True,
            owner_id=user.id,
            collection_name=f"coll_{uuid.uuid4().hex[:8]}"
        )
        db_session.add(chat_type)
        db_session.commit()
        db_session.refresh(chat_type)
        
        # Criar dois chats
        chat1 = Chat(user_id=user.id, chat_type_id=chat_type.id, title="Chat 1")
        chat2 = Chat(user_id=user.id, chat_type_id=chat_type.id, title="Chat 2")
        
        db_session.add(chat1)
        db_session.add(chat2)
        db_session.commit()
        db_session.refresh(chat1)
        db_session.refresh(chat2)
        
        # Adicionar mensagens diferentes
        chat_service.save_message(chat1.id, MessageRole.USER, "Chat 1 message")
        chat_service.save_message(chat2.id, MessageRole.USER, "Chat 2 message")
        
        # Validar isolamento
        history1 = chat_service.get_chat_history(chat1.id)
        history2 = chat_service.get_chat_history(chat2.id)
        
        assert len(history1) == 1
        assert len(history2) == 1
        assert "Chat 1 message" in history1[0]["content"]
        assert "Chat 2 message" in history2[0]["content"]


@pytest.mark.regression
class TestRegressionDataIntegrity:
    """Testes de regressão para integridade de dados"""
    
    def test_user_data_persistence(self, db_session: Session):
        """Valida que dados de usuário persistem corretamente"""
        auth_service = AuthService()
        user_repo = UserRepository(db_session)
        
        email = _unique_email("persistence")
        username = f"user_{uuid.uuid4().hex[:8]}"
        
        user = User(
            email=email,
            username=username,
            password_hash=auth_service.get_password_hash("Password123!"),
            is_active=True
        )
        user = user_repo.create(user)
        user_id = user.id
        
        # Recuperar usuário do banco
        retrieved_user = user_repo.get_by_id(user_id)
        
        assert retrieved_user is not None
        assert retrieved_user.email == email
        assert retrieved_user.username == username
        assert retrieved_user.is_active is True
    
    def test_chat_history_order(self, db_session: Session):
        """Valida que histórico de chat mantém ordem correta"""
        auth_service = AuthService()
        user_repo = UserRepository(db_session)
        chat_service = ChatService(db_session)
        
        user = User(
            email=_unique_email("order"),
            username=f"user_{uuid.uuid4().hex[:8]}",
            password_hash=auth_service.get_password_hash("Password123!"),
            is_active=True
        )
        user = user_repo.create(user)
        
        chat_type = ChatType(
            name=f"KB_{uuid.uuid4().hex[:8]}",
            description="Test",
            is_public=True,
            owner_id=user.id,
            collection_name=f"coll_{uuid.uuid4().hex[:8]}"
        )
        db_session.add(chat_type)
        db_session.commit()
        db_session.refresh(chat_type)
        
        chat = Chat(user_id=user.id, chat_type_id=chat_type.id, title="Order Chat")
        db_session.add(chat)
        db_session.commit()
        db_session.refresh(chat)
        
        # Adicionar mensagens em sequência
        messages = ["First", "Second", "Third", "Fourth", "Fifth"]
        for msg in messages:
            chat_service.save_message(chat.id, MessageRole.USER, msg)
        
        # Validar ordem
        history = chat_service.get_chat_history(chat.id)
        
        assert len(history) == len(messages)
        for i, msg in enumerate(messages):
            assert msg in history[i]["content"]


@pytest.mark.regression
class TestRegressionErrorHandling:
    """Testes de regressão para tratamento de erros"""
    
    def test_invalid_credentials(self, db_session: Session):
        """Valida que autenticação com credenciais inválidas falha"""
        auth_service = AuthService()
        user_repo = UserRepository(db_session)
        
        email = _unique_email("invalid")
        user = User(
            email=email,
            username=f"user_{uuid.uuid4().hex[:8]}",
            password_hash=auth_service.get_password_hash("CorrectPassword123!"),
            is_active=True
        )
        user = user_repo.create(user)
        
        # Tentar autenticar com senha errada
        authenticated = auth_service.authenticate_user(
            user_repo,
            email,
            "WrongPassword123!"
        )
        
        assert authenticated is None
    
    def test_nonexistent_user(self, db_session: Session):
        """Valida que busca de usuário inexistente retorna None"""
        user_repo = UserRepository(db_session)
        
        user = user_repo.get_by_email(_unique_email("nonexistent"))
        
        assert user is None
    
    def test_empty_chat_history(self, db_session: Session):
        """Valida que histórico vazio retorna lista vazia"""
        auth_service = AuthService()
        user_repo = UserRepository(db_session)
        chat_service = ChatService(db_session)
        
        user = User(
            email=_unique_email("empty"),
            username=f"user_{uuid.uuid4().hex[:8]}",
            password_hash=auth_service.get_password_hash("Password123!"),
            is_active=True
        )
        user = user_repo.create(user)
        
        chat_type = ChatType(
            name=f"KB_{uuid.uuid4().hex[:8]}",
            description="Test",
            is_public=True,
            owner_id=user.id,
            collection_name=f"coll_{uuid.uuid4().hex[:8]}"
        )
        db_session.add(chat_type)
        db_session.commit()
        db_session.refresh(chat_type)
        
        chat = Chat(user_id=user.id, chat_type_id=chat_type.id, title="Empty Chat")
        db_session.add(chat)
        db_session.commit()
        db_session.refresh(chat)
        
        # Validar que histórico vazio retorna lista vazia
        history = chat_service.get_chat_history(chat.id)
        
        assert history == []
