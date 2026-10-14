from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Optional

from jarvis_ai.utils.logger import LOGGER


class ModelCategory(Enum):
    """Categories of AI models managed by the registry."""

    STT = "stt"
    TTS = "tts"
    VISION = "vision"
    LANGUAGE = "language"


@dataclass(frozen=True)
class ModelInfo:
    """Metadata for a registered model."""

    name: str
    category: ModelCategory
    relative_path: str  # relative to models root, e.g. 'stt/whisper/small'
    size_mb: float  # approximate size in MB
    license: str  # e.g. 'MIT', 'Apache-2.0'
    required: bool = False  # if True, app warns on missing
    gpu_capable: bool = False
    description: str = ""


class ModelRegistry:
    """Central registry for all model metadata and path resolution."""

    _instance: Optional[ModelRegistry] = None

    def __new__(cls) -> ModelRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._models: Dict[str, ModelInfo] = {}
        self._models_root: Optional[Path] = None
        self._resolve_models_root()
        self._register_builtin_models()

    def _resolve_models_root(self) -> None:
        """Resolve the models root directory."""
        import sys

        if getattr(sys, 'frozen', False):
            self._models_root = Path(sys.executable).parent / 'models'
        else:
            # Development mode - use project root
            self._models_root = Path(__file__).resolve().parent.parent.parent / 'models'
        LOGGER.info("ModelRegistry: models root = %s", self._models_root)

    def _register_builtin_models(self) -> None:
        """Register all known models."""
        # STT models
        self.register(ModelInfo(
            name='vosk-en-us',
            category=ModelCategory.STT,
            relative_path='vosk-model',
            size_mb=70.9,
            license='Apache-2.0',
            required=False,
            gpu_capable=False,
            description='Vosk small English US model (Kaldi)',
        ))
        self.register(ModelInfo(
            name='whisper-small',
            category=ModelCategory.STT,
            relative_path='stt/whisper/small',
            size_mb=460,
            license='MIT',
            required=False,
            gpu_capable=True,
            description='OpenAI Whisper small - multilingual STT',
        ))
        self.register(ModelInfo(
            name='whisper-large-v3-turbo',
            category=ModelCategory.STT,
            relative_path='stt/whisper/large-v3-turbo',
            size_mb=1500,
            license='MIT',
            required=False,
            gpu_capable=True,
            description='OpenAI Whisper large-v3-turbo - high accuracy multilingual',
        ))
        # Vision models
        self.register(ModelInfo(
            name='yolov8n',
            category=ModelCategory.VISION,
            relative_path='yolov8n.pt',
            size_mb=6.55,
            license='AGPL-3.0',
            required=False,
            gpu_capable=True,
            description='YOLOv8 Nano object detection',
        ))
        self.register(ModelInfo(
            name='yunet-face',
            category=ModelCategory.VISION,
            relative_path='face_detection_yunet_2023mar.onnx',
            size_mb=0.23,
            license='MIT',
            required=False,
            gpu_capable=False,
            description='YuNet 5-point face detector',
        ))
        self.register(ModelInfo(
            name='sface',
            category=ModelCategory.VISION,
            relative_path='face_recognition_sface_2021dec.onnx',
            size_mb=38.7,
            license='Apache-2.0',
            required=False,
            gpu_capable=True,
            description='SFace 128-d face recognition',
        ))
        # TTS models (registered when downloaded)
        self.register(ModelInfo(
            name='kokoro-v1',
            category=ModelCategory.TTS,
            relative_path='tts/kokoro/kokoro-v1.0.onnx',
            size_mb=330,
            license='Apache-2.0',
            required=False,
            gpu_capable=True,
            description='Kokoro 82M neural TTS (EN, HI)',
        ))
        self.register(ModelInfo(
            name='piper-en-us',
            category=ModelCategory.TTS,
            relative_path='tts/piper/en_US-lessac-medium.onnx',
            size_mb=60,
            license='MIT',
            required=False,
            gpu_capable=False,
            description='Piper English US voice',
        ))
        self.register(ModelInfo(
            name='piper-hi-in',
            category=ModelCategory.TTS,
            relative_path='tts/piper/hi_IN-rohan-medium.onnx',
            size_mb=45,
            license='CC-BY-4.0',
            required=False,
            gpu_capable=False,
            description='Piper Hindi voice',
        ))
        self.register(ModelInfo(
            name='piper-te-in',
            category=ModelCategory.TTS,
            relative_path='tts/piper/te_IN-padmavathi-medium.onnx',
            size_mb=45,
            license='CC-BY-4.0',
            required=False,
            gpu_capable=False,
            description='Piper Telugu female voice',
        ))

    def register(self, info: ModelInfo) -> None:
        """Register a model in the registry.

        Args:
            info: Model metadata to register.
        """
        self._models[info.name] = info

    def get_info(self, name: str) -> Optional[ModelInfo]:
        """Get metadata for a registered model.

        Args:
            name: The model name.

        Returns:
            The ModelInfo if found, else None.
        """
        return self._models.get(name)

    def get_model_path(self, name: str) -> Optional[Path]:
        """Get the full filesystem path for a registered model.

        Args:
            name: The model name.

        Returns:
            The resolved path, or None if the model is unknown.
        """
        info = self._models.get(name)
        if info is None or self._models_root is None:
            return None
        path = self._models_root / info.relative_path
        return path

    def is_available(self, name: str) -> bool:
        """Check whether a model's files exist on disk.

        Args:
            name: The model name.

        Returns:
            True if the path exists, False otherwise.
        """
        path = self.get_model_path(name)
        if path is None:
            return False
        return path.exists()

    def list_models(self, category: Optional[ModelCategory] = None) -> list[ModelInfo]:
        """List all registered models, optionally filtered by category.

        Args:
            category: If provided, only models in this category are returned.

        Returns:
            A list of ModelInfo objects.
        """
        models = list(self._models.values())
        if category:
            models = [m for m in models if m.category == category]
        return models

    def list_available(self, category: Optional[ModelCategory] = None) -> list[ModelInfo]:
        """List models whose files are present on disk.

        Args:
            category: Optional category filter.

        Returns:
            A list of available ModelInfo objects.
        """
        return [m for m in self.list_models(category) if self.is_available(m.name)]

    def list_missing(self, category: Optional[ModelCategory] = None) -> list[ModelInfo]:
        """List models whose files are *not* present on disk.

        Args:
            category: Optional category filter.

        Returns:
            A list of missing ModelInfo objects.
        """
        return [m for m in self.list_models(category) if not self.is_available(m.name)]

    @property
    def models_root(self) -> Optional[Path]:
        """The root directory where all models are stored."""
        return self._models_root
