from __future__ import annotations

import threading
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

from jarvis_ai.utils.logger import LOGGER


class VoiceEvent(Enum):
    """Events emitted by the Voice System 2.0 pipeline.

    Components subscribe to specific events via the VoiceEventBus
    instead of polling state or using ad-hoc callbacks.
    """

    # -- Speech lifecycle --
    SPEECH_STARTED = "speech_started"
    SPEECH_FINISHED = "speech_finished"
    SPEECH_INTERRUPTED = "speech_interrupted"

    # -- Streaming --
    STREAMING_STARTED = "streaming_started"
    STREAMING_CHUNK_READY = "streaming_chunk_ready"
    STREAMING_FINISHED = "streaming_finished"

    # -- Listening --
    LISTENING_STARTED = "listening_started"
    LISTENING_STOPPED = "listening_stopped"
    LISTENING_PAUSED = "listening_paused"
    LISTENING_RESUMED = "listening_resumed"

    # -- Recognition --
    WAKE_WORD_DETECTED = "wake_word_detected"
    RECOGNITION_RESULT = "recognition_result"

    # -- Backend --
    BACKEND_CHANGED = "backend_changed"
    BACKEND_ERROR = "backend_error"

    # -- State --
    STATE_CHANGED = "state_changed"

    # -- Errors --
    ERROR_OCCURRED = "error_occurred"
    ERROR_RECOVERED = "error_recovered"


@dataclass
class VoiceEventData:
    """Payload attached to every voice event.

    Attributes:
        event: The event type.
        data:  Arbitrary event-specific payload.  For example:
               - SPEECH_STARTED: {"text": "Hello", "job_id": "abc123"}
               - STATE_CHANGED: {"old": VoiceState.IDLE, "new": VoiceState.SPEAKING}
               - BACKEND_CHANGED: {"backend": "edge-tts"}
    """

    event: VoiceEvent
    data: dict[str, Any]


class VoiceEventBus:
    """Lightweight publish/subscribe bus for voice pipeline events.

    Thread-safe.  Callbacks are invoked synchronously on the publisher's
    thread.  Subscribers that need UI-thread delivery should use Qt signals
    or ``QMetaObject.invokeMethod`` internally.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: dict[VoiceEvent, list[Callable[[VoiceEventData], None]]] = {}

    def subscribe(self, event: VoiceEvent, callback: Callable[[VoiceEventData], None]) -> None:
        """Register *callback* for *event*."""
        with self._lock:
            self._subscribers.setdefault(event, []).append(callback)

    def unsubscribe(self, event: VoiceEvent, callback: Callable[[VoiceEventData], None]) -> None:
        """Remove a previously registered callback."""
        with self._lock:
            listeners = self._subscribers.get(event, [])
            try:
                listeners.remove(callback)
            except ValueError:
                pass

    def emit(self, event: VoiceEvent, data: dict[str, Any] | None = None) -> None:
        """Publish *event* with optional *data* to all subscribers."""
        payload = VoiceEventData(event=event, data=data or {})
        with self._lock:
            listeners = list(self._subscribers.get(event, []))

        for listener in listeners:
            try:
                listener(payload)
            except Exception as exc:
                LOGGER.warning("VoiceEventBus: subscriber error on %s: %s", event.value, exc)

    def clear(self) -> None:
        """Remove all subscriptions.  Used during shutdown."""
        with self._lock:
            self._subscribers.clear()
