from __future__ import annotations

import time
import cv2
import numpy as np

from jarvis_ai.config import CONFIG
from jarvis_ai.utils.logger import LOGGER
from shared.models.model_registry import ModelRegistry, ModelInfo, ModelCategory

class EmotionDetector:
    EMOTION_LABELS = ['neutral', 'happy', 'surprise', 'sad', 'angry', 'disgust', 'fear', 'contempt']
    
    def __init__(self) -> None:
        self._last_run = 0.0
        self.available = True
        self.session = None
        
        # Register the model in registry
        try:
            registry = ModelRegistry()
            if not registry.get_info("emotion-ferplus"):
                registry.register(ModelInfo(
                    name="emotion-ferplus",
                    category=ModelCategory.VISION,
                    relative_path="emotion_ferplus.onnx",
                    size_mb=12.0,
                    license="MIT",
                    required=False,
                    gpu_capable=True,
                    description="Lightweight ONNX Facial Expression Recognition"
                ))
        except Exception as e:
            LOGGER.error("Failed to register FER model: %s", e)

    def _load_model(self) -> bool:
        if self.session is not None:
            return True
        try:
            import onnxruntime as ort
            registry = ModelRegistry()
            model_path = registry.get_model_path("emotion-ferplus")
            if not model_path or not model_path.exists():
                raise FileNotFoundError("FER model not found.")
                
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if ort.get_device() == 'GPU' else ['CPUExecutionProvider']
            self.session = ort.InferenceSession(str(model_path), providers=providers)
            return True
        except Exception as e:
            self.available = False
            LOGGER.warning("Emotion detection unavailable (ONNX FER failed to load): %s", e)
            return False

    def detect(self, frame: np.ndarray) -> str | None:
        if time.time() - self._last_run < CONFIG.vision.emotion_interval_seconds:
            return None
        self._last_run = time.time()
        
        if not self.available or not self._load_model():
            return None
            
        try:
            # Resize and preprocess for FER+ (assumes 64x64 grayscale input)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Typically you'd crop to face here, but if full frame is passed,
            # we do a naive resize (assuming face is mostly centered/large)
            resized = cv2.resize(gray, (64, 64))
            
            # Normalize depending on model, FER+ typically wants float32
            img_data = np.array(resized, dtype=np.float32).reshape(1, 1, 64, 64)
            
            input_name = self.session.get_inputs()[0].name
            output_name = self.session.get_outputs()[0].name
            
            result = self.session.run([output_name], {input_name: img_data})[0]
            emotion_idx = np.argmax(result[0])
            
            return self.EMOTION_LABELS[emotion_idx]
            
        except Exception as exc:
            LOGGER.warning("Emotion detection runtime error: %s", exc)
            return None

    @staticmethod
    def response_for(emotion: str) -> str | None:
        return {
            "sad": "You look a little low. I am here with you.",
            "angry": "You look tense. A short pause might help.",
            "fear": "You seem uneasy. I will keep the interface calm.",
            "happy": "You look happy today.",
            "surprise": "That expression says something interesting just happened.",
        }.get(emotion)
