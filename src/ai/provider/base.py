"""
Base abstract classes for AI providers.
"""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    def generate(self, messages: list[dict[str, str]], **kwargs) -> str:
        """Generate text from messages."""
        pass


class EmbeddingProvider(ABC):
    """Base class for embedding providers."""

    @abstractmethod
    def embed(self, inputs: list[str], **kwargs) -> list[list[float]]:
        """Generate embeddings for texts."""
        pass


class RerankProvider(ABC):
    """Base class for reranking providers."""

    @abstractmethod
    def rerank(self, query: str, documents: list[str], **kwargs) -> list[float]:
        """Rerank documents by relevance to query."""
        pass


class STTProvider(ABC):
    """Base class for Speech-to-Text providers."""

    @abstractmethod
    def transcribe(self, audio_path: str, **kwargs) -> str:
        """Transcribe audio file to text."""
        pass
