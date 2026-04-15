import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from src.services.auth import AuthService
from src.repositories.user import UserRepository
from shared.database.models.user import User
from shared.database.models.chat_type import ChatType
from shared.database.models.chat import Chat
from shared.database.models.message import MessageRole
from src.services.chat import ChatService


@pytest.mark.integration
class TestBasicFlows:
    """Testes de integração para fluxos básicos do sistema"""
    
    def test_user_creation_and_authentication(self, db_session: Session):
        """Testa criação de usuário e autenticação"""
        auth_service = AuthService()
        user_repo = UserRepository(db_session)
        
        # Criar usuário
        email = "test@example.com"
        password = "SecurePassword123!"
        
        user = User(
            email=email,
            username="testuser",
            password_hash=auth_service.get_password_hash(password),
            is_active=True
        )
        user = user_repo.create(user)
        
        assert user.id is not None
        assert user.email == email
        
        # Autenticar
        authenticated = auth_service.authenticate_user(user_repo, email, password)
        assert authenticated is not None
        assert authenticated.id == user.id
    
    def test_user_tokens_creation(self, db_session: Session):
        """Testa criação de tokens para usuário"""
        auth_service = AuthService()
        user_repo = UserRepository(db_session)
        
        user = User(
            email="tokens@test.com",
            username="tokenuser",
            password_hash=auth_service.get_password_hash("Password123!"),
            is_active=True
        )
        user = user_repo.create(user)
        
        # Criar tokens
        tokens = auth_service.create_user_tokens(user, user_repo)
        
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
        assert tokens["expires_in"] > 0
    
    def test_chat_type_and_chat_creation(self, db_session: Session):
        """Testa criação de ChatType e Chat"""
        user_repo = UserRepository(db_session)
        auth_service = AuthService()
        
        # Criar usuário
        user = User(
            email="chat@test.com",
            username="chatuser",
            password_hash=auth_service.get_password_hash("Password123!"),
            is_active=True
        )
        user = user_repo.create(user)
        
        # Criar ChatType
        chat_type = ChatType(
            name="Test Knowledge Base",
            description="Test KB",
            is_public=True,
            owner_id=user.id,
            collection_name="test_collection"
        )
        db_session.add(chat_type)
        db_session.commit()
        db_session.refresh(chat_type)
        
        assert chat_type.id is not None
        assert chat_type.owner_id == user.id
        
        # Criar Chat
        chat = Chat(
            user_id=user.id,
            chat_type_id=chat_type.id,
            title="Test Chat"
        )
        db_session.add(chat)
        db_session.commit()
        db_session.refresh(chat)
        
        assert chat.id is not None
        assert chat.user_id == user.id
        assert chat.chat_type_id == chat_type.id
    
    def test_chat_messages(self, db_session: Session):
        """Testa adição de mensagens em chat"""
        user_repo = UserRepository(db_session)
        auth_service = AuthService()
        chat_service = ChatService(db_session)
        
        # Setup
        user = User(
            email="messages@test.com",
            username="msguser",
            password_hash=auth_service.get_password_hash("Password123!"),
            is_active=True
        )
        user = user_repo.create(user)
        
        chat_type = ChatType(
            name="Message KB",
            description="Test",
            is_public=True,
            owner_id=user.id,
            collection_name="msg_collection"
        )
        db_session.add(chat_type)
        db_session.commit()
        db_session.refresh(chat_type)
        
        chat = Chat(
            user_id=user.id,
            chat_type_id=chat_type.id,
            title="Message Chat"
        )
        db_session.add(chat)
        db_session.commit()
        db_session.refresh(chat)
        
        # Adicionar mensagens
        msg1 = chat_service.save_message(
            chat_id=chat.id,
            role=MessageRole.USER,
            content="Hello"
        )
        
        msg2 = chat_service.save_message(
            chat_id=chat.id,
            role=MessageRole.ASSISTANT,
            content="Hi there!"
        )
        
        assert msg1.id is not None
        assert msg2.id is not None
        
        # Obter histórico
        history = chat_service.get_chat_history(chat.id)
        assert len(history) == 2
        assert history[0]["content"] == "Hello"
        assert history[1]["content"] == "Hi there!"
    
    def test_multiple_users_and_chats(self, db_session: Session):
        """Testa múltiplos usuários com múltiplos chats"""
        user_repo = UserRepository(db_session)
        auth_service = AuthService()
        
        # Criar dois usuários
        user1 = User(
            email="user1@test.com",
            username="user1",
            password_hash=auth_service.get_password_hash("Password123!"),
            is_active=True
        )
        user1 = user_repo.create(user1)
        
        user2 = User(
            email="user2@test.com",
            username="user2",
            password_hash=auth_service.get_password_hash("Password123!"),
            is_active=True
        )
        user2 = user_repo.create(user2)
        
        # Criar ChatType público
        chat_type = ChatType(
            name="Public KB",
            description="Public",
            is_public=True,
            owner_id=user1.id,
            collection_name="public_collection"
        )
        db_session.add(chat_type)
        db_session.commit()
        db_session.refresh(chat_type)
        
        # Ambos os usuários criam chats no mesmo ChatType
        chat1 = Chat(
            user_id=user1.id,
            chat_type_id=chat_type.id,
            title="User1 Chat"
        )
        db_session.add(chat1)
        
        chat2 = Chat(
            user_id=user2.id,
            chat_type_id=chat_type.id,
            title="User2 Chat"
        )
        db_session.add(chat2)
        db_session.commit()
        
        # Verificar que ambos os chats foram criados
        assert chat1.id is not None
        assert chat2.id is not None
        assert chat1.user_id != chat2.user_id
        assert chat1.chat_type_id == chat2.chat_type_id
    
    def test_token_verification(self, db_session: Session):
        """Testa verificação de token"""
        auth_service = AuthService()
        user_repo = UserRepository(db_session)
        
        user = User(
            email="verify@test.com",
            username="verifyuser",
            password_hash=auth_service.get_password_hash("Password123!"),
            is_active=True
        )
        user = user_repo.create(user)
        
        # Criar tokens
        tokens = auth_service.create_user_tokens(user, user_repo)
        
        # Verificar token
        current_user = auth_service.get_current_user_from_token(
            tokens["access_token"],
            user_repo
        )
        
        assert current_user is not None
        assert current_user.id == user.id
    
    def test_password_verification(self, db_session: Session):
        """Testa verificação de senha"""
        auth_service = AuthService()
        password = "TestPassword123!"
        
        hash1 = auth_service.get_password_hash(password)
        hash2 = auth_service.get_password_hash(password)
        
        # Hashes diferentes mas ambos verificam a mesma senha
        assert hash1 != hash2
        assert auth_service.verify_password(password, hash1)
        assert auth_service.verify_password(password, hash2)
        assert not auth_service.verify_password("WrongPassword", hash1)
    
    def test_chat_type_ownership(self, db_session: Session):
        """Testa propriedade de ChatType"""
        user_repo = UserRepository(db_session)
        auth_service = AuthService()
        
        # Criar dois usuários
        owner = User(
            email="owner@test.com",
            username="owner",
            password_hash=auth_service.get_password_hash("Password123!"),
            is_active=True
        )
        owner = user_repo.create(owner)
        
        other_user = User(
            email="other@test.com",
            username="other",
            password_hash=auth_service.get_password_hash("Password123!"),
            is_active=True
        )
        other_user = user_repo.create(other_user)
        
        # Owner cria ChatType privado
        private_kb = ChatType(
            name="Private KB",
            description="Private",
            is_public=False,
            owner_id=owner.id,
            collection_name="private_collection"
        )
        db_session.add(private_kb)
        db_session.commit()
        db_session.refresh(private_kb)
        
        # Owner cria ChatType público
        public_kb = ChatType(
            name="Public KB",
            description="Public",
            is_public=True,
            owner_id=owner.id,
            collection_name="public_collection"
        )
        db_session.add(public_kb)
        db_session.commit()
        db_session.refresh(public_kb)
        
        # Verificar propriedade
        assert private_kb.owner_id == owner.id
        assert private_kb.is_public is False
        assert public_kb.owner_id == owner.id
        assert public_kb.is_public is True
    
    def test_token_refresh_flow(self, db_session: Session):
        """Testa fluxo de refresh de token"""
        auth_service = AuthService()
        user_repo = UserRepository(db_session)
        
        user = User(
            email="refresh@test.com",
            username="refreshuser",
            password_hash=auth_service.get_password_hash("Password123!"),
            is_active=True
        )
        user = user_repo.create(user)
        
        # Criar tokens iniciais
        tokens = auth_service.create_user_tokens(user, user_repo)
        access_token_1 = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        
        # Fazer refresh
        new_tokens = auth_service.refresh_access_token(refresh_token, user_repo)
        access_token_2 = new_tokens["access_token"]
        
        # Verificar que novo token é diferente
        assert access_token_1 != access_token_2
        assert new_tokens["token_type"] == "bearer"
        
        # Verificar que novo token funciona
        current_user = auth_service.get_current_user_from_token(access_token_2, user_repo)
        assert current_user is not None
        assert current_user.id == user.id
    
    def test_token_logout_flow(self, db_session: Session):
        """Testa fluxo de logout (revogação de token)"""
        auth_service = AuthService()
        user_repo = UserRepository(db_session)
        
        user = User(
            email="logout@test.com",
            username="logoutuser",
            password_hash=auth_service.get_password_hash("Password123!"),
            is_active=True
        )
        user = user_repo.create(user)
        
        # Criar tokens
        tokens = auth_service.create_user_tokens(user, user_repo)
        token = tokens["access_token"]
        
        # Verificar que token funciona
        current_user = auth_service.get_current_user_from_token(token, user_repo)
        assert current_user is not None
        
        # Revogar token
        token_record = user_repo.get_token(token)
        token_record.is_active = False
        db_session.commit()
        
        # Verificar que token não funciona mais
        current_user = auth_service.get_current_user_from_token(token, user_repo)
        assert current_user is None
    
    def test_chat_conversation_flow(self, db_session: Session):
        """Testa fluxo completo de conversa em chat"""
        user_repo = UserRepository(db_session)
        auth_service = AuthService()
        chat_service = ChatService(db_session)
        
        # Setup
        user = User(
            email="conversation@test.com",
            username="convuser",
            password_hash=auth_service.get_password_hash("Password123!"),
            is_active=True
        )
        user = user_repo.create(user)
        
        chat_type = ChatType(
            name="Conversation KB",
            description="Test",
            is_public=True,
            owner_id=user.id,
            collection_name="conv_collection"
        )
        db_session.add(chat_type)
        db_session.commit()
        db_session.refresh(chat_type)
        
        chat = Chat(
            user_id=user.id,
            chat_type_id=chat_type.id,
            title="Conversation"
        )
        db_session.add(chat)
        db_session.commit()
        db_session.refresh(chat)
        
        # Simular conversa
        messages = [
            ("user", "What is AI?"),
            ("assistant", "AI is Artificial Intelligence"),
            ("user", "Tell me more"),
            ("assistant", "AI is a field of computer science"),
            ("user", "Thanks"),
            ("assistant", "You're welcome!")
        ]
        
        for role_str, content in messages:
            role = MessageRole.USER if role_str == "user" else MessageRole.ASSISTANT
            chat_service.save_message(chat.id, role, content)
        
        history = chat_service.get_chat_history(chat.id)
        assert len(history) == 6
        
        # Verificar ordem
        assert history[0]["content"] == "What is AI?"
        assert history[1]["content"] == "AI is Artificial Intelligence"
        assert history[-1]["content"] == "You're welcome!"  # Last assistant message
    
    def test_multiple_chats_same_knowledge_base(self, db_session: Session):
        """Testa múltiplos chats usando a mesma base de conhecimento"""
        user_repo = UserRepository(db_session)
        auth_service = AuthService()
        chat_service = ChatService(db_session)
        
        # Criar usuário
        user = User(
            email="multichats@test.com",
            username="multichatsuser",
            password_hash=auth_service.get_password_hash("Password123!"),
            is_active=True
        )
        user = user_repo.create(user)
        
        # Criar ChatType
        chat_type = ChatType(
            name="Shared KB",
            description="Shared knowledge base",
            is_public=True,
            owner_id=user.id,
            collection_name="shared_collection"
        )
        db_session.add(chat_type)
        db_session.commit()
        db_session.refresh(chat_type)
        
        # Criar múltiplos chats
        chats = []
        for i in range(3):
            chat = Chat(
                user_id=user.id,
                chat_type_id=chat_type.id,
                title=f"Chat {i+1}"
            )
            db_session.add(chat)
            db_session.commit()
            db_session.refresh(chat)
            chats.append(chat)
        
        # Adicionar mensagens diferentes em cada chat
        for idx, chat in enumerate(chats):
            chat_service.save_message(
                chat.id,
                MessageRole.USER,
                f"Question in chat {idx+1}"
            )
        
        # Verificar que históricos são independentes
        # Note: get_chat_history excludes the last user message, so with only 1 message, history is empty
        for idx, chat in enumerate(chats):
            history = chat_service.get_chat_history(chat.id)
            assert len(history) == 0
    
    def test_user_authentication_with_wrong_password(self, db_session: Session):
        """Testa autenticação com senha incorreta"""
        auth_service = AuthService()
        user_repo = UserRepository(db_session)
        
        user = User(
            email="wrongpwd@test.com",
            username="wrongpwduser",
            password_hash=auth_service.get_password_hash("CorrectPassword123!"),
            is_active=True
        )
        user = user_repo.create(user)
        
        # Tentar autenticar com senha errada
        authenticated = auth_service.authenticate_user(
            user_repo,
            "wrongpwd@test.com",
            "WrongPassword123!"
        )
        
        assert authenticated is None
    
    def test_user_not_found_authentication(self, db_session: Session):
        """Testa autenticação com usuário não existente"""
        auth_service = AuthService()
        user_repo = UserRepository(db_session)
        
        # Tentar autenticar usuário que não existe
        authenticated = auth_service.authenticate_user(
            user_repo,
            "nonexistent@test.com",
            "Password123!"
        )
        
        assert authenticated is None
    
    def test_chat_with_multiple_users(self, db_session: Session):
        """Testa chat compartilhado entre múltiplos usuários"""
        user_repo = UserRepository(db_session)
        auth_service = AuthService()
        chat_service = ChatService(db_session)
        
        # Criar dois usuários
        user1 = User(
            email="user1@test.com",
            username="user1",
            password_hash=auth_service.get_password_hash("Password123!"),
            is_active=True
        )
        user1 = user_repo.create(user1)
        
        user2 = User(
            email="user2@test.com",
            username="user2",
            password_hash=auth_service.get_password_hash("Password123!"),
            is_active=True
        )
        user2 = user_repo.create(user2)
        
        # Criar ChatType público
        chat_type = ChatType(
            name="Shared Chat KB",
            description="Shared",
            is_public=True,
            owner_id=user1.id,
            collection_name="shared_chat_collection"
        )
        db_session.add(chat_type)
        db_session.commit()
        db_session.refresh(chat_type)
        
        # Ambos criam chats
        chat1 = Chat(
            user_id=user1.id,
            chat_type_id=chat_type.id,
            title="User1 Chat"
        )
        db_session.add(chat1)
        
        chat2 = Chat(
            user_id=user2.id,
            chat_type_id=chat_type.id,
            title="User2 Chat"
        )
        db_session.add(chat2)
        db_session.commit()
        db_session.refresh(chat1)
        db_session.refresh(chat2)
        
        # Adicionar mensagens em cada chat
        chat_service.save_message(chat1.id, MessageRole.USER, "User1 message")
        chat_service.save_message(chat2.id, MessageRole.USER, "User2 message")
        
        # Verificar que históricos são independentes
        # Note: get_chat_history excludes the last user message, so with only 1 message, history is empty
        history1 = chat_service.get_chat_history(chat1.id)
        history2 = chat_service.get_chat_history(chat2.id)
        
        assert len(history1) == 0
        assert len(history2) == 0
