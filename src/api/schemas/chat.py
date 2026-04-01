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
    llm_model: Optional[str] = None
    llm_provider: Optional[str] = None
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
    sources: Optional[List[dict]] = Field(None, description="Retrieved chunks used for RAG")
    
    class Config:
        populate_by_name = True


class ChatModelUpdate(BaseModel):
    """Schema for updating chat LLM model and provider."""
    llm_model: Optional[str] = Field(None, description="LLM model name (e.g., 'llama3.1:8b', 'gpt-4')")
    llm_provider: Optional[str] = Field(None, description="LLM provider (ollama, openai, gemini)")


class LLMModelInfo(BaseModel):
    """Schema for available LLM model information."""
    model: str = Field(..., description="Model identifier")
    provider: str = Field(..., description="Provider name")
    description: Optional[str] = Field(None, description="Model description")


class AvailableModelsResponse(BaseModel):
    """Schema for listing available LLM models."""
    models: List[LLMModelInfo] = Field(..., description="List of available models")
    current_default: str = Field(..., description="Current default model from settings")
