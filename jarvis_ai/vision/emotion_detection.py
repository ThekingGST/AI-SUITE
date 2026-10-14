from __future__ import annotations

import time

import numpy as np

from jarvis_ai.config import CONFIG
from jarvis_ai.utils.logger import LOGGER


class EmotionDetector:
    def __init__(self) -> None:
        self._last_run = 0.0
        self.available = True

    def detect(self, frame: np.ndarray) -> str | None:
        if time.time() - self._last_run < CONFIG.vision.emotion_interval_seconds:
            return None
        self._last_run = time.time()
        if not self.available:
            return None
        try:
            from deepface import DeepFace

            result = DeepFace.analyze(frame, actions=["emotion"], enforce_detection=False, silent=True)
            item = result[0] if isinstance(result, list) else result
            return str(item.get("dominant_emotion", "neutral"))
        except Exception as exc:
            self.available = False
            LOGGER.warning("Emotion detection unavailable: %s", exc)
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
