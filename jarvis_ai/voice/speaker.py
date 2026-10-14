from __future__ import annotations

import queue
import threading
import time
from typing import Any

from config import CONFIG
from utils.logger import LOGGER


class Speaker:
    """Thread-safe pyttsx3 speech queue with interruption support."""

    def __init__(self) -> None:
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._stop_event = threading.Event()
        self._state_lock = threading.RLock()
        self._enabled = True
        self._speaking = False
        self._last_spoken_at = 0.0
        self._thread = threading.Thread(target=self._run, name="JarvisSpeaker", daemon=True)
        self._engine: Any | None = None
        self._thread.start()

    @property
    def enabled(self) -> bool:
        with self._state_lock:
            return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable queued speech without recreating the TTS engine."""
        with self._state_lock:
            self._enabled = enabled
        if not enabled:
            LOGGER.info("TTS muted.")
            self.interrupt()

    def say(self, text: str) -> None:
        self.speak(text)

    def speak(self, text: str) -> None:
        """Queue speech asynchronously through the single shared TTS worker."""
        cleaned = text.strip()
        if not cleaned:
            return
        if not self.enabled:
            LOGGER.info("TTS muted.")
            return
        LOGGER.info("Speaking response...")
        self._queue.put(cleaned)
        LOGGER.info("Speech queue active.")

    @property
    def is_speaking(self) -> bool:
        with self._state_lock:
            return self._speaking

    def recently_spoke(self, seconds: float = 0.8) -> bool:
        with self._state_lock:
            return self._speaking or (time.time() - self._last_spoken_at) < seconds

    def interrupt(self) -> None:
        self._stop_event.set()
        try:
            while True:
                self._queue.get_nowait()
        except queue.Empty:
            pass
        if self._engine:
            try:
                self._engine.stop()
            except Exception:
                pass

    def close(self) -> None:
        self._queue.put(None)
        self._thread.join(timeout=2)

    def _run(self) -> None:
        com_initialized = False
        try:
            try:
                import pythoncom

                pythoncom.CoInitialize()
                com_initialized = True
            except Exception:
                pythoncom = None  # type: ignore[assignment]

            import pyttsx3

            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", CONFIG.voice.speech_rate)
            self._engine.setProperty("volume", CONFIG.voice.speech_volume)
        except Exception as exc:
            LOGGER.warning("TTS engine unavailable: %s", exc)
            self._engine = None

        while True:
            text = self._queue.get()
            if text is None:
                break
            if not self.enabled:
                LOGGER.info("TTS muted.")
                continue
            if not self._engine:
                LOGGER.info("Speech: %s", text)
                continue
            try:
                self._stop_event.clear()
                with self._state_lock:
                    self._speaking = True
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception as exc:
                LOGGER.warning("Speech failed: %s", exc)
            finally:
                with self._state_lock:
                    self._speaking = False
                    self._last_spoken_at = time.time()
        if com_initialized:
            try:
                pythoncom.CoUninitialize()  # type: ignore[name-defined]
            except Exception:
                pass
