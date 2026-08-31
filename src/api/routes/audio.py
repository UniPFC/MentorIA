"""
Audio endpoints for speech-to-text transcription.
"""

import os

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from config.logger import logger
from config.settings import settings
from shared.database.models.user import User
from src.api.dependencies import get_current_active_user

router = APIRouter(prefix="/audio", tags=["audio"])

MAX_AUDIO_SIZE = 15 * 1024 * 1024  # 15 MB limit


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
    language: str | None = None,
    current_user: User = Depends(get_current_active_user),
):
    """
    Transcribe audio file to text using Speech-to-Text.

    Args:
        audio: Audio file (WAV, MP3, M4A, etc.)
        language: Optional language code (e.g., 'pt', 'en'). Auto-detect if not provided.
        current_user: Authenticated active user (JWT Token required).

    Returns:
        Transcribed text with metadata

    Raises:
        HTTPException: If STT is disabled, unauthorized, file too large, or transcription fails
    """
    if not settings.STT_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Speech-to-Text is not enabled",
        )

    # Validate file type
    allowed_extensions = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm"}
    file_ext = os.path.splitext(audio.filename or "")[1].lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}",
        )

    try:
        content = await audio.read()

        # Validate file size (15 MB limit)
        if len(content) > MAX_AUDIO_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Tamanho do arquivo de áudio excede o limite máximo permitido de 15MB.",
            )

        logger.info(f"Forwarding audio {audio.filename} to worker for transcription")

        async with httpx.AsyncClient(timeout=None) as client:
            files = {
                "audio": (audio.filename or "audio.webm", content, audio.content_type)
            }
            data = {"language": language} if language else {}

            response = await client.post(
                f"{settings.AI_WORKER_URL}/internal/transcribe",
                data=data,
                files=files,
                headers={"X-Internal-Token": settings.INTERNAL_API_KEY},
            )
            response.raise_for_status()
            result = response.json()

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
            language_probability=language_probability,
        )

    except httpx.HTTPError as e:
        logger.error(f"Error calling AI worker for STT: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ocorreu um erro ao processar o áudio. Tente novamente.",
        )
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {str(e)}",
        )
