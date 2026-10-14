from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from typing import Generic, TypeVar

from jarvis_ai.utils.logger import LOGGER

T = TypeVar("T")


class CancellableWorker:
    """Base class for background services that need cooperative cancellation."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def stopped(self) -> bool:
        return self._stop_event.is_set()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._safe_run, name=self.name, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)

    def _safe_run(self) -> None:
        try:
            self.run()
        except Exception:
            LOGGER.exception("%s crashed", self.name)

    def run(self) -> None:
        raise NotImplementedError


class LatestOnlyQueue(Generic[T]):
    """Queue that keeps only the newest item, ideal for camera frames."""

    def __init__(self) -> None:
        self._queue: queue.Queue[T] = queue.Queue(maxsize=1)

    def put(self, item: T) -> None:
        try:
            self._queue.put_nowait(item)
        except queue.Full:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            self._queue.put_nowait(item)

    def get(self, timeout: float = 0.1) -> T | None:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None


def run_daemon(name: str, target: Callable[[], None]) -> threading.Thread:
    thread = threading.Thread(target=target, name=name, daemon=True)
    thread.start()
    return thread
