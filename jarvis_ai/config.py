from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from shared.config import ConfigManager

BASE_DIR = ConfigManager.BASE_DIR
PROJECT_ROOT = ConfigManager.PROJECT_ROOT
ASSETS_DIR = ConfigManager.ASSETS_DIR
MODELS_DIR = ConfigManager.MODELS_DIR
DATA_DIR = ConfigManager.DATA_DIR
INTRUDER_DIR = ConfigManager.INTRUDER_DIR
CAPTURES_DIR = ConfigManager.CAPTURES_DIR
SCREENSHOT_DIR = ConfigManager.SCREENSHOT_DIR
FACE_DATASET_DIR = ConfigManager.FACE_DATASET_DIR
OBJECT_DATASET_DIR = ConfigManager.OBJECT_DATASET_DIR
FACE_EMBEDDINGS_DB = ConfigManager.FACE_EMBEDDINGS_DB
MEMORY_DB = ConfigManager.MEMORY_DB
OWNER_EMBEDDINGS = ConfigManager.OWNER_EMBEDDINGS


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
    frame_size: int = 1024
    command_timeout_seconds: float = 9.0
    speech_rate: int = 165
    speech_volume: float = 1.0
    default_tts_backend: str = "edge-tts"
    default_voice: str = "en-US-GuyNeural"
    elevenlabs_api_key: str = field(default_factory=lambda: ConfigManager.secrets.get_secret("ELEVENLABS_API_KEY", ""))
    elevenlabs_voice_id: str = field(default_factory=lambda: ConfigManager.secrets.get_secret("ELEVENLABS_VOICE_ID", "g23Ai3H53LXBxJxfIhFG"))


@dataclass(frozen=True)
class VisionConfig:
    camera_index: int = 0
    width: int = 960
    height: int = 540
    face_confidence: float = 0.62
    object_confidence: float = 0.38
    face_match_threshold: float = 0.70
    face_match_ceiling: float = 0.85
    face_min_size: int = 80
    face_detector_type: str = "yunet"
    alignment_enabled: bool = True
    blur_threshold: float = 100.0
    quality_threshold: float = 0.8
    history_size: int = 5
    history_majority: int = 3
    history_timeout_seconds: float = 2.0
    registration_required_views: tuple[str, ...] = ("FRONT", "LEFT", "RIGHT", "UP", "DOWN", "SMILE", "NEUTRAL")
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
