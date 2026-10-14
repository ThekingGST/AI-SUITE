from __future__ import annotations

import io
import tempfile
import time
from pathlib import Path

from utils.logger import LOGGER

# Timeout for the ElevenLabs API call (seconds).
_API_TIMEOUT_SECONDS = 15


class ElevenLabsEngine:
    """ElevenLabs cloud TTS engine with pygame-based audio playback.

    Audio is generated via the official ``elevenlabs`` Python SDK and played
    locally through ``pygame.mixer``.  The engine is fully self-contained —
    it manages its own mixer lifecycle and network session.

    No caching or streaming in V1: every call does a full-buffer API request.
    """

    def __init__(self, api_key: str, voice_id: str) -> None:
        self._api_key = api_key
        self._voice_id = voice_id
        self._available = False
        self._mixer_initialized = False
        self._client: object | None = None

    # -- TTSEngine protocol ---------------------------------------------------

    def speak(self, text: str) -> None:
        """Generate speech via ElevenLabs and play it locally.

        Blocks until playback completes so ``Speaker._speaking`` stays
        accurate for mic-pause and orb indicators.
        """
        if not self._available:
            raise RuntimeError("ElevenLabsEngine not available")

        from elevenlabs import ElevenLabs

        client: ElevenLabs = self._client  # type: ignore[assignment]

        # Generate audio (full-buffer, no streaming).
        LOGGER.info("TTS ENGINE: ElevenLabs -- generating audio...")
        start = time.monotonic()
        try:
            response = client.text_to_speech.convert(
                voice_id=self._voice_id,
                text=text,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128",
            )

            # The SDK returns a generator of bytes; collect into a buffer.
            audio_bytes = b"".join(chunk for chunk in response)
        except Exception as exc:
            # Extract human-readable message from API errors.
            msg = self._extract_api_error(exc)
            LOGGER.warning("ElevenLabs API error: %s", msg)
            raise RuntimeError(f"ElevenLabs API error: {msg}") from exc

        elapsed = time.monotonic() - start
        LOGGER.info(
            "TTS ENGINE: ElevenLabs -- received %d bytes in %.2fs",
            len(audio_bytes),
            elapsed,
        )

        if not audio_bytes:
            raise RuntimeError("ElevenLabs returned empty audio")

        self._play_audio(audio_bytes)

    def is_available(self) -> bool:
        return self._available

    def engine_name(self) -> str:
        return "elevenlabs"

    def close(self) -> None:
        if self._mixer_initialized:
            try:
                import pygame

                pygame.mixer.quit()
            except Exception as exc:
                LOGGER.warning("pygame mixer quit failed: %s", exc)
            self._mixer_initialized = False
        self._client = None
        self._available = False

    # -- lifecycle -------------------------------------------------------------

    def initialize(self) -> None:
        """Validate API key and initialise pygame mixer.

        Call on the worker thread (same thread that will call speak()).
        """
        if not self._api_key:
            LOGGER.warning("ElevenLabs API key not set -- engine disabled.")
            return

        # Import and create client.
        try:
            from elevenlabs import ElevenLabs
        except ImportError:
            LOGGER.warning("elevenlabs package not installed -- engine disabled.")
            return

        self._client = ElevenLabs(api_key=self._api_key)

        # Initialise pygame mixer for audio playback.
        try:
            import pygame

            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
            self._mixer_initialized = True
        except Exception as exc:
            LOGGER.warning("pygame mixer init failed: %s -- engine disabled.", exc)
            self._client = None
            return

        # Connectivity check: verify the API key is valid.
        try:
            voices = self._client.voices.get_all()
            voice_count = len(voices.voices) if hasattr(voices, "voices") else 0
            LOGGER.info("ElevenLabs Connected -- %d voices available.", voice_count)
        except Exception as exc:
            LOGGER.warning("ElevenLabs connectivity check failed: %s", self._extract_api_error(exc))
            LOGGER.info("ElevenLabs will attempt to work despite failed connectivity check.")

        self._available = True
        LOGGER.info("TTS ENGINE: ElevenLabs initialised (voice_id=%s).", self._voice_id)

    # -- internal --------------------------------------------------------------

    @staticmethod
    def _extract_api_error(exc: Exception) -> str:
        """Extract a human-readable message from an ElevenLabs API exception."""
        body = getattr(exc, "body", None)
        if isinstance(body, dict):
            detail = body.get("detail", {})
            if isinstance(detail, dict):
                return detail.get("message", str(exc))
            return str(detail)
        status = getattr(exc, "status_code", None)
        if status:
            return f"HTTP {status}: {exc}"
        return str(exc)

    def _play_audio(self, audio_bytes: bytes) -> None:
        """Play MP3 audio bytes through pygame.mixer and block until done."""
        import pygame

        try:
            sound = pygame.mixer.Sound(io.BytesIO(audio_bytes))
            channel = sound.play()
            if channel:
                while channel.get_busy():
                    pygame.time.wait(50)
        except Exception as exc:
            LOGGER.warning("pygame playback failed: %s", exc)
            raise
