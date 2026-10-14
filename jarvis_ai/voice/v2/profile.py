from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class VoiceProfile:
    """Defines a user's intent for voice generation.
    
    A VoiceProfile separates the *desired outcome* (e.g., Natural, Fast) from
    the *execution backend* (e.g., ElevenLabs, Edge-TTS, Pyttsx3).
    The Voice Framework negotiates the best backend at runtime based on this profile.
    """
    
    name: str
    
    # Priority ordered list of backend names to try.
    # The first available, healthy backend that satisfies the requirements is chosen.
    fallback_chain: list[str]
    
    # Latency vs Quality tuning
    latency_preference: Literal["lowest", "balanced", "high"] = "balanced"
    quality_preference: Literal["standard", "high", "studio"] = "standard"
    
    # Constraints
    require_offline: bool = False
    prefer_streaming: bool = True
    
    # Backend-agnostic Voice Settings (backends map these to their own configs)
    voice_type: Literal["male", "female", "neutral"] = "neutral"
    speed: float = 1.0
    pitch: float = 1.0
    volume: float = 1.0
    
    # Application specific context (e.g., language code)
    language: str = "en"
    
    # Explicit voice IDs for specific backends
    backend_voice_overrides: dict[str, str] = field(default_factory=dict)


# -- Default Profiles ---------------------------------------------------------
# JARVIS uses Edge-TTS as the strict production default.

from jarvis_ai.config import CONFIG

JarvisProfile = VoiceProfile(
    name="Jarvis",
    fallback_chain=[CONFIG.voice.default_tts_backend, "pyttsx3"],
    quality_preference="high",
    prefer_streaming=True,
    voice_type="male",
    backend_voice_overrides={
        CONFIG.voice.default_tts_backend: CONFIG.voice.default_voice,
    }
)

FridayProfile = VoiceProfile(
    name="Friday",
    fallback_chain=[CONFIG.voice.default_tts_backend, "pyttsx3"],
    quality_preference="high",
    prefer_streaming=True,
    voice_type="female",
    backend_voice_overrides={
        CONFIG.voice.default_tts_backend: "en-US-AriaNeural",
    }
)

EdithProfile = VoiceProfile(
    name="Edith",
    fallback_chain=[CONFIG.voice.default_tts_backend, "pyttsx3"],
    quality_preference="high",
    prefer_streaming=True,
    voice_type="female",
    backend_voice_overrides={
        CONFIG.voice.default_tts_backend: "en-GB-SoniaNeural",
    }
)

NaturalProfile = VoiceProfile(
    name="Natural",
    fallback_chain=[CONFIG.voice.default_tts_backend, "pyttsx3"],
    quality_preference="high",
    prefer_streaming=True,
    require_offline=False,
)

OfflineProfile = VoiceProfile(
    name="Offline",
    fallback_chain=["pyttsx3"],
    quality_preference="standard",
    latency_preference="lowest",
    require_offline=True,
    prefer_streaming=False,
)

FastProfile = VoiceProfile(
    name="Fast",
    fallback_chain=[CONFIG.voice.default_tts_backend, "pyttsx3"],
    quality_preference="standard",
    latency_preference="lowest",
    prefer_streaming=True,
)

StudioProfile = VoiceProfile(
    name="Studio",
    fallback_chain=[CONFIG.voice.default_tts_backend, "pyttsx3"],
    quality_preference="studio",
    prefer_streaming=True,
)

BalancedProfile = VoiceProfile(
    name="Balanced",
    fallback_chain=[CONFIG.voice.default_tts_backend, "pyttsx3"],
    quality_preference="high",
    latency_preference="balanced",
)

# Registry of default profiles
DEFAULT_PROFILES: dict[str, VoiceProfile] = {
    "jarvis": JarvisProfile,
    "friday": FridayProfile,
    "edith": EdithProfile,
    "natural": NaturalProfile,
    "offline": OfflineProfile,
    "fast": FastProfile,
    "studio": StudioProfile,
    "balanced": BalancedProfile,
}
