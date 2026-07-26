"""
Reranker engine for scoring and filtering retrieved chunks.
"""

import threading
from typing import Any

from config.logger import logger
from src.ai.provider.base import RerankProvider


class RerankerEngine:
    """
    Reranks retrieved chunks using a cross-encoder model.
    """

    def __init__(self, rerank_provider: RerankProvider):
        """
        Initialize reranker.

        Args:
            rerank_provider: RerankProvider instance
        """
        self.provider = rerank_provider
        self._lock = threading.Lock()
        logger.info("RerankerEngine initialized")

    def rerank_chunks(
        self,
        query: str,
        chunks: list[dict[str, Any]],
        top_k: int = 5,
        threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        Rerank chunks by relevance to query.

        Args:
            query: Search query
            chunks: List of chunk dicts
            top_k: Number of top chunks to return
            threshold: Minimum score threshold

        Returns:
            Reranked and filtered list of chunks
        """
        if not chunks:
            return []

        try:
            # Prepare documents for reranking (question + answer)
            documents = [
                f"{chunk['question']}\n\n{chunk['answer']}" for chunk in chunks
            ]

            # Get relevance scores (thread-safe)
            with self._lock:
                scores = self.provider.rerank(query, documents)

            # Attach scores to chunks
            for chunk, score in zip(chunks, scores):
                chunk["rerank_score"] = score

            # Filter by threshold
            filtered_chunks = [
                chunk for chunk in chunks if chunk["rerank_score"] >= threshold
            ]

            # Sort by score (descending) and take top_k
            sorted_chunks = sorted(
                filtered_chunks, key=lambda x: x["rerank_score"], reverse=True
            )[:top_k]

            logger.debug(
                f"Reranked {len(chunks)} chunks → {len(sorted_chunks)} after filtering"
            )
            return sorted_chunks

        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            raise
