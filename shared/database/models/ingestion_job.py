"""
SQLAlchemy model for tracking ingestion jobs.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SQLEnum, Uuid
from sqlalchemy.sql import func
from datetime import datetime, timezone
import uuid
import enum
from shared.database.session import Base


class IngestionStatus(str, enum.Enum):
    """Status of an ingestion job."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class IngestionJob(Base):
    """
    Tracks background ingestion jobs for chunk uploads.
    """
    __tablename__ = "ingestion_jobs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    chat_type_id = Column(Uuid(as_uuid=True), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    status = Column(SQLEnum(IngestionStatus), default=IngestionStatus.PENDING, nullable=False, index=True)
    total_chunks = Column(Integer, default=0)
    processed_chunks = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<IngestionJob(id={self.id}, chat_type_id={self.chat_type_id}, status={self.status})>"
