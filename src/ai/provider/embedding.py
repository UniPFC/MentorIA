"""
Embedding providers for vector generation.
"""

import torch
from openai import OpenAI

from config.logger import logger
from src.ai.provider.base import EmbeddingProvider
from src.ai.provider.utils import URLS, resolve_api_key


class HFEmbeddingProvider(EmbeddingProvider):
    """Local HuggingFace embedding provider."""

    def __init__(self, model, tokenizer):
        """
        Initialize with loaded model and tokenizer.

        Args:
            model: HuggingFace model
            tokenizer: HuggingFace tokenizer
        """
        self.model = model
        self.model.eval()
        self.tokenizer = tokenizer
        logger.info("HFEmbeddingProvider ready")

    def embed(self, inputs: list[str], **kwargs) -> list[list[float]]:
        """
        Generate embeddings using local model.

        Args:
            inputs: List of texts
            **kwargs: max_length, etc.

        Returns:
            List of embedding vectors
        """
        max_length = kwargs.get("max_length", 1024)

        try:
            encoded = self.tokenizer(
                inputs,
                padding=True,
                truncation=True,
                max_length=max_length,
                return_tensors="pt",
            ).to(self.model.device)

            with torch.no_grad():
                output = self.model(**encoded)

            embeddings = self._mean_pooling(output, encoded["attention_mask"])
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)

            return embeddings.tolist()

        except Exception as e:
            logger.error(f"Embedding error: {e}")
            raise

    def _mean_pooling(self, model_output, attention_mask):
        """Apply mean pooling with attention mask."""
        token_embeddings = model_output[0]
        input_mask_expanded = (
            attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        )
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(
            input_mask_expanded.sum(1), min=1e-9
        )


class RemoteEmbeddingProvider(EmbeddingProvider):
    """Remote embedding provider (OpenAI-compatible)."""

    def __init__(
        self,
        model_name: str,
        provider_alias: str = "openai",
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        """
        Initialize remote embedding provider.

        Args:
            model_name: Model identifier
            provider_alias: Provider name
            api_key: API key
            base_url: Custom base URL
        """
        normalized_alias = provider_alias.lower()
        self.target_url = (
            base_url if base_url else URLS.get(normalized_alias, URLS["openai"])
        )
        self.api_key = resolve_api_key(normalized_alias, api_key)
        self.client = OpenAI(api_key=self.api_key, base_url=self.target_url)
        self.model_name = model_name
        logger.info(
            f"RemoteEmbeddingProvider: model={model_name}, endpoint={self.target_url}"
        )

    def embed(self, inputs: list[str], **kwargs) -> list[list[float]]:
        """
        Generate embeddings via API.

        Args:
            inputs: List of texts
            **kwargs: Additional parameters

        Returns:
            List of embedding vectors
        """
        try:
            logger.debug(
                f"Remote embedding: model={self.model_name}, batch={len(inputs)}"
            )
            response = self.client.embeddings.create(
                input=inputs, model=self.model_name, **kwargs
            )

            data = sorted(response.data, key=lambda x: x.index)
            embeddings = [item.embedding for item in data]

            logger.debug("Remote embedding completed")
            return embeddings

        except Exception as e:
            logger.error(f"Remote embedding error ({self.target_url}): {e}")
            raise
