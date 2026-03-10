"""
Pydantic schemas for Chat endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class MessageBase(BaseModel):
    """Base schema for Message."""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1)


class MessageResponse(MessageBase):
    """Schema for Message response."""
    id: UUID
    chat_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChatCreate(BaseModel):
    """Schema for creating a new Chat."""
    chat_type_id: UUID = Field(..., description="ID of the chat type")
    title: str = Field(..., min_length=1, max_length=200, description="Chat title")
    user_id: Optional[UUID] = Field(None, description="User ID (temporary, will use auth later)")


class ChatResponse(BaseModel):
    """Schema for Chat response."""
    id: UUID
    user_id: UUID
    chat_type_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ChatWithMessagesResponse(ChatResponse):
    """Schema for Chat with messages."""
    messages: List[MessageResponse]


class SendMessageRequest(BaseModel):
    """Schema for sending a message."""
    content: str = Field(..., min_length=1, description="Message content")


class SendMessageResponse(BaseModel):
    """Schema for message send response with full chat."""
    chat: ChatWithMessagesResponse
    retrieved_chunks: Optional[List[dict]] = Field(None, description="Retrieved chunks used for RAG")
