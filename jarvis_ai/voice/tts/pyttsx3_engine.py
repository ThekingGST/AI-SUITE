from __future__ import annotations

from typing import Any

from config import CONFIG
from utils.logger import LOGGER


class Pyttsx3Engine:
    """Thread-owned pyttsx3 / Windows SAPI engine.

    COM is initialised inside :meth:`initialize` which **must** be called on
    the same thread that will later call :meth:`speak`.  This matches the
    existing JARVIS architecture where the worker thread owns COM.
    """

    def __init__(self) -> None:
        self._engine: Any | None = None
        self._com_initialized = False
        self._pythoncom: Any | None = None
        self._available = False
        self._selected_voice_id: str = ""

    # -- TTSEngine protocol ---------------------------------------------------

    def speak(self, text: str) -> None:
        if not self._available:
            raise RuntimeError("Pyttsx3Engine not initialised")
        # Workaround: pyttsx3's runAndWait() corrupts the engine's internal
        # event-loop state on Windows SAPI, causing all subsequent calls to
        # return instantly without producing audio.  Recreating the engine
        # before each utterance is cheap (~30ms) and fully fixes the issue.
        # COM stays alive on the worker thread -- only the pyttsx3 wrapper
        # is recycled.
        self._recreate_engine()
        self._engine.say(text)
        self._engine.runAndWait()

    def is_available(self) -> bool:
        return self._available

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
        self._available = False

    # -- lifecycle (called on worker thread) -----------------------------------

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
        LOGGER.info("TTS ENGINE: pyttsx3 initialised.")

    # -- internal --------------------------------------------------------------

    def _recreate_engine(self) -> None:
        """Destroy and recreate the pyttsx3 engine.

        This works around a pyttsx3 bug where ``runAndWait()`` leaves the
        class-level ``Engine._inLoop`` flag stuck at ``True``, causing every
        subsequent ``runAndWait()`` to return instantly without producing
        audio.  The fix is to ``stop()`` + ``del`` the old engine, reset the
        class-level flag, and create a fresh instance.

        COM initialisation is kept alive -- only the pyttsx3 wrapper object
        is recycled (~30 ms overhead).
        """
        import pyttsx3

        if self._engine:
            try:
                self._engine.stop()
            except Exception:
                pass
            self._engine = None

        # Reset the class-level flag that pyttsx3 leaves stuck after
        # runAndWait().  Without this, pyttsx3.init() returns a cached
        # (broken) singleton.
        try:
            pyttsx3.engine.Engine._inLoop = False
        except AttributeError:
            pass

        self._engine = pyttsx3.init()
        self._apply_settings()

    def _apply_settings(self) -> None:
        """Apply cached voice/rate/volume settings without log spam."""
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
            LOGGER.info(
                "Available voice: %s | %s | %s",
                voice_id,
                voice_name,
                voice_languages,
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
        LOGGER.info("Speech rate: %s", CONFIG.voice.speech_rate)
