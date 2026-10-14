from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

@dataclass(frozen=True)
class AudioProfile:
    """Defines pipeline behavior for different audio environments."""
    
    name: str
    
    # VAD Settings
    vad_sensitivity: int = 3           # 0 (least aggressive) to 3 (most aggressive filtering)
    silence_timeout_sec: float = 1.0   # How long of silence before ending speech
    speech_timeout_sec: float = 10.0   # Max duration of a single speech block
    
    # Processing Settings
    gain_multiplier: float = 1.0       # Software gain
    noise_suppression_level: int = 0   # 0 (off) to 3 (max)
    
    # Wake Word Settings
    wakeword_confidence_threshold: float = 0.5
    wakeword_cooldown_sec: float = 2.0


DEFAULT_PROFILES: Dict[str, AudioProfile] = {
    "quiet_room": AudioProfile(
        name="Quiet Room",
        vad_sensitivity=1,
        silence_timeout_sec=1.5,
        wakeword_confidence_threshold=0.4
    ),
    "office": AudioProfile(
        name="Office",
        vad_sensitivity=2,
        silence_timeout_sec=1.0,
        noise_suppression_level=1,
        wakeword_confidence_threshold=0.5
    ),
    "laptop": AudioProfile(
        name="Laptop",
        vad_sensitivity=3,
        silence_timeout_sec=0.8,
        noise_suppression_level=2,
        wakeword_confidence_threshold=0.6
    ),
    "headset": AudioProfile(
        name="Headset",
        vad_sensitivity=1,
        silence_timeout_sec=1.0,
        gain_multiplier=1.2,
        noise_suppression_level=0,
        wakeword_confidence_threshold=0.4
    ),
    "studio": AudioProfile(
        name="Studio",
        vad_sensitivity=0,
        silence_timeout_sec=2.0,
        noise_suppression_level=0,
        wakeword_confidence_threshold=0.3
    ),
    "conference": AudioProfile(
        name="Conference",
        vad_sensitivity=3,
        silence_timeout_sec=1.5,
        noise_suppression_level=3,
        wakeword_confidence_threshold=0.6
    )
}
