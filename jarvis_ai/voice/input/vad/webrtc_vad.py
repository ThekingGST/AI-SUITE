from __future__ import annotations

from jarvis_ai.utils.logger import LOGGER
from jarvis_ai.voice.input.capture import AudioFrame
from jarvis_ai.voice.input.profile import AudioProfile
from jarvis_ai.voice.input.vad.base import VADProcessor

try:
    import webrtcvad
    WEBRTC_AVAILABLE = True
except ImportError:
    WEBRTC_AVAILABLE = False


class WebRTCVAD(VADProcessor):
    """Production-grade VAD using Google's WebRTC engine."""

    def __init__(self, profile: AudioProfile, sample_rate: int = 16000) -> None:
        super().__init__(profile)
        self.sample_rate = sample_rate
        
        if not WEBRTC_AVAILABLE:
            raise ImportError("webrtcvad is not installed. Fallback to EnergyVAD.")
            
        self.vad = webrtcvad.Vad()
        self._set_mode(profile.vad_sensitivity)
        
        # WebRTC requires exact frame durations (10, 20, or 30 ms).
        # We'll use 30 ms chunks. At 16kHz, 16-bit mono, 1 frame = 2 bytes.
        # 30 ms = 480 frames = 960 bytes.
        self.chunk_size_bytes = int(self.sample_rate * 0.03 * 2) 
        self._buffer = bytearray()

    def update_profile(self, profile: AudioProfile) -> None:
        super().update_profile(profile)
        self._set_mode(profile.vad_sensitivity)

    def _set_mode(self, sensitivity: int) -> None:
        """Map profile sensitivity (0-3) to WebRTC mode (0-3).
        
        WebRTC Modes:
        0: Normal
        1: Low Bitrate
        2: Aggressive
        3: Very Aggressive (filters out most noise, keeps only speech)
        """
        mode = max(0, min(3, sensitivity))
        self.vad.set_mode(mode)

    def is_speech_frame(self, frame: AudioFrame) -> bool:
        """Buffer raw audio and process in 30ms chunks.
        
        Returns True if ANY of the chunks within the frame contain speech.
        """
        self._buffer.extend(frame.data)
        
        is_speech = False
        while len(self._buffer) >= self.chunk_size_bytes:
            chunk = bytes(self._buffer[:self.chunk_size_bytes])
            del self._buffer[:self.chunk_size_bytes]
            
            try:
                # WebRTC expects exactly chunk_size_bytes
                if self.vad.is_speech(chunk, self.sample_rate):
                    is_speech = True
            except Exception as exc:
                LOGGER.warning("WebRTCVAD error: %s", exc)
                
        return is_speech
