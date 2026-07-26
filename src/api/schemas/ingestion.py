"""
Pydantic schemas for ingestion job endpoints.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class IngestionJobResponse(BaseModel):
    """Schema for ingestion job response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chat_type_id: UUID
    filename: str
    status: str
    total_chunks: int
    processed_chunks: int
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class UploadResponseAsync(BaseModel):
    """Schema for async upload response."""

    job_id: UUID
    chat_type_id: UUID
    message: str
    status_url: str
