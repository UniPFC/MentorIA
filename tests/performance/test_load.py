import pytest
import time
import json
from sqlalchemy.orm import Session
from src.services.auth import AuthService
from src.repositories.user import UserRepository
from src.services.chat import ChatService
from shared.database.models.user import User
from shared.database.models.chat_type import ChatType
from shared.database.models.chat import Chat
from shared.database.models.knowledge_chunk import KnowledgeChunk
from shared.database.models.message import MessageRole


@pytest.mark.performance
class TestPerformanceAndLoad:
    """Testes de performance e carga do sistema"""
    
    def test_bulk_user_creation_performance(self, db_session: Session):
        """Testa performance de criação em massa de usuários"""
        auth_service = AuthService()
        user_repo = UserRepository(db_session)
        
        num_users = 100
        start_time = time.time()
        
        # Criar múltiplos usuários
        for i in range(num_users):
            user = User(
                email=f"user{i}@test.com",
                username=f"user{i}",
                password_hash=auth_service.get_password_hash(f"Password{i}123!"),
                is_active=True
            )
            user_repo.create(user)
        
        elapsed_time = time.time() - start_time
        
        # Verificar que todos foram criados
        all_users = db_session.query(User).filter(
            User.email.like("user%@test.com")
        ).all()
        
        assert len(all_users) == num_users
        
        # Verificar performance (bcrypt é CPU-intensive, então limite é maior)
        avg_time_per_user = elapsed_time / num_users
        assert avg_time_per_user < 0.25, f"User creation too slow: {avg_time_per_user}s per user"
        
        print(f"\n✓ Created {num_users} users in {elapsed_time:.2f}s ({avg_time_per_user*1000:.2f}ms per user)")
    
    def test_bulk_knowledge_chunk_creation_performance(self, db_session: Session):
        """Testa performance de criação em massa de chunks de conhecimento"""
        auth_service = AuthService()
        user_repo = UserRepository(db_session)
        
        # Criar usuário e base de conhecimento
        user = User(
            email="chunks@test.com",
            username="chunksuser",
            password_hash=auth_service.get_password_hash("Password123!"),
            is_active=True
        )
        user = user_repo.create(user)
        
        kb = ChatType(
            name="Performance KB",
            description="KB for performance testing",
            is_public=True,
            owner_id=user.id,
            collection_name="perf_collection"
        )
        db_session.add(kb)
        db_session.commit()
        db_session.refresh(kb)
        
        # Criar múltiplos chunks
        num_chunks = 500
        start_time = time.time()
        
        for i in range(num_chunks):
            chunk = KnowledgeChunk(
                chat_type_id=kb.id,
                qdrant_point_id=f"chunk_{i}",
                source_file=f"file_{i}.txt",
                row_number=i,
                chunk_metadata=json.dumps({
                    "question": f"Question {i}",
                    "answer": f"Answer {i}",
                    "index": i
                })
            )
            db_session.add(chunk)
        
        db_session.commit()
        elapsed_time = time.time() - start_time
        
        # Verificar que todos foram criados
        all_chunks = db_session.query(KnowledgeChunk).filter(
            KnowledgeChunk.chat_type_id == kb.id
        ).all()
        
        assert len(all_chunks) == num_chunks
        
        # Verificar performance
        avg_time_per_chunk = elapsed_time / num_chunks
        assert avg_time_per_chunk < 0.01, f"Chunk creation too slow: {avg_time_per_chunk}s per chunk"
        
        print(f"\n✓ Created {num_chunks} chunks in {elapsed_time:.2f}s ({avg_time_per_chunk*1000:.2f}ms per chunk)")
    
    def test_bulk_message_creation_performance(self, db_session: Session):
        """Testa performance de criação em massa de mensagens"""
        auth_service = AuthService()
        user_repo = UserRepository(db_session)
        chat_service = ChatService(db_session)
        
        # Setup
        user = User(
            email="messages@test.com",
            username="messagesuser",
            password_hash=auth_service.get_password_hash("Password123!"),
            is_active=True
        )
        user = user_repo.create(user)
        
        kb = ChatType(
            name="Messages KB",
            description="KB for message testing",
            is_public=True,
            owner_id=user.id,
            collection_name="msg_collection"
        )
        db_session.add(kb)
        db_session.commit()
        db_session.refresh(kb)
        
        chat = Chat(
            user_id=user.id,
            chat_type_id=kb.id,
            title="Performance Chat"
        )
        db_session.add(chat)
        db_session.commit()
        db_session.refresh(chat)
        
        # Criar múltiplas mensagens
        num_messages = 1000
        start_time = time.time()
        
        for i in range(num_messages):
            role = MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT
            chat_service.save_message(
                chat.id,
                role,
                f"Message {i}: This is a test message with some content"
            )
        
        elapsed_time = time.time() - start_time
        
        # Verificar que todas foram criadas
        history = chat_service.get_chat_history(chat.id, limit=num_messages)
        assert len(history) == num_messages
        
        # Verificar performance
        avg_time_per_message = elapsed_time / num_messages
        assert avg_time_per_message < 0.01, f"Message creation too slow: {avg_time_per_message}s per message"
        
        print(f"\n✓ Created {num_messages} messages in {elapsed_time:.2f}s ({avg_time_per_message*1000:.2f}ms per message)")
    
    def test_chat_history_retrieval_performance(self, db_session: Session):
        """Testa performance de recuperação de histórico de chat"""
        auth_service = AuthService()
        user_repo = UserRepository(db_session)
        chat_service = ChatService(db_session)
        
        # Setup
        user = User(
            email="history@test.com",
            username="historyuser",
            password_hash=auth_service.get_password_hash("Password123!"),
            is_active=True
        )
        user = user_repo.create(user)
        
        kb = ChatType(
            name="History KB",
            description="KB for history testing",
            is_public=True,
            owner_id=user.id,
            collection_name="hist_collection"
        )
        db_session.add(kb)
        db_session.commit()
        db_session.refresh(kb)
        
        chat = Chat(
            user_id=user.id,
            chat_type_id=kb.id,
            title="History Chat"
        )
        db_session.add(chat)
        db_session.commit()
        db_session.refresh(chat)
        
        # Adicionar mensagens
        num_messages = 500
        for i in range(num_messages):
            role = MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT
            chat_service.save_message(chat.id, role, f"Message {i}")
        
        # Testar recuperação
        start_time = time.time()
        history = chat_service.get_chat_history(chat.id, limit=100)
        elapsed_time = time.time() - start_time
        
        assert len(history) == 100
        assert elapsed_time < 0.1, f"History retrieval too slow: {elapsed_time}s"
        
        print(f"\n✓ Retrieved 100 messages from {num_messages} in {elapsed_time*1000:.2f}ms")
    
    def test_authentication_performance(self, db_session: Session):
        """Testa performance de autenticação"""
        auth_service = AuthService()
        user_repo = UserRepository(db_session)
        
        # Criar usuário
        user = User(
            email="auth@test.com",
            username="authuser",
            password_hash=auth_service.get_password_hash("Password123!"),
            is_active=True
        )
        user = user_repo.create(user)
        
        # Testar autenticação múltiplas vezes
        num_attempts = 100
        start_time = time.time()
        
        for _ in range(num_attempts):
            authenticated = auth_service.authenticate_user(
                user_repo,
                "auth@test.com",
                "Password123!"
            )
            assert authenticated is not None
        
        elapsed_time = time.time() - start_time
        
        # Verificar performance (bcrypt é CPU-intensive)
        avg_time_per_auth = elapsed_time / num_attempts
        assert avg_time_per_auth < 0.25, f"Authentication too slow: {avg_time_per_auth}s per auth"
        
        print(f"\n✓ Completed {num_attempts} authentications in {elapsed_time:.2f}s ({avg_time_per_auth*1000:.2f}ms per auth)")
    
    def test_token_generation_performance(self, db_session: Session):
        """Testa performance de geração de tokens"""
        auth_service = AuthService()
        user_repo = UserRepository(db_session)
        
        # Testar geração de tokens múltiplas vezes com usuários diferentes
        num_tokens = 50
        start_time = time.time()
        
        for i in range(num_tokens):
            # Criar usuário único para cada token (evita constraint UNIQUE)
            user = User(
                email=f"tokens{i}@test.com",
                username=f"tokensuser{i}",
                password_hash=auth_service.get_password_hash("Password123!"),
                is_active=True
            )
            user = user_repo.create(user)
            
            tokens = auth_service.create_user_tokens(user, user_repo)
            assert "access_token" in tokens
            assert "refresh_token" in tokens
        
        elapsed_time = time.time() - start_time
        
        # Verificar performance
        avg_time_per_token = elapsed_time / num_tokens
        assert avg_time_per_token < 0.5, f"Token generation too slow: {avg_time_per_token}s per token"
        
        print(f"\n✓ Generated {num_tokens} token pairs in {elapsed_time:.2f}s ({avg_time_per_token*1000:.2f}ms per pair)")
    
    def test_concurrent_chat_operations(self, db_session: Session):
        """Testa operações concorrentes em múltiplos chats"""
        auth_service = AuthService()
        user_repo = UserRepository(db_session)
        chat_service = ChatService(db_session)
        
        # Criar usuário
        user = User(
            email="concurrent@test.com",
            username="concurrentuser",
            password_hash=auth_service.get_password_hash("Password123!"),
            is_active=True
        )
        user = user_repo.create(user)
        
        # Criar base de conhecimento
        kb = ChatType(
            name="Concurrent KB",
            description="KB for concurrent testing",
            is_public=True,
            owner_id=user.id,
            collection_name="concurrent_collection"
        )
        db_session.add(kb)
        db_session.commit()
        db_session.refresh(kb)
        
        # Criar múltiplos chats
        num_chats = 50
        chats = []
        
        for i in range(num_chats):
            chat = Chat(
                user_id=user.id,
                chat_type_id=kb.id,
                title=f"Chat {i}"
            )
            db_session.add(chat)
            db_session.commit()
            db_session.refresh(chat)
            chats.append(chat)
        
        # Adicionar mensagens a todos os chats
        start_time = time.time()
        
        for chat in chats:
            for j in range(10):
                role = MessageRole.USER if j % 2 == 0 else MessageRole.ASSISTANT
                chat_service.save_message(chat.id, role, f"Chat {chat.id} Message {j}")
        
        elapsed_time = time.time() - start_time
        
        # Verificar que todas as mensagens foram criadas
        total_messages = 0
        for chat in chats:
            history = chat_service.get_chat_history(chat.id)
            total_messages += len(history)
        
        assert total_messages == num_chats * 10
        
        # Verificar performance
        avg_time_per_operation = elapsed_time / (num_chats * 10)
        assert avg_time_per_operation < 0.01, f"Operations too slow: {avg_time_per_operation}s per operation"
        
        print(f"\n✓ Completed {num_chats * 10} operations across {num_chats} chats in {elapsed_time:.2f}s ({avg_time_per_operation*1000:.2f}ms per operation)")
