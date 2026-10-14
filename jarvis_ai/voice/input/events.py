from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Dict
import threading
from jarvis_ai.utils.logger import LOGGER

class AudioEvent(Enum):
    """Authoritative events emitted by the Audio Input Framework."""
    # Device Events
    DEVICE_CONNECTED = "device_connected"
    DEVICE_DISCONNECTED = "device_disconnected"
    DEFAULT_DEVICE_CHANGED = "default_device_changed"
    DEVICE_ERROR = "device_error"
    DEVICE_RECOVERED = "device_recovered"
    
    # Pipeline Events
    AUDIO_STARTED = "audio_started"
    AUDIO_STOPPED = "audio_stopped"
    SPEECH_STARTED = "speech_started"
    SPEECH_ENDED = "speech_ended"
    WAKE_WORD_DETECTED = "wake_word_detected"
    NOISE_LEVEL_CHANGED = "noise_level_changed"
    
    # Recognition Events
    RECOGNITION_STARTED = "recognition_started"
    PARTIAL_TRANSCRIPT = "partial_transcript"
    RECOGNITION_FINISHED = "recognition_finished"
    RECOGNITION_FAILED = "recognition_failed"

class AudioEventBus:
    """Thread-safe event bus for audio input events."""
    
    _instance: 'AudioEventBus' = None
    _lock = threading.Lock()

    def __new__(cls) -> 'AudioEventBus':
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._subscribers = {}
                cls._instance._sub_lock = threading.RLock()
            return cls._instance

    def subscribe(self, event: AudioEvent, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Subscribe to a specific audio event."""
        with self._sub_lock:
            if event not in self._subscribers:
                self._subscribers[event] = []
            if callback not in self._subscribers[event]:
                self._subscribers[event].append(callback)

    def unsubscribe(self, event: AudioEvent, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Unsubscribe from a specific audio event."""
        with self._sub_lock:
            if event in self._subscribers and callback in self._subscribers[event]:
                self._subscribers[event].remove(callback)

    def emit(self, event: AudioEvent, payload: Dict[str, Any] = None) -> None:
        """Emit an event to all subscribers."""
        if payload is None:
            payload = {}
            
        with self._sub_lock:
            subs = self._subscribers.get(event, []).copy()
            
        if event == AudioEvent.RECOGNITION_FINISHED:
            import time

            
        for callback in subs:
            cb_name = getattr(callback, "__qualname__", str(callback))
            if event == AudioEvent.RECOGNITION_FINISHED:
                import time

            try:
                callback(payload)
            except Exception as exc:
                import traceback
                tb = traceback.format_exc()
                LOGGER.error(
                    "AudioEventBus error in callback for %s:\nFull traceback\n%s\nCallback name\n%s\nException\n%s", 
                    event.value, tb, cb_name, exc
                )
