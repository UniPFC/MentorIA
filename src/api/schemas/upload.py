"""
Pydantic schemas for file upload endpoints.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """Schema for upload response."""

    chat_type_id: UUID
    chunks_ingested: int
    message: str


class CreateChatTypeFromFileRequest(BaseModel):
    """Schema for creating chat type from file (form data)."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    is_public: bool = Field(
        False, description="Custom chat types are private by default"
    )
    owner_id: UUID | None = Field(None, description="Owner user ID")
    question_column: str = Field("question", description="Column name for questions")
    answer_column: str = Field("answer", description="Column name for answers")
