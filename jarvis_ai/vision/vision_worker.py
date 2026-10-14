from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

from jarvis_ai.config import CONFIG
from jarvis_ai.core.workers import CancellableWorker, LatestOnlyQueue
from jarvis_ai.utils.logger import LOGGER
from jarvis_ai.vision.emotion_detection import EmotionDetector
from jarvis_ai.vision.face_detection import FaceBox, create_detector
from jarvis_ai.vision.face_recognition import FaceRecognizer
from jarvis_ai.vision.gesture_control import GestureController
from jarvis_ai.vision.object_detection import ObjectDetector
from jarvis_ai.vision.object_detection_worker import ObjectDetectionWorker


@dataclass
class VisionSnapshot:
    faces: list[FaceBox] = field(default_factory=list)
    identities: list[tuple[FaceBox, str, float]] = field(default_factory=list)
    objects: list[dict[str, Any]] = field(default_factory=list)
    emotion: str | None = None
    gesture: str | None = None
    updated_at: float = 0.0
    latest_detection_snapshot: dict[str, Any] = field(default_factory=dict)


class VisionWorker(CancellableWorker):
    """Runs heavy perception work away from the camera and UI threads."""

    def __init__(self, on_event) -> None:
        super().__init__("JarvisVisionWorker")
        self.on_event = on_event
        self.frames: LatestOnlyQueue[np.ndarray] = LatestOnlyQueue()
        
        self.vision_enabled = False
        self.face_recognition_enabled = False
        self.enabled_gestures = True
        self.enabled_emotions = True

        self._face_detector = None
        self._face_recognizer = None
        self._temporal_recognizer = None
        self._object_worker = None
        self._emotion_detector = None
        self._gestures = None

        self._snapshot = VisionSnapshot()
        self._snapshot_lock = threading.RLock()
        self._unknown_last_saved = 0.0
        self._welcomed_names: set[str] = set()

    def submit_frame(self, frame: np.ndarray) -> None:
        self.frames.put(frame.copy())
        if self._object_worker:
            self._object_worker.submit_frame(frame)


    def _load_models(self) -> None:
        if self._face_detector is None:
            self._face_detector = create_detector()
        if self._face_recognizer is None:
            self._face_recognizer = FaceRecognizer()
        if self._temporal_recognizer is None:
            from jarvis_ai.vision.temporal_recognizer import TemporalRecognizer
            self._temporal_recognizer = TemporalRecognizer()
        if self._object_worker is None:
            self._object_worker = ObjectDetectionWorker(interval_seconds=0.2)
            self._object_worker.start()
            self._object_worker.set_enabled(True)
        else:
            self._object_worker.set_enabled(True)
        if self._emotion_detector is None:
            self._emotion_detector = EmotionDetector()
        if self._gestures is None:
            self._gestures = GestureController(self.on_event)

    def set_vision_enabled(self, enabled: bool) -> bool:
        self.vision_enabled = enabled
        if enabled:
            try:
                self._load_models()
                return True
            except Exception as e:
                self.vision_enabled = False
                import traceback
                import os
                from datetime import datetime
                from pathlib import Path
                log_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "AISuite" / "logs"
                log_dir.mkdir(parents=True, exist_ok=True)
                error_file = log_dir / "detection_error.log"
                with open(error_file, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().isoformat()}] Detection load error:\n")
                    f.write(traceback.format_exc())
                    f.write("\n")
                self._notify_error("Detection Error: Check Logs")
                return False
        else:
            if self._object_worker:
                self._object_worker.set_enabled(False)
                self._object_worker.stop()
            self._face_detector = None
            self._face_recognizer = None
            self._temporal_recognizer = None
            self._object_worker = None
            self._emotion_detector = None
            self._gestures = None
            from jarvis_ai.core.model_manager import ModelManager
            ModelManager().release_all()
            with self._snapshot_lock:
                self._snapshot = VisionSnapshot()
            return True

    def _notify_error(self, msg: str) -> None:
        from jarvis_ai.utils.logger import LOGGER
        LOGGER.error(msg)

    def start(self) -> None:
        super().start()

    def stop(self, timeout: float = 2.0) -> None:
        super().stop(timeout)
        if self._object_worker:
            self._object_worker.stop(timeout)

    def snapshot(self) -> VisionSnapshot:
        with self._snapshot_lock:
            return VisionSnapshot(
                faces=list(self._snapshot.faces),
                identities=list(self._snapshot.identities),
                objects=list(self._snapshot.objects),
                emotion=self._snapshot.emotion,
                gesture=self._snapshot.gesture,
                updated_at=self._snapshot.updated_at,
                latest_detection_snapshot=dict(self._snapshot.latest_detection_snapshot),
            )

    def describe_objects(self, frame: np.ndarray | None = None) -> str:
        if not self._object_worker:
            return "Vision systems are offline."
        state = self._object_worker.snapshot()
        if not state.enabled:
            return "No objects currently detected."
        if time.time() - state.updated_at > 2.0:
            return "No objects currently detected."
        detections = state.detections
        if not detections:
            return "No objects currently detected."
        counts: dict[str, int] = {}
        for detection in detections:
            label = str(detection["label"])
            counts[label] = counts.get(label, 0) + 1
        labels = ", ".join(f"{count} {label}" if count > 1 else label for label, count in counts.items())
        return f"I currently detect: {labels}."

    @property
    def face_detector(self):
        return self._face_detector

    @property
    def face_recognizer(self):
        return self._face_recognizer

    @property
    def temporal_recognizer(self):
        return self._temporal_recognizer

    @property
    def object_worker(self):
        return self._object_worker

    @property
    def emotion_detector(self):
        return self._emotion_detector

    @property
    def gestures(self):
        return self._gestures

    def run(self) -> None:
        while not self.stopped:
            frame = self.frames.get(timeout=0.2)
            if frame is None:
                continue
            try:
                snapshot = self._process(frame)
                with self._snapshot_lock:
                    self._snapshot = snapshot
            except Exception as exc:
                from jarvis_ai.utils.logger import LOGGER
                import traceback
                LOGGER.error("Vision background worker exception: %s\n%s", exc, traceback.format_exc())
                # Keep thread alive, but avoid spamming immediately if it's a hard loop fail
                time.sleep(1.0)

    def _process(self, frame: np.ndarray) -> VisionSnapshot:
        if not self.vision_enabled:
            return VisionSnapshot()

        faces = self.face_detector.detect(frame) if self.face_detector else []
        identities: list[tuple[FaceBox, str, float]] = []
        
        # If no faces are detected, clear the temporal buffer to prevent ghosting
        if not faces:
            if self._temporal_recognizer is not None:
                self.temporal_recognizer.clear()
            
        for face in faces:
            if self.face_recognition_enabled and self.face_recognizer and self.temporal_recognizer:
                raw_label, raw_score = self.face_recognizer.recognize(frame, face)
                label, score = self.temporal_recognizer.update(raw_label, raw_score)
                
                identities.append((face, label, score))
                if label not in ("unknown", "owner") and label not in self._welcomed_names:
                    self._welcomed_names.add(label)
                    self.on_event(f"Welcome back, {label}.")
                if label == "unknown" and self.face_recognizer.owner_embeddings and time.time() - self._unknown_last_saved > 10:
                    self._unknown_last_saved = time.time()
                    path = self.face_recognizer.save_intruder(frame)
                    self.on_event(f"Unknown face captured: {path.name}")
            else:
                identities.append((face, "unknown", 0.0))

        objects = self.object_worker.snapshot().detections if self.vision_enabled and self.object_worker else []
        gesture = self.gestures.process(frame) if self.enabled_gestures and self.gestures else None
        emotion = self.emotion_detector.detect(frame) if self.enabled_emotions and self.emotion_detector else None
        if emotion:
            response = self.emotion_detector.response_for(emotion)
            if response:
                self.on_event(response)

        latest = {
            "timestamp": time.time(),
            "objects": [det.get("label", "object") for det in objects],
            "faces": [{"name": label, "confidence": score} for _, label, score in identities],
        }
        return VisionSnapshot(
            faces=faces,
            identities=identities,
            objects=objects,
            emotion=emotion,
            gesture=gesture,
            updated_at=time.time(),
            latest_detection_snapshot=latest,
        )


def draw_snapshot(frame: np.ndarray, snapshot: VisionSnapshot) -> None:
    """Draw the latest worker output onto the live camera frame without inference."""

    for face, label, score in snapshot.identities:
        color = (0, 255, 255) if label not in ("unknown",) else (0, 0, 255)
        cv2.rectangle(frame, (face.x, face.y), (face.x + face.w, face.y + face.h), color, 2)
        cv2.putText(
            frame,
            f"{label} {score:.2f}",
            (face.x, max(18, face.y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
        )
    ObjectDetector.draw(frame, snapshot.objects)
    if snapshot.emotion:
        cv2.putText(frame, f"Emotion: {snapshot.emotion}", (18, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 220, 0), 2)
