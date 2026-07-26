"""
Pydantic schemas for Chat endpoints.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MessageBase(BaseModel):
    """Base schema for Message."""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1)


class MessageResponse(MessageBase):
    """Schema for Message response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chat_id: UUID
    created_at: datetime


class ChatCreate(BaseModel):
    """Schema for creating a new Chat."""
    chat_type_id: UUID = Field(..., description="ID of the chat type")
    title: str | None = Field(None, min_length=1, max_length=200, description="Chat title (optional, will generate placeholder if not provided)")


class ChatResponse(BaseModel):
    """Schema for Chat response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    chat_type_id: UUID
    title: str
    llm_model: str | None = None
    llm_provider: str | None = None
    created_at: datetime
    updated_at: datetime


class ChatWithMessagesResponse(ChatResponse):
    """Schema for Chat with messages."""
    messages: list[MessageResponse]


class SendMessageRequest(BaseModel):
    """Schema for sending a message."""
    content: str = Field(..., min_length=1, description="Message content")


class SendMessageResponse(BaseModel):
    """Schema for message send response with full chat."""
    model_config = ConfigDict(populate_by_name=True)

    chat: ChatWithMessagesResponse
    sources: list[dict] | None = Field(None, description="Retrieved chunks used for RAG")


class ChatModelUpdate(BaseModel):
    """Schema for updating chat LLM model and provider."""
    llm_model: str | None = Field(None, description="LLM model name (e.g., 'llama3.1:8b', 'gpt-4')")
    llm_provider: str | None = Field(None, description="LLM provider (ollama, openai, gemini)")


class LLMModelInfo(BaseModel):
    """Schema for available LLM model information."""
    model: str = Field(..., description="Model identifier")
    provider: str = Field(..., description="Provider name")
    description: str | None = Field(None, description="Model description")
    cost_tier: int = Field(5, ge=0, le=9, description="Cost tier 0-9 (0=cheapest, 9=most expensive)")


class AvailableModelsResponse(BaseModel):
    """Schema for listing available LLM models."""
    models: list[LLMModelInfo] = Field(..., description="List of available models")
    current_default: str = Field(..., description="Current default model from settings")
