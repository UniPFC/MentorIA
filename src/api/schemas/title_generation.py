"""
Schemas for title generation responses.
"""

from pydantic import BaseModel, Field


class ChatTitleResponse(BaseModel):
    """Schema for generated chat title response."""
    
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Generated chat title (6-8 words, sentence case)"
    )
