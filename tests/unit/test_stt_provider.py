import pytest
from unittest.mock import Mock
from src.ai.provider.stt import FasterWhisperSTTProvider


@pytest.mark.unit
class TestFasterWhisperSTTProvider:
    """Testes unitários para FasterWhisperSTTProvider"""

    def test_faster_whisper_stt_init(self):
        """Testa inicialização do FasterWhisperSTTProvider"""
        mock_model = Mock()
        
        provider = FasterWhisperSTTProvider(model=mock_model)
        
        assert provider.model is not None
        assert provider.model == mock_model

    def test_faster_whisper_stt_transcribe(self):
        """Testa transcrição de audio"""
        mock_model = Mock()
        
        # Mock segments
        mock_segment1 = Mock()
        mock_segment1.text = "Olá,"
        mock_segment2 = Mock()
        mock_segment2.text = "mundo!"
        
        # Mock info
        mock_info = Mock()
        mock_info.language = "pt"
        mock_info.language_probability = 0.95
        
        mock_model.transcribe.return_value = ([mock_segment1, mock_segment2], mock_info)
        
        provider = FasterWhisperSTTProvider(model=mock_model)
        
        result = provider.transcribe(
            audio_path="/tmp/test.wav",
            language="pt",
            beam_size=5
        )
        
        assert result["text"] == "Olá, mundo!"
        assert result["detected_language"] == "pt"
        assert result["language_probability"] == 0.95
        mock_model.transcribe.assert_called_once_with(
            "/tmp/test.wav",
            beam_size=5,
            language="pt",
            vad_filter=True
        )

    def test_faster_whisper_stt_transcribe_auto_language(self):
        """Testa transcrição com detecção automática de linguagem"""
        mock_model = Mock()
        
        mock_segment = Mock()
        mock_segment.text = "Hello world"
        
        mock_info = Mock()
        mock_info.language = "en"
        mock_info.language_probability = 0.88
        
        mock_model.transcribe.return_value = ([mock_segment], mock_info)
        
        provider = FasterWhisperSTTProvider(model=mock_model)
        
        result = provider.transcribe(
            audio_path="/tmp/test.wav",
            language=None,  # Auto-detect
            beam_size=5
        )
        
        assert result["text"] == "Hello world"
        assert result["detected_language"] == "en"

    def test_faster_whisper_stt_transcribe_with_beam_size(self):
        """Testa transcrição com beam_size customizado"""
        mock_model = Mock()
        
        mock_segment = Mock()
        mock_segment.text = "Test"
        
        mock_info = Mock()
        mock_info.language = "en"
        mock_info.language_probability = 0.9
        
        mock_model.transcribe.return_value = ([mock_segment], mock_info)
        
        provider = FasterWhisperSTTProvider(model=mock_model)
        
        result = provider.transcribe(
            audio_path="/tmp/test.wav",
            language="en",
            beam_size=10
        )
        
        assert result["text"] == "Test"
        mock_model.transcribe.assert_called_once_with(
            "/tmp/test.wav",
            beam_size=10,
            language="en",
            vad_filter=True
        )

    def test_faster_whisper_stt_transcribe_error(self):
        """Testa erro na transcrição"""
        mock_model = Mock()
        mock_model.transcribe.side_effect = Exception("Transcription failed")
        
        provider = FasterWhisperSTTProvider(model=mock_model)
        
        with pytest.raises(Exception, match="Transcription failed"):
            provider.transcribe(audio_path="/tmp/test.wav")

    def test_faster_whisper_stt_transcribe_empty_segments(self):
        """Testa transcrição com segments vazios"""
        mock_model = Mock()
        
        mock_info = Mock()
        mock_info.language = "en"
        mock_info.language_probability = 0.9
        
        mock_model.transcribe.return_value = ([], mock_info)
        
        provider = FasterWhisperSTTProvider(model=mock_model)
        
        result = provider.transcribe(audio_path="/tmp/test.wav")
        
        assert result["text"] == ""
