import pytest
from unittest.mock import patch, MagicMock
from src.ai.provider.utils import URLS, resolve_api_key


@pytest.mark.unit
class TestProviderUtils:
    def test_urls_dict_exists(self):
        assert isinstance(URLS, dict)
        assert "openai" in URLS
        assert "ollama" in URLS
        assert "gemini" in URLS
    
    def test_urls_values(self):
        assert URLS["openai"] == "https://api.openai.com/v1"
        assert URLS["ollama"] == "http://host.docker.internal:11434/v1"
        assert "generativelanguage.googleapis.com" in URLS["gemini"]
    
    def test_resolve_api_key_explicit(self):
        result = resolve_api_key("openai", "explicit-key")
        assert result == "explicit-key"
    
    @patch('src.ai.provider.utils.settings')
    def test_resolve_api_key_openai(self, mock_settings):
        mock_settings.OPENAI_API_KEY = "test-openai-key"
        result = resolve_api_key("openai", None)
        assert result == "test-openai-key"
    
    @patch('src.ai.provider.utils.settings')
    def test_resolve_api_key_gemini(self, mock_settings):
        mock_settings.GOOGLE_API_KEY = "test-gemini-key"
        result = resolve_api_key("gemini", None)
        assert result == "test-gemini-key"
    
    @patch('src.ai.provider.utils.settings')
    def test_resolve_api_key_ollama(self, mock_settings):
        mock_settings.OLLAMA_API_KEY = "test-ollama-key"
        result = resolve_api_key("ollama", None)
        assert result == "test-ollama-key"
    
    @patch('src.ai.provider.utils.settings')
    def test_resolve_api_key_ollama_default(self, mock_settings):
        delattr(mock_settings, 'OLLAMA_API_KEY') if hasattr(mock_settings, 'OLLAMA_API_KEY') else None
        result = resolve_api_key("ollama", None)
        assert result == "ollama"
    
    def test_resolve_api_key_unknown_provider(self):
        with pytest.raises(ValueError, match="Invalid provider alias"):
            resolve_api_key("unknown_provider", None)
    
    def test_resolve_api_key_case_insensitive(self):
        result = resolve_api_key("OPENAI", "test-key")
        assert result == "test-key"
    
    @patch('src.ai.provider.utils.settings')
    def test_resolve_api_key_case_insensitive_provider(self, mock_settings):
        mock_settings.OPENAI_API_KEY = "test-key"
        result = resolve_api_key("OpenAI", None)
        assert result == "test-key"
