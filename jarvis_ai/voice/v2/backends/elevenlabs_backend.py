from __future__ import annotations

import io
import threading
import time

from jarvis_ai.utils.logger import LOGGER
from jarvis_ai.voice.v2.backends.base import AbortedError
from jarvis_ai.voice.v2.capabilities import BackendCapabilities, BackendHealth
from jarvis_ai.voice.v2.playback.base import AudioPlaybackInterface
from jarvis_ai.voice.v2.playback.pygame_player import PygamePlayer


class ElevenLabsBackend:
    """Voice System 2.0 ElevenLabs backend with abort support.

    Audio is generated via the ElevenLabs SDK and played through pygame.
    The abort event is checked between chunk download and during playback
    polling, enabling sub-100ms interruption.
    """

    def __init__(self, api_key: str, voice_id: str, player: AudioPlaybackInterface | None = None) -> None:
        self._api_key = api_key
        self._voice_id = voice_id
        self._player = player or PygamePlayer()
        self._client: object | None = None
        self._capabilities = BackendCapabilities(
            supports_streaming=True,
            supports_interrupt=True,
            supports_voice_selection=True,
            supports_stream_output=True,
            offline=False,
            network_required=True,
        )
        self._health = BackendHealth()

    # -- TTSBackend protocol ---------------------------------------------------

    def speak(self, text: str, abort: threading.Event | None = None) -> None:
        if not self._health.is_available:
            raise RuntimeError("ElevenLabsBackend not available")
        if abort and abort.is_set():
            raise AbortedError("Aborted before speech")

        from elevenlabs import ElevenLabs
        client: ElevenLabs = self._client  # type: ignore[assignment]

        start = time.monotonic()
        try:
            response = client.text_to_speech.convert(
                voice_id=self._voice_id,
                text=text,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128",
            )
            # Collect chunks, checking abort between each
            chunks: list[bytes] = []
            for chunk in response:
                if abort and abort.is_set():
                    raise AbortedError("Aborted during download")
                chunks.append(chunk)
            audio_bytes = b"".join(chunks)
        except AbortedError:
            raise
        except Exception as exc:
            msg = self._extract_api_error(exc)
            LOGGER.warning("ElevenLabs API error: %s", msg)
            raise RuntimeError(f"ElevenLabs API error: {msg}") from exc

        elapsed = time.monotonic() - start
        LOGGER.info("ElevenLabs: received %d bytes in %.2fs", len(audio_bytes), elapsed)

        if not audio_bytes:
            raise RuntimeError("ElevenLabs returned empty audio")

        self._health.record_success(elapsed)
        self._player.play_bytes(audio_bytes, abort)

    def get_capabilities(self) -> BackendCapabilities:
        return self._capabilities

    def get_health(self) -> BackendHealth:
        return self._health

    def is_available(self) -> bool:
        return self._health.is_available

    def engine_name(self) -> str:
        return "elevenlabs"

    def close(self) -> None:
        self._player.close()
        self._health.is_available = False
        self._available = False

    # -- lifecycle -------------------------------------------------------------

    def apply_profile(self, profile: "VoiceProfile") -> None:
        """Apply VoiceProfile constraints to this backend."""
        voice_id = profile.backend_voice_overrides.get("elevenlabs")
        if voice_id:
            self._voice_id = voice_id

    def initialize(self) -> None:
        if not self._api_key:
            LOGGER.warning("ElevenLabs: API key missing, disabled.")
            self._health.is_available = False
            return
            
        try:
            from elevenlabs import ElevenLabs
            self._client = ElevenLabs(api_key=self._api_key)
            self._player.initialize()
        except Exception as exc:
            LOGGER.warning("ElevenLabs init failed: %s", exc)
            self._health.record_error(str(exc))
            return

        def check_connectivity():
            try:
                voices = self._client.voices.get_all()
                voice_count = len(voices.voices) if hasattr(voices, "voices") else 0
                LOGGER.info("ElevenLabs Connected -- %d voices available.", voice_count)
                self._health.record_success()
                LOGGER.info("ElevenLabsBackend initialised (voice_id=%s).", self._voice_id)
            except Exception as exc:
                LOGGER.warning("ElevenLabs connectivity check failed: %s", self._extract_api_error(exc))
                self._health.record_error(self._extract_api_error(exc), is_network_error=True)
                
        threading.Thread(target=check_connectivity, name="ElevenLabsInit", daemon=True).start()

    @staticmethod
    def _extract_api_error(exc: Exception) -> str:
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
