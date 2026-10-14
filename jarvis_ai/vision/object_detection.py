from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from jarvis_ai.core.model_manager import ModelManager
from jarvis_ai.config import CONFIG, MODELS_DIR
from jarvis_ai.utils.logger import LOGGER


class ObjectDetector:
    def __init__(self) -> None:
        self.model = ModelManager().get_yolo()
        self.names: dict[int, str] = {}
        if self.model is not None:
            self.names = self.model.names
            
        from jarvis_ai.vision.object_tracker import ObjectTracker
        self.tracker = ObjectTracker()

    def detect(self, frame: np.ndarray) -> list[dict]:
        if self.model is None:
            return []
        try:
            results = self.model.predict(frame, conf=CONFIG.vision.object_confidence, verbose=False)
        except Exception as exc:
            LOGGER.error("Object detection failed: %s", exc)
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
                
        tracked = self.tracker.update(detections)
        
        # Convert back to dicts for backward compatibility with rest of system
        out_detections = []
        for obj in tracked:
            out_detections.append({
                "box": obj.box,
                "label": obj.label,
                "confidence": obj.confidence,
                "id": obj.id
            })
            
        return out_detections

    @staticmethod
    def draw(frame: np.ndarray, detections: list[dict]) -> None:
        for det in detections:
            x1, y1, x2, y2 = det["box"]
            tid = det.get("id", "")
            id_str = f"[{tid}] " if tid else ""
            label = f"{id_str}{det['label']} {det['confidence']:.0%}"
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 220, 255), 2)
            cv2.putText(frame, label, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 255), 2)
