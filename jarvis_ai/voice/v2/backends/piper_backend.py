from __future__ import annotations

import threading
import wave
import tempfile
import os
from typing import Optional

from jarvis_ai.utils.logger import LOGGER
from jarvis_ai.voice.v2.backends.base import TTSBackend, AbortedError
from jarvis_ai.voice.v2.capabilities import BackendCapabilities, BackendHealth
from jarvis_ai.voice.v2.profile import VoiceProfile
from shared.models.model_registry import ModelRegistry

try:
    from piper.voice import PiperVoice
    import sounddevice as sd
    import numpy as np
    PIPER_AVAILABLE = True
except ImportError:
    PIPER_AVAILABLE = False


class PiperBackend(TTSBackend):
    def __init__(self) -> None:
        self.profile = None
        self.name = "piper"
        self._voice: Optional[PiperVoice] = None
        self._health = BackendHealth(is_available=PIPER_AVAILABLE)
        self._current_model_path: str = ""

    def apply_profile(self, profile: VoiceProfile) -> None:
        self.profile = profile

    def _load_model(self) -> bool:
        if not PIPER_AVAILABLE:
            self._health = BackendHealth(is_available=False, last_error="piper-tts or sounddevice not installed.")
            return False
            
        try:
            registry = ModelRegistry()
            
            # Default to en-us Piper model, but override if specified
            model_name = "piper-en-us"
            language = self.profile.language if self.profile else "en"
            if language == "hi":
                model_name = "piper-hi-in"
            elif language == "te":
                model_name = "piper-te-in"
                
            model_info = registry.get_info(model_name)
            
            if not model_info:
                LOGGER.warning("Piper model info not found for %s, falling back to en-us.", model_name)
                model_info = registry.get_info("piper-en-us")
                
            if not model_info:
                raise FileNotFoundError("No Piper models registered.")
                
            model_path = registry.get_model_path(model_info.name)
            if not model_path or not model_path.exists():
                raise FileNotFoundError(f"Piper model not found at {model_path}")
                
            model_path_str = str(model_path)
            
            # Re-load if model changed
            if self._voice is None or self._current_model_path != model_path_str:
                self._voice = PiperVoice.load(model_path_str)
                self._current_model_path = model_path_str
                
            self._health = BackendHealth(is_available=True)
            return True
        except Exception as e:
            LOGGER.error("Piper load failed: %s", e)
            self._health = BackendHealth(is_available=False, last_error=str(e))
            return False

    def speak(self, text: str, abort: threading.Event | None = None) -> None:
        if abort and abort.is_set():
            raise AbortedError()
            
        if not self._load_model():
            LOGGER.warning("Piper model not loaded, skipping speak.")
            raise RuntimeError("Piper model not loaded")
            
        try:
            # Piper stream generation
            audio_stream = self._voice.synthesize_stream_raw(text)
            
            # Piper output is raw PCM, default sample rate is often 22050
            sample_rate = self._voice.config.sample_rate
            
            def play_chunk(chunk):
                # Piper generates 16-bit PCM chunks
                audio_np = np.frombuffer(chunk, dtype=np.int16)
                sd.play(audio_np, sample_rate, blocking=False)
                while sd.wait(0.1):
                    if abort and abort.is_set():
                        sd.stop()
                        raise AbortedError()
            
            for chunk in audio_stream:
                if abort and abort.is_set():
                    raise AbortedError()
                play_chunk(chunk)
                
        except AbortedError:
            raise
        except Exception as e:
            LOGGER.error("Piper playback failed: %s", e)
            if abort and abort.is_set():
                raise AbortedError()

    def get_capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            supports_streaming=True,
            offline=True,
        )

    def get_health(self) -> BackendHealth:
        if not PIPER_AVAILABLE:
            return BackendHealth(is_available=False, last_error="piper-tts not installed.")
        return self._health

    def is_available(self) -> bool:
        return self.get_health().is_available

    def engine_name(self) -> str:
        return self.name

    def close(self) -> None:
        self._voice = None
