import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from src.services.background import process_ingestion_job
from shared.database.models.ingestion_job import IngestionJob, IngestionStatus


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
