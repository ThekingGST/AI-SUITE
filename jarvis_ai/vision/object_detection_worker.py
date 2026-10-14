from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from core.workers import CancellableWorker, LatestOnlyQueue
from utils.logger import LOGGER
from vision.object_detection import ObjectDetector


@dataclass
class ObjectDetectionState:
    enabled: bool = False
    detections: list[dict[str, Any]] = field(default_factory=list)
    updated_at: float = 0.0


class ObjectDetectionWorker(CancellableWorker):
    """Dedicated throttled YOLO worker controlled by an enabled state."""

    def __init__(self, interval_seconds: float = 0.2) -> None:
        super().__init__("JarvisObjectDetectionWorker")
        self.interval_seconds = interval_seconds
        self.frames: LatestOnlyQueue[np.ndarray] = LatestOnlyQueue()
        self._enabled = False
        self._state = ObjectDetectionState()
        self._lock = threading.RLock()
        self._detector: ObjectDetector | None = None
        self._last_inference = 0.0

    @property
    def enabled(self) -> bool:
        with self._lock:
            return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        with self._lock:
            if self._enabled == enabled:
                return
            self._enabled = enabled
            if not enabled:
                self._state = ObjectDetectionState(enabled=False)
                self._drain_frames()
                LOGGER.info("Object detection disabled")
                LOGGER.info("YOLO worker stopped")
            else:
                self._state.enabled = True
                LOGGER.info("Object detection enabled")
                LOGGER.info("YOLO worker started")

    def submit_frame(self, frame: np.ndarray) -> None:
        if self.enabled:
            self.frames.put(frame.copy())

    def snapshot(self) -> ObjectDetectionState:
        with self._lock:
            return ObjectDetectionState(
                enabled=self._state.enabled,
                detections=list(self._state.detections),
                updated_at=self._state.updated_at,
            )

    def clear(self) -> None:
        with self._lock:
            self._state = ObjectDetectionState(enabled=self._enabled)
        self._drain_frames()

    def run(self) -> None:
        while not self.stopped:
            if not self.enabled:
                time.sleep(0.05)
                continue
            frame = self.frames.get(timeout=0.1)
            if frame is None:
                continue
            now = time.time()
            if now - self._last_inference < self.interval_seconds:
                continue
            self._last_inference = now
            if self._detector is None:
                self._detector = ObjectDetector()
            detections = self._detector.detect(frame) if self._detector else []
            with self._lock:
                if self._enabled:
                    self._state = ObjectDetectionState(
                        enabled=True,
                        detections=detections,
                        updated_at=time.time(),
                    )

    def _drain_frames(self) -> None:
        while self.frames.get(timeout=0.001) is not None:
            pass
