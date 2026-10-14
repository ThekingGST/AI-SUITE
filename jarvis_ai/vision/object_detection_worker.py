from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from jarvis_ai.core.workers import CancellableWorker, LatestOnlyQueue
from jarvis_ai.utils.logger import LOGGER
from jarvis_ai.vision.object_detection import ObjectDetector


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
        try:
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
                    if getattr(self._detector, "model", None) is None:
                        raise RuntimeError("YOLO model failed to load. ObjectDetector returned None.")
                detections = self._detector.detect(frame) if self._detector else []
                with self._lock:
                    if self._enabled:
                        self._state = ObjectDetectionState(
                            enabled=True,
                            detections=detections,
                            updated_at=time.time(),
                        )
        except Exception as exc:
            import traceback
            import os
            from datetime import datetime
            from pathlib import Path
            log_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "AISuite" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            error_file = log_dir / "detection_error.log"
            with open(error_file, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().isoformat()}] ObjectDetectionWorker CRASHED:\n")
                f.write(traceback.format_exc())
                f.write("\n")
            LOGGER.error("ObjectDetectionWorker crashed: %s", exc)
            self.set_enabled(False)

    def _drain_frames(self) -> None:
        while self.frames.get(timeout=0.001) is not None:
            pass
