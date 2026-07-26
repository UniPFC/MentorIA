"""
Speech-to-Text providers for audio transcription.
"""

from config.logger import logger
from src.ai.provider.base import STTProvider


class FasterWhisperSTTProvider(STTProvider):
    """Faster-Whisper STT provider using quantized models."""

    def __init__(self, model):
        """
        Initialize with loaded faster-whisper model.

        Args:
            model: FasterWhisper model instance
        """
        self.model = model
        logger.info("FasterWhisperSTTProvider ready")

    def transcribe(self, audio_path: str, **kwargs) -> dict[Any, Any]:  # type: ignore
        """
        Transcribe audio file to text.

        Args:
            audio_path: Path to audio file
            **kwargs: beam_size, language, etc.

        Returns:
            Dict with transcribed text and detected language
        """
        beam_size = kwargs.get("beam_size", 5)
        language = kwargs.get("language", None)

        try:
            logger.debug(f"Transcribing audio: {audio_path}")
            segments, info = self.model.transcribe(
                audio_path,
                beam_size=beam_size,
                language=language,
                vad_filter=True
            )

            text_parts = []
            for segment in segments:
                text_parts.append(segment.text)

            transcribed_text = " ".join(text_parts).strip()
            logger.debug(f"Transcription completed: {len(transcribed_text)} chars")

            return {
                "text": transcribed_text,
                "detected_language": info.language,
                "language_probability": info.language_probability
            }

        except Exception as e:
            logger.error(f"STT transcription error: {e}")
            raise
