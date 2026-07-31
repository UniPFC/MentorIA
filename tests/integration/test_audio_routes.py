from io import BytesIO
from unittest.mock import Mock, patch

import pytest


@pytest.mark.integration
class TestAudioRoutes:
    """Testes de integração para rotas de audio"""

    def test_transcribe_audio_stt_disabled(self, client):
        """Testa transcrição quando STT está desabilitado"""
        with patch("src.api.routes.audio.settings") as mock_settings:
            mock_settings.STT_ENABLED = False

            audio_file = BytesIO(b"fake audio content")
            audio_file.name = "test.wav"

            response = client.post(
                "/api/v1/audio/transcribe",
                files={"audio": ("test.wav", audio_file, "audio/wav")},
            )

            assert response.status_code == 503
            assert "Speech-to-Text is not enabled" in response.json()["detail"]

    def test_transcribe_audio_unsupported_format(self, client):
        """Testa transcrição com formato não suportado"""
        with patch("src.api.routes.audio.settings") as mock_settings:
            mock_settings.STT_ENABLED = True

            audio_file = BytesIO(b"fake content")
            audio_file.name = "test.txt"

            response = client.post(
                "/api/v1/audio/transcribe",
                files={"audio": ("test.txt", audio_file, "text/plain")},
            )

            assert response.status_code == 400
            assert "Unsupported file format" in response.json()["detail"]

    def test_transcribe_audio_success(self, client):
        """Testa transcrição bem-sucedida"""
        with (
            patch("src.api.routes.audio.settings") as mock_settings,
            patch("src.api.routes.audio.httpx.AsyncClient") as mock_httpx,
        ):
            mock_settings.STT_ENABLED = True
            mock_settings.AI_WORKER_URL = "http://fake-worker"

            mock_response = Mock()
            mock_response.json.return_value = {
                "text": "Olá, mundo!",
                "detected_language": "pt",
                "language_probability": 0.95,
            }
            mock_client = Mock()
            mock_client.post = pytest.importorskip("unittest.mock").AsyncMock(
                return_value=mock_response
            )
            mock_httpx.return_value.__aenter__.return_value = mock_client

            audio_file = BytesIO(b"fake audio content")
            audio_file.name = "test.wav"

            response = client.post(
                "/api/v1/audio/transcribe",
                files={"audio": ("test.wav", audio_file, "audio/wav")},
                params={"language": "pt"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["text"] == "Olá, mundo!"
            assert data["language"] == "pt"
            assert data["detected_language"] == "pt"
            assert data["language_probability"] == 0.95

    def test_transcribe_audio_with_language_param(self, client):
        """Testa transcrição com parâmetro de linguagem"""
        from unittest.mock import AsyncMock

        with (
            patch("src.api.routes.audio.settings") as mock_settings,
            patch("src.api.routes.audio.httpx.AsyncClient") as mock_httpx,
        ):
            mock_settings.STT_ENABLED = True
            mock_settings.AI_WORKER_URL = "http://fake-worker"

            mock_response = Mock()
            mock_response.json.return_value = {
                "text": "Hello world",
                "detected_language": "en",
                "language_probability": 0.85,
            }

            mock_client = Mock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_httpx.return_value.__aenter__.return_value = mock_client

            audio_file = BytesIO(b"fake audio content")
            audio_file.name = "test.mp3"

            response = client.post(
                "/api/v1/audio/transcribe",
                files={"audio": ("test.mp3", audio_file, "audio/mpeg")},
                params={"language": "en"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["text"] == "Hello world"
            # Com probabilidade alta (> 0.8), usa a language detectada
            assert data["language"] == "en"

    def test_transcribe_audio_timeout_error(self, client):
        """Testa transcrição com erro de rede ou timeout (HTTPError)"""
        from unittest.mock import AsyncMock

        import httpx

        with (
            patch("src.api.routes.audio.settings") as mock_settings,
            patch("src.api.routes.audio.httpx.AsyncClient") as mock_httpx,
        ):
            mock_settings.STT_ENABLED = True
            mock_settings.AI_WORKER_URL = "http://fake-worker"

            mock_client = Mock()
            mock_client.post = AsyncMock(side_effect=httpx.HTTPError("Timeout"))
            mock_httpx.return_value.__aenter__.return_value = mock_client

            audio_file = BytesIO(b"fake audio content")
            audio_file.name = "test.wav"

            response = client.post(
                "/api/v1/audio/transcribe",
                files={"audio": ("test.wav", audio_file, "audio/wav")},
            )

            assert response.status_code == 503
            assert "Ocorreu um erro ao processar o áudio" in response.json()["detail"]

    def test_transcribe_audio_runtime_error(self, client):
        """Testa transcrição com erro de runtime 500 do worker"""
        from unittest.mock import AsyncMock

        import httpx

        with (
            patch("src.api.routes.audio.settings") as mock_settings,
            patch("src.api.routes.audio.httpx.AsyncClient") as mock_httpx,
        ):
            mock_settings.STT_ENABLED = True
            mock_settings.AI_WORKER_URL = "http://fake-worker"

            mock_response = Mock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "500 Server Error", request=Mock(), response=Mock()
            )
            mock_client = Mock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_httpx.return_value.__aenter__.return_value = mock_client

            audio_file = BytesIO(b"fake audio content")
            audio_file.name = "test.wav"

            response = client.post(
                "/api/v1/audio/transcribe",
                files={"audio": ("test.wav", audio_file, "audio/wav")},
            )

            # HTTPStatusError from worker translates to 503 from our API
            assert response.status_code == 503
            assert "Ocorreu um erro ao processar o áudio" in response.json()["detail"]

    def test_transcribe_audio_generic_error(self, client):
        """Testa transcrição com erro genérico interno (Exception)"""
        from unittest.mock import AsyncMock

        with (
            patch("src.api.routes.audio.settings") as mock_settings,
            patch("src.api.routes.audio.httpx.AsyncClient") as mock_httpx,
        ):
            mock_settings.STT_ENABLED = True
            mock_settings.AI_WORKER_URL = "http://fake-worker"

            mock_client = Mock()
            mock_client.post = AsyncMock(side_effect=Exception("Unexpected error"))
            mock_httpx.return_value.__aenter__.return_value = mock_client

            audio_file = BytesIO(b"fake audio content")
            audio_file.name = "test.wav"

            response = client.post(
                "/api/v1/audio/transcribe",
                files={"audio": ("test.wav", audio_file, "audio/wav")},
            )

            assert response.status_code == 500
            assert "Transcription failed" in response.json()["detail"]

    def test_transcribe_audio_supported_formats(self, client):
        """Testa que formatos suportados são aceitos"""
        from unittest.mock import AsyncMock

        with (
            patch("src.api.routes.audio.settings") as mock_settings,
            patch("src.api.routes.audio.httpx.AsyncClient") as mock_httpx,
        ):
            mock_settings.STT_ENABLED = True
            mock_settings.AI_WORKER_URL = "http://fake-worker"

            mock_response = Mock()
            mock_response.json.return_value = {
                "text": "Test",
                "detected_language": "en",
                "language_probability": 0.9,
            }
            mock_client = Mock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_httpx.return_value.__aenter__.return_value = mock_client

            supported_formats = [".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm"]

            for ext in supported_formats:
                audio_file = BytesIO(b"fake content")
                audio_file.name = f"test{ext}"

                response = client.post(
                    "/api/v1/audio/transcribe",
                    files={"audio": (f"test{ext}", audio_file, "audio/wav")},
                )

                assert response.status_code == 200, f"Failed for format {ext}"
