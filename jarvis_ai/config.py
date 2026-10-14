from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
MODELS_DIR = BASE_DIR / "models"
DATA_DIR = BASE_DIR / "data"
INTRUDER_DIR = DATA_DIR / "intruders"
CAPTURES_DIR = DATA_DIR / "captures"
SCREENSHOT_DIR = DATA_DIR / "screenshots"
MEMORY_DB = DATA_DIR / "jarvis_memory.sqlite3"
OWNER_EMBEDDINGS = DATA_DIR / "owner_embeddings.json"


@dataclass(frozen=True)
class VoiceConfig:
    wake_word: str = "jarvis"
    sample_rate: int = 16000
    frame_size: int = 4000
    command_timeout_seconds: float = 9.0
    speech_rate: int = 178
    speech_volume: float = 0.95


@dataclass(frozen=True)
class VisionConfig:
    camera_index: int = 0
    width: int = 960
    height: int = 540
    face_confidence: float = 0.62
    object_confidence: float = 0.38
    face_match_threshold: float = 0.45
    gesture_cooldown_seconds: float = 1.2
    emotion_interval_seconds: float = 2.5


@dataclass(frozen=True)
class AIConfig:
    ollama_url: str = "http://localhost:11434"
    preferred_models: tuple[str, ...] = ("llama3", "mistral", "phi")
    max_history_messages: int = 16
    response_timeout_seconds: float = 25.0


@dataclass(frozen=True)
class AppConfig:
    assistant_name: str = "JARVIS"
    voice: VoiceConfig = VoiceConfig()
    vision: VisionConfig = VisionConfig()
    ai: AIConfig = AIConfig()


CONFIG = AppConfig()


def ensure_directories() -> None:
    for path in (
        ASSETS_DIR,
        MODELS_DIR,
        DATA_DIR,
        INTRUDER_DIR,
        CAPTURES_DIR,
        SCREENSHOT_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
