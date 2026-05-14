"""
Pydantic schemas for ingestion job endpoints.
"""

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from uuid import UUID


class IngestionJobResponse(BaseModel):
    """Schema for ingestion job response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    chat_type_id: UUID
    filename: str
    status: str
    total_chunks: int
    processed_chunks: int
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class UploadResponseAsync(BaseModel):
    """Schema for async upload response."""
    job_id: UUID
    chat_type_id: UUID
    message: str
    status_url: str
