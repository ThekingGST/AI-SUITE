from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

from config import CONFIG
from core.workers import CancellableWorker, LatestOnlyQueue
from utils.logger import LOGGER
from vision.emotion_detection import EmotionDetector
from vision.face_detection import FaceBox, FaceDetector
from vision.face_recognition import FaceRecognizer
from vision.gesture_control import GestureController
from vision.object_detection import ObjectDetector
from vision.object_detection_worker import ObjectDetectionWorker


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
        self.face_detector = FaceDetector()
        self.face_recognizer = FaceRecognizer()
        self.object_worker = ObjectDetectionWorker(interval_seconds=0.2)
        self.emotion_detector = EmotionDetector()
        self.gestures = GestureController(on_event)
        self.enabled_gestures = True
        self.enabled_emotions = True
        self._snapshot = VisionSnapshot()
        self._snapshot_lock = threading.RLock()
        self._unknown_last_saved = 0.0
        self._welcomed_names: set[str] = set()

    def submit_frame(self, frame: np.ndarray) -> None:
        self.frames.put(frame.copy())
        self.object_worker.submit_frame(frame)

    @property
    def object_detection_enabled(self) -> bool:
        return self.object_worker.enabled

    def set_object_detection_enabled(self, enabled: bool) -> None:
        self.object_worker.set_enabled(enabled)
        with self._snapshot_lock:
            self._snapshot.objects = []

    def start(self) -> None:
        self.object_worker.start()
        super().start()

    def stop(self, timeout: float = 2.0) -> None:
        super().stop(timeout)
        self.object_worker.stop(timeout)

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
        state = self.object_worker.snapshot()
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

    def run(self) -> None:
        while not self.stopped:
            frame = self.frames.get(timeout=0.2)
            if frame is None:
                continue
            snapshot = self._process(frame)
            with self._snapshot_lock:
                self._snapshot = snapshot

    def _process(self, frame: np.ndarray) -> VisionSnapshot:
        faces = self.face_detector.detect(frame)
        identities: list[tuple[FaceBox, str, float]] = []
        for face in faces:
            label, score = self.face_recognizer.recognize(frame, face)
            identities.append((face, label, score))
            if label not in ("unknown", "owner") and label not in self._welcomed_names:
                self._welcomed_names.add(label)
                self.on_event(f"Welcome back, {label}.")
            if label == "unknown" and self.face_recognizer.owner_embeddings and time.time() - self._unknown_last_saved > 10:
                self._unknown_last_saved = time.time()
                path = self.face_recognizer.save_intruder(frame)
                self.on_event(f"Unknown face captured: {path.name}")

        objects = self.object_worker.snapshot().detections if self.object_detection_enabled else []
        gesture = self.gestures.process(frame) if self.enabled_gestures else None
        emotion = self.emotion_detector.detect(frame) if self.enabled_emotions else None
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
