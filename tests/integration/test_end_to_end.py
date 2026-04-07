import pytest
from sqlalchemy.orm import Session
from src.services.auth import AuthService
from src.repositories.user import UserRepository
from src.services.chat import ChatService
from shared.database.models.user import User
from shared.database.models.chat_type import ChatType
from shared.database.models.chat import Chat
from shared.database.models.knowledge_chunk import KnowledgeChunk
from shared.database.models.message import MessageRole


@pytest.mark.integration
class TestEndToEnd:
    """Testes end-to-end para fluxos completos do sistema"""
    
    def test_complete_user_journey(self, db_session: Session):
        """
        Testa jornada completa do usuário:
        1. Registro de novo usuário
        2. Autenticação
        3. Criação de base de conhecimento
        4. Adição de chunks de conhecimento
        5. Criação de chat
        6. Conversa com histórico
        7. Refresh de token
        8. Logout
        """
        auth_service = AuthService()
        user_repo = UserRepository(db_session)
        chat_service = ChatService(db_session)
        
        # ========== PASSO 1: Registro de novo usuário ==========
        email = "newuser@example.com"
        username = "newuser"
        password = "SecurePassword123!"
        
        new_user = User(
            email=email,
            username=username,
            password_hash=auth_service.get_password_hash(password),
            is_active=True
        )
        user = user_repo.create(new_user)
        
        assert user.id is not None
        assert user.email == email
        assert user.is_active is True
        
        # ========== PASSO 2: Autenticação ==========
        authenticated_user = auth_service.authenticate_user(user_repo, email, password)
        
        assert authenticated_user is not None
        assert authenticated_user.id == user.id
        
        # ========== PASSO 3: Criação de base de conhecimento ==========
        knowledge_base = ChatType(
            name="AI Knowledge Base",
            description="Complete AI and ML knowledge base",
            is_public=True,
            owner_id=user.id,
            collection_name="ai_kb_collection"
        )
        db_session.add(knowledge_base)
        db_session.commit()
        db_session.refresh(knowledge_base)
        
        assert knowledge_base.id is not None
        assert knowledge_base.owner_id == user.id
        
        # ========== PASSO 4: Adição de chunks de conhecimento ==========
        import json
        knowledge_chunks = [
            KnowledgeChunk(
                chat_type_id=knowledge_base.id,
                qdrant_point_id="chunk_1",
                source_file="ai_basics.txt",
                row_number=1,
                chunk_metadata=json.dumps({"question": "What is AI?", "answer": "AI is the simulation of human intelligence", "category": "fundamentals"})
            ),
            KnowledgeChunk(
                chat_type_id=knowledge_base.id,
                qdrant_point_id="chunk_2",
                source_file="ml_basics.txt",
                row_number=1,
                chunk_metadata=json.dumps({"question": "What is ML?", "answer": "ML is a subset of AI", "category": "fundamentals"})
            ),
            KnowledgeChunk(
                chat_type_id=knowledge_base.id,
                qdrant_point_id="chunk_3",
                source_file="dl_basics.txt",
                row_number=1,
                chunk_metadata=json.dumps({"question": "What is DL?", "answer": "DL uses neural networks", "category": "advanced"})
            ),
        ]
        
        for chunk in knowledge_chunks:
            db_session.add(chunk)
        db_session.commit()
        
        # Verificar chunks foram salvos
        saved_chunks = db_session.query(KnowledgeChunk).filter(
            KnowledgeChunk.chat_type_id == knowledge_base.id
        ).all()
        assert len(saved_chunks) == 3
        
        # ========== PASSO 5: Criação de chat ==========
        chat = Chat(
            user_id=user.id,
            chat_type_id=knowledge_base.id,
            title="AI Learning Session"
        )
        db_session.add(chat)
        db_session.commit()
        db_session.refresh(chat)
        
        assert chat.id is not None
        assert chat.user_id == user.id
        assert chat.chat_type_id == knowledge_base.id
        
        # ========== PASSO 6: Conversa com histórico ==========
        conversation = [
            ("user", "Hello, I want to learn about AI"),
            ("assistant", "Great! I can help you learn about AI. What would you like to know?"),
            ("user", "What is the difference between AI and ML?"),
            ("assistant", "AI is broader - it includes all intelligent systems. ML is a subset that learns from data."),
            ("user", "What about Deep Learning?"),
            ("assistant", "Deep Learning uses neural networks with multiple layers for complex pattern recognition."),
            ("user", "Thank you for the explanation"),
            ("assistant", "You're welcome! Feel free to ask more questions anytime."),
        ]
        
        for role_str, content in conversation:
            role = MessageRole.USER if role_str == "user" else MessageRole.ASSISTANT
            chat_service.save_message(chat.id, role, content)
        
        # Verificar histórico
        history = chat_service.get_chat_history(chat.id)
        assert len(history) == 8
        assert history[0]["content"] == "Hello, I want to learn about AI"
        assert history[-1]["content"] == "You're welcome! Feel free to ask more questions anytime."
        
        # ========== PASSO 7: Geração de tokens ==========
        tokens = auth_service.create_user_tokens(user, user_repo)
        
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
        
        # Verificar que token funciona
        current_user = auth_service.get_current_user_from_token(tokens["access_token"], user_repo)
        assert current_user is not None
        assert current_user.id == user.id
        
        # ========== PASSO 8: Refresh de token ==========
        new_tokens = auth_service.refresh_access_token(tokens["refresh_token"], user_repo)
        
        assert new_tokens is not None
        assert new_tokens["access_token"] != tokens["access_token"]
        
        # Verificar novo token funciona
        current_user = auth_service.get_current_user_from_token(new_tokens["access_token"], user_repo)
        assert current_user is not None
        assert current_user.id == user.id
        
        # ========== PASSO 9: Logout ==========
        token_record = user_repo.get_token(new_tokens["access_token"])
        token_record.is_active = False
        db_session.commit()
        
        # Verificar que token não funciona mais
        current_user = auth_service.get_current_user_from_token(new_tokens["access_token"], user_repo)
        assert current_user is None
    
    def test_multi_user_knowledge_sharing(self, db_session: Session):
        """
        Testa compartilhamento de base de conhecimento entre múltiplos usuários:
        1. Usuário A cria base de conhecimento pública
        2. Usuário A adiciona chunks
        3. Usuário B acessa a mesma base
        4. Ambos criam chats independentes
        5. Conversas são isoladas
        """
        auth_service = AuthService()
        user_repo = UserRepository(db_session)
        chat_service = ChatService(db_session)
        
        # ========== PASSO 1: Criar dois usuários ==========
        user_a = User(
            email="usera@example.com",
            username="usera",
            password_hash=auth_service.get_password_hash("Password123!"),
            is_active=True
        )
        user_a = user_repo.create(user_a)
        
        user_b = User(
            email="userb@example.com",
            username="userb",
            password_hash=auth_service.get_password_hash("Password123!"),
            is_active=True
        )
        user_b = user_repo.create(user_b)
        
        # ========== PASSO 2: Usuário A cria base pública ==========
        shared_kb = ChatType(
            name="Shared Knowledge Base",
            description="Public knowledge base for all users",
            is_public=True,
            owner_id=user_a.id,
            collection_name="shared_kb_collection"
        )
        db_session.add(shared_kb)
        db_session.commit()
        db_session.refresh(shared_kb)
        
        # ========== PASSO 3: Usuário A adiciona chunks ==========
        import json
        chunks = [
            KnowledgeChunk(
                chat_type_id=shared_kb.id,
                qdrant_point_id="shared_chunk_1",
                source_file="shared_data.txt",
                row_number=1,
                chunk_metadata=json.dumps({"question": "Question 1", "answer": "Answer 1 from User A", "author": "user_a"})
            ),
            KnowledgeChunk(
                chat_type_id=shared_kb.id,
                qdrant_point_id="shared_chunk_2",
                source_file="shared_data.txt",
                row_number=2,
                chunk_metadata=json.dumps({"question": "Question 2", "answer": "Answer 2 from User A", "author": "user_a"})
            ),
        ]
        
        for chunk in chunks:
            db_session.add(chunk)
        db_session.commit()
        
        # ========== PASSO 4: Ambos criam chats ==========
        chat_a = Chat(
            user_id=user_a.id,
            chat_type_id=shared_kb.id,
            title="User A Chat"
        )
        db_session.add(chat_a)
        
        chat_b = Chat(
            user_id=user_b.id,
            chat_type_id=shared_kb.id,
            title="User B Chat"
        )
        db_session.add(chat_b)
        db_session.commit()
        db_session.refresh(chat_a)
        db_session.refresh(chat_b)
        
        # ========== PASSO 5: Conversas independentes ==========
        # User A conversation
        chat_service.save_message(chat_a.id, MessageRole.USER, "User A question")
        chat_service.save_message(chat_a.id, MessageRole.ASSISTANT, "User A answer")
        
        # User B conversation
        chat_service.save_message(chat_b.id, MessageRole.USER, "User B question")
        chat_service.save_message(chat_b.id, MessageRole.ASSISTANT, "User B answer")
        
        # Verificar isolamento
        history_a = chat_service.get_chat_history(chat_a.id)
        history_b = chat_service.get_chat_history(chat_b.id)
        
        assert len(history_a) == 2
        assert len(history_b) == 2
        assert "User A question" in history_a[0]["content"]
        assert "User B question" in history_b[0]["content"]
        assert "User A question" not in history_b[0]["content"]
        assert "User B question" not in history_a[0]["content"]
    
    def test_knowledge_base_with_metadata(self, db_session: Session):
        """
        Testa base de conhecimento com metadados:
        1. Criar base com múltiplos chunks
        2. Cada chunk tem metadados diferentes
        3. Recuperar chunks com filtros
        """
        auth_service = AuthService()
        user_repo = UserRepository(db_session)
        
        # Criar usuário
        user = User(
            email="metadata@example.com",
            username="metadatauser",
            password_hash=auth_service.get_password_hash("Password123!"),
            is_active=True
        )
        user = user_repo.create(user)
        
        # Criar base de conhecimento
        kb = ChatType(
            name="Metadata KB",
            description="KB with rich metadata",
            is_public=True,
            owner_id=user.id,
            collection_name="metadata_collection"
        )
        db_session.add(kb)
        db_session.commit()
        db_session.refresh(kb)
        
        # Adicionar chunks com diferentes metadados
        import json
        chunks_data = [
            {
                "qdrant_id": "meta_chunk_1",
                "file": "python.txt",
                "row": 1,
                "metadata": {"question": "Python basics", "answer": "Python is a programming language", "language": "python", "level": "beginner", "category": "programming"}
            },
            {
                "qdrant_id": "meta_chunk_2",
                "file": "python.txt",
                "row": 2,
                "metadata": {"question": "Python advanced", "answer": "Advanced Python features include decorators and metaclasses", "language": "python", "level": "advanced", "category": "programming"}
            },
            {
                "qdrant_id": "meta_chunk_3",
                "file": "javascript.txt",
                "row": 1,
                "metadata": {"question": "JavaScript basics", "answer": "JavaScript is a web programming language", "language": "javascript", "level": "beginner", "category": "web"}
            },
            {
                "qdrant_id": "meta_chunk_4",
                "file": "datascience.txt",
                "row": 1,
                "metadata": {"question": "Data Science", "answer": "Data Science uses statistics and ML", "language": "python", "level": "advanced", "category": "data_science"}
            },
        ]
        
        for data in chunks_data:
            chunk = KnowledgeChunk(
                chat_type_id=kb.id,
                qdrant_point_id=data["qdrant_id"],
                source_file=data["file"],
                row_number=data["row"],
                chunk_metadata=json.dumps(data["metadata"])
            )
            db_session.add(chunk)
        db_session.commit()
        
        # Verificar chunks foram salvos
        all_chunks = db_session.query(KnowledgeChunk).filter(
            KnowledgeChunk.chat_type_id == kb.id
        ).all()
        
        assert len(all_chunks) == 4
        
        # Verificar metadados
        python_chunks = [c for c in all_chunks if json.loads(c.chunk_metadata).get("language") == "python"]
        assert len(python_chunks) == 3
        
        beginner_chunks = [c for c in all_chunks if json.loads(c.chunk_metadata).get("level") == "beginner"]
        assert len(beginner_chunks) == 2
        
        advanced_chunks = [c for c in all_chunks if json.loads(c.chunk_metadata).get("level") == "advanced"]
        assert len(advanced_chunks) == 2
