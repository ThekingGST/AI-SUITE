from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from enum import IntEnum


class SpeechPriority(IntEnum):
    """Priority levels for the speech queue.

    Lower numeric value = higher priority.
    """

    EMERGENCY = 0   # System alerts, critical errors
    HIGH = 10       # Direct user responses
    NORMAL = 20     # Conversational AI responses
    LOW = 30        # Ambient notifications, status updates


@dataclass(order=True)
class SpeechJob:
    """A unit of work for the speech pipeline.

    Ordering is by (priority, sequence) so that ``PriorityQueue`` dequeues
    highest-priority jobs first and preserves FIFO within the same priority.
    """

    priority: int
    sequence: int
    text: str = field(compare=False, default="")
    job_id: str = field(compare=False, default_factory=lambda: uuid.uuid4().hex[:8])
    abort: threading.Event = field(compare=False, default_factory=threading.Event)

    # Control jobs (mutually exclusive with text)
    is_shutdown: bool = field(default=False, compare=False)
    switch_backend: str | None = field(default=None, compare=False)


class AbortController:
    """Cooperative cancellation primitive for the voice pipeline.

    A single ``AbortController`` is shared across all active components
    (LLM stream, SentenceBuffer, SpeechManager, TTSBackend, AudioOutput).
    Any component can check ``is_aborted`` and any component can trigger
    ``abort()`` to propagate cancellation through the entire chain.
    """

    def __init__(self) -> None:
        self._event = threading.Event()

    @property
    def is_aborted(self) -> bool:
        return self._event.is_set()

    def abort(self) -> None:
        """Signal all participants to stop."""
        self._event.set()

    def reset(self) -> None:
        """Clear the abort signal for reuse."""
        self._event.clear()

    def wait(self, timeout: float | None = None) -> bool:
        """Block until aborted or timeout expires.

        Returns True if the abort was signalled, False on timeout.
        """
        return self._event.wait(timeout=timeout)

    @property
    def event(self) -> threading.Event:
        """Direct access to the underlying Event for use in ``select``-style waits."""
        return self._event
