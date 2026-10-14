from __future__ import annotations

import threading
import time
from typing import Optional

from jarvis_ai.utils.logger import LOGGER
from jarvis_ai.voice.v2.backends.base import TTSBackend, AbortedError
from jarvis_ai.voice.v2.capabilities import BackendCapabilities, BackendHealth
from jarvis_ai.voice.v2.profile import VoiceProfile
from shared.models.model_registry import ModelRegistry

try:
    # Requires kokoro-onnx and sounddevice
    from kokoro_onnx import Kokoro
    import sounddevice as sd
    KOKORO_AVAILABLE = True
except ImportError:
    KOKORO_AVAILABLE = False


class KokoroBackend(TTSBackend):
    def __init__(self) -> None:
        self.profile = None
        self.name = "kokoro"
        self._kokoro: Optional[Kokoro] = None
        self._health = BackendHealth(is_available=KOKORO_AVAILABLE)

    def apply_profile(self, profile: VoiceProfile) -> None:
        self.profile = profile

    def _load_model(self) -> bool:
        if self._kokoro is not None:
            return True
        if not KOKORO_AVAILABLE:
            self._health = BackendHealth(is_available=False, last_error="kokoro-onnx or sounddevice not installed.")
            return False
            
        try:
            registry = ModelRegistry()
            model_info = registry.get_info("kokoro-v1")
            
            if not model_info:
                raise FileNotFoundError("Kokoro model info not found in registry.")
                
            model_path = registry.get_model_path(model_info.name)
            
            if not model_path or not model_path.exists():
                # For Kokoro, voices are usually stored adjacent to the model
                # or downloaded. Assuming a local ONNX file path is needed.
                # If missing, we can't initialize.
                raise FileNotFoundError(f"Kokoro model not found at {model_path}")
                
            # Voices path - fallback to model directory
            voices_json_path = model_path.parent / "voices.json"
            
            # Initialize Kokoro
            self._kokoro = Kokoro(str(model_path), str(voices_json_path))
            self._health = BackendHealth(is_available=True)
            return True
        except Exception as e:
            LOGGER.error("Kokoro load failed: %s", e)
            self._health = BackendHealth(is_available=False, last_error=str(e))
            return False

    def speak(self, text: str, abort: threading.Event | None = None) -> None:
        if abort and abort.is_set():
            raise AbortedError()
            
        if not self._load_model():
            LOGGER.warning("Kokoro model not loaded, skipping speak.")
            raise RuntimeError("Kokoro model not loaded")
            
        try:
            voice_id = self.profile.backend_voice_overrides.get("kokoro", "af_heart") if self.profile else "af_heart"
            language = self.profile.language if self.profile else "en"
            speed = self.profile.speed if self.profile else 1.0
            
            # For Hindi vs English, choose appropriate voice.
            if language == "hi":
                voice_id = self.profile.backend_voice_overrides.get("kokoro", "hi_IN_default") if self.profile else "hi_IN_default"
                
            # Kokoro create stream
            samples, sample_rate = self._kokoro.create(
                text, voice=voice_id, speed=speed, lang="en-us" if language == "en" else language
            )
            
            if abort and abort.is_set():
                raise AbortedError()
                
            # Play samples
            sd.play(samples, sample_rate)
            
            # Block until playback completes or abort is set
            while sd.wait(0.1):
                if abort and abort.is_set():
                    sd.stop()
                    raise AbortedError()
                    
        except Exception as e:
            LOGGER.error("Kokoro playback failed: %s", e)
            if abort and abort.is_set():
                raise AbortedError()

    def get_capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            supports_streaming=True,
            offline=True,
        )

    def get_health(self) -> BackendHealth:
        if not KOKORO_AVAILABLE:
            return BackendHealth(is_available=False, last_error="kokoro-onnx not installed.")
        return self._health

    def is_available(self) -> bool:
        return self.get_health().is_available

    def engine_name(self) -> str:
        return self.name

    def close(self) -> None:
        if self._kokoro:
            self._kokoro = None
