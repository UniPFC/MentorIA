from unittest.mock import Mock, patch

import pytest

from src.ai.stt_loader import STTLoader, get_stt_loader


@pytest.mark.unit
class TestSTTLoader:
    """Testes unitários para STTLoader"""

    def test_stt_loader_singleton(self):
        """Testa que get_stt_loader retorna a mesma instância"""
        loader1 = get_stt_loader()
        loader2 = get_stt_loader()

        assert loader1 is loader2

    @patch("src.ai.stt_loader.settings")
    def test_stt_loader_disabled(self, mock_settings):
        """Testa carregamento quando STT está desabilitado"""
        mock_settings.STT_ENABLED = False

        loader = STTLoader()

        with pytest.raises(RuntimeError, match="STT is not enabled"):
            loader.get_provider()

    @patch("src.ai.stt_loader.settings")
    @patch("src.ai.stt_loader.WhisperModel")
    def test_stt_loader_get_provider(self, mock_whisper_model, mock_settings):
        """Testa carregamento do provider"""
        mock_settings.STT_ENABLED = True
        mock_settings.STT_MODEL = "base"
        mock_settings.STT_COMPUTE_TYPE = "int8"
        mock_settings.STT_TIMEOUT = 60
        mock_settings.CACHE_DIR = "/tmp/cache"

        mock_model = Mock()
        mock_whisper_model.return_value = mock_model

        loader = STTLoader()
        provider = loader.get_provider()

        assert provider is not None
        assert loader.is_loaded()

    @patch("src.ai.stt_loader.settings")
    @patch("src.ai.stt_loader.WhisperModel")
    def test_stt_loader_get_provider_caches(self, mock_whisper_model, mock_settings):
        """Testa que get_provider cacheia o provider"""
        mock_settings.STT_ENABLED = True
        mock_settings.STT_MODEL = "base"
        mock_settings.STT_COMPUTE_TYPE = "int8"
        mock_settings.STT_TIMEOUT = 60
        mock_settings.CACHE_DIR = "/tmp/cache"

        mock_model = Mock()
        mock_whisper_model.return_value = mock_model

        loader = STTLoader()
        provider1 = loader.get_provider()
        provider2 = loader.get_provider()

        assert provider1 is provider2
        mock_whisper_model.assert_called_once()

    @patch("src.ai.stt_loader.settings")
    @patch("src.ai.stt_loader.WhisperModel")
    def test_stt_loader_timeout(self, mock_whisper_model, mock_settings):
        """Testa timeout ao carregar modelo"""
        mock_settings.STT_ENABLED = True
        mock_settings.STT_MODEL = "base"
        mock_settings.STT_COMPUTE_TYPE = "int8"
        mock_settings.STT_TIMEOUT = 0.1  # Very short timeout
        mock_settings.CACHE_DIR = "/tmp/cache"

        mock_whisper_model.side_effect = Exception("Load failed")

        loader = STTLoader()

        with pytest.raises(TimeoutError, match="Failed to load STT model"):
            loader.get_provider()

    @patch("src.ai.stt_loader.settings")
    @patch("src.ai.stt_loader.WhisperModel")
    def test_stt_loader_unload_model(self, mock_whisper_model, mock_settings):
        """Testa descarga do modelo"""
        mock_settings.STT_ENABLED = True
        mock_settings.STT_MODEL = "base"
        mock_settings.STT_COMPUTE_TYPE = "int8"
        mock_settings.STT_TIMEOUT = 60
        mock_settings.CACHE_DIR = "/tmp/cache"

        mock_model = Mock()
        mock_whisper_model.return_value = mock_model

        loader = STTLoader()
        provider = loader.get_provider()

        assert loader.is_loaded()

        loader.unload_model()

        assert not loader.is_loaded()
        assert loader._provider is None
