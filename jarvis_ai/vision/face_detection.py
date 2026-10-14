from __future__ import annotations

from dataclasses import dataclass
import cv2
import numpy as np

from core.model_manager import ModelManager
from config import CONFIG, MODELS_DIR
from utils.logger import LOGGER


@dataclass
class FaceBox:
    x: int
    y: int
    w: int
    h: int
    confidence: float


class FaceDetector:
    """OpenCV DNN SSD face detector with model-missing fallback."""

    def __init__(self) -> None:
        self.net = ModelManager().get_face_detector()

    def detect(self, frame: np.ndarray) -> list[FaceBox]:
        if self.net is None or frame is None:
            return []
        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 1.0, (300, 300), (104, 177, 123))
        self.net.setInput(blob)
        detections = self.net.forward()
        faces: list[FaceBox] = []
        for i in range(detections.shape[2]):
            confidence = float(detections[0, 0, i, 2])
            if confidence < CONFIG.vision.face_confidence:
                continue
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            x1, y1, x2, y2 = box.astype("int")
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w - 1, x2), min(h - 1, y2)
            faces.append(FaceBox(x1, y1, x2 - x1, y2 - y1, confidence))
        return faces
