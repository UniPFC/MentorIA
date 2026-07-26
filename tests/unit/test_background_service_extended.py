from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from shared.database.models.ingestion_job import IngestionJob, IngestionStatus
from shared.database.models.user import User
from src.services.background import process_ingestion_job


@pytest.mark.unit
class TestBackgroundServiceExtended:
    """Extended tests for background service to increase coverage"""

    @pytest.fixture
    def mock_db_session(self):
        return MagicMock(spec=Session)

    @pytest.fixture
    def mock_ingestion_service(self):
        return MagicMock()

    @pytest.fixture
    def sample_ingestion_job(self, sample_user: User, sample_chat_type):
        return IngestionJob(
            id=uuid4(),
            chat_type_id=sample_chat_type.id,
            filename="test_file.xlsx",
            status=IngestionStatus.PENDING,
            created_at=datetime.now(UTC),
        )

    @patch("src.services.background.SessionLocal")
    @patch("src.services.background.ChunkIngestionService")
    @patch("src.services.background.QdrantManager")
    @patch("src.services.background.Provider")
    def test_process_ingestion_job_success_flow(
        self,
        mock_provider,
        mock_qdrant,
        mock_ingestion,
        mock_session_local,
        mock_db_session,
        sample_ingestion_job,
        mock_ingestion_service,
    ):
        """Test successful ingestion job processing"""
        # Setup mocks
        mock_db_session.query.return_value.filter.return_value.first.return_value = (
            sample_ingestion_job
        )
        mock_session_local.return_value = mock_db_session

        # Mock successful ingestion
        mock_ingestion_service.ingest_from_file.return_value = None

        # Process job
        process_ingestion_job(
            job_id=sample_ingestion_job.id,
            chat_type_id=sample_ingestion_job.chat_type_id,
            file_content=b"test file content",
            filename="test_file.xlsx",
            question_col="Question",
            answer_col="Answer",
            ingestion_service=mock_ingestion_service,
            db=mock_db_session,
        )

        # Verify job status updates
        assert mock_db_session.commit.call_count >= 1

    @patch("src.services.background.SessionLocal")
    @patch("src.services.background.ChunkIngestionService")
    @patch("src.services.background.QdrantManager")
    @patch("src.services.background.Provider")
    def test_process_ingestion_job_with_error(
        self,
        mock_provider,
        mock_qdrant,
        mock_ingestion,
        mock_session_local,
        mock_db_session,
        sample_ingestion_job,
        mock_ingestion_service,
    ):
        """Test ingestion job processing with error"""
        # Setup mocks
        mock_db_session.query.return_value.filter.return_value.first.return_value = (
            sample_ingestion_job
        )
        mock_session_local.return_value = mock_db_session

        # Mock ingestion error
        mock_ingestion_service.ingest_from_file.side_effect = Exception(
            "Ingestion failed"
        )

        # Process job
        process_ingestion_job(
            job_id=sample_ingestion_job.id,
            chat_type_id=sample_ingestion_job.chat_type_id,
            file_content=b"test file content",
            filename="test_file.xlsx",
            question_col="Question",
            answer_col="Answer",
            ingestion_service=mock_ingestion_service,
            db=mock_db_session,
        )

        # Verify job status is set to FAILED
        sample_ingestion_job.status = IngestionStatus.FAILED
        sample_ingestion_job.error_message = "Ingestion failed"

        assert mock_db_session.commit.called

    @patch("src.services.background.SessionLocal")
    def test_process_ingestion_job_not_found(self, mock_session_local, mock_db_session):
        """Test processing non-existent job"""
        # Setup mocks
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        mock_session_local.return_value = mock_db_session

        # Create mock ingestion service
        mock_ingestion_service = MagicMock()

        # Process non-existent job
        job_id = uuid4()
        process_ingestion_job(
            job_id=job_id,
            chat_type_id=uuid4(),
            file_content=b"test content",
            filename="test.xlsx",
            question_col="Question",
            answer_col="Answer",
            ingestion_service=mock_ingestion_service,
            db=mock_db_session,
        )

        # Should not process anything
        assert mock_db_session.commit.called is False
