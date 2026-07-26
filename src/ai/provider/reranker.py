"""
Reranking providers for document relevance scoring.
"""

import torch

from config.logger import logger
from src.ai.provider.base import RerankProvider


class HFRerankProvider(RerankProvider):
    """Local HuggingFace cross-encoder reranker."""

    def __init__(self, model, tokenizer):
        """
        Initialize with loaded model and tokenizer.

        Args:
            model: Cross-encoder model
            tokenizer: Tokenizer
        """
        self.model = model
        self.model.eval()
        self.tokenizer = tokenizer

        if self.tokenizer.pad_token is None:
            if self.tokenizer.eos_token is not None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            else:
                logger.warning("Rerank tokenizer has no pad_token")

        if (
            getattr(self.model, "config", None)
            and getattr(self.model.config, "pad_token_id", None) is None
        ):
            if self.tokenizer.pad_token_id is not None:
                self.model.config.pad_token_id = self.tokenizer.pad_token_id

        logger.info("HFRerankProvider ready")

    def rerank(self, query: str, documents: list[str], **kwargs) -> list[float]:
        """
        Rerank documents using cross-encoder.

        Args:
            query: Search query
            documents: List of documents
            **kwargs: max_length, batch_size

        Returns:
            List of relevance scores
        """
        if not documents:
            return []

        pairs = [[query, doc] for doc in documents]
        max_length = kwargs.get("max_length", 1024)
        batch_size = kwargs.get("batch_size", 8)
        all_scores = []

        try:
            for i in range(0, len(pairs), batch_size):
                batch_pairs = pairs[i : i + batch_size]

                inputs = self.tokenizer(
                    batch_pairs,
                    padding=True,
                    truncation=True,
                    max_length=max_length,
                    return_tensors="pt",
                ).to(self.model.device)

                with torch.no_grad():
                    outputs = self.model(**inputs)

                logits = outputs.logits
                if logits.dim() == 1:
                    scores = logits
                elif logits.shape[1] == 1:
                    scores = logits.squeeze(-1)
                else:
                    scores = logits[:, -1]

                scores = torch.sigmoid(scores)

                all_scores.extend(scores.float().cpu().tolist())

            return all_scores

        except Exception as e:
            logger.error(f"Rerank error: {e}")
            raise
