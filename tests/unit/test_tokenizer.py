"""Unit tests for src.services.tokenizer."""

import pytest

from src.services.tokenizer import (
    _get_encoding,
    count_messages_tokens,
    count_tokens,
    mode_from_provider,
)


class TestCountTokens:
    """Tests for count_tokens."""

    def test_empty_string_returns_zero(self):
        assert count_tokens("") == 0

    def test_none_returns_zero(self):
        assert count_tokens(None) == 0

    def test_basic_text_openai(self):
        result = count_tokens("Hello world", mode="openai")
        assert isinstance(result, int)
        assert result > 0

    def test_basic_text_google(self):
        result = count_tokens("Hello world", mode="google")
        assert isinstance(result, int)
        assert result > 0

    def test_default_mode_is_openai(self):
        assert count_tokens("test") == count_tokens("test", mode="openai")

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError, match="Modo inválido"):
            count_tokens("test", mode="invalid")

    def test_long_text(self):
        text = "Python is great. " * 500
        result = count_tokens(text)
        assert result > 100

    def test_different_modes_may_differ(self):
        text = "A inteligência artificial está transformando o mundo moderno."
        openai_count = count_tokens(text, mode="openai")
        google_count = count_tokens(text, mode="google")
        # Both should be positive, may or may not differ
        assert openai_count > 0
        assert google_count > 0


class TestCountMessagesTokens:
    """Tests for count_messages_tokens."""

    def test_empty_list(self):
        assert count_messages_tokens([]) == 0

    def test_single_message(self):
        messages = [{"role": "user", "content": "Hello"}]
        result = count_messages_tokens(messages)
        assert result > 0

    def test_multiple_messages(self):
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]
        result = count_messages_tokens(messages)
        assert result > 0

    def test_counts_role_and_content(self):
        messages = [{"role": "user", "content": "Hello"}]
        result = count_messages_tokens(messages)
        content_only = count_tokens("Hello")
        # Should be greater because role tokens are also counted
        assert result > content_only

    def test_missing_keys_treated_as_empty(self):
        messages = [{"role": "user"}, {"content": "Hello"}]
        result = count_messages_tokens(messages)
        assert isinstance(result, int)

    def test_google_mode(self):
        messages = [{"role": "user", "content": "Hello"}]
        result = count_messages_tokens(messages, mode="google")
        assert result > 0


class TestModeFromProvider:
    """Tests for mode_from_provider."""

    def test_openai_provider(self):
        assert mode_from_provider("openai") == "openai"

    def test_ollama_provider(self):
        assert mode_from_provider("ollama") == "openai"

    def test_gemini_provider(self):
        assert mode_from_provider("gemini") == "google"

    def test_google_provider(self):
        assert mode_from_provider("google") == "google"

    def test_none_defaults_to_openai(self):
        assert mode_from_provider(None) == "openai"

    def test_empty_string_defaults_to_openai(self):
        assert mode_from_provider("") == "openai"

    def test_unknown_provider_defaults_to_openai(self):
        assert mode_from_provider("anthropic") == "openai"

    def test_case_insensitive(self):
        assert mode_from_provider("OpenAI") == "openai"
        assert mode_from_provider("GEMINI") == "google"
        assert mode_from_provider("Ollama") == "openai"


class TestGetEncoding:
    """Tests for _get_encoding cache."""

    def test_returns_encoding_for_valid_mode(self):
        enc = _get_encoding("openai")
        assert enc is not None

    def test_same_instance_returned_on_repeat(self):
        enc1 = _get_encoding("openai")
        enc2 = _get_encoding("openai")
        assert enc1 is enc2

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError):
            _get_encoding("invalid_mode")
