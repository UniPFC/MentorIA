"""
Pydantic schemas for ChatType endpoints.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID


class ChatTypeBase(BaseModel):
    """Base schema for ChatType."""
    name: str = Field(..., min_length=1, max_length=100, description="Name of the chat type")
    description: Optional[str] = Field(None, description="Description of the chat type")


class ChatTypeCreate(ChatTypeBase):
    """Schema for creating a new ChatType."""
    is_public: bool = Field(True, description="Whether this chat type is public")
    owner_id: Optional[UUID] = Field(None, description="Owner user ID (null for public types)")


class ChatTypeResponse(ChatTypeBase):
    """Schema for ChatType response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    is_public: bool
    owner_id: Optional[UUID]
    owner_name: Optional[str] = Field(None, description="Owner username (system chat types show 'MentorIA')")
    collection_name: str
    created_at: datetime


class ChatTypeListResponse(BaseModel):
    """Schema for listing chat types."""
    chat_types: list[ChatTypeResponse]
    total: int


class ChatTypeSearchParams(BaseModel):
    """Schema for searching chat types."""
    query: Optional[str] = Field(None, description="Search in name and description")
    is_public: Optional[bool] = Field(None, description="Filter by public/private")
    owner_id: Optional[UUID] = Field(None, description="Filter by owner")
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of records to return")
