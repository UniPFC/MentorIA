"""
LLM providers for text generation.
"""

from typing import Any

import torch
from openai import OpenAI

from config.logger import logger
from src.ai.provider.base import LLMProvider
from src.ai.provider.utils import URLS, resolve_api_key


class Provider(LLMProvider):
    """
    OpenAI-compatible LLM provider.
    Supports Ollama, OpenAI, Gemini, and other OpenAI-compatible APIs.
    """

    def __init__(
        self,
        model_name: str,
        provider_alias: str = "openai",
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        """
        Initialize remote LLM provider.

        Args:
            model_name: Model identifier
            provider_alias: Provider name (ollama, openai, gemini)
            api_key: API key (auto-resolved if None)
            base_url: Custom base URL (overrides provider_alias)
        """
        normalized_alias = provider_alias.lower()
        self.target_url = (
            base_url if base_url else URLS.get(normalized_alias, URLS["openai"])
        )
        self.api_key = resolve_api_key(normalized_alias, api_key)
        self.client = OpenAI(api_key=self.api_key, base_url=self.target_url)
        self.model_name = model_name
        logger.info(
            f"Provider configured: model={model_name}, alias={provider_alias}, endpoint={self.target_url}"
        )

    def generate(self, messages: list[dict[str, str]], **kwargs) -> str:
        """
        Generate text completion.

        Args:
            messages: Chat messages
            **kwargs: max_new_tokens, temperature, top_p, etc.

        Returns:
            Generated text
        """
        max_tokens = kwargs.pop("max_new_tokens", 1024)
        temperature = kwargs.pop("temperature", 0.7)
        top_p = kwargs.pop("top_p", 1.0)

        try:
            logger.debug(
                f"Generating: model={self.model_name}, max_tokens={max_tokens}, temp={temperature}"
            )
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stream=False,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Provider error ({self.target_url}): {e}")
            raise

    def generate_structured(
        self, messages: list[dict[str, str]], response_format: Any, **kwargs
    ) -> Any:
        """
        Generate structured output following a Pydantic schema.

        Args:
            messages: Chat messages
            response_format: Pydantic model class
            **kwargs: Generation parameters

        Returns:
            Parsed Pydantic object or raw content
        """
        max_tokens = kwargs.pop("max_new_tokens", 8192)
        temperature = kwargs.pop("temperature", 0.0)
        top_p = kwargs.pop("top_p", 1.0)

        try:
            logger.debug(
                f"Structured generation: model={self.model_name}, format={response_format.__name__}"
            )

            completion = self.client.beta.chat.completions.parse(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                response_format=response_format,
                **kwargs,
            )

            message = completion.choices[0].message
            parsed = getattr(message, "parsed", None)
            if parsed is not None:
                logger.debug("Structured generation completed (parsed object)")
                return parsed

            logger.debug("Structured generation completed (raw content)")
            return message.content
        except Exception as e:
            logger.error(f"Structured provider error ({self.target_url}): {e}")
            raise

    def generate_stream(self, messages: list[dict[str, str]], **kwargs):
        """
        Generate text with streaming.

        Args:
            messages: Chat messages
            **kwargs: Generation parameters

        Yields:
            Text chunks as they arrive
        """
        max_tokens = kwargs.pop("max_new_tokens", 1024)
        temperature = kwargs.pop("temperature", 0.7)
        top_p = kwargs.pop("top_p", 1.0)

        try:
            logger.debug(f"Streaming generation: model={self.model_name}")
            stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stream=True,
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Streaming error ({self.target_url}): {e}")
            raise


class HFProvider(LLMProvider):
    """Local HuggingFace model provider."""

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
        if getattr(self.model, "generation_config", None):
            self.model.generation_config.temperature = None
        logger.info("HFProvider ready")

    def generate(self, messages: list[dict[str, str]], **kwargs) -> str:
        """
        Generate text using local model.

        Args:
            messages: Chat messages
            **kwargs: Generation parameters

        Returns:
            Generated text
        """
        gen_params = {
            "max_new_tokens": 1024,
            "top_p": 1.0,
            "do_sample": False,
            "repetition_penalty": 1.0,
        }

        ignored_temp = kwargs.pop("temperature", None)
        if ignored_temp is not None:
            logger.debug("Temperature ignored for HFProvider")

        gen_params.update(kwargs)

        try:
            input_ids = self.tokenizer.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True, return_tensors="pt"
            ).to(self.model.device)

            attention_mask = (input_ids != self.tokenizer.pad_token_id).long()
        except Exception as e:
            logger.error(f"Chat template error: {e}")
            raise

        with torch.no_grad():
            outputs = self.model.generate(
                input_ids,
                attention_mask=attention_mask,
                **gen_params,
                pad_token_id=self.tokenizer.pad_token_id,
            )

        generated_ids = outputs[0][input_ids.shape[1] :]
        response = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
        logger.debug("HFProvider generation completed")
        return response
