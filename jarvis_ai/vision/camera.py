from __future__ import annotations

import time
from collections.abc import Callable

import cv2
import numpy as np

from config import CONFIG, CAPTURES_DIR
from core.workers import CancellableWorker
from utils.helpers import timestamp_slug
from utils.logger import LOGGER
from vision.vision_worker import VisionWorker, draw_snapshot


class CameraSystem(CancellableWorker):
    """Threaded webcam pipeline; heavy inference is delegated to VisionWorker."""

    def __init__(self, on_event: Callable[[str], None] | None = None) -> None:
        super().__init__("JarvisCamera")
        self.on_event = on_event
        self.vision = VisionWorker(on_event or (lambda _: None))
        self._capture: cv2.VideoCapture | None = None
        import threading

        self._lock = threading.RLock()
        self._frame: np.ndarray | None = None
        self.fps = 0.0

    def start(self) -> None:
        self.vision.start()
        super().start()

    def stop(self) -> None:
        super().stop()
        self.vision.stop()
        if self._capture:
            self._capture.release()

    def latest_frame(self) -> np.ndarray | None:
        with self._lock:
            return None if self._frame is None else self._frame.copy()

    def describe_objects(self) -> str:
        frame = self.latest_frame()
        if frame is None:
            return "Camera is not ready."
        return self.vision.describe_objects(frame)

    def capture_photo(self) -> str:
        frame = self.latest_frame()
        if frame is None:
            return "Camera is not ready."
        path = CAPTURES_DIR / f"capture_{timestamp_slug()}.jpg"
        cv2.imwrite(str(path), frame)
        return str(path)

    def run(self) -> None:
        self._capture = cv2.VideoCapture(CONFIG.vision.camera_index, cv2.CAP_DSHOW)
        if not self._capture.isOpened():
            LOGGER.warning("Camera unavailable.")
            return
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, CONFIG.vision.width)
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, CONFIG.vision.height)
        last = time.time()
        while not self.stopped:
            ok, frame = self._capture.read()
            if not ok:
                time.sleep(0.05)
                continue
            now = time.time()
            self.fps = 1.0 / max(now - last, 1e-6)
            last = now
            self.vision.submit_frame(frame)
            annotated = frame.copy()
            draw_snapshot(annotated, self.vision.snapshot())
            cv2.putText(annotated, f"FPS {self.fps:.1f}", (18, annotated.shape[0] - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            with self._lock:
                self._frame = annotated
        self._capture.release()
