from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import cv2
import numpy as np

from jarvis_ai.core.model_manager import ModelManager
from jarvis_ai.config import CONFIG
from jarvis_ai.utils.logger import LOGGER


@dataclass
class FaceBox:
    x: int
    y: int
    w: int
    h: int
    confidence: float
    # landmarks: Optional list of 5 tuples (x, y)
    # [right_eye, left_eye, nose_tip, right_mouth_corner, left_mouth_corner]
    landmarks: list[tuple[int, int]] | None = field(default=None)


class FaceDetector(ABC):
    """Abstract interface for face detection."""

    @abstractmethod
    def detect(self, frame: np.ndarray) -> list[FaceBox]:
        """Detect faces in the given frame."""
        pass


class YuNetDetector(FaceDetector):
    """OpenCV YuNet face detector. Outputs bounding boxes and 5 landmarks."""

    def __init__(self) -> None:
        self.net = ModelManager().get_yunet_detector()
        self._last_input_size = (0, 0)

    def detect(self, frame: np.ndarray) -> list[FaceBox]:
        if self.net is None or frame is None:
            return []

        h, w = frame.shape[:2]
        
        # Update input size dynamically if the frame size changes
        input_size = (w, h)
        if self._last_input_size != input_size:
            self.net.setInputSize(input_size)
            self._last_input_size = input_size

        # YuNet detect returns: (status, faces)
        # faces is a 2D array of shape (num_faces, 15)
        # 0-3: x, y, w, h
        # 4-13: landmarks x,y for right eye, left eye, nose tip, right mouth, left mouth
        # 14: confidence
        status, faces = self.net.detect(frame)
        if faces is None:
            return []

        results: list[FaceBox] = []
        for face_data in faces:
            confidence = float(face_data[14])
            if confidence < CONFIG.vision.face_confidence:
                continue
                
            x, y, fw, fh = map(int, face_data[0:4])
            
            # Ensure coordinates are within frame bounds
            x1, y1 = max(0, x), max(0, y)
            x2, y2 = min(w - 1, x + fw), min(h - 1, y + fh)
            box_w, box_h = x2 - x1, y2 - y1
            if box_w <= 0 or box_h <= 0:
                continue

            # Extract 5 landmarks
            landmarks = []
            for i in range(5):
                lx = int(face_data[4 + 2 * i])
                ly = int(face_data[4 + 2 * i + 1])
                landmarks.append((lx, ly))

            results.append(FaceBox(x1, y1, box_w, box_h, confidence, landmarks=landmarks))
            
        return results


class SSDDetector(FaceDetector):
    """Legacy OpenCV DNN SSD face detector. Does NOT output landmarks."""

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


def create_detector() -> FaceDetector:
    """Factory method to create the configured face detector."""
    detector_type = getattr(CONFIG.vision, "face_detector_type", "ssd").lower()
    if detector_type == "yunet":
        return YuNetDetector()
    return SSDDetector()
