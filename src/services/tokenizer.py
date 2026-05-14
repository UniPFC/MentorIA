"""
Token counting service.

Two modes:
- "openai" (default): Uses tiktoken with o200k_base encoding. 
  Accurate for OpenAI models and good approximation for local/open-source models.
- "google": Uses tiktoken with cl100k_base as approximation for Gemini models.
"""

from functools import lru_cache
from typing import List, Dict, Optional
import logging

import tiktoken

logger = logging.getLogger(__name__)

ENCODINGS = {
    "openai": "o200k_base",
    "google": "cl100k_base",
}

_PROVIDER_MODE_MAP = {
    "openai": "openai",
    "ollama": "openai",
    "gemini": "google",
    "google": "google",
}


def mode_from_provider(provider: Optional[str]) -> str:
    """
    Map an LLM provider alias to a tokenizer mode.

    Args:
        provider: Provider alias ("openai", "ollama", "gemini", etc.).
                  Falls back to "openai" if None or unknown.

    Returns:
        Tokenizer mode ("openai" or "google").
    """
    if not provider:
        return "openai"
    return _PROVIDER_MODE_MAP.get(provider.lower(), "openai")


@lru_cache(maxsize=4)
def _get_encoding(mode: str) -> tiktoken.Encoding:
    """Get cached tiktoken encoding by mode."""
    encoding_name = ENCODINGS.get(mode)
    if not encoding_name:
        raise ValueError(f"Modo inválido: '{mode}'. Use 'openai' ou 'google'.")
    return tiktoken.get_encoding(encoding_name)


def count_tokens(text: str, mode: str = "openai") -> int:
    """
    Count the number of tokens in a text.

    Args:
        text: Text to count tokens for.
        mode: "openai" (default, also for local models) or "google" (Gemini).

    Returns:
        Token count.
    """
    if not text:
        return 0
    encoding = _get_encoding(mode)
    return len(encoding.encode(text))


def count_messages_tokens(messages: List[Dict[str, str]], mode: str = "openai") -> int:
    """
    Count total tokens across a list of chat messages.

    Each message is expected to have "role" and "content" keys.
    Counts tokens in both role and content of every message.

    Args:
        messages: List of {"role": "...", "content": "..."} dicts.
        mode: "openai" or "google".

    Returns:
        Total token count.
    """
    encoding = _get_encoding(mode)
    total = 0
    for msg in messages:
        total += len(encoding.encode(msg.get("role", "")))
        total += len(encoding.encode(msg.get("content", "")))
    return total
