from __future__ import annotations

import abc
import time
from typing import Optional

from jarvis_ai.utils.logger import LOGGER
from jarvis_ai.voice.input.capture import AudioFrame
from jarvis_ai.voice.input.events import AudioEvent
from jarvis_ai.voice.input.pipeline import AudioProcessor
from jarvis_ai.voice.input.profile import AudioProfile


class VADProcessor(AudioProcessor, abc.ABC):
    """Base Voice Activity Detection processor.
    
    Responsible for emitting SPEECH_STARTED and SPEECH_ENDED events
    based on audio frame analysis.
    """

    def __init__(self, profile: AudioProfile) -> None:
        super().__init__()
        self.profile = profile
        
        self.is_speaking = False
        self._last_speech_time = 0.0
        self._speech_start_time = 0.0

    def update_profile(self, profile: AudioProfile) -> None:
        """Dynamically update thresholds."""
        self.profile = profile

    def process(self, frame: AudioFrame) -> Optional[AudioFrame]:
        is_speech = self.is_speech_frame(frame)
        current_time = frame.timestamp
        
        # We sample the speech activity logging so it doesn't flood, or log transitions
        
        if is_speech:
            self._last_speech_time = current_time
            if not self.is_speaking:
                import threading
                self.is_speaking = True
                
                LOGGER.info("[AUDIO] speech activity: TRUE")
                LOGGER.info("[AUDIO] utterance started")

                self._speech_start_time = current_time
                if self.event_bus:
                    self.event_bus.emit(AudioEvent.SPEECH_STARTED, {"timestamp": current_time})
        else:
            if self.is_speaking:
                silence_duration = current_time - self._last_speech_time
                speech_duration = current_time - self._speech_start_time
                
                # Check silence timeout
                if silence_duration >= self.profile.silence_timeout_sec:
                    self.is_speaking = False
                    import threading
                    LOGGER.info("[AUDIO] speech activity: FALSE")
                    LOGGER.info("[AUDIO] utterance ended")
                    LOGGER.info(f"[AUDIO] utterance duration: {speech_duration:.2f}s")
                    if self.event_bus:
                        self.event_bus.emit(AudioEvent.SPEECH_ENDED, {"reason": "silence"})
                        
                # Check maximum speech timeout (prevent infinite recording if stuck)
                elif speech_duration >= self.profile.speech_timeout_sec:
                    self.is_speaking = False
                    import threading
                    LOGGER.info("[AUDIO] speech activity: FALSE")
                    LOGGER.info("[AUDIO] utterance ended")
                    LOGGER.info(f"[AUDIO] utterance duration: {speech_duration:.2f}s")
                    if self.event_bus:
                        self.event_bus.emit(AudioEvent.SPEECH_ENDED, {"reason": "timeout"})

        # VAD processors usually pass the frame down the chain unmodified
        # so STT can receive it. We could choose to ONLY pass frames if is_speaking is True.
        # But WakeWord might need continuous audio. So we pass it down regardless,
        # but attach a metadata flag.
        
        # We can dynamically add attributes to the frame for downstream nodes
        frame.is_speech = self.is_speaking
        
        return self.pass_to_next(frame)

    @abc.abstractmethod
    def is_speech_frame(self, frame: AudioFrame) -> bool:
        """Analyze raw audio bytes and return True if voice activity is detected."""
        pass
