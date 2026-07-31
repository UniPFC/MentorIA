from typing import Any
from uuid import UUID

from pydantic import BaseModel


class WorkerGenerateRequest(BaseModel):
    """Schema for requesting a generation task from the AI worker."""

    chat_type_id: UUID
    query: str
    chat_history: list[dict[str, str]] | None = None
    k_retrieval: int | None = None
    top_k: int | None = None
    threshold: float | None = None
    llm_model: str | None = None
    llm_provider: str | None = None


class WorkerGenerateResponse(BaseModel):
    """Schema for the worker generation response."""

    answer: str
    chunks: list[dict[str, Any]]
