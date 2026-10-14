from __future__ import annotations

from typing import Optional

from jarvis_ai.utils.logger import LOGGER
from jarvis_ai.voice.input.pipeline import AudioProcessor
from jarvis_ai.voice.input.capture import AudioFrame
from jarvis_ai.voice.input.profile import AudioProfile

class STTBackendRouter(AudioProcessor):
    def __init__(self, profile: AudioProfile, sample_rate: int = 16000, preferred_backend: str = 'vosk') -> None:
        self._backend_instance = None
        super().__init__()
        self.profile = profile
        self.sample_rate = sample_rate
        self.preferred_backend = preferred_backend
        self._active_backend = 'none'
        
        self.preferred_language = "en"
        self.set_backend(self.preferred_backend)

    def set_language(self, language: str) -> None:
        self.preferred_language = language
        if language in ['hi', 'te']:
            self.set_backend('whisper', strict=True)
        elif language == 'en':
            self.set_backend('vosk', strict=False)
        else: # auto
            self.set_backend('auto', strict=False)
            
        if hasattr(self._backend_instance, 'set_language'):
            self._backend_instance.set_language(language)

    def set_backend(self, name: str, strict: bool = False) -> None:
        from jarvis_ai.voice.input.stt.vosk_backend import VoskBackend, VOSK_AVAILABLE
        from jarvis_ai.voice.input.stt.faster_whisper_backend import FasterWhisperBackend, FASTER_WHISPER_AVAILABLE
        from jarvis_ai.voice.input.events import AudioEvent
        
        try:
            if name == 'auto':
                if FASTER_WHISPER_AVAILABLE:
                    self._backend_instance = FasterWhisperBackend(self.profile, self.sample_rate)
                    self._active_backend = 'whisper'
                elif VOSK_AVAILABLE:
                    self._backend_instance = VoskBackend(self.profile, self.sample_rate)
                    self._active_backend = 'vosk'
                else:
                    LOGGER.error("Neither Vosk nor FasterWhisper is available.")
                    self._active_backend = 'none'
                    self._backend_instance = None
                    
            elif name == 'whisper':
                if FASTER_WHISPER_AVAILABLE:
                    self._backend_instance = FasterWhisperBackend(self.profile, self.sample_rate)
                    self._active_backend = 'whisper'
                elif strict:
                    LOGGER.error("Multilingual STT model unavailable; multilingual recognition cannot be performed.")
                    if hasattr(self, 'event_bus') and self.event_bus:
                        self.event_bus.emit(AudioEvent.RECOGNITION_FAILED, {"error": "Telugu/Hindi speech recognition isn't available because the multilingual STT model is missing. Please install the multilingual model or switch to English."})
                    self._active_backend = 'none'
                    self._backend_instance = None
                elif VOSK_AVAILABLE:
                    LOGGER.warning("Whisper requested but not available. Falling back to Vosk.")
                    self._backend_instance = VoskBackend(self.profile, self.sample_rate)
                    self._active_backend = 'vosk'
                else:
                    LOGGER.error("No STT backends available.")
                    self._active_backend = 'none'
                    self._backend_instance = None
                    
            elif name == 'vosk':
                if VOSK_AVAILABLE:
                    self._backend_instance = VoskBackend(self.profile, self.sample_rate)
                    self._active_backend = 'vosk'
                elif strict:
                    LOGGER.error("Vosk requested but not available.")
                    self._active_backend = 'none'
                    self._backend_instance = None
                elif FASTER_WHISPER_AVAILABLE:
                    LOGGER.warning("Vosk requested but not available. Falling back to Whisper.")
                    self._backend_instance = FasterWhisperBackend(self.profile, self.sample_rate)
                    self._active_backend = 'whisper'
                else:
                    LOGGER.error("No STT backends available.")
                    self._active_backend = 'none'
                    self._backend_instance = None
                    
            if self._backend_instance and hasattr(self, 'event_bus') and self.event_bus:
                self._backend_instance.event_bus = self.event_bus
                
        except Exception as e:
            LOGGER.error(f"Failed to set backend {name}: {e}")

    def update_profile(self, profile: AudioProfile) -> None:
        self.profile = profile
        if self._backend_instance and hasattr(self._backend_instance, 'update_profile'):
            self._backend_instance.update_profile(profile)

    def get_active_backend(self) -> str:
        return self._active_backend

    @property
    def event_bus(self):
        return self._event_bus

    @event_bus.setter
    def event_bus(self, value):
        self._event_bus = value
        if self._backend_instance:
            self._backend_instance.event_bus = value

    def process(self, frame: AudioFrame) -> Optional[AudioFrame]:
        if self._backend_instance:
            return self._backend_instance.process(frame)
        return self.pass_to_next(frame)
        
    def close(self) -> None:
        if self._backend_instance and hasattr(self._backend_instance, 'close'):
            self._backend_instance.close()
        self._backend_instance = None
