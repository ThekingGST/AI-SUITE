from __future__ import annotations

import json
import queue
import threading
from typing import Callable

from jarvis_ai.config import CONFIG, MODELS_DIR
from jarvis_ai.utils.logger import LOGGER


class VoiceListener:
    """Compatibility wrapper for AI Suite Audio Input Framework 2.0.
    
    Delegates hardware capture, processing, and STT to the new modular pipeline.
    Preserves the legacy API for existing JARVIS/FRIDAY components.
    """

    def __init__(self, on_text: Callable[[str], None]) -> None:
        self.on_text = on_text
        
        from jarvis_ai.voice.input.framework import AudioInputFramework
        from jarvis_ai.voice.input.events import AudioEvent
        
        # Instantiate the new AI Suite framework
        self._framework = AudioInputFramework(profile_name="office")
        self._framework.event_bus.subscribe(AudioEvent.RECOGNITION_FINISHED, self._on_recognition)
        self._framework.event_bus.subscribe(AudioEvent.DEVICE_ERROR, self._on_error)
        
        self.available = False
        self.error: str | None = None

    def _on_recognition(self, payload: dict) -> None:
        """Handle final recognized text."""
        import time
        import threading

        
        text = payload.get("text", "").strip()
        
        if text:

            self.on_text(text)

    def _on_error(self, payload: dict) -> None:
        """Handle hardware errors."""
        self.error = payload.get("error", "Unknown error")
        self.available = False
        LOGGER.warning("VoiceListener error: %s", self.error)

    def start(self) -> None:
        self._framework.start()
        self.available = True
        LOGGER.info("MIC STARTED (V2 Framework)")

    def stop(self) -> None:
        self._framework.stop()
        self.available = False
        LOGGER.info("MIC STOPPED")

    def pause(self) -> None:
        self._framework.pause()
        LOGGER.info("MIC PAUSED")

    def resume(self) -> None:
        self._framework.resume()
        LOGGER.info("MIC RESUMED")


class TextCommandBus:
    """A simple queue used by UI, tests, and voice recognition to submit commands."""

    def __init__(self) -> None:
        self.queue: queue.Queue[str] = queue.Queue()

    def submit(self, text: str) -> None:
        self.queue.put(text)

    def get(self, timeout: float = 0.1) -> str | None:
        try:
            return self.queue.get(timeout=timeout)
        except queue.Empty:
            return None
