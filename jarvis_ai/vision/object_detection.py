from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from core.model_manager import ModelManager
from config import CONFIG, MODELS_DIR
from utils.logger import LOGGER


class ObjectDetector:
    def __init__(self) -> None:
        self.model = ModelManager().get_yolo()
        self.names: dict[int, str] = {}
        if self.model is not None:
            self.names = self.model.names

    def detect(self, frame: np.ndarray) -> list[dict]:
        if self.model is None:
            return []
        try:
            results = self.model.predict(frame, conf=CONFIG.vision.object_confidence, verbose=False)
        except Exception as exc:
            LOGGER.warning("Object detection failed: %s", exc)
            return []
        detections: list[dict] = []
        for result in results:
            for box in result.boxes:
                xyxy = box.xyxy[0].cpu().numpy().astype(int)
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                detections.append(
                    {
                        "box": tuple(int(v) for v in xyxy),
                        "label": self.names.get(cls, str(cls)),
                        "confidence": conf,
                    }
                )
        return detections

    @staticmethod
    def draw(frame: np.ndarray, detections: list[dict]) -> None:
        for det in detections:
            x1, y1, x2, y2 = det["box"]
            label = f"{det['label']} {det['confidence']:.0%}"
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 220, 255), 2)
            cv2.putText(frame, label, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 255), 2)
