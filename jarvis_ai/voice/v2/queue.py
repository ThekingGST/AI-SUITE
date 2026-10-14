from __future__ import annotations

import queue
import threading
from typing import Iterator

from jarvis_ai.utils.logger import LOGGER
from jarvis_ai.voice.v2.types import SpeechJob, SpeechPriority


class PrioritySpeechQueue:
    """Thread-safe priority queue for speech jobs.

    Jobs are ordered by (priority, sequence).  Within the same priority,
    insertion order (FIFO) is preserved via an auto-incrementing sequence
    counter.

    Supports:
    - Priority-based dequeue (lowest priority number first)
    - Full drain (interrupt / cancel all pending)
    - Preemption (emergency job flushes lower-priority items)
    - Shutdown sentinel
    """

    def __init__(self) -> None:
        self._queue: queue.PriorityQueue[SpeechJob] = queue.PriorityQueue()
        self._sequence = 0
        self._sequence_lock = threading.Lock()

    def _next_seq(self) -> int:
        with self._sequence_lock:
            self._sequence += 1
            return self._sequence

    def put(self, text: str, priority: SpeechPriority = SpeechPriority.NORMAL,
            abort: threading.Event | None = None) -> SpeechJob:
        """Enqueue a speech job and return the created SpeechJob."""
        job = SpeechJob(
            priority=int(priority),
            sequence=self._next_seq(),
            text=text,
            abort=abort or threading.Event(),
        )
        self._queue.put(job)
        return job

    def put_control(self, *, shutdown: bool = False,
                    switch_backend: str | None = None) -> SpeechJob:
        """Enqueue a control job (shutdown or backend switch)."""
        job = SpeechJob(
            priority=int(SpeechPriority.EMERGENCY),
            sequence=self._next_seq(),
            is_shutdown=shutdown,
            switch_backend=switch_backend,
        )
        self._queue.put(job)
        return job

    def get(self, timeout: float = 0.2) -> SpeechJob | None:
        """Dequeue the highest-priority job, or None on timeout."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def drain(self) -> list[SpeechJob]:
        """Remove and return pending jobs, but preserve EMERGENCY jobs."""
        drained: list[SpeechJob] = []
        emergency_jobs: list[SpeechJob] = []
        while True:
            try:
                job = self._queue.get_nowait()
                if job.priority == SpeechPriority.EMERGENCY:
                    emergency_jobs.append(job)
                else:
                    drained.append(job)
            except queue.Empty:
                break
                
        # Put emergency jobs back
        for e_job in emergency_jobs:
            self._queue.put(e_job)
            
        return drained

    @property
    def depth(self) -> int:
        return self._queue.qsize()

    @property
    def empty(self) -> bool:
        return self._queue.empty()
