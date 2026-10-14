from __future__ import annotations

import audioop

from jarvis_ai.voice.input.capture import AudioFrame
from jarvis_ai.voice.input.profile import AudioProfile
from jarvis_ai.voice.input.vad.base import VADProcessor


class EnergyVAD(VADProcessor):
    """A lightweight RMS energy-based Voice Activity Detector.
    
    Acts as a fallback if WebRTCVAD is unavailable or for extremely low-power modes.
    """

    def __init__(self, profile: AudioProfile, sample_width: int = 2) -> None:
        super().__init__(profile)
        self.sample_width = sample_width
        self.base_threshold = 500  # Baseline RMS energy

    def is_speech_frame(self, frame: AudioFrame) -> bool:
        """Calculate RMS energy and compare against threshold."""
        try:
            rms = audioop.rms(frame.data, self.sample_width)
        except audioop.error:
            return False
            
        # Adjust threshold based on profile sensitivity
        # Sensitivity 0 (lowest) -> High threshold (needs loud voice)
        # Sensitivity 3 (highest) -> Low threshold (picks up quiet voice)
        multiplier = {
            0: 2.0,
            1: 1.5,
            2: 1.0,
            3: 0.7
        }.get(self.profile.vad_sensitivity, 1.0)
        
        dynamic_threshold = self.base_threshold * multiplier
        return rms > dynamic_threshold
