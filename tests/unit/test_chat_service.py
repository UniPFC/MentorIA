import pytest
from uuid import uuid4
from sqlalchemy.orm import Session
from src.services.chat import ChatService
from shared.database.models.message import Message, MessageRole
from shared.database.models.chat import Chat


@pytest.mark.unit
class TestChatService:
    def test_save_message_user(self, db_session: Session, sample_chat: Chat):
        chat_service = ChatService(db_session)
        
        message = chat_service.save_message(
            chat_id=sample_chat.id,
            role=MessageRole.USER,
            content="Hello, assistant!"
        )
        
        assert message.id is not None
        assert message.chat_id == sample_chat.id
        assert message.role == MessageRole.USER
        assert message.content == "Hello, assistant!"
        
    def test_save_message_assistant(self, db_session: Session, sample_chat: Chat):
        chat_service = ChatService(db_session)
        
        message = chat_service.save_message(
            chat_id=sample_chat.id,
            role=MessageRole.ASSISTANT,
            content="Hello, user!"
        )
        
        assert message.id is not None
        assert message.role == MessageRole.ASSISTANT
        assert message.content == "Hello, user!"
        
    def test_get_chat_history_empty(self, db_session: Session, sample_chat: Chat):
        chat_service = ChatService(db_session)
        
        history = chat_service.get_chat_history(sample_chat.id)
        
        assert isinstance(history, list)
        assert len(history) == 0
        
    def test_get_chat_history_with_messages(self, db_session: Session, sample_chat: Chat):
        chat_service = ChatService(db_session)
        
        chat_service.save_message(sample_chat.id, MessageRole.USER, "Message 1")
        chat_service.save_message(sample_chat.id, MessageRole.ASSISTANT, "Response 1")
        chat_service.save_message(sample_chat.id, MessageRole.USER, "Message 2")
        
        history = chat_service.get_chat_history(sample_chat.id, limit=10)
        
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Message 1"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "Response 1"
        
    def test_get_chat_history_limit(self, db_session: Session, sample_chat: Chat):
        chat_service = ChatService(db_session)
        
        for i in range(5):
            chat_service.save_message(sample_chat.id, MessageRole.USER, f"Message {i}")
            
        history = chat_service.get_chat_history(sample_chat.id, limit=3)
        
        assert len(history) == 3
        
    def test_get_chat_history_order(self, db_session: Session, sample_chat: Chat):
        chat_service = ChatService(db_session)
        
        chat_service.save_message(sample_chat.id, MessageRole.USER, "First")
        chat_service.save_message(sample_chat.id, MessageRole.ASSISTANT, "Second")
        chat_service.save_message(sample_chat.id, MessageRole.USER, "Third")

        history = chat_service.get_chat_history(sample_chat.id)

        # Last message is USER ("Third"), so it's excluded. Returns First and Second
        assert len(history) == 2
        assert history[0]["content"] == "First"
        assert history[1]["content"] == "Second"
    
    def test_save_message_error_handling(self, db_session: Session):
        from unittest.mock import patch
        chat_service = ChatService(db_session)
        
        with patch.object(db_session, 'commit', side_effect=Exception("Database error")):
            with pytest.raises(Exception, match="Database error"):
                chat_service.save_message(
                    chat_id=uuid4(),
                    role=MessageRole.USER,
                    content="Test"
                )
