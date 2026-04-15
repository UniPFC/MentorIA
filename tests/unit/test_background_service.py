import pytest
from unittest.mock import MagicMock, patch, mock_open
from uuid import uuid4
from sqlalchemy.orm import Session
from src.services.background import (
    process_ingestion_job,
    _load_title_generation_prompt,
    _generate_chat_title_internal,
    generate_chat_title_background,
    schedule_title_generation
)
from shared.database.models.ingestion_job import IngestionJob, IngestionStatus
from shared.database.models.chat import Chat
from shared.database.models.message import Message, MessageRole
from src.api.schemas.title_generation import ChatTitleResponse


@pytest.mark.unit
class TestBackgroundService:
    @pytest.fixture
    def mock_db(self):
        return MagicMock(spec=Session)
    
    @pytest.fixture
    def mock_ingestion_service(self):
        service = MagicMock()
        service.parse_spreadsheet.return_value = [
            {"question": "Q1", "answer": "A1"},
            {"question": "Q2", "answer": "A2"}
        ]
        service.ingest_chunks.return_value = (["point1", "point2"], 2)
        return service
    
    @pytest.fixture
    def mock_job(self):
        job = MagicMock(spec=IngestionJob)
        job.id = uuid4()
        job.status = IngestionStatus.PENDING
        job.total_chunks = 0
        job.processed_chunks = 0
        return job
    
    def test_process_ingestion_job_not_found(self, mock_db, mock_ingestion_service):
        job_id = uuid4()
        chat_type_id = uuid4()
        
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        process_ingestion_job(
            job_id=job_id,
            chat_type_id=chat_type_id,
            file_content=b"test",
            filename="test.xlsx",
            question_col="question",
            answer_col="answer",
            ingestion_service=mock_ingestion_service,
            db=mock_db
        )
        
        mock_db.commit.assert_not_called()
    
    def test_process_ingestion_job_success(self, mock_db, mock_ingestion_service, mock_job):
        job_id = uuid4()
        chat_type_id = uuid4()
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_job
        
        process_ingestion_job(
            job_id=job_id,
            chat_type_id=chat_type_id,
            file_content=b"test content",
            filename="test.xlsx",
            question_col="question",
            answer_col="answer",
            ingestion_service=mock_ingestion_service,
            db=mock_db
        )
        
        assert mock_job.status == IngestionStatus.COMPLETED
        assert mock_job.total_chunks == 2
        assert mock_job.processed_chunks == 2
        assert mock_job.started_at is not None
        assert mock_job.completed_at is not None
        assert mock_db.commit.call_count >= 3
        
        mock_ingestion_service.parse_spreadsheet.assert_called_once_with(
            b"test content", "test.xlsx", "question", "answer"
        )
        mock_ingestion_service.ingest_chunks.assert_called_once()
    
    def test_process_ingestion_job_parse_error(self, mock_db, mock_ingestion_service, mock_job):
        job_id = uuid4()
        chat_type_id = uuid4()
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_job
        mock_ingestion_service.parse_spreadsheet.side_effect = Exception("Parse error")
        
        process_ingestion_job(
            job_id=job_id,
            chat_type_id=chat_type_id,
            file_content=b"test",
            filename="test.xlsx",
            question_col="question",
            answer_col="answer",
            ingestion_service=mock_ingestion_service,
            db=mock_db
        )
        
        assert mock_job.status == IngestionStatus.FAILED
        assert mock_job.error_message == "Parse error"
        assert mock_job.completed_at is not None
    
    def test_process_ingestion_job_ingest_error(self, mock_db, mock_ingestion_service, mock_job):
        job_id = uuid4()
        chat_type_id = uuid4()
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_job
        mock_ingestion_service.ingest_chunks.side_effect = Exception("Ingest error")
        
        process_ingestion_job(
            job_id=job_id,
            chat_type_id=chat_type_id,
            file_content=b"test",
            filename="test.xlsx",
            question_col="question",
            answer_col="answer",
            ingestion_service=mock_ingestion_service,
            db=mock_db
        )
        
        assert mock_job.status == IngestionStatus.FAILED
        assert mock_job.error_message == "Ingest error"
        assert mock_job.completed_at is not None
    
    def test_process_ingestion_job_sets_processing_status(self, mock_db, mock_ingestion_service, mock_job):
        job_id = uuid4()
        chat_type_id = uuid4()
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_job
        
        process_ingestion_job(
            job_id=job_id,
            chat_type_id=chat_type_id,
            file_content=b"test",
            filename="test.xlsx",
            question_col="question",
            answer_col="answer",
            ingestion_service=mock_ingestion_service,
            db=mock_db
        )
        
        assert mock_job.status == IngestionStatus.COMPLETED
        assert mock_job.started_at is not None
    
    def test_load_title_generation_prompt_system(self):
        """Test loading system prompt"""
        mock_content = "You are a helpful assistant that generates chat titles."
        
        with patch("builtins.open", mock_open(read_data=mock_content)):
            with patch("pathlib.Path.exists", return_value=True):
                result = _load_title_generation_prompt(system=True)
                assert result == mock_content
    
    def test_load_title_generation_prompt_user(self):
        """Test loading user prompt"""
        mock_content = "Generate a title for: {user_question} {assistant_response}"
        
        with patch("builtins.open", mock_open(read_data=mock_content)):
            with patch("pathlib.Path.exists", return_value=True):
                result = _load_title_generation_prompt(system=False)
                assert result == mock_content
    
    def test_generate_chat_title_internal_chat_not_found(self, mock_db):
        """Test title generation when chat doesn't exist"""
        chat_id = uuid4()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = _generate_chat_title_internal(chat_id, mock_db)
        
        assert result is False
        mock_db.commit.assert_not_called()
    
    def test_generate_chat_title_internal_not_auto_generated(self, mock_db):
        """Test title generation when chat has manual title"""
        chat_id = uuid4()
        mock_chat = MagicMock(spec=Chat)
        mock_chat.id = chat_id
        mock_chat.title_auto_generated = False
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_chat
        
        result = _generate_chat_title_internal(chat_id, mock_db)
        
        assert result is False
        mock_db.commit.assert_not_called()
    
    def test_generate_chat_title_internal_no_user_message(self, mock_db):
        """Test title generation when no user message exists"""
        chat_id = uuid4()
        mock_chat = MagicMock(spec=Chat)
        mock_chat.id = chat_id
        mock_chat.title_auto_generated = True
        
        def query_side_effect(*args):
            mock_query = MagicMock()
            if args[0] == Chat:
                mock_query.filter.return_value.first.return_value = mock_chat
            else:  # Message query
                mock_query.filter.return_value.filter.return_value.order_by.return_value.first.return_value = None
            return mock_query
        
        mock_db.query.side_effect = query_side_effect
        
        result = _generate_chat_title_internal(chat_id, mock_db)
        
        assert result is False
    
    @patch("src.services.background._load_title_generation_prompt")
    @patch("src.services.background.Provider")
    def test_generate_chat_title_internal_success(self, mock_provider_class, mock_load_prompt, mock_db):
        """Test successful title generation"""
        chat_id = uuid4()
        mock_chat = MagicMock(spec=Chat)
        mock_chat.id = chat_id
        mock_chat.title_auto_generated = True
        mock_chat.title = "Auto-generated"
        
        mock_user_msg = MagicMock(spec=Message)
        mock_user_msg.content = "What is AI?"
        mock_user_msg.role = MessageRole.USER
        
        mock_assistant_msg = MagicMock(spec=Message)
        mock_assistant_msg.content = "AI is Artificial Intelligence"
        mock_assistant_msg.role = MessageRole.ASSISTANT
        
        def query_side_effect(*args):
            mock_query = MagicMock()
            if args[0] == Chat:
                mock_query.filter.return_value.first.return_value = mock_chat
            elif args[0] == Message:
                # First call returns user message, second returns assistant message
                filter_mock = mock_query.filter.return_value.filter.return_value
                order_mock = filter_mock.order_by.return_value
                if not hasattr(query_side_effect, 'call_count'):
                    query_side_effect.call_count = 0
                query_side_effect.call_count += 1
                if query_side_effect.call_count == 1:
                    order_mock.first.return_value = mock_user_msg
                else:
                    order_mock.first.return_value = mock_assistant_msg
            return mock_query
        
        mock_db.query.side_effect = query_side_effect
        
        mock_load_prompt.side_effect = [
            "System prompt: Generate titles",
            "User prompt: {user_question} {assistant_response}"
        ]
        
        mock_provider = MagicMock()
        mock_title_response = ChatTitleResponse(title="Introduction to AI")
        mock_provider.generate_structured.return_value = mock_title_response
        mock_provider_class.return_value = mock_provider
        
        result = _generate_chat_title_internal(chat_id, mock_db)
        
        assert result is True
        assert mock_chat.title == "Introduction to AI"
        assert mock_chat.title_auto_generated is False
        mock_db.commit.assert_called()
    
    @patch("src.services.background._load_title_generation_prompt")
    @patch("src.services.background.Provider")
    def test_generate_chat_title_internal_fallback_string_response(self, mock_provider_class, mock_load_prompt, mock_db):
        """Test title generation with string fallback"""
        chat_id = uuid4()
        mock_chat = MagicMock(spec=Chat)
        mock_chat.id = chat_id
        mock_chat.title_auto_generated = True
        
        mock_user_msg = MagicMock(spec=Message)
        mock_user_msg.content = "Hello"
        
        mock_assistant_msg = MagicMock(spec=Message)
        mock_assistant_msg.content = "Hi there!"
        
        def query_side_effect(*args):
            mock_query = MagicMock()
            if args[0] == Chat:
                mock_query.filter.return_value.first.return_value = mock_chat
            elif args[0] == Message:
                filter_mock = mock_query.filter.return_value.filter.return_value
                order_mock = filter_mock.order_by.return_value
                if not hasattr(query_side_effect, 'msg_count'):
                    query_side_effect.msg_count = 0
                query_side_effect.msg_count += 1
                if query_side_effect.msg_count == 1:
                    order_mock.first.return_value = mock_user_msg
                else:
                    order_mock.first.return_value = mock_assistant_msg
            return mock_query
        
        mock_db.query.side_effect = query_side_effect
        mock_load_prompt.side_effect = ["System", "User: {user_question} {assistant_response}"]
        
        mock_provider = MagicMock()
        mock_provider.generate_structured.return_value = '"Greeting Conversation"'
        mock_provider_class.return_value = mock_provider
        
        result = _generate_chat_title_internal(chat_id, mock_db)
        
        assert result is True
        assert mock_chat.title == "Greeting Conversation"
    
    @patch("src.services.background._load_title_generation_prompt")
    @patch("src.services.background.Provider")
    def test_generate_chat_title_internal_empty_title(self, mock_provider_class, mock_load_prompt, mock_db):
        """Test title generation returns empty title"""
        chat_id = uuid4()
        mock_chat = MagicMock(spec=Chat)
        mock_chat.id = chat_id
        mock_chat.title_auto_generated = True
        
        mock_user_msg = MagicMock(spec=Message)
        mock_user_msg.content = "Test"
        
        def query_side_effect(*args):
            mock_query = MagicMock()
            if args[0] == Chat:
                mock_query.filter.return_value.first.return_value = mock_chat
            elif args[0] == Message:
                filter_mock = mock_query.filter.return_value.filter.return_value
                order_mock = filter_mock.order_by.return_value
                order_mock.first.return_value = mock_user_msg
            return mock_query
        
        mock_db.query.side_effect = query_side_effect
        mock_load_prompt.side_effect = ["System", "User: {user_question} {assistant_response}"]
        
        mock_provider = MagicMock()
        mock_response = MagicMock()
        mock_response.__str__ = MagicMock(return_value="")
        mock_provider.generate_structured.return_value = mock_response
        mock_provider_class.return_value = mock_provider
        
        result = _generate_chat_title_internal(chat_id, mock_db)
        
        assert result is False
        mock_db.commit.assert_not_called()
    
    @patch("src.services.background._load_title_generation_prompt")
    @patch("src.services.background.Provider")
    def test_generate_chat_title_internal_exception(self, mock_provider_class, mock_load_prompt, mock_db):
        """Test title generation handles exceptions"""
        chat_id = uuid4()
        mock_chat = MagicMock(spec=Chat)
        mock_chat.id = chat_id
        mock_chat.title_auto_generated = True
        
        mock_user_msg = MagicMock(spec=Message)
        mock_user_msg.content = "Test"
        
        def query_side_effect(*args):
            mock_query = MagicMock()
            if args[0] == Chat:
                mock_query.filter.return_value.first.return_value = mock_chat
            elif args[0] == Message:
                filter_mock = mock_query.filter.return_value.filter.return_value
                order_mock = filter_mock.order_by.return_value
                order_mock.first.return_value = mock_user_msg
            return mock_query
        
        mock_db.query.side_effect = query_side_effect
        mock_load_prompt.side_effect = Exception("LLM Error")
        
        result = _generate_chat_title_internal(chat_id, mock_db)
        
        assert result is False
        mock_db.rollback.assert_called()
    
    @patch("src.services.background.SessionLocal")
    @patch("src.services.background._generate_chat_title_internal")
    @patch("src.services.background.threading.Thread")
    def test_generate_chat_title_background(self, mock_thread_class, mock_generate_internal, mock_session_local):
        """Test background title generation thread creation"""
        chat_id = uuid4()
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        mock_generate_internal.return_value = True
        
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread
        
        generate_chat_title_background(chat_id)
        
        mock_thread_class.assert_called_once()
        call_kwargs = mock_thread_class.call_args[1]
        assert call_kwargs['daemon'] is True
        mock_thread.start.assert_called_once()
    
    @patch("src.services.background.SessionLocal")
    @patch("src.services.background._generate_chat_title_internal")
    def test_generate_chat_title_background_executes_task(self, mock_generate_internal, mock_session_local):
        """Test background task actually executes and closes session"""
        chat_id = uuid4()
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        mock_generate_internal.return_value = True
        
        with patch("src.services.background.threading.Thread") as mock_thread_class:
            # Capture the target function
            target_func = None
            def capture_thread(*args, **kwargs):
                nonlocal target_func
                target_func = kwargs['target']
                mock_thread = MagicMock()
                return mock_thread
            
            mock_thread_class.side_effect = capture_thread
            generate_chat_title_background(chat_id)
            
            # Execute the captured function
            target_func()
            
            mock_session_local.assert_called_once()
            mock_generate_internal.assert_called_once_with(chat_id, mock_session)
            mock_session.close.assert_called_once()
    
    @patch("src.services.background.SessionLocal")
    @patch("src.services.background._generate_chat_title_internal")
    def test_generate_chat_title_background_handles_exception(self, mock_generate_internal, mock_session_local):
        """Test background task handles exceptions and closes session"""
        chat_id = uuid4()
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        mock_generate_internal.side_effect = Exception("Task failed")
        
        with patch("src.services.background.threading.Thread") as mock_thread_class:
            target_func = None
            def capture_thread(*args, **kwargs):
                nonlocal target_func
                target_func = kwargs['target']
                return MagicMock()
            
            mock_thread_class.side_effect = capture_thread
            generate_chat_title_background(chat_id)
            
            # Execute should not raise exception
            target_func()
            
            mock_session.close.assert_called_once()
    
    @patch("src.services.background.generate_chat_title_background")
    def test_schedule_title_generation_success(self, mock_generate_bg):
        """Test scheduling title generation"""
        chat_id = uuid4()
        
        schedule_title_generation(chat_id)
        
        mock_generate_bg.assert_called_once_with(chat_id)
    
    @patch("src.services.background.generate_chat_title_background")
    def test_schedule_title_generation_handles_exception(self, mock_generate_bg):
        """Test schedule handles exceptions gracefully"""
        chat_id = uuid4()
        mock_generate_bg.side_effect = Exception("Scheduling failed")
        
        # Should not raise exception
        schedule_title_generation(chat_id)
