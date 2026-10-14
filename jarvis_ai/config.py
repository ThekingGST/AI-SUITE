from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

_ENV_FILE = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV_FILE, override=False)

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
ASSETS_DIR = BASE_DIR / "assets"
MODELS_DIR = BASE_DIR / "models"
DATA_DIR = BASE_DIR / "data"
INTRUDER_DIR = DATA_DIR / "intruders"
CAPTURES_DIR = DATA_DIR / "captures"
SCREENSHOT_DIR = DATA_DIR / "screenshots"
FACE_DATASET_DIR = DATA_DIR / "faces"
OBJECT_DATASET_DIR = DATA_DIR / "objects"
FACE_EMBEDDINGS_DB = DATA_DIR / "face_embeddings.pkl"
MEMORY_DB = DATA_DIR / "jarvis_memory.sqlite3"
OWNER_EMBEDDINGS = DATA_DIR / "owner_embeddings.json"


def path_diagnostics() -> dict[str, str]:
    return {
        "project_root": str(PROJECT_ROOT),
        "base_dir": str(BASE_DIR),
        "data_dir": str(DATA_DIR),
        "models_dir": str(MODELS_DIR),
        "assets_dir": str(ASSETS_DIR),
        "memory_db": str(MEMORY_DB),
        "face_embeddings": str(FACE_EMBEDDINGS_DB),
        "vosk_model": str(MODELS_DIR / "vosk-model"),
        "yolo_model": str(MODELS_DIR / "yolov8n.pt"),
        "sface_model": str(MODELS_DIR / "face_recognition_sface_2021dec.onnx"),
    }


@dataclass(frozen=True)
class VoiceConfig:
    wake_word: str = "jarvis"
    sample_rate: int = 16000
    frame_size: int = 4000
    command_timeout_seconds: float = 9.0
    speech_rate: int = 165
    speech_volume: float = 1.0
    tts_engine: str = field(default_factory=lambda: os.getenv("TTS_ENGINE", "pyttsx3"))
    elevenlabs_api_key: str = field(default_factory=lambda: os.getenv("ELEVENLABS_API_KEY", ""))
    elevenlabs_voice_id: str = field(default_factory=lambda: os.getenv("ELEVENLABS_VOICE_ID", "g23Ai3H53LXBxJxfIhFG"))


@dataclass(frozen=True)
class VisionConfig:
    camera_index: int = 0
    width: int = 960
    height: int = 540
    face_confidence: float = 0.62
    object_confidence: float = 0.38
    face_match_threshold: float = 0.70
    gesture_cooldown_seconds: float = 1.2
    emotion_interval_seconds: float = 2.5


@dataclass(frozen=True)
class AIConfig:
    ollama_url: str = "http://localhost:11434"
    preferred_models: tuple[str, ...] = ("llama3", "mistral", "phi")
    max_history_messages: int = 16
    response_timeout_seconds: float = 60.0


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
        FACE_DATASET_DIR,
        OBJECT_DATASET_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
