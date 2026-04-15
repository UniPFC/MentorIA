import pytest
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from src.repositories.ingestion_job import IngestionJobRepository
from shared.database.models.ingestion_job import IngestionJob, IngestionStatus
from shared.database.models.chat_type import ChatType
from shared.database.models.user import User


class TestIngestionJobRepository:
    """Test suite for IngestionJobRepository"""

    @pytest.fixture
    def job_repo(self, db_session: Session):
        return IngestionJobRepository(db_session)

    @pytest.fixture
    def sample_job(self, db_session: Session, sample_chat_type: ChatType):
        job = IngestionJob(
            id=uuid4(),
            chat_type_id=sample_chat_type.id,
            filename="file.xlsx",
            status=IngestionStatus.PENDING,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        return job

    def test_get_by_id_found(self, job_repo: IngestionJobRepository, sample_job: IngestionJob):
        result = job_repo.get_by_id(sample_job.id)
        
        assert result is not None
        assert result.id == sample_job.id
        assert result.filename == sample_job.filename

    def test_get_by_id_not_found(self, job_repo: IngestionJobRepository):
        non_existent_id = uuid4()
        result = job_repo.get_by_id(non_existent_id)
        
        assert result is None

    def test_get_by_user(self, job_repo: IngestionJobRepository, db_session: Session, sample_user: User, sample_chat_type: ChatType):
        job1 = IngestionJob(
            id=uuid4(),
            chat_type_id=sample_chat_type.id,
            filename="file1.xlsx",
            status=IngestionStatus.PENDING,
            created_at=datetime.now(timezone.utc)
        )
        job2 = IngestionJob(
            id=uuid4(),
            chat_type_id=sample_chat_type.id,
            filename="file2.xlsx",
            status=IngestionStatus.COMPLETED,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add_all([job1, job2])
        db_session.commit()
        
        result = job_repo.get_by_user(sample_user.id)
        
        assert len(result) == 2
        assert all(job.chat_type_id == sample_chat_type.id for job in result)

    def test_get_by_user_with_chat_type_filter(self, job_repo: IngestionJobRepository, db_session: Session, sample_user: User):
        ct1 = ChatType(
            id=uuid4(),
            name="Type 1",
            description="Description 1",
            owner_id=sample_user.id,
            collection_name="type_1",
            created_at=datetime.now(timezone.utc)
        )
        ct2 = ChatType(
            id=uuid4(),
            name="Type 2",
            description="Description 2",
            owner_id=sample_user.id,
            collection_name="type_2",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add_all([ct1, ct2])
        db_session.commit()
        
        job1 = IngestionJob(
            id=uuid4(),
            chat_type_id=ct1.id,
            filename="file1.xlsx",
            status=IngestionStatus.PENDING,
            created_at=datetime.now(timezone.utc)
        )
        job2 = IngestionJob(
            id=uuid4(),
            chat_type_id=ct2.id,
            filename="file2.xlsx",
            status=IngestionStatus.COMPLETED,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add_all([job1, job2])
        db_session.commit()
        
        result = job_repo.get_by_user(sample_user.id, chat_type_id=ct1.id)
        
        assert len(result) == 1
        assert result[0].chat_type_id == ct1.id

    def test_get_by_user_with_pagination(self, job_repo: IngestionJobRepository, db_session: Session, sample_user: User, sample_chat_type: ChatType):
        for i in range(5):
            job = IngestionJob(
                id=uuid4(),
                chat_type_id=sample_chat_type.id,
                filename=f"file{i}.xlsx",
                status=IngestionStatus.PENDING,
                created_at=datetime.now(timezone.utc)
            )
            db_session.add(job)
        db_session.commit()
        
        result = job_repo.get_by_user(sample_user.id, skip=2, limit=2)
        
        assert len(result) == 2

    def test_get_by_user_only_owned_chat_types(self, job_repo: IngestionJobRepository, db_session: Session, sample_user: User):
        other_user = User(
            id=uuid4(),
            username="otheruser",
            email="other@example.com",
            password_hash="hash",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(other_user)
        db_session.commit()
        
        my_chat_type = ChatType(
            id=uuid4(),
            name="My Type",
            description="My type",
            owner_id=sample_user.id,
            collection_name="my_type",
            created_at=datetime.now(timezone.utc)
        )
        other_chat_type = ChatType(
            id=uuid4(),
            name="Other Type",
            description="Other type",
            owner_id=other_user.id,
            collection_name="other_type",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add_all([my_chat_type, other_chat_type])
        db_session.commit()
        
        my_job = IngestionJob(
            id=uuid4(),
            chat_type_id=my_chat_type.id,
            filename="my_file.xlsx",
            status=IngestionStatus.PENDING,
            created_at=datetime.now(timezone.utc)
        )
        other_job = IngestionJob(
            id=uuid4(),
            chat_type_id=other_chat_type.id,
            filename="other_file.xlsx",
            status=IngestionStatus.PENDING,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add_all([my_job, other_job])
        db_session.commit()
        
        result = job_repo.get_by_user(sample_user.id)
        
        assert len(result) == 1
        assert result[0].id == my_job.id

    def test_create(self, job_repo: IngestionJobRepository, sample_chat_type: ChatType):
        job = IngestionJob(
            id=uuid4(),
            chat_type_id=sample_chat_type.id,
            filename="new_file.xlsx",
            status=IngestionStatus.PENDING,
            created_at=datetime.now(timezone.utc)
        )
        
        result = job_repo.create(job)
        
        assert result.id == job.id
        assert result.filename == "new_file.xlsx"
        assert result.status == IngestionStatus.PENDING

    def test_update(self, job_repo: IngestionJobRepository, sample_job: IngestionJob):
        sample_job.status = IngestionStatus.PROCESSING
        sample_job.error_message = None
        
        result = job_repo.update(sample_job)
        
        assert result.status == IngestionStatus.PROCESSING

    def test_update_with_completion(self, job_repo: IngestionJobRepository, sample_job: IngestionJob):
        sample_job.status = IngestionStatus.COMPLETED
        sample_job.completed_at = datetime.now(timezone.utc)
        sample_job.processed_chunks = 100
        
        result = job_repo.update(sample_job)
        
        assert result.status == IngestionStatus.COMPLETED
        assert result.completed_at is not None
        assert result.processed_chunks == 100

    def test_update_with_error(self, job_repo: IngestionJobRepository, sample_job: IngestionJob):
        sample_job.status = IngestionStatus.FAILED
        sample_job.error_message = "Test error"
        
        result = job_repo.update(sample_job)
        
        assert result.status == IngestionStatus.FAILED
        assert result.error_message == "Test error"

    def test_delete(self, job_repo: IngestionJobRepository, db_session: Session, sample_job: IngestionJob):
        job_id = sample_job.id
        
        job_repo.delete(sample_job)
        
        deleted = db_session.query(IngestionJob).filter(IngestionJob.id == job_id).first()
        assert deleted is None
