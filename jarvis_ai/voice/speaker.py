from __future__ import annotations

import queue
import re
import threading
import time
from dataclasses import dataclass
from typing import Any

from jarvis_ai.config import CONFIG, DATA_DIR
from jarvis_ai.utils.logger import LOGGER

# ---------------------------------------------------------------------------
# Voice-mode persistence
# ---------------------------------------------------------------------------

_VOICE_MODE_FILE = DATA_DIR / "voice_mode.txt"

_MODE_TO_PROFILE = {
    "standard": "jarvis",
    "premium": "jarvis",
    "jarvis": "jarvis",
    "friday": "friday",
    "edith": "edith",
}

def _load_voice_mode() -> str:
    """Load persisted voice mode.  Returns ``'standard'`` or ``'premium'``."""
    try:
        mode = _VOICE_MODE_FILE.read_text(encoding="utf-8").strip().lower()
        if mode in _MODE_TO_PROFILE:
            return mode
    except (FileNotFoundError, OSError):
        pass
    return "standard"


def _save_voice_mode(mode: str) -> None:
    """Persist the current voice mode to disk."""
    try:
        _VOICE_MODE_FILE.write_text(mode, encoding="utf-8")
    except OSError as exc:
        LOGGER.warning("Failed to save voice mode: %s", exc)


# ---------------------------------------------------------------------------
# Speech job
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SpeechJob:
    text: str | None = None
    shutdown: bool = False
    switch_mode: str | None = None  # "standard" or "premium"


# ---------------------------------------------------------------------------
# Speaker (V2 Compatibility Layer)
# ---------------------------------------------------------------------------

class Speaker:
    """Legacy API preserved for backward compatibility.
    
    Internally delegates to the V2 SpeechManager. Existing callers
    do not need to be updated immediately.
    """

    def __init__(self) -> None:
        from jarvis_ai.voice.v2.speech_manager import SpeechManager
        from jarvis_ai.voice.v2.events import VoiceEventBus
        from jarvis_ai.voice.v2.backends.registry import TTSBackendRegistry
        from jarvis_ai.voice.v2.backends.edge_tts_backend import EdgeTtsBackend
        from jarvis_ai.voice.v2.profile import DEFAULT_PROFILES
        from jarvis_ai.config import CONFIG
        
        self.event_bus = VoiceEventBus()
        self.registry = TTSBackendRegistry()
        
        # Register Edge-TTS
        self.registry.register(CONFIG.voice.default_tts_backend, EdgeTtsBackend())
        
        # Register Pyttsx3 (Offline Fallback)
        from jarvis_ai.voice.v2.backends.pyttsx3_backend import Pyttsx3Backend
        self.registry.register("pyttsx3", Pyttsx3Backend())
        
        # Note: ElevenLabs backend exists in codebase but is intentionally
        # disabled and not initialized in production per requirements.
            
        self._speech_manager = SpeechManager(self.registry, self.event_bus)
        
        # Load persisted mode and apply
        self._voice_mode: str = _load_voice_mode()
        profile_name = _MODE_TO_PROFILE.get(self._voice_mode, "jarvis")
        self._speech_manager.set_profile(DEFAULT_PROFILES[profile_name])
        
        # Start worker
        self._speech_manager.start()
        
        self.speak("Systems online.")

    @property
    def enabled(self) -> bool:
        return self._speech_manager.enabled

    @property
    def is_speaking(self) -> bool:
        return self._speech_manager.is_speaking

    @property
    def active_engine_name(self) -> str:
        return self._speech_manager.active_profile_name

    @property
    def voice_mode(self) -> str:
        return self._speech_manager.voice_mode

    @property
    def manager(self):
        """Allow direct access to the underlying SpeechManager."""
        return self._speech_manager

    def set_enabled(self, enabled: bool) -> None:
        self._speech_manager.set_enabled(enabled)

    def set_voice_mode(self, mode: str) -> None:
        if mode not in _MODE_TO_PROFILE:
            LOGGER.warning("Unknown voice mode: %s", mode)
            return
        if mode == self._voice_mode:
            return
        self._voice_mode = mode
        _save_voice_mode(mode)
        
        from jarvis_ai.voice.v2.profile import DEFAULT_PROFILES
        profile_name = _MODE_TO_PROFILE.get(mode, "offline")
        self._speech_manager.set_profile(DEFAULT_PROFILES[profile_name])

    def say(self, text: str) -> None:
        self.speak(text)

    def speak(self, text: str) -> None:
        from jarvis_ai.voice.v2.types import SpeechPriority
        self._speech_manager.enqueue(text, SpeechPriority.NORMAL)

    def recently_spoke(self, seconds: float = 1.0) -> bool:
        return self._speech_manager.recently_spoke(seconds)

    def interrupt(self) -> None:
        self._speech_manager.interrupt()

    def close(self) -> None:
        self._speech_manager.close()
