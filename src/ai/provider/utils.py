"""
Utility functions for providers.
"""

from typing import Optional
from config.settings import settings


URLS = {
    "ollama": "http://host.docker.internal:11434/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "openai": "https://api.openai.com/v1"
}


def resolve_api_key(provider_alias: str, explicit_key: Optional[str]) -> str:
    """
    Determines the correct credential for the selected provider.
    
    Args:
        provider_alias: Provider name (ollama, openai, gemini)
        explicit_key: Explicitly provided API key
        
    Returns:
        Resolved API key
    """
    if explicit_key:
        return explicit_key

    alias = provider_alias.lower()
    match alias:
        case "ollama":
            return getattr(settings, "OLLAMA_API_KEY", alias)
        case "gemini":
            return getattr(settings, "GEMINI_API_KEY", "")
        case "openai":
            return getattr(settings, "OPENAI_API_KEY", "")
        case _:
            raise ValueError(f"Invalid provider alias: {provider_alias}")
