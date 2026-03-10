"""
Pydantic schemas for ChatType endpoints.
"""

from pydantic import BaseModel, Field
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
    id: UUID
    is_public: bool
    owner_id: Optional[UUID]
    collection_name: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChatTypeListResponse(BaseModel):
    """Schema for listing chat types."""
    chat_types: list[ChatTypeResponse]
    total: int
