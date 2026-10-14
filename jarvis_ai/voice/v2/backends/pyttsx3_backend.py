from __future__ import annotations

import threading
from typing import Any

from jarvis_ai.config import CONFIG
from jarvis_ai.utils.logger import LOGGER
from jarvis_ai.voice.v2.backends.base import AbortedError
from jarvis_ai.voice.v2.capabilities import BackendCapabilities, BackendHealth


class Pyttsx3Backend:
    """Voice System 2.0 pyttsx3 backend.

    Wraps the existing pyttsx3/Windows SAPI engine with V2 abort support.
    pyttsx3 cannot be interrupted mid-utterance, so the abort check occurs
    *before* starting and the engine completes atomically if already started.

    COM is initialised inside ``initialize()`` which **must** be called on
    the same thread that will later call ``speak()``.
    """

    def __init__(self) -> None:
        self._engine: Any | None = None
        self._com_initialized = False
        self._pythoncom: Any | None = None
        self._available = False
        self._selected_voice_id: str = ""
        self._capabilities = BackendCapabilities(
            supports_streaming=False,
            supports_interrupt=False, # only between chunks
            supports_rate=True,
            supports_volume=True,
            supports_voice_selection=True,
            offline=True,
            network_required=False,
        )
        self._health = BackendHealth()

    # -- TTSBackend protocol ---------------------------------------------------

    def speak(self, text: str, abort: threading.Event | None = None) -> None:
        if not self._available:
            raise RuntimeError("Pyttsx3Backend not initialised")
        if abort and abort.is_set():
            raise AbortedError("Aborted before speech")
            
        try:
            self._engine.say(text)
            self._engine.runAndWait()
        except Exception as exc:
            # If SAPI breaks, we attempt to resurrect the engine for the next call
            LOGGER.warning("pyttsx3 execution failed: %s", exc)
            self._recreate_engine()
            
        # Post-playback abort check: signal that we noticed the abort
        if abort and abort.is_set():
            raise AbortedError("Aborted after speech completed")

    def get_capabilities(self) -> BackendCapabilities:
        return self._capabilities

    def get_health(self) -> BackendHealth:
        return self._health

    def is_available(self) -> bool:
        return self._health.is_available

    def engine_name(self) -> str:
        return "pyttsx3"

    def close(self) -> None:
        if self._engine:
            try:
                self._engine.stop()
            except Exception as exc:
                LOGGER.warning("pyttsx3 engine stop failed: %s", exc)
            self._engine = None
        if self._com_initialized and self._pythoncom:
            try:
                self._pythoncom.CoUninitialize()
            except Exception as exc:
                LOGGER.warning("COM uninitialise failed: %s", exc)
            self._com_initialized = False
        self._health.is_available = False

    # -- lifecycle (called on worker thread) -----------------------------------

    def apply_profile(self, profile: "VoiceProfile") -> None:
        """Apply VoiceProfile constraints to this backend."""
        # Optional: override specific voice ID if provided for Windows SAPI
        voice_id = profile.backend_voice_overrides.get("pyttsx3")
        if voice_id:
            self._selected_voice_id = voice_id
            if self._engine:
                self._engine.setProperty("voice", self._selected_voice_id)

    def initialize(self) -> None:
        """Set up COM and the pyttsx3 engine.  Call on the worker thread."""
        try:
            import pythoncom as _pythoncom
            self._pythoncom = _pythoncom
            self._pythoncom.CoInitialize()
            self._com_initialized = True
        except Exception as exc:
            LOGGER.warning("COM initialisation skipped: %s", exc)

        import pyttsx3
        self._engine = pyttsx3.init()
        self._configure()
        self._available = True
        self._health.record_success()
        LOGGER.info("Pyttsx3Backend initialised.")

    # -- internal --------------------------------------------------------------

    def _recreate_engine(self) -> None:
        import pyttsx3
        if self._engine:
            try:
                self._engine.stop()
            except Exception:
                pass
            self._engine = None
        try:
            pyttsx3.engine.Engine._inLoop = False
        except AttributeError:
            pass
        self._engine = pyttsx3.init()
        self._apply_settings()

    def _apply_settings(self) -> None:
        if not self._engine:
            return
        if self._selected_voice_id:
            self._engine.setProperty("voice", self._selected_voice_id)
        self._engine.setProperty("rate", CONFIG.voice.speech_rate)
        self._engine.setProperty("volume", CONFIG.voice.speech_volume)

    def _configure(self) -> None:
        if not self._engine:
            return
        voices = self._engine.getProperty("voices") or []
        self._selected_voice_id = ""
        for voice in voices:
            voice_id = str(getattr(voice, "id", ""))
            voice_name = str(getattr(voice, "name", ""))
            voice_languages = " ".join(
                str(item) for item in getattr(voice, "languages", []) or []
            )
            searchable = f"{voice_id} {voice_name} {voice_languages}".lower()
            if not self._selected_voice_id and (
                "english" in searchable
                or " en" in searchable
                or "en_" in searchable
            ):
                self._selected_voice_id = voice_id
        if self._selected_voice_id:
            self._engine.setProperty("voice", self._selected_voice_id)
        self._engine.setProperty("rate", CONFIG.voice.speech_rate)
        self._engine.setProperty("volume", CONFIG.voice.speech_volume)
        LOGGER.info("Selected voice: %s", self._selected_voice_id or "system default")
