from jarvis_ai.voice.input.vad.base import VADProcessor
from jarvis_ai.voice.input.vad.energy_vad import EnergyVAD
from jarvis_ai.voice.input.vad.webrtc_vad import WEBRTC_AVAILABLE, WebRTCVAD
from jarvis_ai.voice.input.profile import AudioProfile

def create_vad(profile: AudioProfile, sample_rate: int = 16000) -> VADProcessor:
    """Factory to create the best available VAD implementation."""
    if WEBRTC_AVAILABLE:
        return WebRTCVAD(profile, sample_rate)
    return EnergyVAD(profile)
