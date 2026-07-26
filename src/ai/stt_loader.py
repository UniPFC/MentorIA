"""
STT (Speech-to-Text) loader with lazy loading and memory management.
"""

import os
import threading
import time

from faster_whisper import WhisperModel

from config.logger import logger
from config.settings import settings
from src.ai.provider.stt import FasterWhisperSTTProvider


class STTLoader:
    """
    Lazy loader for STT models with memory management and timeout.
    """

    def __init__(self):
        """Initialize STT loader with lazy loading."""
        self._model: WhisperModel | None = None
        self._provider: FasterWhisperSTTProvider | None = None
        self._lock = threading.Lock()
        self._last_used: float | None = None
        self._cache_dir = os.path.join(settings.CACHE_DIR, "models")
        self._model_size = settings.STT_MODEL
        self._compute_type = settings.STT_COMPUTE_TYPE
        self._timeout = settings.STT_TIMEOUT

        os.makedirs(self._cache_dir, exist_ok=True)
        logger.info(f"STTLoader initialized. Model: {self._model_size}, Compute: {self._compute_type}")

    def _load_model(self) -> WhisperModel:
        """
        Load the STT model with timeout for memory availability.

        Returns:
            Loaded WhisperModel instance

        Raises:
            TimeoutError: If model cannot be loaded within timeout
            RuntimeError: If STT is not enabled
        """
        if not settings.STT_ENABLED:
            raise RuntimeError("STT is not enabled in settings")

        start_time = time.time()

        while time.time() - start_time < self._timeout:
            try:
                logger.info(f"Loading STT model: {self._model_size} (compute_type={self._compute_type})")

                # Try loading from local cache first (no network requests)
                try:
                    model = WhisperModel(
                        self._model_size,
                        device="cpu",
                        compute_type=self._compute_type,
                        download_root=self._cache_dir,
                        local_files_only=True,
                    )
                    logger.info("STT model loaded from local cache")
                    return model
                except Exception:
                    logger.info("Local cache miss, downloading STT model...")
                    model = WhisperModel(
                        self._model_size,
                        device="cpu",
                        compute_type=self._compute_type,
                        download_root=self._cache_dir,
                        use_auth_token=settings.HUGGINGFACE_TOKEN,
                    )

                logger.info("STT model loaded successfully")
                return model
            except Exception as e:
                logger.warning(f"Failed to load STT model (retrying in 2s): {e}")
                time.sleep(2)

        raise TimeoutError(f"Failed to load STT model within {self._timeout} seconds")

    def get_provider(self) -> FasterWhisperSTTProvider:
        """
        Get or create STT provider with lazy loading.

        Returns:
            FasterWhisperSTTProvider instance

        Raises:
            RuntimeError: If STT is not enabled
            TimeoutError: If model cannot be loaded within timeout
        """
        if not settings.STT_ENABLED:
            raise RuntimeError("STT is not enabled in settings")

        with self._lock:
            if self._provider is None:
                model = self._load_model()
                self._model = model
                self._provider = FasterWhisperSTTProvider(model)
                self._last_used = time.time()
            else:
                self._last_used = time.time()

            return self._provider

    def unload_model(self):
        """Unload the model to free memory."""
        with self._lock:
            if self._model is not None:
                logger.info("Unloading STT model to free memory")
                del self._model
                self._model = None
                self._provider = None
                self._last_used = None

    def is_loaded(self) -> bool:
        """Check if model is currently loaded."""
        return self._model is not None

    def get_last_used(self) -> float | None:
        """Get the last time the model was used."""
        return self._last_used


# Global instance
_stt_loader: STTLoader | None = None
_loader_lock = threading.Lock()


def get_stt_loader() -> STTLoader:
    """
    Get the global STT loader instance (singleton).

    Returns:
        STTLoader instance
    """
    global _stt_loader

    with _loader_lock:
        if _stt_loader is None:
            _stt_loader = STTLoader()

    return _stt_loader
