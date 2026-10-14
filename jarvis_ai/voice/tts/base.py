from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TTSEngine(Protocol):
    """Protocol that all TTS engines must implement.

    Each engine handles its own resource lifecycle (COM, network, audio).
    The Speaker worker thread calls these methods sequentially — no
    concurrent-call safety is required inside the engine itself.
    """

    def speak(self, text: str) -> None:
        """Synthesize and play *text* synchronously.

        Must block until playback completes so that the Speaker's
        ``_speaking`` flag accurately reflects audible output.

        Raises on any failure so the TTSManager can attempt failover.
        """
        ...

    def is_available(self) -> bool:
        """Return True when the engine is ready to accept speak() calls."""
        ...

    def engine_name(self) -> str:
        """Human-readable engine identifier (e.g. ``'elevenlabs'``)."""
        ...

    def close(self) -> None:
        """Release resources (COM handles, mixer, network sessions)."""
        ...
