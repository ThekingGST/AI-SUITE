from __future__ import annotations

import threading
from typing import Protocol, runtime_checkable

from jarvis_ai.voice.v2.capabilities import BackendCapabilities, BackendHealth


class AbortedError(Exception):
    """Raised by a TTSBackend when its abort event is set mid-playback."""


@runtime_checkable
class TTSBackend(Protocol):
    """Protocol that all Voice System 2.0 TTS backends must implement.

    Key differences from the V1 ``TTSEngine`` protocol:
    - ``speak()`` accepts an ``abort`` event for cooperative cancellation.
    - ``supports_streaming()`` declares chunked-input capability.
    - Backends are fully self-contained (own lifecycle, own resources).
    """

    def speak(self, text: str, abort: threading.Event | None = None) -> None:
        """Synthesize and play *text*.

        If *abort* is set during playback, the backend should stop as
        quickly as possible and raise ``AbortedError``.  Backends that
        cannot interrupt mid-utterance (e.g. pyttsx3) should check
        *abort* before starting and after finishing, but may complete
        the current utterance atomically.

        Must block until playback completes (or is aborted).
        """
        ...

    def get_capabilities(self) -> BackendCapabilities:
        """Return the static capabilities of this backend."""
        ...
        
    def get_health(self) -> BackendHealth:
        """Return the dynamic runtime health of this backend."""
        ...

    def is_available(self) -> bool:
        """Convenience method for get_health().is_available."""
        ...

    def engine_name(self) -> str:
        """Human-readable backend identifier (e.g. ``'edge-tts'``)."""
        ...

    def close(self) -> None:
        """Release resources (COM handles, mixer, network sessions)."""
        ...
