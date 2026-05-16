import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException, status
from uuid import uuid4, UUID
from src.api.routes.chats import verify_chat_ownership


@pytest.mark.unit
class TestChatsRoutes:
    """Testes unitários para rotas de chats"""

    def test_verify_chat_ownership_success(self):
        """Testa verificação de propriedade de chat bem-sucedida"""
        chat_id = uuid4()
        user_id = uuid4()
        
        chat = Mock()
        chat.id = chat_id
        chat.user_id = user_id
        
        chat_repo = Mock()
        chat_repo.get_by_id.return_value = chat
        
        result = verify_chat_ownership(chat_id, user_id, chat_repo)
        
        assert result == chat
        chat_repo.get_by_id.assert_called_once_with(chat_id)

    def test_verify_chat_ownership_not_found(self):
        """Testa verificação quando chat não existe"""
        chat_id = uuid4()
        user_id = uuid4()
        
        chat_repo = Mock()
        chat_repo.get_by_id.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            verify_chat_ownership(chat_id, user_id, chat_repo)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in exc_info.value.detail

    def test_verify_chat_ownership_forbidden(self):
        """Testa verificação quando chat não pertence ao usuário"""
        chat_id = uuid4()
        user_id = uuid4()
        other_user_id = uuid4()
        
        chat = Mock()
        chat.id = chat_id
        chat.user_id = other_user_id  # Different user
        
        chat_repo = Mock()
        chat_repo.get_by_id.return_value = chat
        
        with pytest.raises(HTTPException) as exc_info:
            verify_chat_ownership(chat_id, user_id, chat_repo)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "permission" in exc_info.value.detail

    def test_verify_chat_ownership_different_ids(self):
        """Testa verificação com IDs diferentes"""
        chat_id = uuid4()
        user_id = uuid4()
        
        chat = Mock()
        chat.id = uuid4()  # Different ID
        chat.user_id = user_id
        
        chat_repo = Mock()
        chat_repo.get_by_id.return_value = chat
        
        result = verify_chat_ownership(chat_id, user_id, chat_repo)
        
        assert result == chat

    def test_create_chat_type_not_found(self):
        """Testa criação com chat type inexistente"""
        from src.api.routes.chats import create_chat
        
        chat_type_repo = Mock()
        chat_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()
        
        chat_type_repo.get_by_id.return_value = None
        
        chat_data = Mock()
        chat_data.chat_type_id = uuid4()
        chat_data.title = "Test"
        
        with pytest.raises(HTTPException) as exc_info:
            create_chat(
                chat_data=chat_data,
                current_user=current_user,
                chat_type_repo=chat_type_repo,
                chat_repo=chat_repo
            )
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    def test_create_chat_private_no_permission(self):
        """Testa criação com chat type privado sem permissão"""
        from src.api.routes.chats import create_chat
        
        chat_type_repo = Mock()
        chat_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()
        
        other_user_id = uuid4()
        chat_type = Mock()
        chat_type.id = uuid4()
        chat_type.is_public = False
        chat_type.owner_id = other_user_id
        
        chat_type_repo.get_by_id.return_value = chat_type
        
        chat_data = Mock()
        chat_data.chat_type_id = chat_type.id
        chat_data.title = "Test"
        
        with pytest.raises(HTTPException) as exc_info:
            create_chat(
                chat_data=chat_data,
                current_user=current_user,
                chat_type_repo=chat_type_repo,
                chat_repo=chat_repo
            )
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    def test_update_chat_model_invalid(self):
        """Testa update de modelo inválido"""
        from src.api.routes.chats import update_chat_model
        
        chat_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()
        
        chat = Mock()
        chat.id = uuid4()
        chat.user_id = current_user.id
        chat.llm_model = "gpt-4"
        chat.llm_provider = "openai"
        
        chat_repo.get_by_id.return_value = chat
        
        model_update = Mock()
        model_update.llm_model = "invalid-model"
        model_update.llm_provider = "invalid-provider"
        
        with patch('src.api.routes.chats.settings') as mock_settings:
            mock_settings.get_available_models.return_value = [
                {"model": "gpt-4", "provider": "openai"},
                {"model": "claude-3", "provider": "anthropic"}
            ]
            
            with pytest.raises(HTTPException) as exc_info:
                update_chat_model(
                    chat_id=chat.id,
                    model_update=model_update,
                    current_user=current_user,
                    chat_repo=chat_repo,
                    db=Mock()
                )
            
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_chat_model_success(self):
        """Testa update de modelo com sucesso"""
        from src.api.routes.chats import update_chat_model
        
        chat_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()
        
        chat = Mock()
        chat.id = uuid4()
        chat.user_id = current_user.id
        chat.llm_model = "gpt-4"
        chat.llm_provider = "openai"
        
        chat_repo.get_by_id.return_value = chat
        chat_repo.update.return_value = chat
        
        model_update = Mock()
        model_update.llm_model = "claude-3"
        model_update.llm_provider = "anthropic"
        
        with patch('src.api.routes.chats.settings') as mock_settings:
            mock_settings.get_available_models.return_value = [
                {"model": "gpt-4", "provider": "openai"},
                {"model": "claude-3", "provider": "anthropic"}
            ]
            
            result = update_chat_model(
                chat_id=chat.id,
                model_update=model_update,
                current_user=current_user,
                chat_repo=chat_repo,
                db=Mock()
            )
            
            assert result.llm_model == "claude-3"
            assert result.llm_provider == "anthropic"

    def test_get_available_models_success(self):
        """Testa listagem de modelos com sucesso"""
        from src.api.routes.chats import get_available_models
        
        with patch('src.api.routes.chats.settings') as mock_settings:
            mock_settings.LLM_MODEL = "gpt-4"
            mock_settings.LLM_PROVIDER = "openai"
            mock_settings.get_available_models.return_value = [
                {"model": "gpt-4", "provider": "openai", "description": "GPT-4"},
                {"model": "claude-3", "provider": "anthropic", "description": "Claude 3"}
            ]
            
            result = get_available_models(current_user=Mock())
            
            assert len(result.models) == 2
            assert result.current_default == "gpt-4 (openai)"

    def test_get_available_models_exception(self):
        """Testa listagem de modelos com exceção"""
        from src.api.routes.chats import get_available_models
        from fastapi import HTTPException
        
        with patch('src.api.routes.chats.settings') as mock_settings:
            mock_settings.LLM_MODEL = "gpt-4"
            mock_settings.LLM_PROVIDER = "openai"
            mock_settings.get_available_models.side_effect = Exception("Config error")
            
            with pytest.raises(HTTPException) as exc_info:
                get_available_models(current_user=Mock())
            
            assert exc_info.value.status_code == 500

    def test_create_chat_exception(self):
        """Testa criação de chat com exceção"""
        from src.api.routes.chats import create_chat
        from fastapi import HTTPException
        
        chat_type_repo = Mock()
        chat_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()
        
        chat_type = Mock()
        chat_type.id = uuid4()
        chat_type.is_public = True
        chat_type.owner_id = current_user.id
        
        chat_type_repo.get_by_id.return_value = chat_type
        chat_repo.count_by_user.side_effect = Exception("DB error")
        
        chat_data = Mock()
        chat_data.chat_type_id = chat_type.id
        chat_data.title = None
        
        with pytest.raises(HTTPException) as exc_info:
            create_chat(
                chat_data=chat_data,
                current_user=current_user,
                chat_type_repo=chat_type_repo,
                chat_repo=chat_repo
            )
        
        assert exc_info.value.status_code == 500

    def test_list_chats_exception(self):
        """Testa listagem de chats com exceção"""
        from src.api.routes.chats import list_chats
        from fastapi import HTTPException
        
        chat_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()
        
        chat_repo.get_by_user.side_effect = Exception("DB error")
        
        with pytest.raises(HTTPException) as exc_info:
            list_chats(
                chat_type_id=None,
                skip=0,
                limit=100,
                current_user=current_user,
                chat_repo=chat_repo
            )
        
        assert exc_info.value.status_code == 500

    def test_create_chat_with_title(self):
        """Testa criação de chat com título fornecido"""
        from src.api.routes.chats import create_chat
        from shared.database.models.chat import Chat
        from datetime import datetime, timezone
        
        chat_type_repo = Mock()
        chat_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()
        
        chat_type = Mock()
        chat_type.id = uuid4()
        chat_type.is_public = True
        chat_type.owner_id = current_user.id
        
        chat_type_repo.get_by_id.return_value = chat_type
        
        new_chat = Chat(
            id=uuid4(),
            user_id=current_user.id,
            chat_type_id=chat_type.id,
            title="Custom Title",
            title_auto_generated=False,
            llm_model="gpt-4",
            llm_provider="openai",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        chat_repo.create.return_value = new_chat
        
        chat_data = Mock()
        chat_data.chat_type_id = chat_type.id
        chat_data.title = "Custom Title"
        
        with patch('src.api.routes.chats.settings') as mock_settings:
            mock_settings.LLM_MODEL = "gpt-4"
            mock_settings.LLM_PROVIDER = "openai"
            
            result = create_chat(
                chat_data=chat_data,
                current_user=current_user,
                chat_type_repo=chat_type_repo,
                chat_repo=chat_repo
            )
            
            assert result.title == "Custom Title"
            assert result.title_auto_generated is False

    def test_create_chat_auto_title(self):
        """Testa criação de chat sem título (auto-generated)"""
        from src.api.routes.chats import create_chat
        from shared.database.models.chat import Chat
        from datetime import datetime, timezone
        
        chat_type_repo = Mock()
        chat_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()
        
        chat_type = Mock()
        chat_type.id = uuid4()
        chat_type.is_public = True
        chat_type.owner_id = current_user.id
        
        chat_type_repo.get_by_id.return_value = chat_type
        chat_repo.count_by_user.return_value = 0
        
        new_chat = Chat(
            id=uuid4(),
            user_id=current_user.id,
            chat_type_id=chat_type.id,
            title="Chat #1",
            title_auto_generated=True,
            llm_model="gpt-4",
            llm_provider="openai",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        chat_repo.create.return_value = new_chat
        
        chat_data = Mock()
        chat_data.chat_type_id = chat_type.id
        chat_data.title = None
        
        with patch('src.api.routes.chats.settings') as mock_settings:
            mock_settings.LLM_MODEL = "gpt-4"
            mock_settings.LLM_PROVIDER = "openai"
            
            result = create_chat(
                chat_data=chat_data,
                current_user=current_user,
                chat_type_repo=chat_type_repo,
                chat_repo=chat_repo
            )
            
            assert result.title == "Chat #1"
            assert result.title_auto_generated is True

    def test_list_chats_success(self):
        """Testa listagem de chats com sucesso"""
        from src.api.routes.chats import list_chats
        
        chat_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()
        
        chat_repo.get_by_user.return_value = []
        
        result = list_chats(
            chat_type_id=None,
            skip=0,
            limit=100,
            current_user=current_user,
            chat_repo=chat_repo
        )
        
        assert result == []
        chat_repo.get_by_user.assert_called_once_with(
            user_id=current_user.id,
            chat_type_id=None,
            skip=0,
            limit=100
        )

    def test_get_chat_success(self):
        """Testa obtenção de chat com sucesso"""
        from src.api.routes.chats import get_chat
        from shared.database.models.chat import Chat
        from datetime import datetime, timezone
        
        chat_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()
        
        chat = Chat(
            id=uuid4(),
            user_id=current_user.id,
            chat_type_id=uuid4(),
            title="Test Chat",
            title_auto_generated=False,
            llm_model="gpt-4",
            llm_provider="openai",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        chat.messages = []
        
        chat_repo.get_by_id.return_value = chat
        
        result = get_chat(
            chat_id=chat.id,
            current_user=current_user,
            chat_repo=chat_repo
        )
        
        assert result.id == chat.id

    def test_delete_chat_success(self):
        """Testa exclusão de chat com sucesso"""
        from src.api.routes.chats import delete_chat
        
        chat_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()
        
        chat = Mock()
        chat.id = uuid4()
        chat.user_id = current_user.id
        chat.title = "Test"
        
        chat_repo.get_by_id.return_value = chat
        
        result = delete_chat(
            chat_id=chat.id,
            current_user=current_user,
            chat_repo=chat_repo
        )
        
        chat_repo.delete.assert_called_once_with(chat)

    def test_delete_chat_forbidden(self):
        """Testa exclusão de chat de outro usuário (HTTPException path)"""
        from src.api.routes.chats import delete_chat
        from fastapi import HTTPException
        
        chat_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()
        
        other_user_id = uuid4()
        chat = Mock()
        chat.id = uuid4()
        chat.user_id = other_user_id
        chat.title = "Test"
        
        chat_repo.get_by_id.return_value = chat
        
        with pytest.raises(HTTPException) as exc_info:
            delete_chat(
                chat_id=chat.id,
                current_user=current_user,
                chat_repo=chat_repo
            )
        
        assert exc_info.value.status_code == 403

    def test_delete_chat_exception(self):
        """Testa exclusão de chat com exceção"""
        from src.api.routes.chats import delete_chat
        from fastapi import HTTPException
        
        chat_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()
        
        chat = Mock()
        chat.id = uuid4()
        chat.user_id = current_user.id
        chat.title = "Test"
        
        chat_repo.get_by_id.return_value = chat
        chat_repo.delete.side_effect = Exception("DB error")
        
        with pytest.raises(HTTPException) as exc_info:
            delete_chat(
                chat_id=chat.id,
                current_user=current_user,
                chat_repo=chat_repo
            )
        
        assert exc_info.value.status_code == 500

    def test_update_chat_model_exception(self):
        """Testa update de modelo com exceção"""
        from src.api.routes.chats import update_chat_model
        from fastapi import HTTPException
        
        chat_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()
        
        chat = Mock()
        chat.id = uuid4()
        chat.user_id = current_user.id
        chat.llm_model = "gpt-4"
        chat.llm_provider = "openai"
        
        chat_repo.get_by_id.return_value = chat
        chat_repo.update.side_effect = Exception("DB error")
        
        model_update = Mock()
        model_update.llm_model = "gpt-4"
        model_update.llm_provider = "openai"
        
        with patch('src.api.routes.chats.settings') as mock_settings:
            mock_settings.get_available_models.return_value = [
                {"model": "gpt-4", "provider": "openai"}
            ]
            
            with pytest.raises(HTTPException) as exc_info:
                update_chat_model(
                    chat_id=chat.id,
                    model_update=model_update,
                    current_user=current_user,
                    chat_repo=chat_repo,
                    db=Mock()
                )
            
            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """Testa envio de mensagem com sucesso"""
        from src.api.routes.chats import send_message
        from shared.database.models.chat import Chat
        from datetime import datetime, timezone
        
        chat_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()
        
        chat = Chat(
            id=uuid4(),
            user_id=current_user.id,
            chat_type_id=uuid4(),
            title="Test Chat",
            title_auto_generated=False,
            llm_model="gpt-4",
            llm_provider="openai",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        chat.messages = []
        
        chat_repo.get_by_id.return_value = chat
        
        message_data = Mock()
        message_data.content = "Hello"
        
        with patch('src.api.routes.chats.ChatService') as mock_chat_service, \
             patch('src.api.routes.chats.RAGPipeline') as mock_rag:
            
            chat_service = Mock()
            chat_service.save_message.return_value = Mock()
            chat_service.get_chat_history.return_value = []
            mock_chat_service.return_value = chat_service
            
            rag = Mock()
            rag.run.return_value = {
                "answer": "Hello back",
                "chunks": [{"question": "Q", "answer": "A", "score": 0.9}]
            }
            mock_rag.return_value = rag
            
            with patch('src.api.routes.chats.schedule_title_generation'):
                result = await send_message(
                    chat_id=chat.id,
                    message_data=message_data,
                    db=Mock(),
                    current_user=current_user,
                    chat_repo=chat_repo
                )
                
                assert result.chat is not None
                rag.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_exception(self):
        """Testa envio de mensagem com exceção genérica"""
        from src.api.routes.chats import send_message
        from shared.database.models.chat import Chat
        from datetime import datetime, timezone
        from fastapi import HTTPException
        
        chat_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()
        
        chat = Chat(
            id=uuid4(),
            user_id=current_user.id,
            chat_type_id=uuid4(),
            title="Test Chat",
            title_auto_generated=False,
            llm_model="gpt-4",
            llm_provider="openai",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        chat.messages = []
        
        chat_repo.get_by_id.return_value = chat
        
        message_data = Mock()
        message_data.content = "Hello"
        
        with patch('src.api.routes.chats.ChatService') as mock_chat_service:
            chat_service = Mock()
            chat_service.save_message.side_effect = Exception("DB error")
            mock_chat_service.return_value = chat_service
            
            with pytest.raises(HTTPException) as exc_info:
                await send_message(
                    chat_id=chat.id,
                    message_data=message_data,
                    db=Mock(),
                    current_user=current_user,
                    chat_repo=chat_repo
                )
            
            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_send_message_http_exception_raised(self):
        """Testa re-raise de HTTPException dentro de send_message"""
        from src.api.routes.chats import send_message
        from shared.database.models.chat import Chat
        from datetime import datetime, timezone
        from fastapi import HTTPException
        
        chat_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()
        
        chat = Chat(
            id=uuid4(),
            user_id=current_user.id,
            chat_type_id=uuid4(),
            title="Test Chat",
            title_auto_generated=False,
            llm_model="gpt-4",
            llm_provider="openai",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        chat.messages = []
        
        chat_repo.get_by_id.return_value = chat
        
        message_data = Mock()
        message_data.content = "Hello"
        
        with patch('src.api.routes.chats.ChatService') as mock_chat_service:
            chat_service = Mock()
            chat_service.get_chat_history.return_value = []
            chat_service.save_message.return_value = Mock()
            mock_chat_service.return_value = chat_service
            
            with patch('src.api.routes.chats.RAGPipeline') as mock_rag:
                rag = Mock()
                rag.run.side_effect = HTTPException(status_code=400, detail="Bad request")
                mock_rag.return_value = rag
                
                with pytest.raises(HTTPException) as exc_info:
                    await send_message(
                        chat_id=chat.id,
                        message_data=message_data,
                        db=Mock(),
                        current_user=current_user,
                        chat_repo=chat_repo
                    )
                
                assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_send_message_stream_success(self):
        """Testa envio de mensagem em streaming via instant response"""
        import asyncio
        from src.api.routes.chats import send_message_stream
        
        chat_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()
        
        chat = Mock()
        chat.id = uuid4()
        chat.user_id = current_user.id
        chat.chat_type_id = uuid4()
        chat.llm_model = "gpt-4"
        chat.llm_provider = "openai"
        
        chat_repo.get_by_id.return_value = chat
        
        message_data = Mock()
        message_data.content = "Hello"
        
        with patch('src.api.routes.chats.ChatService') as mock_chat_service, \
             patch('src.api.routes.chats.RAGPipeline') as mock_rag, \
             patch('src.api.routes.chats.InstantResponseService') as mock_instant:
            
            chat_service = Mock()
            chat_service.save_message.return_value = Mock()
            chat_service.get_chat_history.return_value = []
            mock_chat_service.return_value = chat_service
            
            # Return an instant response so it doesn't need to call run_stream
            mock_instant.get_instant_response.return_value = "Instant answer"
            
            rag = Mock()
            mock_rag.return_value = rag
            
            with patch('src.api.routes.chats.schedule_title_generation'):
                response = await send_message_stream(
                    chat_id=chat.id,
                    message_data=message_data,
                    db=Mock(),
                    current_user=current_user,
                    chat_repo=chat_repo
                )
                
                # Consume the generator to trigger the instant response path
                body = []
                async for chunk in response.body_iterator:
                    body.append(chunk)
                
                mock_instant.get_instant_response.assert_called_once_with("Hello")

    @pytest.mark.asyncio
    async def test_send_message_stream_run_stream(self):
        """Testa envio de mensagem em streaming via RAG run_stream"""
        from src.api.routes.chats import send_message_stream
        
        chat_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()
        
        chat = Mock()
        chat.id = uuid4()
        chat.user_id = current_user.id
        chat.chat_type_id = uuid4()
        chat.llm_model = "gpt-4"
        chat.llm_provider = "openai"
        
        chat_repo.get_by_id.return_value = chat
        
        message_data = Mock()
        message_data.content = "Hello"
        
        with patch('src.api.routes.chats.ChatService') as mock_chat_service, \
             patch('src.api.routes.chats.RAGPipeline') as mock_rag, \
             patch('src.api.routes.chats.InstantResponseService') as mock_instant, \
             patch('src.api.routes.chats.SessionLocal') as mock_session_local:
            
            chat_service = Mock()
            chat_service.save_message.return_value = Mock()
            chat_service.get_chat_history.return_value = []
            mock_chat_service.return_value = chat_service
            
            mock_instant.get_instant_response.return_value = None
            
            rag = Mock()
            rag.run_stream.return_value = [
                {"type": "token", "content": "Hello"},
                {"type": "sources", "content": [{"question": "Q", "answer": "A"}]}
            ]
            mock_rag.return_value = rag
            
            mock_session = Mock()
            mock_session_local.return_value = mock_session
            
            with patch('src.api.routes.chats.schedule_title_generation'):
                response = await send_message_stream(
                    chat_id=chat.id,
                    message_data=message_data,
                    db=Mock(),
                    current_user=current_user,
                    chat_repo=chat_repo
                )
                
                # Consume the generator to trigger run_stream
                body = []
                async for chunk in response.body_iterator:
                    body.append(chunk)
                
                rag.run_stream.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_stream_run_stream_error(self):
        """Testa envio de mensagem em streaming com erro no run_stream"""
        from src.api.routes.chats import send_message_stream
        
        chat_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()
        
        chat = Mock()
        chat.id = uuid4()
        chat.user_id = current_user.id
        chat.chat_type_id = uuid4()
        chat.llm_model = "gpt-4"
        chat.llm_provider = "openai"
        
        chat_repo.get_by_id.return_value = chat
        
        message_data = Mock()
        message_data.content = "Hello"
        
        with patch('src.api.routes.chats.ChatService') as mock_chat_service, \
             patch('src.api.routes.chats.RAGPipeline') as mock_rag, \
             patch('src.api.routes.chats.InstantResponseService') as mock_instant, \
             patch('src.api.routes.chats.SessionLocal') as mock_session_local:
            
            chat_service = Mock()
            chat_service.save_message.return_value = Mock()
            chat_service.get_chat_history.return_value = []
            mock_chat_service.return_value = chat_service
            
            mock_instant.get_instant_response.return_value = None
            
            rag = Mock()
            rag.run_stream.side_effect = Exception("RAG error")
            mock_rag.return_value = rag
            
            mock_session = Mock()
            mock_session_local.return_value = mock_session
            
            with patch('src.api.routes.chats.schedule_title_generation'):
                response = await send_message_stream(
                    chat_id=chat.id,
                    message_data=message_data,
                    db=Mock(),
                    current_user=current_user,
                    chat_repo=chat_repo
                )
                
                # Consume the generator to trigger error handling
                body = []
                async for chunk in response.body_iterator:
                    body.append(chunk)
                
                # Should have yielded error message
                assert len(body) > 0

    @pytest.mark.asyncio
    async def test_send_message_stream_empty_content(self):
        """Testa streaming quando run_stream retorna apenas sources (sem tokens)"""
        from src.api.routes.chats import send_message_stream
        
        chat_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()
        
        chat = Mock()
        chat.id = uuid4()
        chat.user_id = current_user.id
        chat.chat_type_id = uuid4()
        chat.llm_model = "gpt-4"
        chat.llm_provider = "openai"
        
        chat_repo.get_by_id.return_value = chat
        
        message_data = Mock()
        message_data.content = "Hello"
        
        with patch('src.api.routes.chats.ChatService') as mock_chat_service, \
             patch('src.api.routes.chats.RAGPipeline') as mock_rag, \
             patch('src.api.routes.chats.InstantResponseService') as mock_instant, \
             patch('src.api.routes.chats.SessionLocal') as mock_session_local:
            
            chat_service = Mock()
            chat_service.save_message.return_value = Mock()
            chat_service.get_chat_history.return_value = []
            mock_chat_service.return_value = chat_service
            
            mock_instant.get_instant_response.return_value = None
            
            rag = Mock()
            # Only sources, no tokens - triggers empty content fallback
            rag.run_stream.return_value = [
                {"type": "sources", "content": []}
            ]
            mock_rag.return_value = rag
            
            mock_session = Mock()
            mock_session_local.return_value = mock_session
            
            with patch('src.api.routes.chats.schedule_title_generation'):
                response = await send_message_stream(
                    chat_id=chat.id,
                    message_data=message_data,
                    db=Mock(),
                    current_user=current_user,
                    chat_repo=chat_repo
                )
                
                body = []
                async for chunk in response.body_iterator:
                    body.append(chunk)
                
                assert len(body) > 0

    @pytest.mark.asyncio
    async def test_send_message_stream_message_response(self):
        """Testa yield de message_response quando cliente permanece conectado"""
        from src.api.routes.chats import send_message_stream
        from shared.database.models.message import MessageRole
        
        chat_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()
        
        chat = Mock()
        chat.id = uuid4()
        chat.user_id = current_user.id
        chat.chat_type_id = uuid4()
        chat.llm_model = "gpt-4"
        chat.llm_provider = "openai"
        
        chat_repo.get_by_id.return_value = chat
        
        message_data = Mock()
        message_data.content = "Hello"
        
        with patch('src.api.routes.chats.ChatService') as mock_chat_service, \
             patch('src.api.routes.chats.RAGPipeline') as mock_rag, \
             patch('src.api.routes.chats.InstantResponseService') as mock_instant, \
             patch('src.api.routes.chats.SessionLocal') as mock_session_local:
            
            chat_service = Mock()
            
            # Create a proper mock message that can be validated
            mock_message = Mock()
            mock_message.id = uuid4()
            mock_message.chat_id = chat.id
            mock_message.role = MessageRole.ASSISTANT
            mock_message.content = "Hello back"
            mock_message.created_at = Mock()
            mock_message.model_dump_json.return_value = '{"id": "test", "content": "Hello back"}'
            
            chat_service.save_message.return_value = mock_message
            chat_service.get_chat_history.return_value = []
            mock_chat_service.return_value = chat_service
            
            mock_instant.get_instant_response.return_value = None
            
            rag = Mock()
            rag.run_stream.return_value = [
                {"type": "token", "content": "Hello"},
                {"type": "sources", "content": []}
            ]
            mock_rag.return_value = rag
            
            mock_session = Mock()
            mock_session_local.return_value = mock_session
            
            with patch('src.api.routes.chats.schedule_title_generation'):
                response = await send_message_stream(
                    chat_id=chat.id,
                    message_data=message_data,
                    db=Mock(),
                    current_user=current_user,
                    chat_repo=chat_repo
                )
                
                body = []
                async for chunk in response.body_iterator:
                    body.append(chunk)
                
                # Should have token, sources, and message chunks
                assert len(body) >= 3

    @pytest.mark.asyncio
    async def test_send_message_stream_generator_exit(self):
        """Testa GeneratorExit no caminho de instant_response (sem inner handler)"""
        from src.api.routes.chats import send_message_stream
        
        chat_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()
        
        chat = Mock()
        chat.id = uuid4()
        chat.user_id = current_user.id
        chat.chat_type_id = uuid4()
        chat.llm_model = "gpt-4"
        chat.llm_provider = "openai"
        
        chat_repo.get_by_id.return_value = chat
        
        message_data = Mock()
        message_data.content = "Hello"
        
        with patch('src.api.routes.chats.ChatService') as mock_chat_service, \
             patch('src.api.routes.chats.RAGPipeline') as mock_rag, \
             patch('src.api.routes.chats.InstantResponseService') as mock_instant, \
             patch('src.api.routes.chats.SessionLocal') as mock_session_local:
            
            chat_service = Mock()
            chat_service.save_message.return_value = Mock()
            chat_service.get_chat_history.return_value = []
            mock_chat_service.return_value = chat_service
            
            # Use instant_response so GeneratorExit propagates to outer handler
            mock_instant.get_instant_response.return_value = "Hi"
            
            rag = Mock()
            mock_rag.return_value = rag
            
            mock_session = Mock()
            mock_session_local.return_value = mock_session
            
            with patch('src.api.routes.chats.schedule_title_generation'):
                response = await send_message_stream(
                    chat_id=chat.id,
                    message_data=message_data,
                    db=Mock(),
                    current_user=current_user,
                    chat_repo=chat_repo
                )
                
                # Read first chunk then close to trigger GeneratorExit
                gen = response.body_iterator.__aiter__()
                chunk = await gen.__anext__()
                await gen.aclose()

    @pytest.mark.asyncio
    async def test_send_message_stream_error_save_fail(self):
        """Testa erro salvando resposta após exceção no run_stream"""
        from src.api.routes.chats import send_message_stream
        
        chat_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()
        
        chat = Mock()
        chat.id = uuid4()
        chat.user_id = current_user.id
        chat.chat_type_id = uuid4()
        chat.llm_model = "gpt-4"
        chat.llm_provider = "openai"
        
        chat_repo.get_by_id.return_value = chat
        
        message_data = Mock()
        message_data.content = "Hello"
        
        with patch('src.api.routes.chats.ChatService') as mock_chat_service, \
             patch('src.api.routes.chats.RAGPipeline') as mock_rag, \
             patch('src.api.routes.chats.InstantResponseService') as mock_instant, \
             patch('src.api.routes.chats.SessionLocal') as mock_session_local:
            
            chat_service = Mock()
            # Fail on calls inside the except block
            call_count = [0]
            def side_effect(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] >= 2:  # Inside except block
                    raise Exception("DB save failed")
                return Mock()
            
            chat_service.save_message.side_effect = side_effect
            chat_service.get_chat_history.return_value = []
            mock_chat_service.return_value = chat_service
            
            mock_instant.get_instant_response.return_value = None
            
            def bad_generator():
                yield {"type": "token", "content": "H"}
                raise Exception("RAG error")
            
            rag = Mock()
            rag.run_stream.return_value = bad_generator()
            mock_rag.return_value = rag
            
            mock_session = Mock()
            mock_session_local.return_value = mock_session
            
            with patch('src.api.routes.chats.schedule_title_generation'):
                response = await send_message_stream(
                    chat_id=chat.id,
                    message_data=message_data,
                    db=Mock(),
                    current_user=current_user,
                    chat_repo=chat_repo
                )
                
                body = []
                async for chunk in response.body_iterator:
                    body.append(chunk)
                
                # Should have token and error chunks
                assert len(body) > 0
