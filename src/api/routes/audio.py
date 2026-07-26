"""
Audio endpoints for speech-to-text transcription.
"""

import os
import tempfile
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from config.logger import logger
from config.settings import settings
from src.ai.stt_loader import get_stt_loader

router = APIRouter(prefix="/audio", tags=["audio"])


class TranscribeResponse(BaseModel):
    """Response model for audio transcription."""
    text: str
    duration: float | None = None
    language: str | None = None
    detected_language: str | None = None
    language_probability: float | None = None


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str | None = None
):
    """
    Transcribe audio file to text using Speech-to-Text.

    Args:
        audio: Audio file (WAV, MP3, M4A, etc.)
        language: Optional language code (e.g., 'pt', 'en'). Auto-detect if not provided.

    Returns:
        Transcribed text with metadata

    Raises:
        HTTPException: If STT is disabled or transcription fails
    """
    if not settings.STT_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Speech-to-Text is not enabled"
        )

    # Validate file type
    allowed_extensions = {'.wav', '.mp3', '.m4a', '.ogg', '.flac', '.webm'}
    file_ext = os.path.splitext(audio.filename)[1].lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}"
        )

    # Save to temporary file
    temp_filename = f"{uuid.uuid4()}{file_ext}"
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_path = temp_file.name
            content = await audio.read()
            temp_file.write(content)
            temp_file.flush()

        logger.info(f"Transcribing audio: {audio.filename} -> {temp_path}")

        # Get STT provider and transcribe
        stt_loader = get_stt_loader()
        provider = stt_loader.get_provider()

        result = provider.transcribe(
            temp_path,
            language=language,
            beam_size=5
        )

        transcribed_text = result["text"]
        detected_language = result["detected_language"]
        language_probability = result["language_probability"]

        # Use detected language if confidence is high, otherwise use request language
        final_language = detected_language if language_probability > 0.8 else language

        logger.info(f"Transcription completed: {len(transcribed_text)} chars")

        return TranscribeResponse(
            text=transcribed_text,
            language=final_language,
            detected_language=detected_language,
            language_probability=language_probability
        )

    except TimeoutError as e:
        logger.error(f"STT timeout: {e}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Failed to load STT model: insufficient memory or timeout"
        )
    except RuntimeError as e:
        logger.error(f"STT runtime error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {str(e)}"
        )
    finally:
        # Clean up temporary file
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
                logger.debug(f"Cleaned up temporary file: {temp_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp file {temp_path}: {e}")
