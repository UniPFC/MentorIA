from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from shared.database.models.ingestion_job import IngestionJob
from shared.database.models.chat_type import ChatType


class IngestionJobRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, job_id: UUID) -> Optional[IngestionJob]:
        return self.db.query(IngestionJob).filter(IngestionJob.id == job_id).first()

    def get_by_user(
        self,
        user_id: UUID,
        chat_type_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[IngestionJob]:
        """
        Get ingestion jobs for chat types owned by the user.
        """
        query = self.db.query(IngestionJob).select_from(IngestionJob).join(
            ChatType, IngestionJob.chat_type_id == ChatType.id
        )
        
        query = query.filter(ChatType.owner_id == user_id)
        
        if chat_type_id is not None:
            query = query.filter(IngestionJob.chat_type_id == chat_type_id)
        
        return query.order_by(IngestionJob.created_at.desc()).offset(skip).limit(limit).all()

    def create(self, job: IngestionJob) -> IngestionJob:
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def update(self, job: IngestionJob) -> IngestionJob:
        self.db.commit()
        self.db.refresh(job)
        return job

    def delete(self, job: IngestionJob) -> None:
        self.db.delete(job)
        self.db.commit()
