from __future__ import annotations

import time
from typing import List, Optional

from jarvis_ai.utils.logger import LOGGER
from jarvis_ai.voice.input.capture import AudioFrame
from jarvis_ai.voice.input.events import AudioEvent
from jarvis_ai.voice.input.pipeline import AudioProcessor
from jarvis_ai.voice.input.profile import AudioProfile

try:
    import openwakeword
    from openwakeword.model import Model
    OPENWAKEWORD_AVAILABLE = True
except ImportError:
    OPENWAKEWORD_AVAILABLE = False


class WakeWordEngine(AudioProcessor):
    """Processes audio frames to detect wake words."""

    def __init__(self, profile: AudioProfile, wake_words: List[str] = ["jarvis"]) -> None:
        super().__init__()
        self.profile = profile
        self.wake_words = [w.lower() for w in wake_words]
        
        self._last_detect_time = 0.0
        self._model = None
        
        if OPENWAKEWORD_AVAILABLE:
            try:
                # openwakeword downloads models automatically if not present
                self._model = Model(wakeword_models=self.wake_words)
                LOGGER.info("WakeWordEngine: Initialized openwakeword with %s", self.wake_words)
            except Exception as exc:
                LOGGER.warning("WakeWordEngine: Failed to load openwakeword model: %s", exc)

    def process(self, frame: AudioFrame) -> Optional[AudioFrame]:
        # If no model, just pass through (rely on STT for fallback wake word matching)
        if not self._model:
            return self.pass_to_next(frame)
            
        # Check cooldown
        current_time = frame.timestamp
        if current_time - self._last_detect_time < self.profile.wakeword_cooldown_sec:
            return self.pass_to_next(frame)

        try:
            import numpy as np
            # openwakeword expects 16-bit 16kHz audio as numpy array
            audio_data = np.frombuffer(frame.data, dtype=np.int16)
            prediction = self._model.predict(audio_data)
            
            for ww_name, score in prediction.items():
                if score >= self.profile.wakeword_confidence_threshold:
                    LOGGER.info("WAKE WORD DETECTED: '%s' (score: %.2f)", ww_name, score)
                    self._last_detect_time = current_time
                    
                    if self.event_bus:
                        self.event_bus.emit(AudioEvent.WAKE_WORD_DETECTED, {
                            "wake_word": ww_name,
                            "confidence": score,
                            "timestamp": current_time
                        })
                    break  # Only trigger once per frame
                    
        except Exception as exc:
            # We don't want to kill the audio pipeline if prediction fails
            LOGGER.error("WakeWordEngine prediction error: %s", exc)

        return self.pass_to_next(frame)
