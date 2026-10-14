from __future__ import annotations

from utils.logger import LOGGER
from voice.tts.elevenlabs_engine import ElevenLabsEngine
from voice.tts.pyttsx3_engine import Pyttsx3Engine


class TTSManager:
    """Manages primary + fallback TTS engines with automatic failover.

    Initialisation and all ``speak()`` calls happen on the Speaker's worker
    thread — no additional synchronisation is needed here.

    Failover behaviour:
        * If the primary engine fails on a given utterance, the fallback is
          tried immediately for **that utterance**.
        * The primary engine remains the default for the *next* utterance —
          transient network blips do not permanently demote it.
    """

    def __init__(
        self,
        tts_engine: str,
        elevenlabs_api_key: str,
        elevenlabs_voice_id: str,
    ) -> None:
        self._requested_engine = tts_engine.lower().strip()
        self._api_key = elevenlabs_api_key
        self._voice_id = elevenlabs_voice_id

        self._primary: Pyttsx3Engine | ElevenLabsEngine | None = None
        self._fallback: Pyttsx3Engine | None = None
        self._active_name: str = "initializing"

    # -- public API -----------------------------------------------------------

    @property
    def active_engine_name(self) -> str:
        """Name of the engine that handled the most recent utterance."""
        return self._active_name

    def speak(self, text: str) -> None:
        """Synthesize *text* using the primary engine, falling back on error."""
        # Try primary engine.
        if self._primary and self._primary.is_available():
            try:
                self._primary.speak(text)
                self._active_name = self._primary.engine_name()
                return
            except Exception as exc:
                LOGGER.warning(
                    "Primary TTS (%s) failed: %s -- falling back.",
                    self._primary.engine_name(),
                    exc,
                )

        # Fallback to pyttsx3.
        if self._fallback and self._fallback.is_available():
            try:
                LOGGER.info("TTS ENGINE: pyttsx3 (fallback)")
                self._fallback.speak(text)
                self._active_name = "pyttsx3"
                return
            except Exception as exc:
                LOGGER.exception("Fallback TTS (pyttsx3) also failed: %s", exc)

        LOGGER.error("All TTS engines failed -- speech dropped: %s", text)

    def close(self) -> None:
        if self._primary:
            self._primary.close()
        if self._fallback and self._fallback is not self._primary:
            self._fallback.close()

    # -- lifecycle (called on worker thread) -----------------------------------

    def initialize(self) -> None:
        """Initialise engines on the worker thread.

        Always brings up pyttsx3 first (safe baseline), then attempts
        ElevenLabs if configured.
        """
        # 1. Always initialise pyttsx3 as the safe baseline.
        pyttsx3_engine = Pyttsx3Engine()
        try:
            pyttsx3_engine.initialize()
            LOGGER.info("ElevenLabs Fallback Active -- pyttsx3 ready as fallback.")
        except Exception as exc:
            LOGGER.exception("pyttsx3 initialisation failed: %s", exc)
            pyttsx3_engine = None  # type: ignore[assignment]

        # 2. Attempt ElevenLabs if requested.
        if self._requested_engine == "elevenlabs" and self._api_key:
            LOGGER.info("ElevenLabs Available -- API key found.")
            elevenlabs_engine = ElevenLabsEngine(self._api_key, self._voice_id)
            try:
                elevenlabs_engine.initialize()
                if elevenlabs_engine.is_available():
                    LOGGER.info("ElevenLabs Connected -- engine online.")
                    self._primary = elevenlabs_engine
                    self._fallback = pyttsx3_engine
                    self._active_name = "elevenlabs"
                    LOGGER.info("TTS ENGINE: ElevenLabs")
                    return
                else:
                    LOGGER.warning(
                        "ElevenLabs engine not available after init -- "
                        "using pyttsx3 as primary."
                    )
                    elevenlabs_engine.close()
            except Exception as exc:
                LOGGER.warning("ElevenLabs init failed: %s -- using pyttsx3.", exc)
                elevenlabs_engine.close()

        elif self._requested_engine == "elevenlabs" and not self._api_key:
            LOGGER.warning(
                "TTS_ENGINE set to 'elevenlabs' but ELEVENLABS_API_KEY is empty -- "
                "falling back to pyttsx3."
            )

        # 3. pyttsx3 as primary (either requested or ElevenLabs unavailable).
        self._primary = pyttsx3_engine
        self._fallback = None
        self._active_name = "pyttsx3" if pyttsx3_engine and pyttsx3_engine.is_available() else "unavailable"
        LOGGER.info("TTS ENGINE: pyttsx3")
